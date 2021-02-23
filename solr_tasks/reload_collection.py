# encoding: utf-8


import argparse
import logging
import solr_tasks.lib.utils as utils
from solr_tasks.lib.solr import SolrCollection, solr_collections


def main() -> None:
    utils.setup_logger(__file__)

    parser = argparse.ArgumentParser(description='Reloads a Solr collection')
    parser.add_argument('--collection', type=str, required=True,
                        choices=solr_collections(), help='Which collection to '
                                                         'reload')

    input_arguments = vars(parser.parse_args())

    logging.info('reload_collection.py -- starting')
    logging.info(' > collection: %s', input_arguments['collection'])

    collection = SolrCollection(input_arguments['collection'])
    collection.reload()

    logging.info('reload_collection.py -- finished')


if '__main__' == __name__:
    main()
