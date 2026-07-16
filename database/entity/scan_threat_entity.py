class ScanThreatEntity:
    def __init__(
        self,
        scan_id,
        file_path,
        virus_name,
        action,
        detection_time,
        id=None
    ):
        self.id = id
        self.scan_id = scan_id
        self.file_path = file_path
        self.virus_name = virus_name
        self.action = action
        self.detection_time = detection_time

    def to_tuple(self):
        return (
            self.scan_id,
            self.file_path,
            self.virus_name,
            self.action,
            self.detection_time
        )

    @classmethod
    def from_row(cls, row):
        return cls(
            scan_id=row["scan_id"],
            file_path=row["file_path"],
            virus_name=row["virus_name"],
            action=row["action"],
            detection_time=row["detection_time"],
            id=row["id"]
        )
