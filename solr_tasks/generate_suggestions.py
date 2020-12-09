# encoding: utf-8


import dateutil.parser as date_parser
import logging
import os
import time
from solr_tasks.lib import utils
from solr_tasks.lib.solr import SolrCollection
from solr_tasks.lib.mapper import DictMapper


def get_suggestions(search_core: SolrCollection,
                    in_context: str, doc_type: str,
                    mappings: dict) -> list:
    """
    Get suggestions of a given doc_type in a given context from the search core

    :param search_core: The search core to get suggestions from
    :param in_context: The context
    :param doc_type: The doc type
    :param mappings: The mappings of the given context
    :return: The list of suggestions
    """
    dict_mapper = DictMapper(mappings)
    doc_entities = search_core.select_all_documents(
        'sys_type:"{0}"'.format(doc_type),
        id_field='sys_id'
    )
    context_entities = search_core.select_all_documents(
        'sys_type:"{0}"'.format(in_context),
        id_field='sys_id'
    )

    counts = {}

    for doc_entity in doc_entities:
        for context_entity in context_entities:
            if doc_entity['sys_uri'] in context_entity['relation']:
                counts[doc_entity['sys_uri']] = \
                    counts[doc_entity['sys_uri']] + 1 \
                        if doc_entity['sys_uri'] in counts else 1

    suggestions = []

    for doc_entity in doc_entities:
        if doc_entity['sys_uri'] in counts:
            mapped_doc_entity = dict_mapper.apply_map(doc_entity)
            mapped_doc_entity.update({
                'weight': counts[doc_entity['sys_uri']],
                'in_context_of': in_context,
                'language': ['nl', 'en']
            })
            suggestions.append(mapped_doc_entity)

    return suggestions


def get_theme_suggestions(search_core: SolrCollection, in_context: str) -> list:
    """
    Get theme suggestions within a given context and use the number of
    occurrences of a theme within the context as weight

    :param search_core: The search core to get theme suggestions from
    :param in_context: The context
    :return: The list of theme suggestions
    """
    context_entities = search_core.select_all_documents(
        'sys_type:"{0}"'.format(in_context), ['theme'], id_field='sys_id'
    )

    counts = {}

    for context_entity in context_entities:
        if 'theme' not in context_entity:
            continue

        for theme in context_entity['theme']:
            if theme not in counts:
                counts[theme] = 0

            counts[theme] += 1

    synonyms_uri_nl = search_core.select_managed_synonyms('uri_nl')

    return [{
        'theme': synonyms_uri_nl[theme] if theme in synonyms_uri_nl else theme,
        'weight': count,
        'payload': theme,
        'type': 'theme',
        'language': ['nl', 'en'],
        'in_context_of': in_context
    } for theme, count in counts.items()]


def get_doc_suggestions(search_core: SolrCollection,
                        doc_type: str, mappings: dict) -> list:
    """
    Get suggestions of a given doc_type from the search core

    :param SolrCollection search_core: The search core to get suggestions from
    :param str doc_type: The document type to get suggestions for
    :param dict mappings: The mapping from the search core to the suggester core
    :return: The list of doc suggestions
    """
    dict_mapper = DictMapper(mappings)
    suggestions = []
    entities = search_core.select_all_documents(
        'sys_type:"{0}"'.format(doc_type),
        list(mappings.keys()),
        id_field='sys_id'
    )

    for entity in entities:
        entity = dict_mapper.apply_map(entity)

        weight = time.mktime(date_parser.parse(entity['weight'][0])
                             .timetuple()) if 'weight' in entity else 0
        entity['weight'] = weight
        entity['language'] = ['nl', 'en']

        suggestions.append(entity)

    return suggestions


def main() -> None:
    utils.setup_logger(__file__)

    logging.info('generate_suggestions.py -- starting')

    suggest = SolrCollection(os.getenv('SOLR_COLLECTION_SUGGESTER'))
    search = SolrCollection(os.getenv('SOLR_COLLECTION_SEARCH'))

    logging.info('clearing suggestions')
    suggest.delete_documents('*:*', commit=False)

    suggestion_types = utils.load_resource('suggestions')
    doc_suggestions = {doc_type: get_doc_suggestions(search, doc_type,
                                                     config['mapping'])
                       for doc_type, config in suggestion_types.items()}

    logging.info('adding title suggestions:')

    for doc_type, doc_type_suggestions in doc_suggestions.items():
        suggest.index_documents(doc_type_suggestions, commit=False)
        logging.info(' titles: %s of type %s',
                     len(doc_type_suggestions), doc_type)

    context_suggestions = {
        doc_type: {
            relation: get_suggestions(search, doc_type, relation,
                                      suggestion_types[relation]['mapping'])
        } for doc_type, config in suggestion_types.items()
    for relation in config['relations']}

    logging.info('adding context suggestions:')

    for doc_type, relations in context_suggestions.items():
        for relation, suggestions in relations.items():
            suggest.index_documents(suggestions, commit=False)
            logging.info(' titles: %s of type %s in context of %s',
                         len(suggestions), relation, doc_type)

    logging.info('adding theme suggestions:')
    theme_suggestions = get_theme_suggestions(search, 'dataset')
    suggest.index_documents(theme_suggestions, commit=False)
    logging.info(' themes: %s in context of %s',
                 len(theme_suggestions), 'dataset')

    logging.info('committing changes to index')
    suggest.index_documents([], commit=True)

    logging.info('building Solr suggester')
    suggest.build_suggestions('build_suggest')

    logging.info('generate_suggestions.py -- finished')


if '__main__' == __name__:
    main()
