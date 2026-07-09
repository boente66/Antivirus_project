import platform
from PyQt5.QtCore import QObject, pyqtSignal

from services.uninstaller_service import UninstallerService
from workers.uninstaller_worker import UninstallerWorker


class UninstallerController(QObject):

    # --------------------------------------------------
    # SIGNALS
    # --------------------------------------------------

    program_list_updated = pyqtSignal(list)

    progress_updated = pyqtSignal(int, str)
    uninstall_completed = pyqtSignal(str)

    error = pyqtSignal(str)

    request_admin_password = pyqtSignal(str)

    # --------------------------------------------------
    # INIT
    # --------------------------------------------------

    def __init__(self, service=None):

        super().__init__()

        self.service = service or UninstallerService()

        self.worker = None

        self.os_type = platform.system()

        self._pending_program = None

    # ==================================================
    # LISTAGEM
    # ==================================================

    def get_installed_programs(self):

        try:

            programs = self.service.list_installed()

            self.program_list_updated.emit(programs)

        except Exception as e:

            self.error.emit(str(e))

    # ==================================================
    # DESINSTALAÇÃO
    # ==================================================

    def uninstall_program(self, program_name):

        if self.worker and self.worker.isRunning():
            return

        if not program_name:
            self.error.emit("Programa inválido.")
            return

        # Linux / macOS pedem senha
        if self.os_type in ("Linux", "Darwin"):

            self._pending_program = program_name

            self.request_admin_password.emit(program_name)

            return

        self._start_worker(program_name, None)

    # --------------------------------------------------

    def provide_admin_password(self, password):

        if not self._pending_program:
            return

        if not password:

            self.error.emit("Senha de administrador não fornecida.")
            self._pending_program = None
            return

        program = self._pending_program

        self._pending_program = None

        self._start_worker(program, password)

    # ==================================================
    # WORKER
    # ==================================================

    def _start_worker(self, program_name, password):

        self.worker = UninstallerWorker(
            service=self.service,
            program_name=program_name,
            password=password
        )

        self.worker.progress.connect(self.progress_updated.emit)

        self.worker.finished.connect(self._on_finished)

        self.worker.error.connect(self._on_error)

        self.worker.start()

    # --------------------------------------------------

    def _on_finished(self, message):

        self.worker = None

        self.uninstall_completed.emit(message)

        # atualizar lista automaticamente
        self.get_installed_programs()

    # --------------------------------------------------

    def _on_error(self, message):

        self.worker = None

        self.error.emit(message)

    # ==================================================
    # CANCELAMENTO
    # ==================================================

    def stop(self):

        if self.worker:

            try:
                self.worker.stop()
            except Exception:
                pass