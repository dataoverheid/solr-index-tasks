# encoding: utf-8


import argparse
import logging
import os
from solr_tasks.lib import utils
from solr_tasks.lib.solr import SolrCollection, solr_collections


def manage_stopwords(collection: SolrCollection, language_code: str) -> None:
    logging.info('managing stopwords_{0} resource'.format(language_code))

    language_map = {
        'nl': 'dutch',
        'en': 'english',
    }

    language = language_map[language_code] if language_code in language_map \
        else language_code

    current_stopwords = collection.select_managed_stopwords(language)

    logging.info('current stopwords:   %s', len(current_stopwords))

    stopwords = list(set(
        utils.load_resource('stopwords_{0}'.format(language_code))).
                        difference(current_stopwords))

    logging.info('words to add:        %s', len(stopwords))

    if len(stopwords) > 0:
        if collection.add_managed_stopwords(language, stopwords):
            logging.info('stopwords_{0} updated'.format(language_code))
        else:
            logging.error('failed to update stopwords_{0} resource'.
                          format(language_code))
    else:
        logging.info('no action required')


def manage_stopwords_nl(collection: SolrCollection) -> None:
    manage_stopwords(collection, 'nl')


def manage_stopwords_en(collection: SolrCollection) -> None:
    manage_stopwords(collection, 'en')


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


def manage_label_synonyms(collection: SolrCollection, language_code: str) -> None:
    logging.info('> managing label resource')

    current_label_synonyms = collection.select_managed_synonyms(
        'label_{0}'.format(language_code))

    logging.info(' current: %s synonyms', len(current_label_synonyms))

    label_synonyms = utils.load_resource('labels_{0}'.format(language_code))

    synonyms_to_add = {key: value
                       for key, value in label_synonyms.items()
                       if key not in current_label_synonyms.keys()}

    logging.info(' adding: %s synonyms', len(synonyms_to_add))

    if len(synonyms_to_add) > 0:
        collection.add_managed_synonyms(
            'label_{0}'.format(language_code), synonyms_to_add)


def manage_label_synonyms_nl(collection: SolrCollection) -> None:
    manage_label_synonyms(collection, 'nl')


def manage_label_synonyms_en(collection: SolrCollection) -> None:
    manage_label_synonyms(collection, 'en')


def main() -> None:
    resources = {'stopwords_nl': manage_stopwords_nl,
                 'stopwords_en': manage_stopwords_en,
                 'labels_nl': manage_label_synonyms_nl,
                 'labels_en': manage_label_synonyms_en,
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
