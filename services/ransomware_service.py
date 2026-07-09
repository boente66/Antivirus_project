from queue import Queue, Full
import os
from datetime import datetime

from services.ransomware.engine import RansomwareEngine
from workers.ransomware_worker import RansomwareWorker


class RansomwareService:

    def __init__(self, notify_callback, quarantine_folder=None):

        self.notify_callback = notify_callback
        self.quarantine_folder = quarantine_folder or "./quarantine"

        # garantir que pasta de quarentena exista
        os.makedirs(self.quarantine_folder, exist_ok=True)

        self.engine = None
        self.worker = None

        # fila de eventos do watchdog
        self.event_queue = Queue(maxsize=10000)

        self.logs = []

    # --------------------------------------------------
    # START
    # --------------------------------------------------

    def start(self, directory):

        if self.engine or self.worker:
            self._log("Proteção já está ativa")
            return

        if not directory or not os.path.isdir(directory):
            raise ValueError(
                f"Diretório inválido: {directory}"
            )

        # Engine (monitoramento)

        try:

            self.engine = RansomwareEngine(
                directory,
                self._enqueue_event
            )

            self.engine.start_protection()

        except Exception as e:

            self.engine = None
            raise RuntimeError(
                f"Erro ao iniciar engine de ransomware: {e}"
            )

        # Worker (processamento)

        try:

            self.worker = RansomwareWorker(
                event_queue=self.event_queue,
                quarantine_folder=self.quarantine_folder,
                notify_callback=self.notify_callback,
                logs=self.logs
            )

            self.worker.start()

        except Exception as e:

            if self.engine:
                self.engine.stop_protection()
                self.engine = None

            raise RuntimeError(
                f"Erro ao iniciar worker de ransomware: {e}"
            )

        self._log(f"Proteção iniciada para {directory}")

    # --------------------------------------------------
    # STOP
    # --------------------------------------------------

    def stop(self):

        if self.engine:

            try:
                self.engine.stop_protection()
            except Exception:
                pass

            self.engine = None

        if self.worker:

            try:
                self.worker.stop()
                self.worker.join(timeout=5)
            except Exception:
                pass

            self.worker = None

        self._log("Proteção encerrada")

    # --------------------------------------------------
    # ENQUEUE EVENT
    # --------------------------------------------------

    def _enqueue_event(self, event_type, file_path):

        try:

            self.event_queue.put_nowait(
                (event_type, file_path)
            )

        except Full:

            # fila cheia
            self._log("Fila de eventos cheia")

        except Exception as e:

            self._log(f"Erro ao adicionar evento: {e}")

    # --------------------------------------------------
    # STATUS
    # --------------------------------------------------

    def is_active(self):

        return self.engine is not None and self.worker is not None

    # --------------------------------------------------
    # LOG
    # --------------------------------------------------

    def _log(self, message):

        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        self.logs.append(
            f"[{timestamp}] {message}"
        )

    # --------------------------------------------------
    # GET LOGS
    # --------------------------------------------------

    def get_logs(self, limit=100):

        if limit <= 0:
            return []

        return self.logs[-limit:]