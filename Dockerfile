ARG PYTHON_VERSION=3.8

FROM library/python:${PYTHON_VERSION}

ENV PROJECT_ROOT=/usr/src/index-tasks \
    LOGGING_FILE_ENABLE=true \
    LOGGING_FILE_LOCATION=/usr/src/index-tasks/log \
    BUGSNAG_ENABLE=true \
    SOLR_CLOUD=false \
    SOLR_USERNAME=donl_index_tasks \
    SOLR_COLLECTION_DATASET=donl_dataset \
    SOLR_COLLECTION_SEARCH=donl_search \
    SOLR_COLLECTION_SIGNALS=donl_signals \
    SOLR_COLLECTION_SIGNALS_AGGREGATED=donl_signals_aggregated \
    SOLR_COLLECTION_SUGGESTER=donl_suggester \
    HTTP_RETRY=3 \
    VALUELIST_DIR=/usr/src/index-tasks/lists

COPY . ${PROJECT_ROOT}

WORKDIR ${PROJECT_ROOT}

RUN pip install --no-cache-dir --editable ./ && \
    mkdir -p ${PROJECT_ROOT}/log && \
    useradd -r index-tasks && \
    chown -R index-tasks:index-tasks ${PROJECT_ROOT} && \
    chmod -R o-rwx ${PROJECT_ROOT} && \
    chmod -R ugo+rx ${PROJECT_ROOT}/lists

USER index-tasks

CMD ["/bin/bash"]
