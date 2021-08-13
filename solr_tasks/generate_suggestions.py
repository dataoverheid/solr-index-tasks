# encoding: utf-8


import logging
import os
from solr_tasks.lib import utils
from solr_tasks.lib.solr import SolrCollection
from solr_tasks.lib.mapper import DictMapper


def get_suggestions(search_core: SolrCollection,
                    in_context: str, doc_type: str,
                    mappings: dict, communities: dict) -> list:
    """
    Get suggestions of a given doc_type in a given context from the search core

    :param search_core: The search core to get suggestions from
    :param in_context: The context
    :param doc_type: The doc type
    :param mappings: The mappings of the given context
    :param dict communities: A dictionary with community URIs as keys and
    community names as value
    :return: The list of suggestions
    """

    # For context suggestions search for payload mapping and set it to
    # sys_uri => payload
    delete_mappings = [key for key, value in mappings.items()
                       if 'payload' in value]

    for mapping in delete_mappings:
        del mappings[mapping]

    mappings['sys_uri'] = ['payload']

    dict_mapper = DictMapper(mappings)
    doc_entities = search_core.select_all_documents(
        'sys_type:"{0}" AND sys_uri:[* TO *]'.format(doc_type),
        id_field='sys_id'
    )
    context_entities = search_core.select_all_documents(
        'sys_type:"{0}" AND relation:[* TO *]'.format(in_context),
        ['relation'],
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
        entity = dict_mapper.apply_map(doc_entity)

        if 'relation_community' in entity:
            names = []
            for community_uri in entity['relation_community']:
                if community_uri in communities:
                    names.append(communities[community_uri])
            entity['relation_community'] = names

        if doc_entity['sys_uri'] not in counts:
            continue
        
        entity.update({
            'weight': counts[doc_entity['sys_uri']]
            if doc_entity['sys_uri'] in counts else 0,
            'in_context_of': in_context,
            'language': ['nl', 'en'],
            'type': [suggestion_type + '_filter'
                     for suggestion_type in entity['type']]
            if 'type' in entity else ['filter']
        })
        suggestions.append(entity)

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


def get_doc_suggestions(search_core: SolrCollection, doc_type: str,
                        mappings: dict, relation_counts: dict,
                        communities: dict, fq: str = None) -> list:
    """
    Get suggestions of a given doc_type from the search core

    :param SolrCollection search_core: The search core to get suggestions from
    :param str doc_type: The document type to get suggestions for
    :param dict mappings: The mapping from the search core to the suggester core
    :param dict relation_counts: A dictionary of the relation facet field
    :param dict communities: A dictionary with community URIs as keys and
    community names as value
    :param str fq: An optional string used for filtering documents for which
    suggestions are returned
    :return: The list of doc suggestions
    """
    dict_mapper = DictMapper(mappings)
    suggestions = []

    filter_all_docs = 'sys_type:"{0}"'.format(doc_type)

    if fq is not None:
        filter_all_docs += ' AND ' + fq

    entities = search_core.select_all_documents(
        filter_all_docs,
        list(mappings.keys()) + ['sys_uri'],
        id_field='sys_id'
    )

    for entity in entities:
        sys_uri = entity['sys_uri']

        if sys_uri not in relation_counts:
            continue

        entity = dict_mapper.apply_map(entity)

        if 'relation_community' in entity:
            names = []
            for community_uri in entity['relation_community']:
                if community_uri in communities:
                    names.append(communities[community_uri])
            entity['relation_community'] = names

        entity['weight'] = relation_counts[sys_uri]
        entity['language'] = ['nl', 'en']
        entity['in_context_of'] = 'self'

        suggestions.append(entity)

    return suggestions


def main() -> None:
    utils.setup_logger(__file__)

    logging.info('generate_suggestions.py -- starting')

    suggest = SolrCollection(os.getenv('SOLR_COLLECTION_SUGGESTER'))
    search = SolrCollection(os.getenv('SOLR_COLLECTION_SEARCH'))

    logging.info('clearing suggestions')
    suggest.delete_documents('*:*', commit=False)

    relation_counts = search.get_facet_counts('relation')

    community_uri_to_name = search.select_all_documents(
        fq='sys_type:community',
        fl=['sys_uri', 'sys_name'],
        id_field='sys_id'
    )

    community_uri_to_name = {community['sys_uri']: community['sys_name']
                             for community in community_uri_to_name}

    suggestion_types = utils.load_resource('suggestions')
    doc_suggestions = {doc_type: get_doc_suggestions(
        search, doc_type, config['mapping'], relation_counts,
        community_uri_to_name)
        for doc_type, config in suggestion_types.items()}

    logging.info('adding title suggestions:')

    for doc_type, doc_type_suggestions in doc_suggestions.items():
        suggest.index_documents(doc_type_suggestions, commit=False)
        logging.info(' titles: %s of type %s',
                     len(doc_type_suggestions), doc_type)

    user_defined_synonym_suggestions = {doc_type: get_doc_suggestions(
        search, doc_type, config['user_defined_synonyms'], relation_counts,
        community_uri_to_name, 'user_defined_synonyms:[* TO *]')
        for doc_type, config in suggestion_types.items()
        if 'user_defined_synonyms' in config}

    logging.info('adding user defined synonym suggestions:')

    for doc_type, doc_type_suggestions in user_defined_synonym_suggestions.items():
        suggest.index_documents(doc_type_suggestions, commit=False)
        logging.info(' user defined synonyms: %s of type %s',
                     len(doc_type_suggestions), doc_type)

    context_suggestions = {
        doc_type: {
            relation: get_suggestions(search, doc_type, relation,
                                      suggestion_types[relation]['mapping'],
                                      community_uri_to_name)
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
