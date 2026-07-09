from PyQt5.QtCore import QObject, QTimer
import time
import threading


class EngineWatchdogService(QObject):
    """
    Monitor contínuo do engine ClamAV.

    Responsável por:
    - verificar daemon
    - verificar conexão
    - verificar banco de vírus
    - recuperar engine automaticamente
    """

    # =====================================================
    # INIT
    # =====================================================

    def __init__(self, clamav_service, interval_ms=30000):

        super().__init__()

        self.clamav = clamav_service
        self.interval = interval_ms

        self.timer = QTimer()
        self.timer.timeout.connect(self._check_engine)

        self._lock = threading.Lock()

        # controle de atualização
        self._last_update_attempt = 0
        self._update_interval = 3600  # 1 hora

    # =====================================================
    # CONTROLE
    # =====================================================

    def start(self):
        """Inicia o monitoramento."""
        self.timer.start(self.interval)

    def stop(self):
        """Para o monitoramento."""
        self.timer.stop()

    def is_running(self):
        return self.timer.isActive()

    # =====================================================
    # LOG
    # =====================================================

    def _log(self, message):

        ts = time.strftime("%H:%M:%S")

        print(f"[WATCHDOG {ts}] {message}")

    # =====================================================
    # VERIFICAÇÃO DO ENGINE
    # =====================================================

    def _check_engine(self):

        # evitar execução concorrente
        if not self._lock.acquire(blocking=False):
            return

        try:

            # -----------------------------
            # ClamAV instalado?
            # -----------------------------

            if not self.clamav.is_installed():

                self._log("ClamAV não instalado")

                return

            # -----------------------------
            # Daemon rodando?
            # -----------------------------

            status = self.clamav.get_status()

            if status != "running":

                self._log("Daemon parado. Tentando iniciar...")

                try:
                    self.clamav.ensure_engine_ready()
                    self._log("Daemon iniciado")
                except Exception as e:
                    self._log(f"Falha ao iniciar daemon: {e}")

                return

            # -----------------------------
            # Conectado?
            # -----------------------------

            if not self.clamav.is_connected():

                self._log("Engine desconectado. Reconectando...")

                try:
                    if self.clamav.auto_connect():
                        self._log("Reconectado ao engine")
                    else:
                        self._log("Falha ao reconectar")
                except Exception as e:
                    self._log(f"Erro ao reconectar: {e}")

            # -----------------------------
            # Banco de vírus
            # -----------------------------

            try:

                if self.clamav.database_is_outdated():

                    now = time.time()

                    # evitar tentar atualizar sempre
                    if now - self._last_update_attempt > self._update_interval:

                        self._last_update_attempt = now

                        self._log("Banco desatualizado. Atualizando...")

                        self.clamav.update_database()

                        self._log("Banco atualizado")

            except Exception as e:

                self._log(f"Falha ao atualizar banco: {e}")

        except Exception as e:

            self._log(f"Erro inesperado: {e}")

        finally:

            self._lock.release()