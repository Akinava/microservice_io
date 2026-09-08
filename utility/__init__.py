from datetime import date, datetime
from decimal import Decimal


class NotFound:
    pass


class SelfItem:
    pass


not_found = NotFound()
self_item = SelfItem()


class Singleton(object):
    _instance = None

    def __new__(class_, *args, **kwargs):
        if not isinstance(class_._instance, class_):
            class_._instance = object.__new__(class_)
        return class_._instance


def json_serial(obj):
    if isinstance(obj, Decimal):
        return str(obj)
    if isinstance(obj, float):
        return str(obj)
    if isinstance(obj, (datetime, date)):
        return obj.isoformat()
    if obj is list:
        return 'list'
    raise TypeError("Type %s not serializable" % type(obj))


def deep_copy(obj):
    if isinstance(obj, dict):
        return copy_dict(obj)
    if isinstance(obj, (list, tuple, set)):
        return copy_array(obj)
    if isinstance(obj, (str, int, float)):
        return obj
    if type(obj).__name__ in ['datetime', 'function', 'DeclarativeMeta', 'Select', 'type', 'NoneType', 'SelfItem']:
        return obj
    raise TypeError(type(obj).__name__)


def copy_dict(obj):
    new_dict = {}
    for k, v in obj.items():
        new_dict[deep_copy(k)] = deep_copy(v)
    return new_dict


def copy_array(obj):
    new_array = []
    for i in obj:
        new_array.append(deep_copy(i))
    return type(obj)(new_array)


def copy_base_instance(base_instance):
    copy_schema = deep_copy(base_instance.schema)
    cls = base_instance.__class__
    return cls(copy_schema)


def get_value_by_path(path, data):
    path = deep_copy(path)
    if isinstance(path, list):
        if len(path) == 0:
            return data
    else:
        path = [path]
    key = path.pop(0)
    try:
        data = data[key]
    except (IndexError, TypeError, KeyError):
        return not_found
    return get_value_by_path(path, data)


def set_value_by_path(obj, path, data):
    if isinstance(path, list):
        obj = get_value_by_path(path[:-1], obj)
        path = path[-1]
    obj[path] = data
