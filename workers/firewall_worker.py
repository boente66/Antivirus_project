from PyQt5.QtCore import QThread, pyqtSignal


class FirewallWorker(QThread):
    operation_started = pyqtSignal(str, str)
    awaiting_authorization = pyqtSignal(str, str)
    progress = pyqtSignal(str, int)
    completed = pyqtSignal(object)
    failed = pyqtSignal(object)

    def __init__(self, service, request, parent=None):
        super().__init__(parent)
        self.service = service
        self.request = request

    def run(self):
        operation_id = self.request.operation_id
        if self.isInterruptionRequested():
            return
        self.operation_started.emit(operation_id, self.request.operation)
        requirement = self.service.get_privilege_requirement(self.request)
        if requirement.required and requirement.can_prompt:
            self.awaiting_authorization.emit(operation_id, requirement.reason)
        self.progress.emit(operation_id, 20)
        if self.isInterruptionRequested():
            return
        result = self.service.execute(self.request)
        self.progress.emit(operation_id, 100)
        if result.succeeded:
            self.completed.emit(result)
        else:
            self.failed.emit(result)

    def cancel(self):
        # Seguro antes da execução. Uma mutação já entregue ao pkexec não é
        # encerrada abruptamente para evitar estado parcial.
        self.requestInterruption()
