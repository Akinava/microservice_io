import inspect
import asyncio
from microservice_io.utility import (
    not_found,
    deep_copy,
    copy_base_instance,
)
from microservice_io.utility.status_code import StatusSignal
from microservice_io.utility.data_dependency_tree import DataDependencyTree
from microservice_io.utility.log import Log


class BaseList:
    @property
    def get_source_data_type(self):
        return self.schema.get('source_data_type', not_found)

    def _source_data_type_is_list(self):
        return self.get_source_data_type is list

    async def async_produce(self, data: dict):
        if self._source_data_type_is_list():
            return await self._async_produce_list(data)
        return await self._async_produce_once(data)

    def produce(self, data: dict):
        if self._source_data_type_is_list():
            return self._produce_list(data)
        return self._produce_once(data)

    async def _async_produce_list(self, data):
        # TODO move async func to __await__
        self._init_produce_list(data)
        pending_task = []

        if self._data_list_is_empty(data):
            return self._handler_empty_list_result()

        for data_part in data[self.source_data_key]:
            if self.check_status_code_in_data(data_part):
                continue
            self.set_status_in_progress()
            self.data = data_part

            handler_instance = copy_base_instance(self)
            handler_instance.set_status_in_progress()
            handler_instance.source_data = self.source_data
            handler_instance.data = data_part

            if self._check_schema_condition_list():
                # TODO try?
                # FIXME use class __awaut__ instead of function
                pending_task.append(asyncio.create_task(handler_instance.do()))

        done_task, _ = await asyncio.wait(pending_task, return_when=asyncio.ALL_COMPLETED)
        self._collect_async_list_result(done_task)

        self._finalize_produce_list()

    def _produce_list(self, data):
        self._init_produce_list(data)

        if self._data_list_is_empty(data):
            return self._handler_empty_list_result()

        for data_part in data[self.source_data_key]:
            if self.check_status_code_in_data(data_part):
                continue
            self.set_status_in_progress()
            self.data = data_part
            if self._check_schema_condition_list():
                # TODO try
                # FIXME use class __awaut__ instead of function
                try:
                    self.result.append(self.do())
                except:
                    self.traceback()

        self._finalize_produce_list()

    def _check_schema_condition_list(self):
        # FIXME ???
        if 'conditions' not in self.schema:
            return True
        for condition in self.schema['conditions']:
            condition_controller = deep_copy(condition['controller'])
            check_condition_data = deep_copy(self.source_data)
            check_condition_data.update(self.data)
            if condition_controller(condition, check_condition_data) is False:
                self.set_status_code(condition['status_code'])
                return False
        return True

    def _init_produce_list(self, data):
        self.result = []
        self.source_data = data

    def _finalize_produce_list(self):
        self.debug_handler_result()
        self._save_result()
        self.set_status_done()

    def _collect_async_list_result(self, done_task):
        for task in done_task:
            self.result.append(task.result())

    def _data_list_is_empty(self, data):
        return data[self.source_data_key] == []

    def _handler_empty_list_result(self):
        self.set_status_skip()
        self.handle_not_done_status_code()


class Base(BaseList, StatusSignal, Log):
    MESSAGE_ID_KEY = '__id'
    ALL_MESSAGES = '__all_messages'

    def __init__(self, schema: dict):
        self.schema = deep_copy(schema)
        self.set_status_init()
        self.source_data = None
        self.data = None
        self.result = None

    @property
    def id(self):
        return '{}.{}'.format(self.result_data_key, self.message_id)

    @property
    def source_data_key(self):
        return self.schema.get('source_data_key', not_found)

    @property
    def wait_data_key(self):
        return self.schema.get('wait_data_key', not_found)

    @property
    def result_data_key(self):
        return self.schema['result_data_key']

    @property
    def message_id(self):
        if self.check_handler_has_no_source_key():
            return self.schema['description']
        return self.source_data[self.MESSAGE_ID_KEY]

    def task_is_async(self):
        if not inspect.iscoroutinefunction(self.do):
            return False
        return True

    def can_be_run(self, data):
        self.source_data = data
        if self.check_handler_has_no_source_key():
            return self._check_this_handler_can_be_run()
        if self._check_message_has_result_key():
            return False
        if self._check_message_has_source_data_key() is False:
            return False
        if self._check_message_has_wait_data_key() is False:
            return False
        return True

    def check_message_has_handled(self, data):
        self.source_data = data
        return self._check_message_has_result_key()

    def _check_this_handler_can_be_run(self):
        raise Exception('handler "{}" should have can_be_run method'.format(
            self.schema['description']
        ))

    def _check_schema_condition_once(self):
        if 'conditions' not in self.schema:
            return True
        for condition in self.schema['conditions']:
            condition_controller = condition['controller']
            if condition_controller(condition, self.source_data) is False:
                self.set_status_code(condition['status_code'])
                return False
        return True

    async def _async_produce_once(self, data):
        self._init_produce(data)
        if self._check_schema_condition_once():
            try:
                # FIXME use class __awaut__ instead of function
                self.result = await self.do()
            except:
                self.traceback()

        if self.check_status_code_is_not_done():
            self.handle_not_done_status_code()
            return
        self._finalize_produce()

    def _produce_once(self, data):
        self._init_produce(data)
        if self._check_schema_condition_once():
            try:
                # FIXME use class __awaut__ instead of function
                self.result = self.do()
            except:
                self.traceback()

        if self.check_status_code_is_not_done():
            self.handle_not_done_status_code()
            return
        self._finalize_produce()

    def _init_produce(self, data):
        self.source_data = data
        self.set_status_in_progress()
        self._get_source_data()

    def _finalize_produce(self):
        if self.check_handler_has_no_source_key():
            self.debug_data_provider_result()
        else:
            self.debug_handler_result()
        self._save_result()
        self._clean_all_messages_key()
        self.set_status_done()

    def check_handler_has_no_source_key(self):
        return self.source_data_key is not_found

    def _set_key_as_list(self, key):
        if isinstance(key, list):
            return key
        return [key]

    def _check_message_has_result_key(self):
        return self.result_data_key in self.source_data

    def _get_data_with_source_key(self):
        self.data = self.source_data[self.source_data_key]

    def _check_message_has_source_data_key(self):
        for key in self._set_key_as_list(self.source_data_key):
            if not key in self.source_data:
                return False
        return True

    def _check_message_has_wait_data_key(self):
        if self.wait_data_key is not_found:
            return True
        for key in self._set_key_as_list(self.wait_data_key):
            if not self._check_wait_key_in_branch_source_data(key):
                return False
        return True

    def _check_wait_key_in_branch_source_data(self, data_key):
        if isinstance(data_key, dict):
            return DataDependencyTree().check_branch_has_status(data_key, self.source_data)
        return data_key in self.source_data

    def check_required_source_data_keys_has_exit_code(self, data):
        self.source_data = data
        if self.check_status_code_in_data(self.source_data):
            return True
        for key in self._set_key_as_list(self.source_data_key):
            if self.check_status_code_in_data(self.source_data[key]):
                return True
        return False

    def _get_source_data(self):
        if self.check_handler_has_no_source_key():
            self.data = self.source_data
        elif isinstance(self.source_data_key, list):
            self.data = self.source_data
        else:
            self._get_data_with_source_key()

    def _save_result(self):
        if self.check_handler_has_no_source_key():
            self.source_data += self.result
        else:
            self.source_data[self.result_data_key] = self.result

    def _clean_all_messages_key(self):
        if self.schema.get('required_all_messages') is True:
            del self.source_data[self.ALL_MESSAGES]