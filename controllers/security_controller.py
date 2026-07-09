from PyQt5.QtCore import QObject, pyqtSignal

from services.clamav_service import ClamAVService
from services.ransomware_service import RansomwareService
from services.engine_watchdog_service import EngineWatchdogService


class SecurityController(QObject):

    # --------------------------------------------------
    # SIGNALS
    # --------------------------------------------------

    status_changed = pyqtSignal(str)
    info = pyqtSignal(str)
    warning = pyqtSignal(str)
    error = pyqtSignal(str)

    ransomware_state_changed = pyqtSignal(bool)

    # ==================================================
    # INIT
    # ==================================================

    def __init__(self, ui_reference=None):

        super().__init__()

        self.ui = ui_reference

        # ------------------------------------------
        # SERVICES
        # ------------------------------------------

        self.clamav_service = ClamAVService()

        self.ransomware_service = RansomwareService(
            self._notify_ransomware
        )

        self.watchdog = EngineWatchdogService(
            self.clamav_service
        )

        # ------------------------------------------
        # INTERNAL STATE
        # ------------------------------------------

        self.engine_connected = False
        self.engine_mode = None

    # ==================================================
    # INITIALIZATION
    # ==================================================

    def initialize_security(self):

        try:

            if not self.clamav_service.is_installed():

                self._warning("ClamAV não instalado")

                return

            self.refresh_clamav_status()

        except Exception as e:

            self._error(f"Erro ao inicializar segurança: {e}")

    # ==================================================
    # WATCHDOG
    # ==================================================

    def start_watchdog(self):

        try:

            if not self.watchdog.is_running():

                self.watchdog.start()

        except Exception as e:

            self._error(f"Erro ao iniciar monitor do engine: {e}")

    # --------------------------------------------------

    def stop_watchdog(self):

        try:

            if self.watchdog.is_running():

                self.watchdog.stop()

        except Exception as e:

            self._error(f"Erro ao parar monitor do engine: {e}")

    # ==================================================
    # CLAMAV STATUS
    # ==================================================

    def refresh_clamav_status(self):

        try:

            if not self.clamav_service.is_installed():

                self._status("ClamAV não instalado")
                return

            status = self.clamav_service.get_status()

            if status == "running":

                self._status("Ativo")

            elif status == "stopped":

                self._status("Desativado")

            else:

                self._status("Desconhecido")

        except Exception as e:

            self._error(f"Erro ao verificar status do ClamAV: {e}")

    # ==================================================
    # CONNECT ENGINE
    # ==================================================

    def connect_clamav(self, mode="Local", address=None, port=None):

        try:

            if not self.clamav_service.is_installed():

                self._warning(
                    "ClamAV não está instalado.\n"
                    "Instale com:\n"
                    "sudo apt install clamav clamav-daemon"
                )

                return

            # garantir daemon ativo

            status = self.clamav_service.get_status()

            if status != "running":

                try:
                    self.clamav_service.start_daemon()
                except Exception:
                    pass

            # ----------------------------------
            # LOCAL
            # ----------------------------------

            if mode == "Local":

                self.clamav_service.connect_local()

                self.engine_connected = True
                self.engine_mode = "local"

                self._status("Ativo")
                self._info("Conectado ao ClamAV local.")

            # ----------------------------------
            # SERVER
            # ----------------------------------

            elif mode == "Servidor":

                if not address or not port:

                    self._warning("Dados do servidor incompletos.")
                    return

                self.clamav_service.connect_network(address, port)

                self.engine_connected = True
                self.engine_mode = "network"

                self._status(f"Servidor {address}:{port} ativo")
                self._info("Conectado ao servidor ClamAV.")

            # iniciar watchdog

            self.start_watchdog()

        except Exception as e:

            self._error(f"Erro ao conectar ao ClamAV: {e}")

    # --------------------------------------------------

    def disconnect_clamav(self):

        try:

            self.stop_watchdog()

            try:
                self.clamav_service.stop_daemon()
            except Exception:
                pass

            try:
                self.clamav_service.disconnect()
            except Exception:
                pass

            self.engine_connected = False
            self.engine_mode = None

            self._status("Desativado")
            self._info("ClamAV desconectado.")

        except Exception as e:

            self._error(f"Erro ao desconectar ClamAV: {e}")

    # ==================================================
    # UPDATE SIGNATURES
    # ==================================================

    def update_virus_database(self):

        try:

            self._info("Atualizando banco de vírus...")

            self.clamav_service.update_database()

            self._info("Banco de vírus atualizado com sucesso.")

        except Exception as e:

            self._error(f"Erro ao atualizar banco de vírus: {e}")

    # ==================================================
    # RANSOMWARE PROTECTION
    # ==================================================

    def toggle_ransomware(self, directory):

        try:

            if not self.ransomware_service.is_active():

                if not directory:

                    self._warning("Nenhum diretório selecionado.")
                    return

                self.ransomware_service.start(directory)

                self.ransomware_state_changed.emit(True)

                self._info("Proteção contra ransomware ativada.")

            else:

                self.ransomware_service.stop()

                self.ransomware_state_changed.emit(False)

                self._info("Proteção contra ransomware desativada.")

        except Exception as e:

            self._error(f"Erro na proteção ransomware: {e}")

    # ==================================================
    # INTERNAL HELPERS
    # ==================================================

    def _status(self, message):

        self.status_changed.emit(message)

        if self.ui:
            self.ui.update_status(message)

    def _info(self, message):

        self.info.emit(message)

        if self.ui:
            self.ui.show_info(message)

    def _warning(self, message):

        self.warning.emit(message)

        if self.ui:
            self.ui.show_warning(message)

    def _error(self, message):

        self.error.emit(message)

        if self.ui:
            self.ui.show_error(message)

    # --------------------------------------------------

    def _notify_ransomware(self, message):

        self._warning(message)