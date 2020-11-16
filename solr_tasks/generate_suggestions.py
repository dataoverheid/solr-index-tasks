# encoding: utf-8


import dateutil.parser as date_parser
import logging
import os
import time
from solr_tasks.lib import utils
from solr_tasks.lib.solr import SolrCollection
from solr_tasks.lib.mapper import DatasetMapper


def get_uri_suggestions(search_core: SolrCollection,
                        uri_field: str,
                        suggester_field: str,
                        donl_type: str) -> list:
    """
    Get uri suggestions using donl_search_core and managed synonyms

    :param SolrCollection search_core: The search core to get suggestions from
    :param str uri_field: The URI field in search_core
    :param str suggester_field: The field in suggester_core
    :param str donl_type: The DONL type to get suggestions for
    :rtype: list of dict[str, any]
    :return: The list of organization suggestions
    """
    uris = {}
    entities = search_core.select_all_documents('sys_type:{0}'.format(donl_type),
                                                [uri_field, 'facet_community'],
                                                id_field='sys_id')

    for entity in entities:
        communities = []

        if 'facet_community' in entity:
            communities = entity['facet_community']

        if uri_field in entity:
            for uri in entity[uri_field]:
                if uri in uris:
                    uris[uri]['community'].update(communities)
                    uris[uri]['count'] += 1
                else:
                    uris[uri] = {'community': set(),
                                 'count': 1}
                    uris[uri]['community'].update(communities)

    languages = ['nl', 'en']
    suggestions = []

    for language in languages:
        synonyms = search_core.select_managed_synonyms('uri_{0}'.format(language))

        for uri in uris.keys():
            if uri in synonyms:
                for label in synonyms[uri]:
                    suggestions.append({
                        suggester_field: label,
                        'type': donl_type,
                        'payload': uri,
                        'weight': uris[uri]['count'],
                        'language': language,
                        'community': list(uris[uri]['community'])
                    })

    return suggestions


def get_organization_suggestions(search_core: SolrCollection,
                                 donl_type: str) -> list:
    """
    Get organization suggestions for a given type

    :param SolrCollection search_core: The search core to get suggestions from
    :param str donl_type: The DONL type to get suggestions for
    :rtype: list of dict[str, any]
    :return: The list of organization suggestions
    """
    return get_uri_suggestions(search_core, 'authority', 'organization',
                               donl_type)


def get_theme_suggestions(search_core: SolrCollection,
                          donl_type: str) -> list:
    """
    Get theme suggestions for a given type

    :param SolrCollection search_core: The search core to get suggestions from
    :param str donl_type: The DONL type to get suggestions for
    :rtype: list of dict[str, any]
    :return: The list of theme suggestions
    """
    return get_uri_suggestions(search_core, 'theme', 'theme', donl_type)


def get_dataset_title_suggestions(search_core: SolrCollection,
                                  mappings: dict) -> list:

    """
    Get title suggestions from donl_search

    :param SolrCollection search_core: The search core to get suggestions from
    :param dict mappings: The mapping from the search core to the suggester core
    for dataset titles
    """

    dataset_mapper = DatasetMapper(mappings)
    title_suggestions = []
    datasets = search_core.select_all_documents('sys_type:dataset',
                                                list(mappings.keys()),
                                                id_field='sys_id')

    for dataset in datasets:
        dataset = dataset_mapper.apply_map(dataset)
        dataset['weight'] = time.mktime(date_parser.parse(
            dataset['weight'][0]).timetuple()
        ) if 'weight' in dataset else 0

        dataset['language'] = ['nl', 'en']

        title_suggestions.append(dataset)

    logging.info(' new title suggestions: %d', len(title_suggestions))

    return title_suggestions


def main() -> None:
    utils.setup_logger(__file__)

    logging.info('generate_suggestions.py -- starting')

    suggest = SolrCollection(os.getenv('SOLR_COLLECTION_SUGGESTER'))
    search = SolrCollection(os.getenv('SOLR_COLLECTION_SEARCH'))

    logging.info('clearing suggestions')
    suggest.delete_documents('*:*', commit=False)

    title_suggestions = get_dataset_title_suggestions(
        search, utils.load_resource('dataset_title_suggestions_mappings')
    )
    organization_suggestions = get_organization_suggestions(search, 'dataset')
    theme_suggestions = get_theme_suggestions(search, 'dataset')

    logging.info('adding suggestions:')

    suggest.index_documents(title_suggestions, commit=False)
    logging.info(' titles:        %s', len(title_suggestions))

    suggest.index_documents(organization_suggestions, commit=False)
    logging.info(' organizations: %s', len(organization_suggestions))

    suggest.index_documents(theme_suggestions, commit=False)
    logging.info(' themes:        %s', len(theme_suggestions))

    logging.info('committing changes to index')
    suggest.index_documents([], commit=True)

    logging.info('building Solr suggester')
    suggest.build_suggestions('select')

    logging.info('generate_suggestions.py -- finished')


if '__main__' == __name__:
    main()
