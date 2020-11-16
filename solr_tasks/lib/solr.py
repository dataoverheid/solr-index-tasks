# encoding: utf-8


import json
import logging
import os
from typing import Union
from solr_tasks.lib.utils import setup_request_session
import requests


def solr_collections() -> list:
    """
    Returns a list of collection names. This list is based on the following
    environment variables:

    - `SOLR_COLLECTION_DATASET`
    - `SOLR_COLLECTION_SEARCH`
    - `SOLR_COLLECTION_SUGGESTER`
    - `SOLR_COLLECTION_SIGNALS`
    """
    collections = ['SOLR_COLLECTION_DATASET',
                   'SOLR_COLLECTION_SEARCH',
                   'SOLR_COLLECTION_SUGGESTER',
                   'SOLR_COLLECTION_SIGNALS']

    return [os.getenv(collection) for collection in collections]


def solr_host() -> str:
    """
    Returns the Solr host to use, this information is based on the `SOLR_HOST`
    environment variable.
    """
    return os.getenv('SOLR_HOST')


def solr_auth() -> tuple:
    """
    Returns the Solr BasicAuth credentials to use, this information is based on
    the following environment variables:

    - `SOLR_USERNAME`
    - `SOLR_PASSWORD`
    """
    return os.getenv('SOLR_USERNAME'), os.getenv('SOLR_PASSWORD')


class SolrCollection:
    def __init__(self, collection: str):
        """
        Initialize a SolrCollection instance.

        :param str collection: The name of the Solr collection
        :rtype: SolrCollection
        """
        self.solr_host = solr_host()
        self.collection = collection
        self.request_session = setup_request_session()
        self.request_session.auth = solr_auth()

    def document_count(self,
                       selector: str = '*:*') -> Union[int, None]:
        """
        Retrieve the total amount of documents that match the given selector.

        :param str selector: The 'q' parameter of a Solr query
        :rtype: int|None
        :return: The amount of documents that match the query, or None if the
                 request failed
        """
        return self.select_documents({
            'omitHeader': True,
            'wt': 'json',
            'q': selector,
            'rows': 0,
            'facet': False
        })['response']['numFound']

    def select_documents(self,
                         query: dict,
                         handler: str = 'select') -> Union[dict, None]:
        """
        Select and return documents from the Solr index that match the given
        query.

        :param dict[str, Any] query: The Solr query to perform to identify the
                                     documents to select
        :param str handler: The Solr requestHandler to use
        :rtype: dict[str, Any]|None
        :return: The response as a JSON dictionary, or None if the request
                 failed
        """
        response = self._execute_request(self._create_collection_request(
            handler, {'params': query})
        )

        if not response:
            return None

        return json.loads(response)

    def select_all_documents(self,
                             fq: str = None,
                             fl: list = None,
                             documents_per_request: int = 500,
                             id_field: str = 'id') -> list:
        """
        Selects all the documents from the Solr collection and returns them as a
        JSON object. Uses a Solr cursor to iterate over the entire index.

        :param str fq: The filter query to apply
        :param list of str fl: The fields to select per document, defaults to
                               '*'
        :param int documents_per_request: The amount of documents to retrieve
                                          per request
        :param str id_field: The ID field of the collection to sort on
        :rtype: list of dict[str, Any]
        :return: The complete list of documents selected from the Solr
                 collection
        """
        selected_documents = []
        got_all_documents = False
        cursor = '*'

        if fl and id_field not in fl:
            fl.append(id_field)

        while not got_all_documents:
            query = {k: v for k, v in {
                'q': '*:*',
                'fq': fq,
                'fl': '*' if not fl else ','.join(fl),
                'rows': documents_per_request,
                'sort': '{0} asc'.format(id_field),
                'cursorMark': cursor,
                'omitHeader': 'true',
                'wt': 'json'
            }.items() if v is not None}

            results = self.select_documents(query)
            new_cursor = results['nextCursorMark']
            documents = results['response']['docs']

            logging.debug('found %s documents for cursor %s, next cursor: %s',
                          str(len(documents)), cursor, new_cursor)

            if len(documents) > 0:
                selected_documents.append(documents)

            if cursor == new_cursor:
                got_all_documents = True

            if len(documents) < documents_per_request:
                got_all_documents = True

            cursor = new_cursor

        return [document for batch in selected_documents for document in batch]

    def index_documents(self,
                        documents: list,
                        commit: bool = True,
                        batch_size: int = 200) -> bool:
        """
        Add the given documents to the index of the Solr collection.

        :param list of dict[str, Any] documents: The list of dictionaries that
                                                 represent the documents to
                                                 index
        :param bool commit: Whether or not to commit the changes made to the
                            Solr collection to the index
        :param int batch_size: The amount of documents to send to Solr per
                               batch, defaults to 200
        :rtype: bool
        :return: Whether or not the documents were added to the index
        """
        batches = [documents[i:i+batch_size]
                   for i in range(0, len(documents), batch_size)]

        results = [self._execute_request(self._create_collection_request(
            'update', batch)
        ) for batch in batches]

        if commit:
            self._execute_request(self._create_collection_request(
                'update?commit=true')
            )

        return all(results)

    def delete_documents(self,
                         query: str,
                         commit: bool = True) -> bool:
        """
        Delete all the documents from the Solr collection's index that match the
        given query.

        :param str query: The Solr query to identify the documents to delete
        :param bool commit: Whether or not to write the changes to the Solr
                            index
        :rtype: bool
        :return: Whether or not the documents that match the query were deleted
                 from the Solr collection
        """
        return self._execute_request(self._create_collection_request(
            'update{0}'.format('?commit=true' if commit else ''), 
            {'delete': {'query': query}})
        ) is not None

    def reload(self):
        """
        Reloads this Solr collection.

        :rtype: bool
        :return: Whether or not the collection was successfully reloaded
        """
        if 'true' == os.getenv('SOLR_CLOUD'):
            http_call = 'admin/collections?action=RELOAD&name='
        else:
            http_call = 'admin/cores?action=RELOAD&core='

        return self._execute_request(self._create_solr_request(
            '{0}{1}'.format(http_call, self.collection)
        )) is not None

    def select_managed_stopwords(self,
                                 name: str) -> Union[list, None]:
        """
        Retrieve all the managed stopwords for the given name from the Solr
        collection.

        :param str name: The name of the stopwords list
        :rtype: list of str|None
        :return: The list of managed stopwords, or None if the request failed
        """
        response = self._execute_request(self._create_collection_request(
            'schema/analysis/stopwords/{0}'.format(name)
        ))

        if not response:
            return None

        return json.loads(response)['wordSet']['managedList']

    def add_managed_stopwords(self,
                              name: str,
                              values: list) -> bool:
        """
        Add the given values as stopwords to the managed stopwords list with the
        given name.

        :param str name: The name of the managed list
        :param list of str values: The list of values to add
        :rtype: bool
        """
        return self._execute_request(self._create_collection_request(
            'schema/analysis/stopwords/{0}'.format(name), values)
        ) is not None

    def remove_managed_stopwords(self,
                                 name: str,
                                 values: list) -> bool:
        """
        Remove the given stopwords from the managed list in Solr.

        :param str name: The name of the managed list
        :param list of str values: The list of stopwords to remove
        :rtype: bool
        """
        return all([self._execute_request(self._create_collection_request(
            'schema/analysis/stopwords/{0}/{1}'.format(name, value)
        ), method='DELETE') for value in values])

    def select_managed_synonyms(self,
                                name: str) -> Union[dict, list, None]:
        """
        Retrieve the synonyms managed by Solr under the given name.

        :param str name: The name of the managed list
        :rtype: dict[str, list of str]|None
        :return: The synonym dictionary managed by Solr containing the terms as
                 keys and their synonyms as a list of strings, or None if the
                 request failed
        """
        response = self._execute_request(self._create_collection_request(
            'schema/analysis/synonyms/{0}'.format(name)
        ))

        if not response:
            return None

        return json.loads(response)['synonymMappings']['managedMap']

    def add_managed_synonyms(self,
                             name: str,
                             values: Union[dict, list]) -> bool:
        """
        Add the given synonyms to the managed synonym list in Solr.

        :param str name: The name of the managed list
        :param dict[str, list of str] values: A list of dictionaries containing
                                              synonyms to introduce
        :rtype: bool
        :return: Whether or not the synonyms were added to the list
        """
        return self._execute_request(self._create_collection_request(
            'schema/analysis/synonyms/{0}'.format(name), values)
        ) is not None

    def remove_managed_synonyms(self,
                                name: str,
                                values: list) -> bool:
        """
        Remove the given synonyms from the managed synonyms with the given name
        in Solr.

        :param str name: The name of the managed list
        :param list values: The list of synonyms to remove
        :rtype: bool
        """
        return all([self._execute_request(self._create_collection_request(
            'schema/analysis/synonyms/{0}/{1}'.format(name, value)
        ), method='DELETE') for value in values])

    def build_suggestions(self,
                          handler: str) -> bool:
        """
        Builds the suggestions for the specified suggestion handler.

        :param str handler: The name of the suggestion handler
        :rtype: bool
        :return: Whether or not the suggestions were built
        """
        return self._execute_request(self._create_collection_request(
            '{0}?suggest.build=true'.format(handler)
        )) is not None

    def build_spellcheck(self, handler: str) -> bool:
        """
        Builds the spellcheck for the specified spellcheck handler.

        :param str handler: The name of the spellcheck handler
        :rtype: bool
        :return: Whether or not the spellcheck was built
        """
        return self._execute_request(self._create_collection_request(
            '{0}?spellcheck.build=true'.format(handler)
        )) is not None

    def _create_collection_request(self,
                                   request: str,
                                   json_data: Union[dict, list] = None) -> dict:
        """
        Creates a urllib2 Request object based on the given request and possible
        JSON post data.

        :param str request: The request, containing only the segments after
                            '{solr_host}/{solr_collection}/'
        :param dict[str, Any]|list of str json_data: The optional JSON data to
                                                     include in the request
        :rtype: dict[str, Any]
        """
        return self._create_solr_request('{0}/{1}'.format(self.collection, request),
                                         json_data)

    def _create_solr_request(self,
                             request: str,
                             json_data: Union[dict, list] = None) -> dict:
        """
        Creates a urllib2 Request object based on the given Solr host and the
        request string and possible JSON body.

        :param str request: The request, containing only the segments after
                            '{solr_host}/'
        :param dict[str, Any]|list of str json_data: The optional JSON data to
                                                     include in the request
        :rtype: dict[str, Any]
        """
        return {
            'method': 'GET' if json_data is None else 'POST',
            'url': '{0}/{1}'.format(self.solr_host, request),
            'json': json_data
        }

    def _execute_request(self,
                         request: dict,
                         method: str = None):
        """
        Execute a request against the Solr installation. The HTTP method will be
        either GET or POST depending on the presence of data in the request. if
        'method' is provided, the given method will be used instead.

        :param dict[str, Any] request: The request object to execute
        :param str method: Which HTTP method to use
        :rtype: Any|None
        :return: The response of the request, or None if the request failed
        """
        data = request.get('json', None)

        try:
            if data is not None:
                response = self.request_session.request(
                    method=method if method else request.get('method'),
                    url=request.get('url'), json=data
                )
            else:
                response = self.request_session.request(
                    method=method if method else request.get('method'),
                    url=request.get('url')
                )

            response.raise_for_status()

            return response.text
        except requests.exceptions.RequestException as e:
            logging.error('request failed;')
            logging.error(' response: requests.exceptions.RequestException')
            logging.error(' call:     %s', request.get('url'))
            logging.error(' data:     %s', data)
            logging.error(' error:    %s', e)

        return None
