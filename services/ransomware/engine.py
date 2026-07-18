import os
import shutil
from watchdog.observers import Observer
from .handler import RansomwareProtectionHandler


class RansomwareEngine:
    """Engine to monitor and protect against ransomware threats."""
    def __init__(self, path_to_monitor, quarantine_folder, callback):
        self.path_to_monitor = path_to_monitor
        self.quarantine_folder = quarantine_folder
        self.callback = callback
        self.observer = Observer()
        self.event_handler = RansomwareProtectionHandler(self._internal_callback)

    def _internal_callback(self, message, file_path):
        self.callback(message, file_path)

    def move_to_quarantine(self, file_path):
        try:
            if not os.path.exists(self.quarantine_folder):
                os.makedirs(self.quarantine_folder)
            shutil.move(file_path, self.quarantine_folder)
        except Exception as e:
            self.callback(f"Erro ao mover arquivo: {e}", None)

    def start(self):
        self.observer.schedule(self.event_handler, self.path_to_monitor, recursive=True)
        self.observer.start()

    def stop(self):
        self.observer.stop()
        self.observer.join()

    def start_protection(self):
        self.start()

    def stop_protection(self):
        self.stop()
