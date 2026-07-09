import os
import shutil
import threading
import time
from pathlib import Path
from queue import Empty


class RansomwareWorker(threading.Thread):

    def __init__(self, event_queue, quarantine_folder, notify_callback, logs):

        super().__init__(daemon=True)

        self.event_queue = event_queue
        self.quarantine_folder = Path(quarantine_folder)

        self.notify_callback = notify_callback
        self.logs = logs

        self.running = True

        # garantir pasta de quarentena
        self.quarantine_folder.mkdir(parents=True, exist_ok=True)

    # --------------------------------------------------
    # EXECUÇÃO
    # --------------------------------------------------

    def run(self):

        while self.running:

            try:

                # timeout permite parar a thread
                event_type, file_path = self.event_queue.get(timeout=1)

            except Empty:
                continue

            try:

                if not file_path:
                    continue

                message = f"Atenção! Evento {event_type}: {file_path}"

                self._log(message)

                quarantine_path = self._move_to_quarantine(file_path)

                if quarantine_path:

                    notify_msg = (
                        f"Arquivo suspeito isolado:\n{file_path}"
                    )

                    self.notify_callback(notify_msg)

                else:

                    self._log(
                        f"Falha ao mover para quarentena: {file_path}"
                    )

            except Exception as e:

                self._log(f"Erro no processamento do evento: {e}")

            finally:

                try:
                    self.event_queue.task_done()
                except Exception:
                    pass

    # --------------------------------------------------
    # STOP
    # --------------------------------------------------

    def stop(self):

        self.running = False

    # --------------------------------------------------
    # QUARENTENA
    # --------------------------------------------------

    def _move_to_quarantine(self, file_path):

        try:

            src = Path(file_path)

            if not src.exists():
                return None

            # nome único
            target = self.quarantine_folder / src.name

            i = 1
            while target.exists():

                target = self.quarantine_folder / f"{src.stem}_{i}{src.suffix}"
                i += 1

            shutil.move(str(src), str(target))

            self._log(
                f"Arquivo movido para quarentena: {target}"
            )

            return target

        except Exception as e:

            self._log(f"Erro ao mover arquivo: {e}")

            return None

    # --------------------------------------------------
    # LOG
    # --------------------------------------------------

    def _log(self, message):

        timestamp = time.strftime("%H:%M:%S")

        self.logs.append(
            f"[{timestamp}] {message}"
        )