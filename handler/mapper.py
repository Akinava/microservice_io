import types
from microservice_io.dispatcher.base import Base
from microservice_io.utility import not_found, get_value_by_path, set_value_by_path


class SkipMapping:
    pass


class Mapper(Base):
    def do(self):
        result = self._map_fields_data()
        return result

    def _map_fields_data(self):
        result = {}
        for mapping in self.schema['mapping']:
            in_data = self._get_mapping_in_data(mapping)
            in_data_type_casted = self._casting_mapping_type_(in_data, mapping)
            if in_data_type_casted is SkipMapping:
                continue
            result = self._set_mapping_out_data(in_data_type_casted, mapping, result)
        return result

    def _set_mapping_out_data(self, in_data, mapping, result):
        out_path = mapping.get('out_path', not_found)
        if out_path is not_found:
            return in_data
        else:
            set_value_by_path(result, out_path, in_data)
        return result

    def _get_mapping_in_data(self, mapping):
        in_path = mapping.get('in_path', not_found)
        in_value = mapping.get('in_value', not_found)
        default_out = mapping.get('default_out', not_found)
        if not in_value is not_found:
            compile_in_value = self._compile_in(in_value)
        elif not in_path is not_found:
            compile_in_value = get_value_by_path(in_path, self.data)

            if compile_in_value is not_found:
                compile_in_value = default_out

            if compile_in_value is not_found:
                raise Exception(
                    'Error mapping schema, result_data_key "{}", data "in_path" "{}" is not_found and "default_out" in not_found'.format(
                        self.result_data_key,
                        in_path,
                    ))
        else:
            raise Exception('Error mapping schema, result_data_key "{}", data "in" is not_found'.format(
                self.result_data_key,
            ))
        return compile_in_value

    def _compile_in(self, in_value):
        if isinstance(in_value, types.FunctionType):
            return in_value(self.data)
        return in_value

    def _casting_mapping_type_(self, data, mapping):
        if 'set_type' in mapping:
            type_casting_function = mapping['set_type']
            try:
                return type_casting_function(data)
            except (TypeError, KeyError, IndexError):
                field = mapping.get('out_path')
                function_name = type_casting_function.__name__
                raise Exception('schema result_data_key "{}" can not cast field "{}" data "{}" with "{}"'.format(
                    self.result_data_key,
                    field,
                    data,
                    function_name))
        return data
