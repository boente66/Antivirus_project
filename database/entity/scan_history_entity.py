class ScanHistoryEntity:
    def __init__(
        self,
        id,
        user,
        scan_type,
        start_time,
        end_time,
        directory_scanned,
        total_files,
        infected_files,
        treated_threats,
        failed_files,
        status,
        error_message=None,
        threat_count=0
    ):
        self.id = id
        self.user = user
        self.scan_type = scan_type
        self.start_time = start_time
        self.end_time = end_time
        self.directory_scanned = directory_scanned
        self.total_files = total_files or 0
        self.infected_files = infected_files or 0
        self.treated_threats = treated_threats or 0
        self.failed_files = failed_files or 0
        self.status = status
        self.error_message = error_message
        self.threat_count = threat_count or 0

    @classmethod
    def from_row(cls, row):
        keys = set(row.keys())
        return cls(
            id=row["id"],
            user=row["user"],
            scan_type=row["scan_type"] if "scan_type" in keys else None,
            start_time=row["start_time"],
            end_time=row["end_time"],
            directory_scanned=row["directory_scanned"],
            total_files=row["total_files"],
            infected_files=row["infected_files"],
            treated_threats=(
                row["treated_threats"] if "treated_threats" in keys else 0
            ),
            failed_files=row["failed_files"] if "failed_files" in keys else 0,
            status=row["status"],
            error_message=row["error_message"],
            threat_count=row["threat_count"] if "threat_count" in keys else 0,
        )
