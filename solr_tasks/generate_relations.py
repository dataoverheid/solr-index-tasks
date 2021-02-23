# encoding: utf-8


import logging
import os
from solr_tasks.lib import utils
from solr_tasks.lib.solr import SolrCollection


def update_reverse_relations(searcher: SolrCollection) -> None:
    """
    Ensures that the relations in the following example are mirrored:

        [{
          "sys_type": "A",
          "identifier": "Foo",
          "relation_B": "Bar"
        },
        {
         "sys_type": "B",
         "identifier": "Bar"
        }]

    Afterwards the relations are set as:

        [{
          "sys_type": "A",
          "identifier": "Foo",
          "relation_B": "Bar"
        },
        {
         "sys_type": "B",
         "identifier": "Bar",
         "relation_A": "Foo"
        }]

    This ensures that all relations are traversable regardless which object is
    used as a reference point.
    :param SolrCollection searcher: The searcher to find and update objects with
    """
    relations = utils.load_resource('relations')

    for source_object, source_data in relations.items():
        for relation, mapping in source_data.items():
            logging.info('updating reverse relations from %s to %s',
                         source_object, relation)

            field_entities = searcher.select_all_documents(
                'sys_type:{0}'.format(source_object),
                ['sys_id', mapping['match'], mapping['to']],
                id_field='sys_id'
            )
            field_entities = {entity[mapping['match']]: entity
                              for entity in field_entities}

            relation_entities = searcher.select_all_documents(
                'sys_type:{0}'.format(relation),
                [mapping['match'], mapping['from']],
                id_field='sys_id'
            )

            entities_to_relation_entities = {}

            for relation_entity in relation_entities:
                if mapping['from'] not in relation_entity:
                    continue

                for uri in relation_entity[mapping['from']]:
                    if uri in field_entities.keys():
                        if uri not in entities_to_relation_entities:
                            entities_to_relation_entities[uri] = []

                        entities_to_relation_entities[uri].append(
                            relation_entity[mapping['match']]
                        )

            logging.info(' found %s objects of type %s with relations to'
                         ' objects of type %s',
                         len(entities_to_relation_entities.keys()),
                         relation,
                         source_object)

            deletes = [{'sys_id': field_entity['sys_id'],
                        mapping['to']: {
                            'remove': field_entity[mapping['to']]
                        }} for field_entity in field_entities
                       if mapping['to'] in field_entity
                       and field_entity[mapping['match']] not in
                       entities_to_relation_entities.keys()]

            updates = [{
                'sys_id': field_entities[uri]['sys_id'],
                mapping['to']: {
                    'set': entities_to_relation_entities[uri]
                }
            } for uri in entities_to_relation_entities]

            searcher.index_documents(deletes, commit=False)
            searcher.index_documents(updates, commit=False)

            logging.info('results')
            logging.info(' deleted: %s', len(deletes))
            logging.info(' updated: %s', len(updates))


def update_relations(searcher: SolrCollection) -> None:
    has_relations = utils.load_resource('has_relations')
    updates = {}
    for relation_source, mapping in has_relations.items():
        logging.info('relations for %s', relation_source)

        sources = searcher.select_all_documents(
            fq='sys_type:{0}'.format(relation_source),
            id_field='sys_id'
        )
        rels = searcher.select_all_documents(
            fl=list(set(list(mapping.values()) + ['sys_uri', 'sys_type'])),
            fq='sys_type:{0}'.format(' OR sys_type:'.join(mapping.keys())),
            id_field='sys_id'
        )

        logging.info(' subjects:        %s', len(sources))
        logging.info(' relations:       %s', len(rels))

        [source.update({'related_to': []}) for source in sources]

        for source in sources:
            related_to = set()
            for mapping_target, mapping_source in mapping.items():
                if mapping_target in source['related_to']:
                    continue

                for relation in rels:
                    if mapping_target != relation['sys_type']:
                        continue

                    try:
                        if isinstance(relation[mapping_source], list):
                            if source['sys_uri'] in relation[mapping_source]:
                                related_to.add(mapping_target)
                        else:
                            if source['sys_uri'] == relation[mapping_source]:
                                related_to.add(mapping_target)
                    except KeyError:
                        continue

            if source['sys_id'] not in updates:
                updates[source['sys_id']] = set()

            for related_to_type in related_to:
                updates[source['sys_id']].add(related_to_type)

    logging.info('indexing relations')

    updates = [{
        'sys_id': sys_id,
        'related_to': {
            'set': list(update)
        }
    } for sys_id, update in updates.items()]

    searcher.index_documents(updates, commit=False)

    logging.info('results')
    logging.info(' indexed:         %s', len(updates))


def update_authority_kind(searcher: SolrCollection) -> None:
    organization_types = {organization['sys_uri']: organization['kind']
                     for organization in searcher.select_all_documents(
            'sys_type:organization', ['sys_uri', 'kind'], id_field='sys_id'
        ) if 'kind' in organization and 'sys_uri' in organization}

    objects_with_authority = searcher.select_all_documents(
        'authority:[* TO *]',
        ['sys_id, authority'],
        id_field='sys_id'
    )

    logging.info('Found {0} objects with a relation with an authority')

    updates = [{
        'sys_id': donl_object['sys_id'],
        'authority_kind': {
            'set': [organization_types[authority]
                    for authority in donl_object['authority']
                    if authority in organization_types]
        }
    } for donl_object in objects_with_authority]

    searcher.index_documents(updates, commit=False)

    logging.info('results')
    logging.info(' indexed:         %s', len(updates))


def main():
    utils.setup_logger(__file__)

    logging.info('generate_relations.py -- starting')

    collection = SolrCollection(os.getenv('SOLR_COLLECTION_SEARCH'))
    update_reverse_relations(collection)

    logging.info('committing index changes')
    collection.index_documents([], commit=True)

    update_relations(collection)
    update_authority_kind(collection)

    logging.info('committing index changes')
    collection.index_documents([], commit=True)

    logging.info('generate_relations.py -- finished')


if '__main__' == __name__:
    main()
