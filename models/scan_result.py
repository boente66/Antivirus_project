from datetime import datetime
from typing import Optional

from models.detected_file import DetectedFile
from models.virus_model import Virus


class ScanResult:
    """Represents the result of a scan operation on a file."""

    def __init__(
        self,
        file_path=None,
        status=None,
        signature=None,
        infected: bool = False,
        datetime_scanned=None,
        *,
        detected_file: Optional[DetectedFile] = None,
        virus: Optional[Virus] = None,
        action: Optional[str] = None
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
        self.infected = bool(infected)
        self.action = action

        self.file_path = file_path
        self.status = status
        self.signature = signature
        self.datetime_scanned = datetime_scanned or datetime.now()
