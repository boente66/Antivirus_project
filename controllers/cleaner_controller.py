from PyQt5.QtCore import QObject, pyqtSignal
from PyQt5.QtWidgets import QDialog

import os
import json
import subprocess
import sys
from pathlib import Path

from views.admin_dialog import AdminPermissionDialog
from workers.cleaner_worker import CleanerWorker
from services.cleaner_service import CleanerService
from services.browser_detection_service import BrowserDetectionService

from core.platform.platform_factory import PlatformFactory


class CleanerController(QObject):

    # -------------------------
    # SINAIS
    # -------------------------

    cleaning_progress = pyqtSignal(int)
    cleaning_log = pyqtSignal(str)
    cleaning_completed = pyqtSignal(str)
    error = pyqtSignal(str)

    # -------------------------
    # INIT
    # -------------------------

    def __init__(self, service=None):

        super().__init__()

        self.adapter = PlatformFactory.create()
        self.service = service or CleanerService(self.adapter)
        self.browser_detection = BrowserDetectionService(self.adapter)

        self.worker = None
        self._pending_admin_tasks = []

    # =====================================================
    # 🔧 CONSTRUIR TASKS
    # =====================================================

    def build_tasks_from_selection(self, selected_labels):

        home = Path(self.adapter.get_home_directory())
        tasks = []

        temp_dirs = self.adapter.get_temp_directories()
        system_dirs = self.adapter.get_system_directories()

        for label in selected_labels:

            # -------------------------
            # BROWSERS
            # -------------------------

            if label in (
                "Cache do Firefox",
                "Cookies do Firefox",
                "Cache do Chrome",
                "Cookies do Chrome"
            ):

                tasks.extend(self.build_browser_tasks())
                continue

            # -------------------------
            # LOGS DO SISTEMA
            # -------------------------

            if label == "Logs do sistema":

                for path in system_dirs:

                    if "log" in path.lower():

                        tasks.append({
                            "action": "delete",
                            "paths": [path],
                            "requires_admin": True
                        })

                continue

            # -------------------------
            # TEMP FILES
            # -------------------------

            if label == "Arquivos temporários":

                for p in temp_dirs:

                    tasks.append({
                        "action": "delete",
                        "paths": [p],
                        "requires_admin": not p.startswith(home.as_posix())
                    })

                continue

            # -------------------------
            # CACHE THUMBNAILS
            # -------------------------

            if label == "Cache de miniaturas":

                tasks.append({
                    "action": "delete",
                    "paths": [str(home / ".cache" / "thumbnails")],
                    "requires_admin": False
                })

                continue

            # -------------------------
            # TRASH
            # -------------------------

            if label == "Lixeira":

                trash_paths = [

                    home / ".local/share/Trash/files",
                    home / ".Trash",

                    Path(os.getenv("TEMP", "")) / "Recycle.Bin"
                ]

                tasks.append({
                    "action": "delete",
                    "paths": [str(p) for p in trash_paths if p.exists()],
                    "requires_admin": False
                })

                continue

            # -------------------------
            # APP CACHE
            # -------------------------

            if label == "Cache de aplicativos":

                tasks.append({
                    "action": "delete",
                    "paths": [str(home / ".cache")],
                    "requires_admin": False
                })

                continue

        return tasks

    # =====================================================
    # 🔍 BROWSER TASKS
    # =====================================================

    def build_browser_tasks(self):

        browsers = self.browser_detection.detect()
        tasks = []

        for _, categories in browsers.items():

            for _, paths in categories.items():

                tasks.append({
                    "action": "delete",
                    "paths": paths,
                    "requires_admin": False
                })

        return tasks

    # =====================================================
    # 🔍 ANÁLISE
    # =====================================================

    def start_analyze(self, selected_labels):

        if self.worker:
            return

        tasks = self.build_tasks_from_selection(selected_labels)

        self.worker = CleanerWorker(
            service=self.service,
            tasks=tasks,
            target_path=self.adapter.get_home_directory(),
            require_admin=False,
            analyze_only=True
        )

        self._bind_worker()

        self.worker.start()

    # =====================================================
    # 🧹 LIMPEZA
    # =====================================================

    def start_clean(self, selected_labels):

        if self.worker:
            return

        tasks = self.build_tasks_from_selection(selected_labels)

        admin_tasks = [t for t in tasks if t.get("requires_admin")]
        normal_tasks = [t for t in tasks if not t.get("requires_admin")]

        self._pending_admin_tasks = admin_tasks

        if normal_tasks:

            self.worker = CleanerWorker(
                service=self.service,
                tasks=normal_tasks,
                target_path=self.adapter.get_home_directory(),
                require_admin=False,
                analyze_only=False
            )

            self._bind_worker()

            self.worker.start()

        else:

            self._execute_admin_if_needed()

    # =====================================================
    # 🔐 EXECUÇÃO ADMIN
    # =====================================================

    def _execute_admin_if_needed(self):

        if not self._pending_admin_tasks:
            return

        dlg = AdminPermissionDialog(
            None,
            reason="Remover arquivos do sistema"
        )

        if dlg.exec_() != QDialog.Accepted:

            self.error.emit("Operação administrativa cancelada.")
            self._pending_admin_tasks = []

            return

        self._run_admin_tasks(self._pending_admin_tasks)

        self._pending_admin_tasks = []

    # =====================================================
    # EXECUÇÃO PKEXEC
    # =====================================================

    def _run_admin_tasks(self, tasks):

        try:

            payload = json.dumps(tasks)

            subprocess.run(
                [
                    "pkexec",
                    sys.executable,
                    "-m",
                    "services.admin_executor",
                    payload
                ],
                check=True
            )

            self.cleaning_completed.emit(
                "Tarefas administrativas concluídas com sucesso."
            )

        except subprocess.CalledProcessError as e:

            self.error.emit(f"Erro administrativo: {e}")

    # =====================================================
    # STOP
    # =====================================================

    def stop(self):

        if self.worker:

            self.worker.stop()

    # =====================================================
    # WORKER CONNECTIONS
    # =====================================================

    def _bind_worker(self):

        self.worker.progress.connect(self.cleaning_progress.emit)
        self.worker.log.connect(self.cleaning_log.emit)

        self.worker.finished.connect(self._on_finished)
        self.worker.error.connect(self._on_error)

    # =====================================================
    # CALLBACKS
    # =====================================================

    def _on_finished(self, message):

        self.worker = None

        self.cleaning_completed.emit(message)

        self._execute_admin_if_needed()

    def _on_error(self, message):

        self.worker = None

        self.error.emit(message)
