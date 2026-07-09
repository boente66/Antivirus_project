import os
from watchdog.events import FileSystemEventHandler

class RansomwareProtectionHandler(FileSystemEventHandler):
    def __init__(self, callback):
        self.callback = callback

    def on_modified(self, event):
        if event.is_directory:
            return

        file_path = event.src_path
        file_extension = os.path.splitext(file_path)[1]

        if file_extension not in [".txt", ".docx", ".pdf"]:
            self.callback("Arquivo suspeito modificado", file_path)

    def on_created(self, event):
        if event.is_directory:
            return

        file_path = event.src_path
        self.callback("Arquivo suspeito criado", file_path)