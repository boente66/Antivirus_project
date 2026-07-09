from PyQt5.QtCore import QObject, pyqtSignal, QTimer
from services.system_status_service import SystemStatusService


class StatusController(QObject):

    # --------------------------------------------------
    # SIGNALS
    # --------------------------------------------------

    status_loaded = pyqtSignal(dict)
    error = pyqtSignal(str)

    # --------------------------------------------------
    # INIT
    # --------------------------------------------------

    def __init__(self, refresh_interval=0):

        super().__init__()

        self.service = SystemStatusService()

        self._loading = False

        # Timer opcional para monitoramento automático
        self.timer = QTimer()
        self.timer.timeout.connect(self.load_status)

        if refresh_interval > 0:
            self.start_auto_refresh(refresh_interval)

    # ==================================================
    # LOAD STATUS
    # ==================================================

    def load_status(self):

        if self._loading:
            return

        self._loading = True

        try:

            data = self.service.get_status()

            if not isinstance(data, dict):
                raise RuntimeError("Formato inválido de status.")

            self.status_loaded.emit(data)

        except Exception as e:

            self.error.emit(str(e))

        finally:

            self._loading = False

    # ==================================================
    # AUTO REFRESH
    # ==================================================

    def start_auto_refresh(self, interval_ms=5000):
        """
        Inicia atualização automática do status.
        """
        if not self.timer.isActive():
            self.timer.start(interval_ms)

    # --------------------------------------------------

    def stop_auto_refresh(self):
        """
        Para atualização automática.
        """
        if self.timer.isActive():
            self.timer.stop()

    # --------------------------------------------------

    def is_auto_refresh_running(self):

        return self.timer.isActive()