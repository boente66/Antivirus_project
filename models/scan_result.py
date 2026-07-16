from datetime import datetime

from models.detected_file import DetectedFile


class ScanResult:
    def __init__(
        self,
        file_path=None,
        status=None,
        signature=None,
        infected=False,
        datetime_scanned=None,
        *,
        detected_file=None,
        virus=None,
        action=None
    ):
        if detected_file is None and hasattr(file_path, "path"):
            detected_file = file_path
            file_path = None

        if file_path is None and detected_file is not None:
            file_path = detected_file.path

        if detected_file is None and file_path is not None:
            detected_file = DetectedFile(file_path)

        if signature is None and virus is not None:
            signature = virus.name

        if status is None:
            status = "INFECTED" if infected else "CLEAN"

        self.detected_file = detected_file
        self.virus = virus
        self.infected = infected
        self.action = action

        self.file_path = file_path
        self.status = status
        self.signature = signature
        self.datetime_scanned = datetime_scanned or datetime.now()
