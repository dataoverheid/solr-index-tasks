# Changelog

## 0.17.3 (2022/05)

- Use `metadata_modified` instead of `last_modified` for modified date of datasets. In newer CKAN releases this should be reverted.

## 0.17.2 (2022/03)

- Delete documents in chunks, so that large delete requests do not result in an error.

## 0.17.1 (2021/08)

- Explicitly interpret the `HTTP_RETRY` environment variable as an integer.

## 0.17.0 (2021/08)

- Add `get_facet_counts` to `SolrCollection` that returns a map <field-value, count> of a given field's counts.
- Update `popularity` index, based on the number of relations of an object, in `generate_relations.py`.

## 0.16.4 (2021/07)

- Exclude filter suggestions that lead to a empty resultset.

## 0.16.3 (2021/06)

- Map res_description to text directly while synchronizing `donl_dataset` and `donl_search`.
- Map distribution type while synchronizing `donl_dataset` and `donl_search`.
- Index suggestions that have at least 1 relation only.

## 0.16.2 (2021/06)

- Fixed a bug that prevented all but the first DataSchema distribution from being indexed in the `donl_search` collection when running the `solr_tasks/synchronize_collections.py` task.

## 0.16.1 (2021/05)

- Set more lenient permissions for the `./lists` directory in the Docker image. The old behaviour prevented other users from having read access to the directory itself causing permissions issues when mounting the lists directory as a volume in other containers.

## 0.16.0 (2021/05)

- Add user defined synonyms of organizations to organization suggestions.

## 0.15.0 (2021/05)

- Add index of dataschema.

## 0.14.1 (2021/05)

- The `generate_relations.py` script now commits after each function.

## 0.14.0 (2021/04)

- Updated `generate_suggestions.py` so that it indexes user defined synonym suggestions.
- Updated `resources/suggestions.json` with an optional key named `user_defined_synonyms` per content type that holds the user defined synonym mapping.

## 0.13.0 (2021/04)

- Added script `update_relations_with_object_property.py`. This script indexes an object property to its relations according to the mapping in `resources/property_to_relation.json`.

## 0.12.0 (2021/04)

- Several optimizations made to the created Docker image.

## 0.11.2 (2021/03)

- Bugfix in `generate_suggestions.py`. When generating suggestions we now use objects with a non-empty `relation` field for setting the weight of suggestions.

## 0.11.1 (2021/02)

- Updated the `donl_dataset` to `donl_search` mapping to accommodate the changes made in `ckanext-dataoverheid@2.5.2`.

## 0.11.0 (2021/02)

- The `generate_relations.py` script now also indexes authority kind (in addition to authority).

## 0.10.0 (2021/01)

- Suggestions are now generated within the context of a specific community. Suggestions can be filtered by including the `sys_name` of the community in the `suggest.cfq`.

## 0.9.0 (2021/01)

- Suggestions now use their relation count (i.e. how many relations a suggestion has with other objects) as suggestions weight.

## 0.8.0 (2021/01)

- Filter suggestions now have `_filter` appended to their type.
- Support the `DONL:WOBUitzondering` list for `donl_dataset` to `donl_search` mapping and URI synonym generation.

## 0.7.0 (2021/01)

- Add explicit label `in_context_of:self` to suggestions without any context.
- Always use `sys_uri` as payload for context/filter suggestions (overwriting what is in the suggestion mapping mapped to the `payload` field).

## 0.6.1 (2020/12)

- Ensured that generated Solr fields are not overwritten during collection synchronization.

## 0.6.0 (2020/12)

- Index dataservice suggestions.

## 0.5.0 (2020/11)

- Updated the generation of Solr suggestions to include all content-types rather than just generating dataset related suggestions.
- Renamed `DatasetMapper` so that it can logically be reused in a non-dataset context.

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
