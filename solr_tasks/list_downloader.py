# encoding: utf-8


import json
import logging
import requests
import os
from solr_tasks.lib import utils


request_session = utils.setup_request_session()


def update_vocabulary(name: str,
                      local_resource: str,
                      online_resource: str) -> None:
    """
    Updates a given vocabulary based on the contents of the online resource.

    :param str name: The name of the vocabulary
    :param str local_resource: The local resource representing the vocabulary
                               (absolute path)
    :param str online_resource: The online version of the vocabulary
    :rtype: None
    """
    local_resource = os.path.abspath(local_resource)

    logging.info(name)
    logging.info(' > source %s', online_resource)
    logging.info(' > target %s', local_resource)

    try:
        response = request_session.get(online_resource)
        response.raise_for_status()
        resource = response.json()

        with open(local_resource, 'w', encoding='UTF-8') as fp:
            json.dump(resource, fp)

            logging.info(' > vocabulary updated')
    except requests.exceptions.RequestException as e:
        logging.error(e)


def update_taxonomy(name: str,
                    local_resource: str,
                    online_resource: str) -> None:
    """
    Updates a given taxonomy based on the contents of the online resource.

    :param str name: The name of the taxonomy
    :param str local_resource: The local file representing the taxonomy
                               (absolute path)
    :param str online_resource: The online version of the taxonomy
    :rtype: None
    """
    local_resource = os.path.abspath(local_resource)

    logging.info(name)
    logging.info(' > source %s', online_resource)
    logging.info(' > target %s', local_resource)

    try:
        response = request_session.get(online_resource)
        response.raise_for_status()
        resource = response.json()

        taxonomy_content = {taxonomy['field_identifier']: {
            'labels': {'nl-NL': taxonomy['label_nl'],
                       'en-US': taxonomy['label_en']}
        } for taxonomy in resource}

        with open(local_resource, 'w', encoding='UTF-8') as fp:
            json.dump(taxonomy_content, fp)

        logging.info(' > taxonomy updated')
    except requests.exceptions.RequestException as e:
        logging.error(e)


def update_vocabularies(vocabularies: dict) -> None:
    """
    Updates all the vocabularies defined in the given config dictionary under
    the 'vocabularies' key.

    :param dict[str, dict[str, str]] vocabularies: A list containing the
                                                   configuration data per
                                                   vocabulary
    :rtype: None
    """
    [update_vocabulary(vocabulary_name, os.path.join(os.getenv('VALUELIST_DIR'),
                                                     vocabulary['local']),
                       vocabulary['online'])
     for vocabulary_name, vocabulary in vocabularies.items()]


def update_taxonomies(taxonomies: dict) -> None:
    """
    Updates all the taxonomies defined in the given config dictionary under the
    'taxonomies' key.

    :param dict[str, dict[str, str]] taxonomies: A list containing the
                                                 configuration data per taxonomy
    :rtype: None
    """
    [update_taxonomy(taxonomy_name, os.path.join(os.getenv('VALUELIST_DIR'),
                                                 vocabulary['local']),
                     vocabulary['online'])
     for taxonomy_name, vocabulary in taxonomies.items()]


def main() -> None:
    utils.setup_logger(__file__)

    logging.info('list_downloader.py started')

    lists = utils.load_resource('lists')
    update_vocabularies(lists['vocabularies'])
    update_taxonomies(lists['taxonomies'])

    logging.info('list_downloader.py finished')


if '__main__' == __name__:
    main()
