from PyQt5.QtCore import QThread, pyqtSignal
import os

from models.scan_result import ScanResult


class ScanWorker(QThread):

    progress = pyqtSignal(int)
    file_changed = pyqtSignal(str)
    threat_found = pyqtSignal(ScanResult)
    error = pyqtSignal(str)
    finished = pyqtSignal(list)

    def __init__(self, service, profile, custom_path=None):

        super().__init__()

        self.service = service
        self.profile = profile
        self.custom_path = custom_path

        self.running = True
        self.results = []
        self.total_files = 0
        self.scanned_files = 0
        self.failed_files = 0

    # --------------------------------------------------
    # PROCESSO PRINCIPAL
    # --------------------------------------------------

    def run(self):

        try:

            if not self.service:
                raise RuntimeError("ScanWorker: serviço de scan não informado.")

            # ------------------------------------------
            # Conectar engine
            # ------------------------------------------

            if not self.service.is_connected():

                if not self.service.connect_engine():

                    raise RuntimeError(
                        "ClamAV engine não disponível"
                    )

            if not self.running:
                self.finished.emit(self.results)
                return

            # ------------------------------------------
            # Definir alvos
            # ------------------------------------------

            targets = self._get_targets()

            if not targets:
                raise RuntimeError("Nenhum alvo de scan encontrado.")

            # ------------------------------------------
            # Contar arquivos para progresso
            # ------------------------------------------

            self.total_files = self._count_files(targets)

            scanned = 0

            # ------------------------------------------
            # Scan real
            # ------------------------------------------

            for t in targets:

                if not self.running:
                    break

                for file_path in self.service.iter_files(t):

                    if not self.running:
                        break

                    scanned += 1
                    self.scanned_files = scanned

                    self.file_changed.emit(file_path)

                    try:

                        if not os.path.isfile(file_path):
                            continue

                        # ----------------------------------
                        # Análise via ScanService
                        # ----------------------------------

                        result = self.service.analyze_file(file_path)

                        if result and getattr(result, "infected", False):

                            self.results.append(result)

                            self.threat_found.emit(result)

                    except PermissionError:
                        self.failed_files += 1
                        continue

                    except FileNotFoundError:
                        self.failed_files += 1
                        continue

                    except Exception as exc:
                        raise RuntimeError(
                            f"Falha ao analisar '{file_path}': {exc}"
                        ) from exc

                    # ----------------------------------
                    # Atualizar progresso
                    # ----------------------------------

                    try:
                        percent = int((scanned / self.total_files) * 100)
                    except Exception:
                        percent = 0

                    percent = max(0, min(100, percent))

                    self.progress.emit(percent)

            # ------------------------------------------
            # Finalização
            # ------------------------------------------

            if self.running:
                self.progress.emit(100)

            self.finished.emit(self.results)

        except Exception as e:

            self.error.emit(str(e))

            self.finished.emit(self.results)

    # --------------------------------------------------
    # OBTER ALVOS
    # --------------------------------------------------

    def _get_targets(self):

        if self.profile == "SMART":

            targets = self.service.get_smart_scan_targets()

            return targets or []

        if not self.custom_path:

            raise RuntimeError(
                "Caminho personalizado inválido"
            )

        return [self.custom_path]

    # --------------------------------------------------
    # CONTAR ARQUIVOS
    # --------------------------------------------------

    def _count_files(self, targets):

        total = 0

        for t in targets:

            try:

                for _ in self.service.iter_files(t):

                    if not self.running:
                        return max(total, 1)

                    total += 1

            except Exception:
                continue

        return max(total, 1)

    # --------------------------------------------------
    # CANCELAR SCAN
    # --------------------------------------------------

    def stop(self):

        self.running = False
