# encoding: utf-8


import datetime
import logging
import os
from solr_tasks.lib import utils
from solr_tasks.lib.solr import SolrCollection
import copy


def reduce_date_field_to_hours(documents: list, date_field: str) -> list:
    """
    Reduces a date field to the hour

    :param documents: The list of documents
    :param date_field: The date field to reduce

    :return: The list of documents with the updated date field
    """
    for document in documents:
        if date_field not in document:
            continue

        date_time = datetime.datetime.strptime(
            document[date_field],
            '%Y-%m-%dT%H:%M:%SZ'
        )

        document[date_field] = date_time.hour

    return documents


def preprocess_filters(documents: list) -> list:
    """
    Preprocesses a specific format of filters
    Each clause (split by AND) of a filter becomes a separate filter
    Also include the combined set of filters (combined with AND)

    :param documents: The list of documents with filters

    :return: The updated list of documents
    """
    for document in documents:
        if 'filters' not in document:
            continue

        filters = []
        for value in document['filters']:
            clauses = value.split(' AND ')
            filters += clauses

            if len(clauses) > 1:
                filters.append(value)

        if len(document['filters']) > 1:
            filters.append(' AND '.join(document['filters']))

        document['filters'] = filters

    return documents


def expand_mv_fields(documents: list, group_field: str) -> list:
    """
    Expand multivalued fields to separate documents

    :param documents: The list of documents
    :param group_field: The field that may contain a list to expand

    :return: The expanded list of documents
    """
    new_documents = []
    for document in documents:
        if not isinstance(document[group_field], list):
            new_documents.append(document)
            continue

        for val in document[group_field]:
            document_copy = copy.deepcopy(document)
            document_copy[group_field] = val
            new_documents.append(document_copy)

    return new_documents


def aggregate_fields(documents: list, group_fields: list) -> dict:
    """
    Aggregates documents based on a list of group fields

    :param documents: The list of documents to aggregate
    :param group_fields: The list of group fields

    :return: The aggregated counts
    """
    counts = {}

    for group_field in group_fields:
        documents = expand_mv_fields(documents, group_field)

    for document in documents:
        groups_key = tuple([document[group_field]
                            if group_field in document else None
                            for group_field in group_fields])

        if groups_key in counts:
            counts[groups_key] += 1
        else:
            counts[groups_key] = 1

    return counts


def is_identical_aggregation(aggr_x: dict, aggr_y: dict) -> bool:
    """
    Checks whether two aggregated signals are identical
    Both signals are checked on and therefore *must* contain the following keys:
    - type
    - subject
    - handler

    :param aggr_x: Aggregation x
    :param aggr_y: Aggregation y

    :return: Returns a boolean indicating whether x and y are identical
    """
    if not aggr_x['type'] == aggr_y['type']:
        return False

    if not aggr_x['subject'] == aggr_y['subject']:
        return False

    if not aggr_x['handler'] == aggr_y['handler']:
        return False

    return True


def get_aggregations(counts: dict, aggregated_signals: list, signal_type: str,
                     df: float = 0.5) -> list:
    """
    Get aggregation documents to send to Solr
    This also takes already existing aggregations into account with a given
    degradation factor

    :param counts: The dict of counts.
    Note that this function expects the keys to be tuples:
    (subject, handler)

    :param aggregated_signals: The list of existing aggregated signals
    :param signal_type: The type of signal
    :param df: The degradation factor of existing aggregated signals

    :return: The list of aggregations to index
    """
    query_aggregations = []
    for groups_key, count in counts.items():
        subject, handler = groups_key

        new_signal = {
            'subject': subject,
            'handler': handler,
            'type': signal_type,
            'count': count
        }

        for aggregated_signal in aggregated_signals:
            if is_identical_aggregation(aggregated_signal, new_signal):
                new_signal = {
                    'id': aggregated_signal['id'],
                    'count': {
                        'set': int(df * aggregated_signal['count']) + count
                    }
                }

                break

        query_aggregations.append(new_signal)

    return query_aggregations


def main() -> None:
    utils.setup_logger(__file__)

    logging.info('aggregate_signals.py started')

    signal_collection = SolrCollection(os.getenv('SOLR_COLLECTION_SIGNALS'))
    signal_aggregated_collection = SolrCollection(
        os.getenv('SOLR_COLLECTION_SIGNALS_AGGREGATED')
    )

    signals = signal_collection.select_all_documents()
    aggregated_signals = signal_aggregated_collection.select_all_documents()

    signal_aggregated_collection.index_documents(get_aggregations(
        aggregate_fields(signals, ['query', 'handler']),
        aggregated_signals,
        'query'
    ))

    signal_aggregated_collection.index_documents(get_aggregations(
        aggregate_fields(
            reduce_date_field_to_hours(signals, 'search_timestamp'),
            ['search_timestamp', 'handler']
        ),
        aggregated_signals,
        'search_timestamp'
    ))

    signal_aggregated_collection.index_documents(get_aggregations(
        aggregate_fields(
            preprocess_filters(signals),
            ['filters', 'handler']
        ),
        aggregated_signals,
        'filters'
    ))

    signal_collection.delete_documents('*:*')

    logging.info('aggregate_signals.py finished')


if '__main__' == __name__:
    main()
