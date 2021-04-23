# encoding: utf-8

from solr_tasks.lib import utils
import logging
from solr_tasks.lib.solr import SolrCollection
import os


def get_object_uri_to_source_mapping(search_collection: SolrCollection,
                                     object_type: str,
                                     source_field: str) -> dict:
    objects = search_collection.select_all_documents(
        'sys_type:{0} AND {1}:[* TO *]'.format(
            object_type, source_field),
        ['sys_uri', source_field],
        id_field='sys_id'
    )

    return {
        single_object['sys_uri']: single_object[source_field]
        for single_object in objects
    }


def get_relation_updates(relation: dict, mapping: dict,
                         object_uri_to_source_mapping: dict,
                         relation_objects: list) -> list:
    relation_updates = [{
        'sys_id': relation_object['sys_id'],
        mapping['to']: {
            'set': object_uri_to_source_mapping[
                relation_object[relation['match']][0]
            ]
        }
    }
        for relation_object in relation_objects
        if relation_object[relation['match']][0]
        in object_uri_to_source_mapping
    ]

    logging.info(' Preparing to index {0} {1} updates for {2}'.format(
        len(relation_updates), mapping['to'], relation['type']
    ))

    return relation_updates


def main():
    utils.setup_logger(__file__)

    logging.info('update_relations_with_object_property.py -- starting')

    search_collection = SolrCollection(os.getenv('SOLR_COLLECTION_SEARCH'))
    property_to_relation = utils.load_resource('property_to_relation')

    updates = []
    for object_type, mapping in property_to_relation.items():
        object_uri_to_source_mapping = get_object_uri_to_source_mapping(
            search_collection, object_type, mapping['source'])

        for relation in mapping['relations']:
            relation_objects = search_collection.select_all_documents(
                'sys_type:{0} AND {1}:[* TO *]'.format(
                    relation['type'], relation['match']),
                ['sys_uri', relation['match']],
                id_field='sys_id'
            )

            updates += get_relation_updates(relation, mapping,
                                            object_uri_to_source_mapping,
                                            relation_objects)

    search_collection.index_documents(updates)

    logging.info('update_relations_with_object_property.py -- finished')


if '__main__' == __name__:
    main()
