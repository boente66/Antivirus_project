from PyQt5.QtCore import QThread, pyqtSignal


class CleanerWorker(QThread):

    progress = pyqtSignal(int)
    log = pyqtSignal(str)
    finished = pyqtSignal(str)
    error = pyqtSignal(str)

    def __init__(
        self,
        service,
        tasks,
        target_path,
        require_admin: bool = False,
        analyze_only: bool = False
    ):
        super().__init__()

        self.service = service
        self.tasks = tasks or []
        self.target_path = target_path
        self.require_admin = require_admin
        self.analyze_only = analyze_only

        self._running = True

    # --------------------------------------------------
    # Controle externo
    # --------------------------------------------------

    def stop(self):
        self._running = False

    # --------------------------------------------------
    # Execução principal
    # --------------------------------------------------

    def run(self):

        try:

            if not self.service:
                raise ValueError("CleanerWorker: service não informado.")

            if not isinstance(self.tasks, list):
                raise ValueError("CleanerWorker: tasks deve ser uma lista.")

            if not self._running:
                return

            # --------------------------------------------------
            # callbacks seguros
            # --------------------------------------------------

            def progress_cb(percent):

                if not self._running:
                    return

                try:
                    percent = max(0, min(100, int(percent)))
                except Exception:
                    percent = 0

                self.progress.emit(percent)

            def log_cb(msg):

                if not self._running:
                    return

                if isinstance(msg, str):
                    self.log.emit(msg)

            # ==================================================
            # 🔎 MODO ANÁLISE
            # ==================================================

            if self.analyze_only:

                log_cb("Iniciando análise de limpeza...")

                total_items_found, total_size = self.service.analyze(
                    tasks=self.tasks,
                    target_path=self.target_path,
                    progress_cb=progress_cb,
                    log_cb=log_cb,
                )

                if not self._running:
                    return

                total_size = total_size or 0
                total_items_found = total_items_found or 0

                size_mb = total_size / 1024 / 1024

                self.progress.emit(100)

                self.finished.emit(
                    f"Análise concluída: {total_items_found} itens "
                    f"({size_mb:.2f} MB podem ser liberados)"
                )

                return

            # ==================================================
            # 🧹 MODO LIMPEZA
            # ==================================================

            log_cb("Iniciando processo de limpeza...")

            removed, freed = self.service.clean(
                tasks=self.tasks,
                target_path=self.target_path,
                require_admin=self.require_admin,
                progress_cb=progress_cb,
                log_cb=log_cb,
            )

            if not self._running:
                return

            removed = removed or 0
            freed = freed or 0

            freed_mb = freed / 1024 / 1024

            self.progress.emit(100)

            self.finished.emit(
                f"Limpeza concluída: {removed} itens removidos "
                f"({freed_mb:.2f} MB liberados)"
            )

        except Exception as e:

            self.error.emit(str(e))