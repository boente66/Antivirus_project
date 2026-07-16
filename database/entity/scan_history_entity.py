class ScanHistoryEntity:
    def __init__(
        self,
        id,
        user,
        start_time,
        end_time,
        directory_scanned,
        total_files,
        infected_files,
        status,
        error_message=None,
        threats=None,
        threat_count=0
    ):
        self.id = id
        self.user = user
        self.start_time = start_time
        self.end_time = end_time
        self.directory_scanned = directory_scanned
        self.total_files = total_files
        self.infected_files = infected_files
        self.status = status
        self.error_message = error_message
        self.threats = threats or []
        self.threat_count = threat_count

    @classmethod
    def from_row(cls, row, threats=None):
        threats = threats or []

        return cls(
            row["id"],
            row["user"],
            row["start_time"],
            row["end_time"],
            row["directory_scanned"],
            row["total_files"],
            row["infected_files"],
            row["status"],
            row["error_message"],
            threats=threats,
            threat_count=len(threats)
        )
