from PyQt5.QtCore import QObject, pyqtSignal


class DiskUsageWorker(QObject):

    finished = pyqtSignal(object)
    error = pyqtSignal(str)

    progress = pyqtSignal(int)
    status = pyqtSignal(str)

    def __init__(self, controller, mountpoint):

        super().__init__()

        self.controller = controller
        self.mountpoint = mountpoint

        self._running = True

    # --------------------------------------------------
    # Cancelamento
    # --------------------------------------------------

    def cancel(self):

        self._running = False

    # --------------------------------------------------
    # Execução
    # --------------------------------------------------

    def run(self):

        try:

            if not self.controller:
                raise ValueError("DiskUsageWorker: controller não informado.")

            if not self.mountpoint:
                raise ValueError("DiskUsageWorker: mountpoint inválido.")

            if not self._running:
                return

            # ----------------------------------
            # resumo do disco
            # ----------------------------------

            self.status.emit("Obtendo informações do disco...")

            summary = self.controller.get_volume_summary(
                self.mountpoint
            )

            if not self._running:
                return

            # ----------------------------------
            # análise de diretórios
            # ----------------------------------

            self.status.emit("Analisando diretórios principais...")

            breakdown = self.controller.get_directory_breakdown(
                self.mountpoint
            )

            if not breakdown:
                breakdown = []

            total_dirs = max(len(breakdown), 1)

            processed = 0

            result_dirs = []

            for item in breakdown:

                if not self._running:
                    self.status.emit("Operação cancelada.")
                    return

                processed += 1

                try:
                    percent = int((processed / total_dirs) * 100)
                except Exception:
                    percent = 0

                percent = max(0, min(100, percent))

                self.progress.emit(percent)

                path = item.get("path") or item.get("name") or "desconhecido"

                self.status.emit(
                    f"Processando: {path}"
                )

                result_dirs.append(item)

            # ----------------------------------
            # resultado final
            # ----------------------------------

            result = {
                "summary": summary,
                "breakdown": result_dirs
            }

            if self._running:
                self.progress.emit(100)
                self.status.emit("Análise concluída")
                self.finished.emit(result)

        except Exception as e:

            self.error.emit(str(e))