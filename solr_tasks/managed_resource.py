# encoding: utf-8


import argparse
import logging
import os
from solr_tasks.lib import utils
from solr_tasks.lib.solr import SolrCollection, solr_collections


def manage_stopwords_nl(collection: SolrCollection) -> None:
    logging.info('managing stopwords_nl resource')

    current_stopwords_nl = collection.select_managed_stopwords('dutch')

    logging.info('current stopwords:   %s', len(current_stopwords_nl))

    stopwords_nl = list(set(utils.load_resource('stopwords_nl')).difference(
        current_stopwords_nl
    ))

    logging.info('words to add:        %s', len(stopwords_nl))

    if len(stopwords_nl) > 0:
        if collection.add_managed_stopwords('dutch', stopwords_nl):
            logging.info('stopwords_nl updated')
        else:
            logging.error('failed to update stopwords_nl resource')
    else:
        logging.info('no action required')


def manage_uri_synonyms(collection: SolrCollection) -> None:
    logging.info('> managing uri_synonyms resources')

    uri_synonyms = {'uri_nl': {},
                    'uri_en': {}}
    legacy_license_files = ['ckan_license.json',
                            'overheid_license.json']

    for valuelist in os.listdir(os.getenv('VALUELIST_DIR')):
        if not valuelist.endswith('.json'):
            continue

        if valuelist in legacy_license_files:
            continue

        filepath = os.path.join(os.getenv('VALUELIST_DIR'), valuelist)

        for uri, properties in utils.load_json_file(filepath).items():
            uri_synonyms['uri_nl'][uri] = properties['labels']['nl-NL']
            uri_synonyms['uri_en'][uri] = properties['labels']['en-US']

    for lang in uri_synonyms.keys():
        logging.info('managed resource: synonyms|%s', lang)

        current_uri_synonyms = collection.select_managed_synonyms(lang)

        if not current_uri_synonyms:
            current_uri_synonyms = {}

        logging.info(' current: %s synonyms', len(current_uri_synonyms))

        synonyms_to_add = {key: value
                           for key, value in uri_synonyms[lang].items()
                           if key not in current_uri_synonyms.keys()}

        logging.info(' adding: %s synonyms', len(synonyms_to_add))

        if len(synonyms_to_add) > 0:
            collection.add_managed_synonyms(lang, synonyms_to_add)


def manage_hierarchy_theme(collection: SolrCollection) -> None:
    logging.info('> managing hierarchy_theme resources')

    for hierarchy_item in ['hierarchy_theme', 'hierarchy_theme_query']:
        logging.info('managed resource: synonyms|{0}'.format(hierarchy_item))

        hierarchy_data = utils.load_resource(hierarchy_item)
        current_data = collection.select_managed_synonyms(hierarchy_item)

        if not current_data:
            current_data = {}

        logging.info(' current: %s synonyms', len(current_data))

        data_to_add = {key: value for key, value in hierarchy_data.items()
                       if key not in current_data.keys()}

        logging.info(' adding: %s synonyms', len(data_to_add))

        if len(data_to_add) > 0:
            collection.add_managed_synonyms(hierarchy_item, data_to_add)


def main() -> None:
    resources = {'stopwords_nl': manage_stopwords_nl,
                 'uri_synonyms': manage_uri_synonyms,
                 'hierarchy_theme': manage_hierarchy_theme}

    utils.setup_logger(__file__)

    logging.info('managed_resource.py -- starting')

    parser = argparse.ArgumentParser(description='Maintain the Solr managed '
                                                 'resources.')
    parser.add_argument('--collection', type=str, required=True,
                        choices=solr_collections(),
                        help='Which collection to manage the resource for')
    parser.add_argument('--resource', type=str, choices=resources.keys(),
                        help='Which resource to manage', required=True)
    parser.add_argument('--reload', type=bool, nargs='?', default=False,
                        const=True, help='To reload the collection afterwards')

    input_arguments = vars(parser.parse_args())
    collection = SolrCollection(input_arguments['collection'])

    resources.get(input_arguments['resource'])(collection)

    if input_arguments['reload']:
        logging.info('reloading Solr collection')
        collection.reload()

    logging.info('managed_resource.py -- finished')


if '__main__' == __name__:
    main()
