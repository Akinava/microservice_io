from microservice_io.utility import Singleton, not_found
from microservice_io.utility.status_code import StatusCode
from microservice_io.utility.log import Log


class DataDependencyTree(Singleton, Log):
    _tree = {}
    _inspected_tree = {}
    _data_providers = []
    _handlers = []
    _finalizers = []
    _data_provider_key = not_found

    def add_data_providers(self, data_providers):
        self._data_providers = data_providers

    def add_handlers(self, handlers):
        self._handlers = handlers

    def add_finalizers(self, finalizers):
        self._finalizers = finalizers

    def inspect(self):
        self._build_data_tree()
        self._inspect_tree()

    def _build_data_tree(self):
        for handler in self._data_providers + self._handlers + self._finalizers:
            self._add_handler_keys(handler)
        self._merge_tree()

    def _merge_tree(self):
        keys = self._join_uniq_list(self._inspected_tree.keys(), self._tree.keys())
        for key in keys:
            value = self._join_uniq_list(self._inspected_tree.get(key, []), self._tree.get(key, []))
            self._inspected_tree[key] = value

    def _join_uniq_list(self, l1, l2):
        return list(set(l1).union(set(l2)))

    def _get_instance(self, instance):
        return instance()

    def _add_handler_keys(self, handler):
        handler_instance = self._get_instance(handler)
        result_data_key = handler_instance.result_data_key
        if result_data_key in self._tree:
            new_source_data_keys = self._set_key_as_list(handler_instance.source_data_key)
            exist_source_data_keys = self._tree[handler_instance.result_data_key]
            self._tree[handler_instance.result_data_key] = list(set(exist_source_data_keys + new_source_data_keys))
        else:
            self._tree[handler_instance.result_data_key] = self._set_key_as_list(handler_instance.source_data_key)
        if handler_instance.wait_data_key is not_found:
            return
        wait_data_key = self._get_wait_data_key(handler_instance.wait_data_key)
        self._inspected_tree[handler_instance.result_data_key] = wait_data_key

    def check_branch_has_status(self, wait_data_description, data):
        wait_key, status = self._parce_wait_key(wait_data_description)
        if self._data_has_wait_key(wait_key, data):
            return True
        keys = self._set_key_as_list(wait_key)
        while self._list_is_not_empty(keys):
            key = keys.pop()
            if not key in data:
                keys += self._get_source_keys(key)
                continue
            if self._key_has_status(key, status, data):
                return True
        return False

    def _get_wait_data_key(self, wait_data_key):
        result = []
        wait_data_key = self._set_key_as_list(wait_data_key)
        for key in wait_data_key:
            if isinstance(key, dict):
                result.append(key['key'])
            else:
                result.append(key)
        return result

    def _data_has_wait_key(self, wait_key, data):
        return wait_key in data

    def _key_has_status(self, key, status, data):
        if not key in data:
            return False
        data_part = data[key]
        if not isinstance(data_part, dict):
            return False
        if not StatusCode.STATUS_KEY in data_part:
            return False
        data_status_code = data_part[StatusCode.STATUS_KEY]
        return data_status_code == status

    def _parce_wait_key(self, wait_key):
        return wait_key['key'], wait_key[StatusCode.STATUS_KEY]

    def _list_is_not_empty(self, keys):
        return keys != []

    def _set_key_as_list(self, keys):
        if isinstance(keys, list):
            return keys
        return [keys]

    def _get_source_keys(self, key):
        return self._tree.get(key, [])

    def _check_key_exist_in_tree(self, key):
        if key is self._data_provider_key:
            return True
        if key in self._tree:
            return True
        return False

    def _inspect_tree(self):
        for result_key in self._inspected_tree.keys():
            source_keys = self._inspected_tree[result_key]
            for key in source_keys:
                if not self._check_key_exist_in_tree(key):
                    self.logger.warning('result_key "{}" has no source_keys "{}" key in inspected_tree'.format(result_key, key))
