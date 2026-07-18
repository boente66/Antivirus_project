from copy import deepcopy

from PyQt5.QtCore import QThread, pyqtSignal


class CleanerWorker(QThread):
    progress = pyqtSignal(int)
    log = pyqtSignal(str)
    finished = pyqtSignal(object)
    error = pyqtSignal(str)

    def __init__(
        self,
        service,
        tasks,
        target_path=None,
        require_admin: bool = False,
        analyze_only: bool = False,
    ):
        super().__init__()
        if service is None:
            raise ValueError("CleanerWorker: service não informado.")
        if not isinstance(tasks, (list, tuple)):
            raise ValueError("CleanerWorker: tasks deve ser uma lista ou tupla.")

        self.service = service
        self.tasks = tuple(deepcopy(list(tasks)))
        self.target_path = target_path
        self.require_admin = bool(require_admin)
        self.analyze_only = bool(analyze_only)
        self._running = True
        self._finished_emitted = False

    def stop(self):
        self._running = False

    def run(self):
        self.progress.emit(0)

        try:
            operation = "análise" if self.analyze_only else "limpeza"
            self.log.emit(f"Iniciando {operation} segura...")

            kwargs = {
                "tasks": self.tasks,
                "target_path": self.target_path,
                "progress_cb": self._emit_progress,
                "log_cb": self._emit_log,
                "should_stop": lambda: not self._running,
            }
            if self.analyze_only:
                result = self.service.analyze(**kwargs)
            else:
                result = self.service.clean(
                    **kwargs,
                    require_admin=self.require_admin,
                )

            if (
                not result.get("cancelled")
                and result.get("status") != "failed"
            ):
                self.progress.emit(100)

            self._emit_finished(result)
        except (ValueError, PermissionError, OSError, RuntimeError) as exc:
            self.error.emit(f"CleanerWorker: falha estrutural: {exc}")

    def _emit_progress(self, percent):
        value = max(0, min(100, int(percent)))
        if value == 100:
            value = 99
        if self._running:
            self.progress.emit(value)

    def _emit_log(self, message):
        if isinstance(message, str):
            self.log.emit(message)

    def _emit_finished(self, result):
        if self._finished_emitted:
            return
        self._finished_emitted = True
        self.finished.emit(result)
