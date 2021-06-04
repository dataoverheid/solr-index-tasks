# encoding: utf-8


import argparse
import logging
import os
import dateutil.parser as date_parser
from solr_tasks.lib import utils
from solr_tasks.lib.mapper import DictMapper
from solr_tasks.lib.solr import SolrCollection
import json


def get_dataschema_fields(resource_descriptions: list) -> dict:
    dataschema_fields = {
        'dataschema_name': [],
        'dataschema_code': [],
        'dataschema_type': [],
        'dataschema_description': [],
    }

    for description in resource_descriptions:
        try:
            dataschema_json = json.loads(description)

            for row in dataschema_json:
                dataschema_fields['dataschema_name'].append(row['name'])
                dataschema_fields['dataschema_code'].append(row['code'])
                dataschema_fields['dataschema_type'].append(row['type'])
                dataschema_fields['dataschema_description'].append(
                    row['description'])

            break
        except ValueError:
            continue

    return dataschema_fields


def determine_dataset_mutations(solr_dataset: SolrCollection,
                                solr_search: SolrCollection,
                                mappings: dict,
                                delta: bool = True) -> dict:
    ckan_datasets = solr_dataset.select_all_documents(fq='private:false',
                                                      fl=list(mappings.keys()),
                                                      id_field='index_id')
    logging.info('ckan datasets: %s', len(ckan_datasets))

    solr_datasets = solr_search.select_all_documents(fq='sys_type:dataset',
                                                     id_field='sys_id')
    logging.info('solr datasets: %s', len(solr_datasets))

    mapper = DictMapper(mappings, {'sys_type': 'dataset'})
    ckan_datasets = {dataset['id']: mapper.apply_map(dataset)
                     for dataset in ckan_datasets}

    # Get dataschema fields from resource description
    for dataset_id in ckan_datasets.keys():
        try:
            ckan_datasets[dataset_id].update(
                get_dataschema_fields(
                    ckan_datasets[dataset_id].pop('res_description')
                )
            )
        except KeyError:
            continue

    solr_datasets = {dataset['sys_id']: dataset for dataset in solr_datasets}

    logging.info('datasets mapped to search schema')

    return {
        'create': {dataset_key: dataset
                   for dataset_key, dataset in ckan_datasets.items()
                   if dataset_key not in solr_datasets.keys()},
        'update': determine_datasets_to_update(delta, mappings, ckan_datasets,
                                               solr_datasets),
        'delete': {dataset_key: dataset
                   for dataset_key, dataset in solr_datasets.items()
                   if dataset_key not in ckan_datasets.keys()}
    }


def determine_datasets_to_update(delta: bool,
                                 mappings: dict,
                                 ckan_datasets: dict,
                                 solr_datasets: dict) -> dict:
    datasets_to_update = {}

    for key, dataset in solr_datasets.items():
        if key not in ckan_datasets.keys():
            continue

        if key in datasets_to_update.keys():
            continue

        ckan_dataset = ckan_datasets[key]

        for solr_key, values in dataset.items():
            if not solr_key.startswith('relation_'):
                continue

            if solr_key not in ckan_dataset:
                ckan_dataset[solr_key] = values

        if delta is False:
            datasets_to_update[key] = ckan_dataset
            continue

        date_key = mappings['metadata_modified'][0]

        if date_key not in dataset.keys():
            datasets_to_update[key] = ckan_dataset
            continue

        if date_key not in ckan_dataset.keys():
            datasets_to_update[key] = ckan_dataset
            continue

        ckan_date = date_parser.parse(ckan_dataset[date_key][0])
        solr_date = date_parser.parse(dataset[date_key])

        if ckan_date > solr_date:
            datasets_to_update[key] = ckan_dataset

    return datasets_to_update


def create_update_dict(dataset: dict) -> dict:
    update = {field: {'set': dataset[field]}
              for field in dataset if not field == 'sys_id'}
    update['sys_id'] = dataset['sys_id']

    return update


def update_dataset_with_communities(dataset: dict,
                                    community_rules: dict) -> dict:
    """
    Updates a dataset with their communities
    based on the rules defined in the communities config file

    :param dataset: The dataset to assign communities to
    :param community_rules: The rules of when to assign a community to a dataset
    :return: The updated dataset with communities
    """
    if 'relation_community' not in dataset:
        dataset['relation_community'] = []

    communities = {uri: config for uri, config in
                   community_rules.items() if uri in
                   utils.load_json_file(os.path.join(os.getenv('VALUELIST_DIR'),
                                                     'donl_communities.json'))}

    dataset_communities = set()

    for uri, config in communities.items():
        for field in config['rules']:
            if field not in dataset:
                continue

            field_value = dataset[field] \
                if type(dataset[field]) is list else [dataset[field]]

            if any([v in config['rules'][field] for v in field_value]):
                dataset_communities.add(uri)

    logging.info('Found {0} communities for dataset {1}'.format(
        len(dataset_communities), dataset['sys_uri'][0])
    )

    dataset['relation_community'] = list(dataset_communities)

    return dataset


def build_group_community_rules(solr_search: SolrCollection,
                                community_rules: dict) -> dict:
    """
    Builds group community rules based on group index

    :param solr_search: The solr search collection
    :param community_rules: The existing community
    rules to update with group rules

    :return: An updated set of community rules
    """
    groups = solr_search.select_all_documents(
        'relation_community:[* TO *] AND sys_type:group',
        ['sys_uri', 'relation_community'], id_field='sys_id'
    )

    for group in groups:
        for community in group['relation_community']:
            if community not in community_rules:
                community_rules[community] = {'rules': {}}

            if 'relation_group' not in community_rules[community]['rules']:
                community_rules[community]['rules']['relation_group'] = []

            community_rules[community]['rules']['relation_group'].append(
                group['sys_uri']
            )

    return community_rules


def main() -> None:
    utils.setup_logger(__file__)

    parser = argparse.ArgumentParser(description='Synchronize the donl_dataset '
                                                 'and donl_search collections')
    parser.add_argument('--delta', type=bool, nargs='?', const=True,
                        default=False, help='Only synchronize recent changes')

    input_arguments = vars(parser.parse_args())

    logging.info('synchronize_collections.py -- starting')
    logging.info(' > delta index' if input_arguments['delta']
                 else ' > full index')

    dataset_collection = SolrCollection(os.getenv('SOLR_COLLECTION_DATASET'))
    search_collection = SolrCollection(os.getenv('SOLR_COLLECTION_SEARCH'))

    mutations = determine_dataset_mutations(dataset_collection,
                                            search_collection,
                                            utils.load_resource('mappings'),
                                            bool(input_arguments['delta']))

    logging.info('analysis:')
    logging.info(' create: %s', len(mutations['create']))
    logging.info(' update: %s', len(mutations['update']))
    logging.info(' delete: %s', len(mutations['delete']))

    logging.info('index results:')

    logging.info('building group community rules')

    community_rules = build_group_community_rules(
        search_collection, utils.load_resource('communities')
    )

    datasets_to_create = [
        update_dataset_with_communities(dataset, community_rules)
        for dataset in list(mutations['create'].values())
    ]

    search_collection.index_documents(datasets_to_create, commit=False)
    logging.info(' created: %s', len(datasets_to_create))

    datasets_to_update = [
        create_update_dict(
            update_dataset_with_communities(dataset, community_rules)
        )
        for dataset in list(mutations['update'].values())
    ]

    search_collection.index_documents(datasets_to_update, commit=False)
    logging.info(' updated: %s', len(datasets_to_update))

    delete_query = ' OR '.join(['sys_id:"{0}"'.format(sys_id)
                                for sys_id in list(mutations['delete'].keys())])
    if delete_query:
        search_collection.delete_documents(delete_query, commit=False)

    logging.info(' deleted: %s', len(mutations['delete']))

    logging.info('committing index changes')
    search_collection.index_documents([], commit=True)

    logging.info('building spellcheck')
    search_collection.build_spellcheck('select')

    logging.info('synchronize_collections.py -- finished')


if '__main__' == __name__:
    main()
