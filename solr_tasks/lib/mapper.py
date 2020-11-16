# encoding: utf-8


class DatasetMapper:
    def __init__(self, mappings: dict, fields_to_add: dict = None):
        """
        Initializes a DatasetMapper instance.

        :param dict[str, str] mappings: The source > target key mapping
        :param dict[str, Any]|None fields_to_add: Which key: value pairs to add
                                                  to the mapped datasets
        :rtype: DatasetMapper
        """
        self.mappings = mappings
        self.fields_to_add = fields_to_add

    def apply_map(self, dataset: dict):
        """
        Applies the mapping given to this `DatasetMapper` to the given dataset.

        Executed logic:
        - All properties are mapped according to the given map
        - Keys not present in the mapping will be stripped
        - Boolean `False` values are stripped
        - Boolean `True` values are converted to strings with their keys as
          values
        - All values will be converted to lists
        - Each `self.fields_to_add` key: value pair is added to the dataset

        :param dict[str, Any] dataset: The dataset to apply the mapping to
        :rtype: dict[str, Any]
        :return: A dictionary containing all the mapped attributes from the
                 given dataset
        """
        ignore_list = []

        for key, value in dataset.items():
            if key not in self.mappings.keys():
                continue

            if isinstance(value, bool):
                if value is True:
                    dataset[key] = key
                elif value is False:
                    ignore_list.append(key)

        document = {}

        for key, value in dataset.items():
            if key not in self.mappings.keys() or key in ignore_list:
                continue

            target_keys = self.mappings[key]

            for target_key in target_keys:
                document[target_key] = [] if target_key not in document \
                    else document[target_key]

                if isinstance(value, list):
                    [document[target_key].append(single_value)
                     for single_value in value]
                else:
                    document[target_key].append(value)

        if self.fields_to_add:
            for key, value in self.fields_to_add.items():
                document[key] = value

        return document
