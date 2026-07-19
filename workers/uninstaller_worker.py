from PyQt5.QtCore import QThread, pyqtSignal


class UninstallerWorker(QThread):

    progress = pyqtSignal(int, str)
    finished = pyqtSignal(str)
    error = pyqtSignal(str)

    def __init__(self, service, program_name, password=None):

        super().__init__()

        self.service = service
        self.program_name = program_name 
        self.password = password

        self._running = True

    # --------------------------------------------------
    # Execução principal
    # --------------------------------------------------

    def run(self):

        try:

            if not self.service:
                raise RuntimeError(
                    "UninstallerWorker: serviço não informado."
                )

            if not self.program_name:
                raise RuntimeError(
                    "UninstallerWorker: nome do programa inválido."
                )

            if not self._running:
                return

            success, message = self.service.uninstall(
                program_name=self.program_name,
                password=self.password,
                progress_cb=self._emit_progress
            )

            if not self._running:
                return

            if success:

                if not message:
                    message = "Programa removido com sucesso."

                self.finished.emit(message)

            else:

                if not message:
                    message = "Falha na desinstalação."

                self.error.emit(message)

        except Exception as e:

            self.error.emit(str(e))

    # --------------------------------------------------
    # Cancelar execução
    # --------------------------------------------------

    def stop(self):

        self._running = False

    # --------------------------------------------------
    # Callback de progresso
    # --------------------------------------------------

    def _emit_progress(self, percent, message):

        if not self._running:
            return

        try:
            percent = int(percent)
        except Exception:
            percent = 0

        percent = max(0, min(100, percent))

        if not isinstance(message, str):
            message = ""

        self.progress.emit(percent, message)