import asyncio
from microservice_io.dispatcher.base import Base
from microservice_io.utility.data_dependency_tree import DataDependencyTree
from microservice_io.utility.log import Log


class Dispatcher(Log):
    def __init__(self):
        self._data_providers = []
        self._handlers = []
        self._finalizers = []
        self._messages = []
        self._alive = False
        self._ran_tasks = {}

    def add_data_provider(self, handler, schema):
        self.logger.debug('init data_provider.schema "{}.{}"'.format(
            handler.__name__,
            schema['result_data_key']))
        self._data_providers.append(lambda: handler(schema))

    def add_handler(self, handler, schema):
        self.logger.debug('init handler.schema "{}.{}"'.format(
            handler.__name__,
            schema['result_data_key']))
        self._handlers.append(lambda: handler(schema))

    def add_finalizer(self, handler, schema):
        self.logger.debug('init finalizer.schema "{}.{}"'.format(
            handler.__name__,
            schema['result_data_key']))
        self._finalizers.append(lambda: handler(schema))

    async def run(self):
        self._inspect_schema()
        self._set_self_alive()

        while self._alive:
            while True:
                if await self._run_data_provider():
                    continue
                if await self._run_data_handler():
                    continue
                if await self._run_data_finalizer():
                    continue
                break

            await self._await_tasks()
            self._clean_task_pool()
            self._clean_messages()

    async def _run_data_provider(self):
        '''
        data_provider handler should provide method can_be_run
        '''
        for handler in self._data_providers:
            handler_instance = self._get_instance(handler)
            if not handler_instance.can_be_run(self._messages):
                continue
            if self._data_provider_in_progress(handler_instance):
                continue
            await self._create_task(handler_instance, self._messages)
            return True
        return False

    def _data_provider_in_progress(self, handler_instance):
        return len(self._get_handler_ran_tasks(handler_instance)) > 0

    async def _run_data_handler(self):
        for handler in self._handlers:
            handler_instance = self._get_instance(handler)
            for message in self._messages:
                if not handler_instance.can_be_run(message):
                    continue
                if handler_instance.check_required_source_data_keys_has_exit_code(message) is True:
                    continue
                if self._handler_in_progress(handler_instance, message):
                    continue
                await self._create_task(handler_instance, message)
                return True
        return False

    def _handler_in_progress(self, handler_instance, message):
        handler_ran_tasks = self._get_handler_ran_tasks(handler_instance)
        message_id = self._get_message_id(message)
        for ran_handler in handler_ran_tasks:
            if ran_handler.message_id == message_id:
                return True
        return False

    async def _run_data_finalizer(self):
        def check_message_can_be_handled(message):
            for handler in self._handlers:
                handler_instance = self._get_instance(handler)
                if not handler_instance.can_be_run(message):
                    continue
                if handler_instance.check_required_source_data_keys_has_exit_code(message):
                    continue
                return True
            return False

        def check_message_has_ran_handler(message):
            for handler in self._handlers:
                handler_instance = self._get_instance(handler)
                if self._handler_in_progress(handler_instance, message):
                    return True
            return False

        for message in self._messages:
            if check_message_can_be_handled(message):
                continue
            if check_message_has_ran_handler(message):
                continue

            for finalize in self._finalizers:
                finalize_instance = self._get_instance(finalize)
                if not finalize_instance.can_be_run(message):
                    continue
                if self._handler_in_progress(finalize_instance, message):
                    continue
                await self._create_task(finalize_instance, message)
                return True

        return False

    def _clean_task_pool(self):
        for handler_instances in self._ran_tasks.values():
            for _ in range(len(handler_instances)):
                handler_instance = handler_instances.pop()
                if handler_instance.check_status_code_is_finished():
                    self.logger.debug('{}.{}.{}'.format(
                        handler_instance.__class__.__name__,
                        handler_instance.result_data_key,
                        handler_instance.message_id))
                    continue
                task = handler_instance.task
                if task.done() is True:
                    self.logger.warning('{}.{}.{} is done without status_code is finished'.format(
                        handler_instance.__class__.__name__,
                        handler_instance.result_data_key,
                        handler_instance.message_id))
                    handler_instance.set_status_error()
                    handler_instance.handle_not_done_status_code()
                    continue
                handler_instances.insert(0, handler_instance)

    def _clean_messages(self):
        def get_last_message():
            return self._messages.pop()

        def put_message_to_beginning(message):
            self._messages.insert(0, message)

        def check_message_has_all_finalize_result_key(message):
            for finalize in self._finalizers:
                finalize_instance = self._get_instance(finalize)
                if not finalize_instance.check_message_has_handled(message):
                    return False
            return True

        for _ in range(len(self._messages)):
            message = get_last_message()
            if check_message_has_all_finalize_result_key(message):
                self.logger.debug('remove compiled message {}'.format(
                    self._get_message_id(message)
                ))
                continue
            put_message_to_beginning(message)

    async def _await_tasks(self):
        self.logger.debug('await job pool length {}, messages pool length {}'.format(
            len(self._get_pending_task()),
            len(self._messages)))

        if len(self._get_pending_task()) == 0:
            self.logger.warning('await empty job pool')
            return
        _, _ = await asyncio.wait(self._get_pending_task(), return_when=asyncio.FIRST_COMPLETED)

    def _handler_in_progress_with_message(self, handler_instance, message):
        handler_instance_run_tasks = self._get_handler_ran_tasks(handler_instance)
        message_id = self._get_message_id(message)
        for progress_handler in handler_instance_run_tasks:
            if progress_handler.message_id == message_id:
                return True
        return False

    def _get_handler_ran_tasks(self, handler_instance):
        return self._ran_tasks.get(handler_instance.result_data_key, [])

    def _set_self_alive(self):
        self._alive = True

    def _add_handler_to_run_tasks(self, handler_instance):
        handler_instances = self._ran_tasks.get(handler_instance.result_data_key, [])
        handler_instances.append(handler_instance)
        self._ran_tasks[handler_instance.result_data_key] = handler_instances

    def _run_async_task(self, handler_instance, data):
        return asyncio.create_task(handler_instance.async_produce(data))

    def _run_task(self, handler_instance, data):
        handler_instance.produce(data)

    def _get_pending_task(self):
        pending_task = set()
        for handler_instances in self._ran_tasks.values():
            for handler_instance in handler_instances:
                pending_task.add(handler_instance.task)
        return pending_task

    def _get_instance(self, instance):
        return instance()

    def _get_message_id(self, message):
        if not isinstance(message, dict):
            return None
        return message[Base.MESSAGE_ID_KEY]

    async def _create_task(self, handler_instance, data):
        data = self._make_data(handler_instance, data)
        self.logger.debug('{}.{}.{}'.format(
            handler_instance.__class__.__name__,
            handler_instance.result_data_key,
            self._get_message_id(data)))
        if handler_instance.task_is_async():
            async_task = self._run_async_task(handler_instance, data)
            async_task.set_name(handler_instance.id)
            handler_instance.task = async_task
            self._add_handler_to_run_tasks(handler_instance)
        else:
            self._run_task(handler_instance, data)

    def _make_data(self, handler_instance, data):
        if handler_instance.schema.get('required_all_messages') is True:
            data[Base.ALL_MESSAGES] = self._messages
        return data

    def _inspect_schema(self):
        data_dependency_tree = DataDependencyTree()
        data_dependency_tree.add_data_providers(self._data_providers)
        data_dependency_tree.add_handlers(self._handlers)
        data_dependency_tree.add_finalizers(self._finalizers)
        return data_dependency_tree.inspect()
