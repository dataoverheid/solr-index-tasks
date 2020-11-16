# Solr Index Tasks

Repository: [github.com/dataoverheid/solr-index-tasks](https://github.com/dataoverheid/solr-index-tasks)

## Contact

- Web: [data.overheid.nl/contact](https://data.overheid.nl/contact)
- Email: [opendata@overheid.nl](mailto:opendata@overheid.nl)

## Requirements

- Python >= 3.6

## License

Licensed under the CC0 license. View the `LICENSE.md` file for more information.

## Installation

```shell script
cd /path/to/solr-index-tasks
python3 -m venv ./venv --prompt solr-index-tasks
venv/bin/pip install -e ./
```

Now update the `.env` file with the appropriate values.

Alternatively you can use a Docker container by building the `solr-index-tasks` locally:

```shell script
cd /path/to/solr-index-tasks
bin/docker_build.sh
```

## Usage:

The following scripts are now available:

### solr_tasks/list_downloader.py

Downloads the various DCAT-AP-DONL valuelists and stores them locally in a directory defined by the `.env` file.

```shell script
cd /path/to/solr-index-tasks

# CLI
venv/bin/python solr_tasks/list_downloader.py

# Docker
docker run \
  --network {solr network} \
  -v "./.env:/usr/src/app/.env" \
  -v "/path/to/valuelists:/path/defined/in/env/file" \
  -v "/path/to/logs:/path/defined/in/env/file" \
  donl_solr_index_tasks:$(cat ./VERSION) \
  python solr_tasks/list_downloader.py
```

### solr_tasks/synchronize_cores.py [--delta]

Synchronized the contents of the `donl_dataset` collection/core with the `donl_search` collection/core. These collections/cores are based on configsets published on [github.com/dataoverheid/solr-configsets](https://github.com/dataoverheid/solr-configsets). 

**Arguments**:
- `--delta` (optional): triggers a delta synchronization rather than a full synchronization.

```shell script
cd /path/to/solr-index-tasks

# CLI
venv/bin/python solr_tasks/synchronize_cores.py [--delta]

# Docker
docker run \
  --network {solr network} \
  -v "./.env:/usr/src/app/.env" \
  -v "/path/to/valuelists:/path/defined/in/env/file" \
  -v "/path/to/logs:/path/defined/in/env/file" \
  donl_solr_index_tasks:$(cat ./VERSION) \
  python solr_tasks/synchronize_cores.py [--delta]
```

### solr_tasks/managed_resource.py --collection={collection} --resource={resource} [--reload]

Manages the Solr ManagedResources that are part of the collections/cores based on the configsets published on [github.com/dataoverheid/solr-configsets](https://github.com/dataoverheid/solr-configsets).

**Arguments**:
- `--collection`: the Solr collection/core which contains the managed resource
- `--resource`: the name of the resource to manage
- `--reload` (optional): Reloads the collection/core after updating the resource

```shell script
cd /path/to/solr-index-tasks

# CLI
venv/bin/python solr_tasks/synchronize_cores.py --collection={collection} --resource={resource} [--delta]

# Docker
docker run \
  --network {solr network} \
  -v "./.env:/usr/src/app/.env" \
  -v "/path/to/valuelists:/path/defined/in/env/file" \
  -v "/path/to/logs:/path/defined/in/env/file" \
  donl_solr_index_tasks:$(cat ./VERSION) \
  python solr_tasks/synchronize_cores.py --collection={collection} --resource={resource} [--delta]
```

### solr_tasks/generate_relations.py

Populates the appropriate `relation_*` fields for each `sys_type` in the collection/core based on the `donl_search` configset published on [github.com/dataoverheid/solr-configsets](https://github.com/dataoverheid/solr-configsets).

```shell script
cd /path/to/solr-index-tasks

# CLI
venv/bin/python solr_tasks/generate_relations.py

# Docker
docker run \
  --network {solr network} \
  -v "./.env:/usr/src/app/.env" \
  -v "/path/to/valuelists:/path/defined/in/env/file" \
  -v "/path/to/logs:/path/defined/in/env/file" \
  donl_solr_index_tasks:$(cat ./VERSION) \
  python solr_tasks/generate_relations.py
```

### solr_tasks/generate_suggestions.py

Populates the `donl_suggester` collection/core with suggestions based on the contents of the `donl_search` collection/core. Both collections/cores are based on configsets published on [github.com/dataoverheid/solr-configsets](https://github.com/dataoverheid/solr-configsets).

```shell script
cd /path/to/solr-index-tasks

# CLI
venv/bin/python solr_tasks/generate_suggestions.py

# Docker
docker run \
  --network {solr network} \
  -v "./.env:/usr/src/app/.env" \
  -v "/path/to/valuelists:/path/defined/in/env/file" \
  -v "/path/to/logs:/path/defined/in/env/file" \
  donl_solr_index_tasks:$(cat ./VERSION) \
  python solr_tasks/generate_suggestions.py
```

### solr_tasks/rotate_signals.py

Rotates the `donl_signals` collection. Signals older than a given number of days are deleted.

The script uses the `search_timestamp` Solr date field to determine how old a signal is. Refer to the `donl_signals` configset for more information: [github.com/dataoverheid/solr-configsets](https://github.com/dataoverheid/solr-configsets).

**Arguments**:
- `--number_of_days`: the number of days after which signals are considered old

```shell script
cd /path/to/solr-index-tasks

# CLI
venv/bin/python solr_tasks/rotate_signals.py [--number_of_days={number_of_days}]

# Docker
docker run \
  --network {solr network} \
  -v "./.env:/usr/src/app/.env" \
  -v "/path/to/valuelists:/path/defined/in/env/file" \
  -v "/path/to/logs:/path/defined/in/env/file" \
  donl_solr_index_tasks:$(cat ./VERSION) \
  python solr_tasks/rotate_signals.py --number_of_days={number_of_days}
```
