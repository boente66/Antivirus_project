from database.database import Database
from database.entity.scan_history_entity import ScanHistoryEntity


class ScanHistoryRepository(Database):

    # ---------------------------------
    # CREATE
    # ---------------------------------
    def create_scan(self, user, directory_scanned, start_time, status):
        cursor = self.execute_query(
            """
            INSERT INTO scan_history (
                user, start_time, directory_scanned, status
            ) VALUES (?, ?, ?, ?)
            """,
            (
                user,
                start_time.isoformat(),
                directory_scanned,
                status
            )
        )
        return cursor.lastrowid

    # ---------------------------------
    # FINISH (OK)
    # ---------------------------------
    def finish_scan(self, scan_id, total_files, infected_files, end_time, status):
        self.execute_query(
            """
            UPDATE scan_history
            SET end_time = ?, total_files = ?, infected_files = ?, status = ?
            WHERE id = ?
            """,
            (
                end_time.isoformat(),
                total_files,
                infected_files,
                status,
                scan_id
            )
        )

    # ---------------------------------
    # FAIL
    # ---------------------------------
    def update_status(self, scan_id, status, error_message=None):
        self.execute_query(
            """
            UPDATE scan_history
            SET status = ?, error_message = ?
            WHERE id = ?
            """,
            (status, error_message, scan_id)
        )

    # ---------------------------------
    # LIST
    # ---------------------------------
    def list_all(self):
        rows = self.fetch_all(
            "SELECT * FROM scan_history ORDER BY start_time DESC"
        )
        return [ScanHistoryEntity.from_row(r) for r in rows]

    def get_recent_scans(self, limit=100):
        rows = self.fetch_all(
            "SELECT * FROM scan_history ORDER BY start_time DESC LIMIT ?",
            (limit,)
        )
        return [ScanHistoryEntity.from_row(r) for r in rows]

    # ---------------------------------
    # THREATS
    # ---------------------------------
    def add_threat(
        self,
        scan_id,
        file_path,
        virus_name,
        action,
        detection_time
    ):
        self.execute_query(
            """
            INSERT INTO scan_threats (
                scan_id, file_path, virus_name, action, detection_time
            ) VALUES (?, ?, ?, ?, ?)
            """,
            (
                scan_id,
                file_path,
                virus_name,
                action,
                detection_time.isoformat()
            )
        )
