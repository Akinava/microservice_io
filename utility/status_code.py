class StatusCode:
    STATUS_KEY = '__status'
    DONE = 'done'
    ERROR = 'error'
    INTERRUPT_HANDLING = 'interrupt_handling'
    SKIP_HANDLING = 'skip_handling'
    IN_PROGRESS = 'in_progress'
    INIT = 'init'


class StatusSignal(StatusCode):
    def check_status_code_is_finished(self):
        return self._status_code in [
            self.ERROR,
            self.INTERRUPT_HANDLING,
            self.SKIP_HANDLING,
            self.DONE]

    def check_status_code_is_not_done(self):
        return self._status_code in [
            self.ERROR,
            self.INTERRUPT_HANDLING,
            self.SKIP_HANDLING]

    def set_status_code(self, status_code):
        self._status_code = status_code

    @property
    def status_code(self):
        return self._status_code

    def set_status_init(self):
        self._status_code = self.INIT

    def set_status_in_progress(self):
        self._status_code = self.IN_PROGRESS

    def set_status_done(self):
        self._status_code = self.DONE

    def set_status_skip(self):
        self._status_code = self.SKIP_HANDLING

    def set_status_interrupt(self):
        self._status_code = self.INTERRUPT_HANDLING

    def set_status_error(self):
        self._status_code = self.ERROR

    def handle_not_done_status_code(self):
        self.log_status_code(self._status_code)
        self._move_status_code_from_handler_to_data()

    def check_status_code_in_data(self, data):
        if not isinstance(data, dict):
            return False
        return self.STATUS_KEY in data

    def _move_status_code_from_handler_to_data(self):
        if self.status_code in [self.ERROR, self.INTERRUPT_HANDLING]:
            self.source_data[self.STATUS_KEY] = self._status_code
        if self.status_code == self.SKIP_HANDLING:
            self.source_data[self.result_data_key] = {self.STATUS_KEY: self._status_code}
