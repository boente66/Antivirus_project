from database.database import Database
from database.entity.scan_history_entity import ScanHistoryEntity
from database.entity.scan_threat_entity import ScanThreatEntity


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

        if cursor is None:
            raise RuntimeError("Falha ao criar registro de scan.")

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
        return self._build_scan_history(rows)

    def get_recent_scans(self, limit=100, include_threats=True):
        rows = self.fetch_all(
            "SELECT * FROM scan_history ORDER BY start_time DESC LIMIT ?",
            (limit,)
        )
        return self._build_scan_history(
            rows,
            include_threats=include_threats
        )

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
        if not scan_id:
            raise ValueError("scan_id inválido para ameaça.")

        entity = ScanThreatEntity(
            scan_id=scan_id,
            file_path=file_path,
            virus_name=virus_name,
            action=action,
            detection_time=detection_time.isoformat()
        )

        cursor = self.execute_query(
            """
            INSERT INTO scan_threats (
                scan_id, file_path, virus_name, action, detection_time
            ) VALUES (?, ?, ?, ?, ?)
            """,
            entity.to_tuple()
        )

        if cursor is None:
            raise RuntimeError("Falha ao registrar ameaça do scan.")

        entity.id = cursor.lastrowid

        return entity.id

    def get_threats_by_scan(self, scan_id):
        rows = self.fetch_all(
            """
            SELECT *
            FROM scan_threats
            WHERE scan_id = ?
            ORDER BY detection_time ASC, id ASC
            """,
            (scan_id,)
        )

        return [ScanThreatEntity.from_row(row) for row in rows]

    def count_threats_by_scan(self, scan_id):
        row = self.fetch_one(
            "SELECT COUNT(*) AS total FROM scan_threats WHERE scan_id = ?",
            (scan_id,)
        )

        return row["total"] if row else 0

    def _build_scan_history(self, rows, include_threats=True):
        history = []

        for row in rows:
            threats = (
                self.get_threats_by_scan(row["id"])
                if include_threats
                else []
            )

            history.append(
                ScanHistoryEntity.from_row(
                    row,
                    threats=threats
                )
            )

        return history
