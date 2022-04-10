# encoding: utf-8


import logging
import os
import json
import requests
import sys
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry
from typing import Union, Any, Dict

root = os.path.join(os.path.dirname(__file__), '..', '..')


if not os.path.isfile('/.dockerenv'):
    from dotenv import load_dotenv

    load_dotenv(dotenv_path=os.path.join(root, '.env'), override=True)


def get_version() -> str:
    """
    Returns the current version of this project. The version is based on the
    contents of the `VERSION` file.
    """
    with open(os.path.join(root, 'VERSION')) as fh:
        version = fh.read()

    return version


def setup_logger(caller: str) -> None:
    """
    Configures the default Python logger.

    :param str caller: The script requesting the logger
    """
    caller = os.path.splitext(os.path.basename(caller))[0]

    logging.getLogger().setLevel(logging.DEBUG)
    formatter = logging.Formatter('%(asctime)s \t %(levelname)s \t %(message)s')

    _enable_console_logger(formatter)
    _enable_file_logger(formatter, caller)
    _enable_bugsnag_logger(formatter)


def load_resource(resource_name: str) -> Union[dict, Dict[Any, dict], list]:
    """
    Loads a given JSON resource from `solr_tasks/resources`.

    :param str resource_name: The resource to load (without the `.json` suffix)
    """
    resource_root = os.path.join(root, 'solr_tasks', 'resources')
    filepath = os.path.join(resource_root, '{0}.json'.format(resource_name))

    with open(filepath, 'r') as config_contents:
        json_contents = json.load(config_contents)

    return json_contents


def load_json_file(filename: str) -> Union[dict, list]:
    """
    Loads a file located at the given filename and returns its contents
    interpreted as JSON.

    Requires at least `read` rights on the file.

    :param str filename: The file load as a JSON resource
    """
    with open(filename, 'r') as file_contents:
        contents = file_contents.read()

    return json.loads(contents)


def setup_request_session() -> requests.Session:
    """
    Creates and configures a `requests.Session` object. HTTP proxy and HTTP
    retry settings are configured when sufficient information is available from
    the environment variables.
    """
    session = requests.Session()
    session = _set_request_proxy(session)
    session = _set_request_retry_policy(session)

    return session


def _set_request_proxy(session: requests.Session) -> requests.Session:
    """
    Ensures that the proxy settings of a given Session object are configured
    correctly based on the environment variables present.

    Consumes the following environment variables:
    - `NO_PROXY`
    - `HTTP_PROXY`
    - `HTTPS_PROXY`

    :param requests.Session session: The session object to update
    :rtype requests.Session:
    """
    proxies = {k: v for k, v in {
        'no_proxy': os.getenv('NO_PROXY'),
        'http': os.getenv('HTTP_PROXY'),
        'https': os.getenv('HTTPS_PROXY')
    }.items() if v is not None}

    if len(proxies) > 0:
        session.proxies = proxies

    return session


def _set_request_retry_policy(session: requests.Session) -> requests.Session:
    """
    Configures the retry policy for HTTP and HTTPS requests. The amount of
    retries is based on the `HTTP_RETRY` environment variable and will default
    to 3 if the environment variable is not present.

    :param requests.Session session: The session object to update
    :rtype requests.Session:
    """
    retry_policy = Retry(total=int(os.getenv('HTTP_RETRY', 3)))

    for protocol in ['http://', 'https://']:
        session.mount(protocol, HTTPAdapter(max_retries=retry_policy))

    return session


def _enable_console_logger(formatter: logging.Formatter) -> None:
    """
    Attaches a `logging.StreamHandler` to the current `logging.Logger`. The
    logging level of this handler is set to `logging.DEBUG`.

    :param logging.Formatter formatter: The logging formatter to attach to the
                                        handler
    """
    console_logger = logging.StreamHandler(sys.stdout)
    console_logger.setLevel(logging.DEBUG)
    console_logger.setFormatter(formatter)

    logging.getLogger().addHandler(console_logger)


def _enable_file_logger(formatter: logging.Formatter, caller: str) -> None:
    """
    Attaches a `logging.handlers.RotatingFileHandler` to the current
    `logging.Logger`. The handler is configured based on the following
    environment variables:

    - `LOGGING_FILE_LOCATION`

    The logging level of this handler is set to `logging.INFO`.

    No handler is configured or attached if the `LOGGING_FILE_ENABLE`
    environment variable is set to `'false'`.

    :param logging.Formatter formatter: The logging formatter to attach to the
                                        handler
    :param str caller: The command being executed, will be used as the filename
                       of the logging output
    """
    if 'false' == os.getenv('LOGGING_FILE_ENABLE'):
        return

    from logging.handlers import RotatingFileHandler

    log_file = '{0}/{1}.log'.format(os.getenv('LOGGING_FILE_LOCATION'), caller)
    file_logger = RotatingFileHandler(filename=log_file, maxBytes=2000000,
                                      backupCount=7)
    file_logger.setLevel(logging.INFO)
    file_logger.setFormatter(formatter)

    logging.getLogger().addHandler(file_logger)


def _enable_bugsnag_logger(formatter: logging.Formatter) -> None:
    """
    Attaches a `bugsnag.handlers.BugsnagHandler` to the current
    `logging.Logger`. The handler is configured based on the following
    environment variables:

    - `BUGSNAG_API_KEY`
    - `BUGSNAG_RELEASE_STAGE`

    The logging level of this handler is set to `logging.WARNING`.

    No handler is configured or attached if the `BUGSNAG_ENABLE` environment
    variable is set to `'false'`.

    :param logging.Formatter formatter: The logging formatter to attach to the
                                        handler
    """
    if 'false' == os.getenv('BUGSNAG_ENABLE'):
        return

    import bugsnag

    bugsnag.configure(api_key=os.getenv('BUGSNAG_API_KEY'),
                      app_version=get_version(),
                      project_root=root,
                      release_stage=os.getenv('BUGSNAG_RELEASE_STAGE'),
                      notify_release_stages=['production', 'staging',
                                             'testing'])

    bugsnag_logger = bugsnag.handlers.BugsnagHandler()
    bugsnag_logger.setLevel(logging.WARNING)
    bugsnag_logger.setFormatter(formatter)

    logging.getLogger().addHandler(bugsnag_logger)
