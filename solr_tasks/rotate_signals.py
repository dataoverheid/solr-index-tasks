# encoding: utf-8


import argparse
import logging
import os
from solr_tasks.lib import utils
from solr_tasks.lib.solr import SolrCollection


def main() -> None:
    utils.setup_logger(__file__)

    parser = argparse.ArgumentParser(description='Deletes old donl signals')
    parser.add_argument('--number_of_days', type=int, default=30,
                        help='Specify the number of days after which signals '
                             'are considered old')

    input_arguments = vars(parser.parse_args())

    logging.info('rotate_signals.py started')

    collection = SolrCollection(os.getenv('SOLR_COLLECTION_SIGNALS'))

    old_signals_query = 'search_timestamp:[* TO NOW-{0}DAYS]'.format(
        input_arguments['number_of_days']
    )

    logging.info('deleting {0} signals that are older than {1} days'.format(
        collection.document_count(old_signals_query),
        input_arguments['number_of_days']
    ))

    collection.delete_documents(old_signals_query)

    logging.info('rotate_signals.py finished')


if '__main__' == __name__:
    main()
