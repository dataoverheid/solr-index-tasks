# Changelog

## 0.4.5 (2020/10)

- Configured retry policy for HTTP requests based on the `HTTP_RETRY` environment variable.

## 0.4.4 (2020/10)

- Several issues pertaining to the persistence of relations have been fixed.
- Computing the `related_to` field for documents no longer updates the entire document, but now uses ```"related_to": {"set": ..."}``` updates.
- Updated several `has_relations` configurations.

## 0.4.3 (2020/10)
- Fixed a bug that prevented datasets from having `relation_community` values.

## 0.4.2 (2020/10)

- Updated several PyDoc strings in `solr_tasks/lib/solr.py` and `solr_tasks/lib/utils.py`.
- File logging can now be disabled via the `.env` file.
- The `requests.Session` object now respects the `NO_PROXY`, `HTTP_PROXY` and `HTTPS_PROXY` environment variables.

## 0.4.1 (2020/10)

- Disable Bugsnag integration unless explicitly enabled via `.env` file.
- Fixed a bug in `solr_tasks/generate_suggestions.py`; The mapper expects a list of target fields now instead of only one target field.
- Moved the dataset title suggestion mappings to a separate configuration file.

## 0.4.0 (2020/10)

- `solr_tasks/lib/solr.py` now uses a Solr cursor to iterate over the Solr index when using `select_all_documents()`.
- Some optimizations have been made to `solr_tasks/lib/solr.py` so that it can reuse HTTP connections rather than opening a new one for each request.
- Reduced duplicate boilerplate code from tasks by moving Solr host and authentication identification to `solr_tasks/lib/solr.py`.
- `solr_tasks/generate_suggestions.py` now uses `suggest.build=true` rather than simply reloading the Solr collection.

## 0.3.1 (2020/10)

- The mapping from `donl_dataset` to `donl_search` now supports mapping to a list of fields.

## 0.3.0 (2020/10)

- Added communities to datasets based on rules defined in `solr_tasks/resources/communities.json` to `synchronize_cores.py`.
- Added to `synchronize_cores.py`: when synchronizing datasets between CKAN and Solr, do not delete fields that are in Solr, but not in CKAN.

## 0.2.0 (2020/09)

- Added Docker support.
- Added Gitlab CI pipeline to create Docker images based on master branch.
- Updated the various `*.md` files.
- Added a script that rotates DONL signals.

## 0.1.0 (2020/09)

- Initial port to `Python 3.x`.
