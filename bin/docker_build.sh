#!/bin/bash


set -eu


PROJECT_ROOT="$(realpath "$(dirname "$0")/../")"
cd "${PROJECT_ROOT}" || return 1

source ./.env


docker build \
    --tag "donl_solr_index_tasks:$(cat ./VERSION)" \
    --rm \
    ./
