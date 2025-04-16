import sys
import json
import traceback
import logging
import uuid
from microservice_io.utility import json_serial


def get_logger(logging_format, logging_level):
    handler = logging.StreamHandler(sys.stdout)
    formatter = logging.Formatter(logging_format)
    handler.setFormatter(formatter)
    logger = logging.getLogger(__name__)
    logger.setLevel(logging_level)
    logger.addHandler(handler)
    return logger


class Log:
    logging_format = '%(message)s'
    logging_level = logging.INFO
    logger = get_logger(logging_format, logging_level)

    @classmethod
    def setup_logger(cls, logging_format=logging_format, logging_level=logging_level):
        cls.logging_format = logging_format
        cls.logging_level = logging_level
        cls.logger.setLevel(logging_level)
        cls.logger.handlers.clear()
        handler = logging.StreamHandler(sys.stdout)
        formatter = logging.Formatter(logging_format)
        handler.setFormatter(formatter)
        cls.logger.addHandler(handler)

    def debug_data_provider_result(self):
        for message in self.result:
            message_id = message[self.MESSAGE_ID_KEY]
            if self.logging_level != logging.DEBUG:
                self.logger.info('{} : {} : {}'.format(
                    self.__class__.__name__,
                    self.result_data_key,
                    message_id))
            else:
                self._log(self.result_data_key, message_id, message)

    def debug_handler_result(self):
        if self.logging_level != logging.DEBUG:
            return
        result_data_key = self.result_data_key
        self._log(result_data_key, self.message_id, self.result)

    def log_status_code(self, status_code):
        self.logger.info('{handler}.{result_key} : message_id {id} : return "{code}" status code'.format(
            handler=self.__class__.__name__,
            result_key=self.result_data_key,
            id=self.message_id,
            code=status_code))

    def traceback(self):
        self._clean_all_messages_key()
        message_id = self.message_id
        traceback_message = traceback.format_exc()
        traceback_uuid = uuid.uuid1()
        self.logger.error((
                '\n' +
                'traceback_uuid {traceback_uuid} source_data: {source_data}\n' +
                'traceback_uuid {traceback_uuid} result_data_key {result_data_key} ' +
                'traceback_message: \n{traceback_message}\n').format(
            message_id=message_id,
            source_data=json.dumps(self.source_data, default=json_serial),
            traceback_message=traceback_message,
            traceback_uuid=traceback_uuid,
            result_data_key=self.result_data_key,

        ))

    def _log(self, result_data_key, message_id, result):
        self.logger.debug('result {}.{}.{} : {}'.format(
            self.__class__.__name__,
            result_data_key,
            message_id,
            json.dumps(result, default=json_serial)))
