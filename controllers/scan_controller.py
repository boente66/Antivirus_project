from datetime import datetime

from PyQt5.QtCore import QObject, QTimer, pyqtSignal

from services.quarantine_service import QuarantineService
from services.process_detection_service import BrowserProcessDetector
from services.scan_preferences_service import ScanPreferencesService
from services.scan_service import ScanService
from services.threat_action_service import ThreatActionService
from workers.scan_worker import ScanWorker


class ScanController(QObject):
    HISTORY_BATCH_SIZE = 50
    HISTORY_FLUSH_INTERVAL_MS = 150

    scan_started = pyqtSignal()
    scan_finished = pyqtSignal(list)
    progress_updated = pyqtSignal(int)
    current_file_changed = pyqtSignal(str)
    threat_detected = pyqtSignal(object)
    scan_error = pyqtSignal(str)
    browser_warning_requested = pyqtSignal(object)
    browser_warning_preference_changed = pyqtSignal(bool)

    def __init__(
        self,
        parent=None,
        quarantine_service=None,
        *,
        scan_service=None,
        process_detector=None,
        preferences_service=None,
    ):
        super().__init__(parent)
        self.parent = parent
        self.scan_service = scan_service or ScanService()
        self.threat_action_service = ThreatActionService()
        self.quarantine_service = quarantine_service or QuarantineService()
        self.process_detector = process_detector or BrowserProcessDetector(
            adapter=self.scan_service.platform,
        )
        self.preferences_service = (
            preferences_service or ScanPreferencesService()
        )
        self.worker = None
        self._pending_scan_request = None
        self.current_scan_id = None
        self.last_scan_status = None
        self._history_flush_timer = QTimer(self)
        self._history_flush_timer.setSingleShot(True)
        self._history_flush_timer.timeout.connect(self._flush_history)
        self._reset_execution_state()

    def start_smart_scan(self):
        return self._request_scan("SMART")

    def start_custom_scan(self, path):
        return self._request_scan("CUSTOM", path)

    def _request_scan(self, profile, path=None):
        if self._is_running() or self._pending_scan_request is not None:
            return False

        if self.preferences_service.should_warn_for_scan(profile):
            browsers = self.process_detector.get_running_browsers()
            if browsers:
                self._pending_scan_request = (profile, path)
                self.browser_warning_requested.emit(browsers)
                return False

        return self._start_scan(profile, path)

    def resolve_browser_warning(self, continue_scan, dont_show_again=False):
        pending = self._pending_scan_request
        self._pending_scan_request = None

        if dont_show_again:
            self.set_browser_warning_enabled(False)

        if not pending or not continue_scan:
            return False

        profile, path = pending
        return self._start_scan(profile, path)

    def browser_warning_enabled(self):
        return self.preferences_service.browser_warning_enabled()

    def set_browser_warning_enabled(self, enabled):
        enabled = bool(enabled)
        self.preferences_service.set_browser_warning_enabled(enabled)
        self.browser_warning_preference_changed.emit(enabled)

    def _is_running(self):
        return bool(self.worker and self.worker.isRunning())

    def _reset_execution_state(self):
        self.scan_failed = False
        self.scan_cancelled = False
        self.audit_failed = False
        self._scan_active = False
        self._scan_finalized = False
        self._engine_error = None
        self._audit_errors = []
        self._registered_threats = set()
        self._pending_threats = []
        self._treated_threats = 0
        self._action_failures = 0
        if hasattr(self, "_history_flush_timer"):
            self._history_flush_timer.stop()

    def _start_scan(self, profile, path=None):
        self._reset_execution_state()
        self.current_scan_id = None
        self.last_scan_status = None

        try:
            if not self.scan_service.connect_engine():
                self.scan_error.emit("ClamAV não disponível")
                return False
        except Exception as exc:
            self.scan_error.emit(f"Falha ao conectar ao ClamAV: {exc}")
            return False

        try:
            self.current_scan_id = self.scan_service.start_scan(
                profile=profile,
                directory=path,
            )
        except Exception as exc:
            self.scan_error.emit(
                "O scan não foi iniciado porque o histórico não pôde ser "
                f"criado: {exc}"
            )
            return False

        self.worker = ScanWorker(
            service=self.scan_service,
            profile=profile,
            custom_path=path,
        )
        self._bind_worker_signals()
        self._scan_active = True
        self.scan_started.emit()
        self.worker.start()
        return True

    def _bind_worker_signals(self):
        self.worker.progress.connect(self.progress_updated.emit)
        self.worker.file_changed.connect(self.current_file_changed.emit)
        self.worker.threat_found.connect(self._on_threat)
        self.worker.error.connect(self._on_error)
        self.worker.finished.connect(self._on_finished)

    def _on_threat(self, result):
        if (
            not self._scan_active
            or self._scan_finalized
            or not self.current_scan_id
            or not result
            or not getattr(result, "infected", False)
        ):
            return

        file_path = result.detected_file.path
        virus_name = result.virus.name
        event_key = (str(file_path), str(virus_name))

        if event_key in self._registered_threats:
            return
        self._registered_threats.add(event_key)

        decided_action = self.threat_action_service.decide(
            file_path=file_path,
            virus_name=virus_name,
        )
        result.action = self._execute_threat_action(
            decided_action,
            file_path,
            virus_name,
        )

        self._pending_threats.append(
            (
                result.detected_file,
                result.virus,
                result.action,
                result.virus.detection_date or datetime.now(),
            )
        )
        if len(self._pending_threats) >= self.HISTORY_BATCH_SIZE:
            self._flush_history()
        else:
            self._history_flush_timer.start(self.HISTORY_FLUSH_INTERVAL_MS)

        self.threat_detected.emit(result)

    def _flush_history(self, final=False):
        if not self._pending_threats or not self.current_scan_id:
            return True

        pending = self._pending_threats
        self._pending_threats = []
        self._history_flush_timer.stop()

        try:
            self.scan_service.register_threats(
                scan_id=self.current_scan_id,
                threats=pending,
            )
            return True
        except Exception as exc:
            self._pending_threats = pending + self._pending_threats
            message = (
                "Falha de auditoria ao registrar lote de ameaças: "
                f"scan_id={self.current_scan_id}, itens={len(pending)}, "
                f"causa={exc}"
            )
            self.scan_error.emit(message)
            if final:
                self.audit_failed = True
                self._audit_errors.append(message)
            else:
                self._history_flush_timer.start(
                    self.HISTORY_FLUSH_INTERVAL_MS * 3
                )
            return False

    def _execute_threat_action(self, action, file_path, virus_name):
        if action == ThreatActionService.ACTION_QUARANTINE:
            try:
                self.quarantine_service.quarantine_from_scan(
                    file_path,
                    virus_name,
                )
                self._treated_threats += 1
                return "quarantine"
            except Exception as exc:
                self._action_failures += 1
                self.scan_error.emit(
                    f"Falha ao colocar '{file_path}' em quarentena: {exc}"
                )
                return "failed"

        if action == ThreatActionService.ACTION_IGNORE:
            return "ignored"

        if action == ThreatActionService.ACTION_SUGGEST_QUARANTINE:
            return "alert"

        return "alert"

    def _on_error(self, message):
        self.scan_failed = True
        self._engine_error = str(message or "Erro desconhecido no motor de scan.")
        self.scan_error.emit(self._engine_error)

    def _on_finished(self, results):
        if self._scan_finalized or not self.current_scan_id:
            return

        self._scan_finalized = True
        self._scan_active = False
        results = list(results or [])
        infected_paths = {
            getattr(getattr(result, "detected_file", None), "path", None)
            for result in results
            if getattr(result, "infected", False)
        }
        infected_paths.discard(None)
        infected = len(infected_paths)
        scanned_files = 0
        failed_files = self._action_failures

        if self.worker is not None:
            scanned_files = max(0, getattr(self.worker, "scanned_files", 0))
            failed_files += max(0, getattr(self.worker, "failed_files", 0))

        total_files = max(scanned_files, infected)
        self._flush_history(final=True)
        status, error = self._final_status(failed_files)

        try:
            self.scan_service.finish_scan(
                scan_id=self.current_scan_id,
                total_files=total_files,
                infected_files=infected,
                treated_threats=self._treated_threats,
                failed_files=failed_files,
                status=status,
                error=error,
            )
        except Exception as exc:
            status = "audit_failed"
            self.scan_error.emit(
                "Falha ao finalizar o histórico: "
                f"scan_id={self.current_scan_id}, causa={exc}. "
                "O resultado do scan foi preservado em memória, mas a "
                "auditoria final pode estar incompleta."
            )

        self.last_scan_status = status
        self.current_scan_id = None
        self._pending_threats = []
        self.scan_finished.emit(results)

    def _final_status(self, failed_files):
        if self.scan_cancelled:
            return "cancelled", "Scan cancelado pelo usuário."
        if self.scan_failed:
            return "failed", self._engine_error
        if self.audit_failed:
            return "audit_failed", "; ".join(self._audit_errors)
        if failed_files:
            return (
                "completed_with_failures",
                f"Scan concluído com {failed_files} falha(s) parcial(is).",
            )
        return "completed", None

    def interrupt_scan(self):
        if not self._is_running() or not self._scan_active:
            return

        self.scan_cancelled = True
        try:
            self.worker.stop()
        except Exception as exc:
            self.scan_cancelled = False
            self.scan_failed = True
            self._engine_error = f"Falha ao interromper o worker: {exc}"
            self.scan_error.emit(self._engine_error)

    def get_scan_history(self, filters=None, limit=50, offset=0):
        return self.scan_service.get_scan_history(
            filters=filters,
            limit=limit,
            offset=offset,
        )

    def get_scan_by_id(self, scan_id):
        return self.scan_service.get_scan_by_id(scan_id)

    def get_scan_threats(self, scan_id, limit=None, offset=0):
        return self.scan_service.get_scan_threats(
            scan_id,
            limit=limit,
            offset=offset,
        )
