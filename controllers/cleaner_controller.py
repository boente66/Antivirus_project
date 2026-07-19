import json
import subprocess
import sys
from pathlib import Path

from PyQt5.QtCore import QObject, pyqtSignal
from PyQt5.QtWidgets import QDialog

from core.platform.platform_factory import PlatformFactory
from services.browser_detection_service import BrowserDetectionService
from services.cleaner_service import CleanerService
from views.admin_dialog import AdminPermissionDialog
from workers.cleaner_worker import CleanerWorker


class CleanerController(QObject):
    cleaning_started = pyqtSignal(str)
    cleaning_progress = pyqtSignal(int)
    cleaning_log = pyqtSignal(str)
    analysis_completed = pyqtSignal(object)
    cleaning_completed = pyqtSignal(object)
    cleaning_cancelled = pyqtSignal(object)
    error = pyqtSignal(str)

    def __init__(
        self,
        service=None,
        *,
        adapter=None,
        browser_detection=None,
        subprocess_runner=None,
        admin_dialog_factory=None,
    ):
        super().__init__()
        self.adapter = adapter or (service.adapter if service else PlatformFactory.create())
        self.service = service or CleanerService(self.adapter)
        self.browser_detection = browser_detection or BrowserDetectionService(self.adapter)
        self.subprocess_runner = subprocess_runner or subprocess.run
        self.admin_dialog_factory = admin_dialog_factory or AdminPermissionDialog

        capabilities = self.adapter.get_cleaner_capabilities()
        self.supported = bool(capabilities.get("supported", False))
        self.support_message = capabilities.get("message", "Cleaner indisponível.")

        self.worker = None
        self._mode = None
        self._pending_admin_tasks = []
        self._normal_result = None
        self._last_analysis = None
        self._last_selection = None
        self._admin_running = False

    def is_running(self):
        return self.worker is not None or self._admin_running

    def build_tasks_from_selection(self, selected_labels):
        if not isinstance(selected_labels, (list, tuple, set)):
            raise ValueError("CleanerController: seleção inválida.")

        labels = set(selected_labels)
        home = Path(self.adapter.get_home_directory()).expanduser().resolve()
        tasks = []

        browser_selection = {
            "Firefox": self._browser_categories(labels, "Firefox"),
            "Chrome": self._browser_categories(labels, "Chrome"),
            "Chromium": self._browser_categories(labels, "Chromium"),
            "Brave": self._browser_categories(labels, "Brave"),
            "Edge": self._browser_categories(labels, "Edge"),
            "Opera": self._browser_categories(labels, "Opera"),
        }
        tasks.extend(self.browser_detection.get_tasks(browser_selection))

        if "Arquivos temporários" in labels:
            for raw in self.adapter.get_temp_directories() or []:
                if not raw:
                    continue
                path = Path(raw).expanduser().resolve(strict=False)
                inside_home = self._same_or_child(path, home)
                tasks.append({
                    "category": "temporary" if inside_home else "system_temporary",
                    "paths": [str(path)],
                    "requires_admin": not inside_home,
                    "removal_mode": CleanerService.MODE_PERMANENT,
                })

        if "Cache de miniaturas" in labels:
            tasks.append({
                "category": "user_cache",
                "paths": [str(home / ".cache" / "thumbnails")],
                "requires_admin": False,
                "removal_mode": CleanerService.MODE_PERMANENT,
            })

        if "Lixeira" in labels:
            trash_paths = [
                home / ".local/share/Trash/files",
                home / ".Trash",
            ]
            tasks.append({
                "category": "trash",
                "paths": [str(path) for path in trash_paths],
                "requires_admin": False,
                "removal_mode": CleanerService.MODE_PERMANENT,
            })

        if "Cache de aplicativos" in labels:
            tasks.append({
                "category": "user_cache",
                "paths": [str(home / ".cache")],
                "requires_admin": False,
                "removal_mode": CleanerService.MODE_PERMANENT,
            })

        return tasks

    def start_analyze(self, selected_labels):
        if not self._can_start("análise"):
            return False
        try:
            tasks = self.build_tasks_from_selection(selected_labels)
        except ValueError as exc:
            self.error.emit(str(exc))
            return False
        if not tasks:
            self.error.emit("Análise: nenhuma tarefa válida selecionada.")
            return False

        self._last_analysis = None
        self._last_selection = frozenset(selected_labels)
        self._start_worker(tasks, analyze_only=True)
        return True

    def start_clean(self, selected_labels):
        if not self._can_start("limpeza"):
            return False
        if not self._last_analysis or not self._last_analysis.get("candidates"):
            self.error.emit("Limpeza: execute uma análise válida antes de limpar.")
            return False
        if frozenset(selected_labels) != self._last_selection:
            self.error.emit(
                "Limpeza: a seleção mudou; execute uma nova análise antes de limpar."
            )
            return False
        try:
            tasks = self.build_tasks_from_selection(selected_labels)
        except ValueError as exc:
            self.error.emit(str(exc))
            return False
        if not tasks:
            self.error.emit("Limpeza: nenhuma tarefa válida selecionada.")
            return False

        normal = [task for task in tasks if not task.get("requires_admin")]
        self._pending_admin_tasks = [task for task in tasks if task.get("requires_admin")]
        self._normal_result = None

        if normal:
            self._start_worker(normal, analyze_only=False)
        else:
            self._mode = "clean"
            self.cleaning_started.emit("clean")
            self._run_pending_admin()
        return True

    def stop(self):
        if self.worker is None:
            return False
        self.worker.stop()
        self.cleaning_log.emit(
            "Cancelamento solicitado; nenhuma nova remoção será iniciada."
        )
        return True

    def _start_worker(self, tasks, *, analyze_only):
        self._mode = "analyze" if analyze_only else "clean"
        self.worker = CleanerWorker(
            service=self.service,
            tasks=list(tasks),
            target_path=self.adapter.get_home_directory(),
            require_admin=False,
            analyze_only=analyze_only,
        )
        self.worker.progress.connect(self.cleaning_progress.emit)
        self.worker.log.connect(self.cleaning_log.emit)
        self.worker.finished.connect(self._on_finished)
        self.worker.error.connect(self._on_error)
        self.cleaning_started.emit(self._mode)
        self.worker.start()

    def _on_finished(self, result):
        mode = self._mode
        self.worker = None

        if result.get("cancelled"):
            self._pending_admin_tasks = []
            self._last_analysis = None
            self._last_selection = None
            self.cleaning_cancelled.emit(result)
            return

        if mode == "analyze":
            self._last_analysis = result
            self.analysis_completed.emit(result)
            return

        self._normal_result = result
        if self._pending_admin_tasks:
            self._run_pending_admin()
        else:
            self._complete_clean(result)

    def _on_error(self, message):
        self.worker = None
        self._pending_admin_tasks = []
        self._last_analysis = None
        self._last_selection = None
        self.error.emit(message)

    def _run_pending_admin(self):
        tasks = list(self._pending_admin_tasks)
        self._pending_admin_tasks = []
        if not tasks:
            self._complete_clean(self._normal_result or self._empty_result())
            return

        dialog = self.admin_dialog_factory(
            None,
            reason="Limpar apenas diretórios temporários administrativos autorizados",
        )
        if dialog.exec_() != QDialog.Accepted:
            result = self._normal_result or self._empty_result()
            result = dict(result)
            result["cancelled"] = True
            result["status"] = CleanerService.STATUS_CANCELLED
            result["errors"] = list(result.get("errors", [])) + [{
                "path": None,
                "category": "admin",
                "code": "authentication_cancelled",
                "message": "Autenticação administrativa cancelada pelo usuário.",
            }]
            self.service.record_result(result)
            self.cleaning_cancelled.emit(result)
            return

        self._admin_running = True
        try:
            admin_result = self._execute_admin(tasks)
        except (FileNotFoundError, PermissionError, RuntimeError, OSError) as exc:
            admin_result = self._empty_result()
            admin_result.update({
                "status": CleanerService.STATUS_FAILED,
                "selected": sum(len(task.get("paths", [])) for task in tasks),
                "failed": 1,
                "errors": [{
                    "path": None,
                    "category": "admin",
                    "code": "admin_execution_failed",
                    "message": f"Limpeza administrativa falhou: {exc}",
                }],
            })
            self.service.record_result(admin_result)
            self.cleaning_log.emit(admin_result["errors"][0]["message"])
            self._complete_clean(self._merge_results(self._normal_result, admin_result))
            return
        finally:
            self._admin_running = False

        self._complete_clean(self._merge_results(self._normal_result, admin_result))

    def _execute_admin(self, tasks):
        project_root = Path(__file__).resolve().parents[1]
        executor = project_root / "services" / "admin_executor.py"
        if not executor.is_file():
            raise FileNotFoundError(
                f"executor administrativo não encontrado: {executor}"
            )

        command = [
            "pkexec",
            sys.executable,
            str(executor),
        ]
        try:
            completed = self.subprocess_runner(
                command,
                capture_output=True,
                text=True,
                input=json.dumps(tasks, ensure_ascii=False),
                timeout=300,
                check=False,
            )
        except FileNotFoundError as exc:
            raise FileNotFoundError("pkexec não encontrado") from exc

        stderr = (completed.stderr or "").strip()
        if completed.returncode in (126, 127):
            raise PermissionError(
                f"autenticação cancelada ou negada{': ' + stderr if stderr else ''}"
            )
        if completed.returncode != 0:
            raise RuntimeError(
                f"comando administrativo retornou {completed.returncode}"
                f"{': ' + stderr if stderr else ''}"
            )

        lines = [line for line in (completed.stdout or "").splitlines() if line.strip()]
        if not lines:
            raise RuntimeError("executor administrativo não retornou resultado")
        try:
            result = json.loads(lines[-1])
        except json.JSONDecodeError as exc:
            raise RuntimeError("resposta administrativa inválida") from exc
        if not isinstance(result, dict) or "status" not in result:
            raise RuntimeError("resultado administrativo incompleto")
        return result

    def _complete_clean(self, result):
        self._last_analysis = None
        self._last_selection = None
        if result.get("cancelled"):
            self.cleaning_cancelled.emit(result)
        else:
            self.cleaning_completed.emit(result)

    def _can_start(self, operation):
        if not self.supported:
            self.error.emit(self.support_message)
            return False
        if self.is_running():
            self.error.emit(
                f"Não é possível iniciar {operation}: outra operação está ativa."
            )
            return False
        return True

    @staticmethod
    def _browser_categories(labels, browser):
        categories = []
        if f"Cache do {browser}" in labels:
            categories.append("cache")
        if f"Cookies do {browser}" in labels:
            categories.append("cookies")
        return categories

    @staticmethod
    def _same_or_child(path, parent):
        try:
            path.relative_to(parent)
            return True
        except ValueError:
            return False

    @staticmethod
    def _empty_result():
        return {
            "operation": "clean",
            "status": CleanerService.STATUS_COMPLETED,
            "selected": 0,
            "processed": 0,
            "removed": 0,
            "ignored": 0,
            "failed": 0,
            "bytes_freed": 0,
            "cancelled": False,
            "permanent": False,
            "errors": [],
        }

    @staticmethod
    def _merge_results(first, second):
        if not first:
            return second
        merged = dict(first)
        for key in ("selected", "processed", "removed", "ignored", "failed", "bytes_freed"):
            merged[key] = int(first.get(key, 0)) + int(second.get(key, 0))
        merged["errors"] = list(first.get("errors", [])) + list(second.get("errors", []))
        merged["cancelled"] = bool(first.get("cancelled") or second.get("cancelled"))
        merged["permanent"] = bool(first.get("permanent") or second.get("permanent"))
        if merged["cancelled"]:
            merged["status"] = CleanerService.STATUS_CANCELLED
        elif merged["failed"] or merged["errors"]:
            merged["status"] = (
                CleanerService.STATUS_PARTIAL
                if merged["processed"] or merged["removed"]
                else CleanerService.STATUS_FAILED
            )
        else:
            merged["status"] = CleanerService.STATUS_COMPLETED
        return merged
