from dataclasses import dataclass
from datetime import datetime

@dataclass
class ScanResult:
    file_path: str
    status: str
    signature: str
    infected: bool
    datetime_scanned: datetime