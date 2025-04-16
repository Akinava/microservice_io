import types
from microservice_io.dispatcher.base import Base
from microservice_io.utility import not_found, self_item


class Mapper(Base):
    def do(self):
        self._result = {}
        self._map_fields_data()
        return self._result

    def _map_fields_data(self):
        for field_description in self.schema['fields']:
            out_path = field_description.get('out', not_found)
            in_path = field_description.get('in', not_found)
            if in_path is not_found and out_path is not_found:
                raise Exception('schema field mapping is empty')
            if in_path is not_found:
                self._copy_out_in_result(out_path)
                continue
            in_data = self._get_in_data(field_description)
            if in_data is not_found:
                raise Exception('schema result_data_key "{}" mapping by path "{}" data is not_found'.format(
                    self.result_data_key,
                    in_path))
            in_data = self._type_casting(in_data, field_description)
            if out_path is not_found:
                self._result = in_data
            else:
                self._result[out_path] = in_data

    def _copy_out_in_result(self, out_):
        for k, v in out_.items():
            self._result[k] = self._compile_out(v)

    def _compile_out(self, out):
        if isinstance(out, types.FunctionType):
            return out(self.data)
        return out

    def _get_in_data(self, field_description):
        in_field_description = field_description.get('in', not_found)
        if isinstance(in_field_description, types.FunctionType):
            return in_field_description(self.data)
        field_data = self._find_data(
            data=self.data,
            path=in_field_description,
            default_data=field_description.get('default_data', not_found)
        )
        return field_data

    def _type_casting(self, data, field_description):
        if 'set_type' in field_description:
            type_casting_function = field_description['set_type']
            try:
                return type_casting_function(data)
            except (TypeError, KeyError, IndexError):
                field = field_description.get('out')
                function_name = type_casting_function.__name__
                raise Exception('schema result_data_key "{}" can not cast field "{}" data "{}" with "{}"'.format(
                    self.result_data_key,
                    field,
                    data,
                    function_name))
        return data

    def _get_nodekey_and_rest_path(self, path):
        rest_path = []
        if isinstance(path, list):
            if len(path) > 1:
                node_key, rest_path = path[0], path[1:]
            else:
                node_key = path[0]
        else:
            node_key = path
        return node_key, rest_path

    def _rest_path_is_empty(self, rest_path):
        return len(rest_path) == 0

    def _find_data(self, data, path, default_data=not_found):
        node_key, rest_path = self._get_nodekey_and_rest_path(path)
        if node_key is self_item:
            return data
        if node_key not in data:
            return default_data
        node_value = data[node_key]

        if self._rest_path_is_empty(rest_path):
            return node_value

        return self._find_data(
            data=node_value,
            path=rest_path,
            default_data=default_data)
