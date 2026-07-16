import os
from PyQt5.QtCore import QObject, pyqtSignal

from workers.scan_worker import ScanWorker

from services.scan_service import ScanService
from services.threat_action_service import ThreatActionService
from services.quarantine_service import QuarantineService
from services.filesystem_service import safe_remove


class ScanController(QObject):

    # --------------------------------------------------
    # SIGNALS
    # --------------------------------------------------

    scan_started = pyqtSignal()
    scan_finished = pyqtSignal(list)

    progress_updated = pyqtSignal(int)
    current_file_changed = pyqtSignal(str)

    threat_detected = pyqtSignal(object)
    scan_error = pyqtSignal(str)

    # --------------------------------------------------
    # INIT
    # --------------------------------------------------

    def __init__(self, parent=None):

        super().__init__(parent)

        self.parent = parent

        # ----------------------------------------
        # SERVICES
        # ----------------------------------------

        self.scan_service = ScanService()
        self.threat_action_service = ThreatActionService()
        self.quarantine_service = QuarantineService()

        # ----------------------------------------
        # CONTROLE
        # ----------------------------------------

        self.worker = None
        self.current_scan_id = None

    # --------------------------------------------------
    # START SCAN
    # --------------------------------------------------

    def start_smart_scan(self):

        if self._is_running():
            return

        self._start_scan("SMART")

    def start_custom_scan(self, path):

        if self._is_running():
            return

        self._start_scan("CUSTOM", path)

    # --------------------------------------------------
    # CHECK RUNNING
    # --------------------------------------------------

    def _is_running(self):

        return self.worker and self.worker.isRunning()

    # --------------------------------------------------
    # START INTERNAL
    # --------------------------------------------------

    def _start_scan(self, profile, path=None):

        try:

            if not self.scan_service.connect_engine():

                self.scan_error.emit("ClamAV não disponível")
                return

        except Exception as e:

            self.scan_error.emit(str(e))
            return

        try:

            self.current_scan_id = self.scan_service.start_scan(
                profile=profile,
                directory=path
            )

        except Exception as e:

            self.scan_error.emit(str(e))
            return

        self.worker = ScanWorker(
            service=self.scan_service,
            profile=profile,
            custom_path=path
        )

        self._bind_worker_signals()

        self.scan_started.emit()

        self.worker.start()

    # --------------------------------------------------
    # SIGNALS
    # --------------------------------------------------

    def _bind_worker_signals(self):

        self.worker.progress.connect(self.progress_updated.emit)
        self.worker.file_changed.connect(self.current_file_changed.emit)

        self.worker.threat_found.connect(self._on_threat)
        self.worker.error.connect(self._on_error)
        self.worker.finished.connect(self._on_finished)

    # --------------------------------------------------
    # THREAT DETECTED
    # --------------------------------------------------

    def _on_threat(self, result):

        file_path = result.detected_file.path
        virus_name = result.virus.name

        # ----------------------------------------
        # DECISÃO
        # ----------------------------------------

        action = self.threat_action_service.decide(
            file_path=file_path,
            virus_name=virus_name
        )

        result.action = action

        # ----------------------------------------
        # EXECUTAR AÇÃO
        # ----------------------------------------

        if action == ThreatActionService.ACTION_QUARANTINE:

            try:

                self.quarantine_service.quarantine_from_scan(
                    file_path,
                    virus_name
                )

            except Exception:
                pass

        elif action == ThreatActionService.ACTION_DELETE:

            try:

                safe_remove([file_path])

            except Exception:
                pass

        # ----------------------------------------
        # HISTÓRICO
        # ----------------------------------------

        try:

            self.scan_service.register_threat(
                scan_id=self.current_scan_id,
                detected_file=result.detected_file,
                virus=result.virus,
                action=action
            )

        except Exception:
            pass

        self.threat_detected.emit(result)

    # --------------------------------------------------
    # ERROR
    # --------------------------------------------------

    def _on_error(self, message):

        try:

            self.scan_service.mark_scan_failed(
                scan_id=self.current_scan_id,
                reason=message
            )

        except Exception:
            pass

        self.scan_error.emit(message)

    # --------------------------------------------------
    # FINISH
    # --------------------------------------------------

    def _on_finished(self, results):

        infected = len([r for r in results if r.infected])
        total_files = infected

        if self.worker is not None:
            total_files = max(
                getattr(self.worker, "scanned_files", 0),
                infected
            )

        try:

            self.scan_service.finish_scan(
                scan_id=self.current_scan_id,
                total_files=total_files,
                infected_files=infected
            )

        except Exception:
            pass

        self.scan_finished.emit(results)

    # --------------------------------------------------
    # CANCEL
    # --------------------------------------------------

    def interrupt_scan(self):

        if not self.worker:
            return

        try:

            self.worker.stop()

        except Exception:
            pass

        try:

            self.scan_service.mark_scan_failed(
                scan_id=self.current_scan_id,
                reason="SCAN_CANCELLED_BY_USER"
            )

        except Exception:
            pass

    # --------------------------------------------------
    # HISTORY
    # --------------------------------------------------

    def get_scan_history(self, limit=100):

        return self.scan_service.get_scan_history(limit)
