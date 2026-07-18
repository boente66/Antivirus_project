import sqlite3
from datetime import datetime

from database.database import Database
from database.entity.scan_history_entity import ScanHistoryEntity
from database.entity.scan_threat_entity import ScanThreatEntity
from models.detected_file import DetectedFile
from models.virus_model import Virus


class ScanHistoryRepository(Database):
    """Persistência transacional do ciclo de vida de um scan."""

    ACTIVE_STATUS = "running"
    FINAL_STATUSES = {
        "completed",
        "completed_with_failures",
        "cancelled",
        "failed",
        "audit_failed",
        "interrupted",
    }
    THREAT_ACTIONS = {
        "alert",
        "quarantine",
        "ignored",
        "delete_confirmed",
        "failed",
    }
    DEFAULT_PAGE_SIZE = 50
    MAX_PAGE_SIZE = 500

    def start_scan(self, scan_type, started_at, target=None, user=None):
        scan_type = str(scan_type or "unknown").strip().lower()
        started_at = self._as_iso(started_at, "started_at")
        target = str(target or scan_type)
        user = str(user or "user")

        try:
            with self.operation_connection() as conn:
                cursor = conn.execute(
                    """
                    INSERT INTO scan_history (
                        user, scan_type, start_time, directory_scanned,
                        total_files, infected_files, treated_threats,
                        failed_files, status
                    ) VALUES (?, ?, ?, ?, 0, 0, 0, 0, ?)
                    """,
                    (user, scan_type, started_at, target, self.ACTIVE_STATUS),
                )
                return cursor.lastrowid
        except sqlite3.Error as exc:
            raise RuntimeError(
                f"Falha ao iniciar histórico do scan para '{target}': {exc}"
            ) from exc

    def add_threat(
        self,
        scan_id,
        detected_file,
        virus,
        action,
        detection_date=None,
    ):
        scan_id = self._valid_scan_id(scan_id)

        if not isinstance(detected_file, DetectedFile):
            raise TypeError("detected_file deve ser uma instância de DetectedFile.")
        if not isinstance(virus, Virus):
            raise TypeError("virus deve ser uma instância de Virus.")

        file_path = str(detected_file.path or "").strip()
        virus_name = str(virus.name or "").strip()
        action = str(action or "").strip().lower()

        if not file_path:
            raise ValueError("Caminho vazio ao registrar ameaça.")
        if not virus_name:
            raise ValueError("Nome da ameaça vazio ao registrar histórico.")
        if action not in self.THREAT_ACTIONS:
            raise ValueError(f"Ação de ameaça inválida: {action!r}.")

        detected_at = detection_date or virus.detection_date or datetime.now()
        detected_at = self._as_iso(detected_at, "detection_date")

        try:
            with self.operation_connection() as conn:
                conn.execute("BEGIN IMMEDIATE")
                scan = conn.execute(
                    "SELECT status FROM scan_history WHERE id = ?",
                    (scan_id,),
                ).fetchone()

                if scan is None:
                    raise ValueError(f"Scan inexistente: scan_id={scan_id}.")
                if self._normalize_status(scan["status"]) != self.ACTIVE_STATUS:
                    raise RuntimeError(
                        "Ameaça rejeitada porque o scan não está ativo: "
                        f"scan_id={scan_id}, status={scan['status']!r}."
                    )

                duplicate = conn.execute(
                    """
                    SELECT id
                    FROM scan_threats
                    WHERE scan_id = ? AND file_path = ? AND virus_name = ?
                    ORDER BY id ASC
                    LIMIT 1
                    """,
                    (scan_id, file_path, virus_name),
                ).fetchone()

                if duplicate is not None:
                    return duplicate["id"]

                cursor = conn.execute(
                    """
                    INSERT INTO scan_threats (
                        scan_id, file_path, virus_name, action, detection_time
                    ) VALUES (?, ?, ?, ?, ?)
                    """,
                    (scan_id, file_path, virus_name, action, detected_at),
                )
                return cursor.lastrowid
        except (TypeError, ValueError, RuntimeError):
            raise
        except sqlite3.Error as exc:
            raise RuntimeError(
                "Falha ao registrar ameaça no histórico: "
                f"scan_id={scan_id}, path='{file_path}', causa={exc}"
            ) from exc

    def add_threats(self, scan_id, threats):
        """Registra um lote de eventos em uma única transação curta."""
        scan_id = self._valid_scan_id(scan_id)
        prepared = [self._prepare_threat(item) for item in threats]
        if not prepared:
            return 0

        statement = """
            INSERT INTO scan_threats (
                scan_id, file_path, virus_name, action, detection_time
            )
            SELECT ?, ?, ?, ?, ?
            WHERE NOT EXISTS (
                SELECT 1 FROM scan_threats
                WHERE scan_id = ? AND file_path = ? AND virus_name = ?
            )
        """
        params = [
            (
                scan_id,
                file_path,
                virus_name,
                action,
                detected_at,
                scan_id,
                file_path,
                virus_name,
            )
            for file_path, virus_name, action, detected_at in prepared
        ]

        try:
            with self.operation_connection() as conn:
                conn.execute("BEGIN IMMEDIATE")
                scan = conn.execute(
                    "SELECT status FROM scan_history WHERE id = ?",
                    (scan_id,),
                ).fetchone()
                if scan is None:
                    raise ValueError(f"Scan inexistente: scan_id={scan_id}.")
                if self._normalize_status(scan["status"]) != self.ACTIVE_STATUS:
                    raise RuntimeError(
                        "Lote de ameaças rejeitado porque o scan não está ativo: "
                        f"scan_id={scan_id}, status={scan['status']!r}."
                    )

                changes_before = conn.total_changes
                conn.executemany(statement, params)
                return conn.total_changes - changes_before
        except (TypeError, ValueError, RuntimeError):
            raise
        except sqlite3.Error as exc:
            raise RuntimeError(
                "Falha ao registrar lote de ameaças: "
                f"scan_id={scan_id}, itens={len(prepared)}, causa={exc}"
            ) from exc

    def finish_scan(
        self,
        scan_id,
        total_files,
        infected_files,
        status,
        ended_at,
        error=None,
        treated_threats=0,
        failed_files=0,
    ):
        scan_id = self._valid_scan_id(scan_id)
        status = self._normalize_status(status)

        if status not in self.FINAL_STATUSES:
            raise ValueError(f"Status final inválido: {status!r}.")

        totals = {
            "total_files": self._non_negative(total_files, "total_files"),
            "infected_files": self._non_negative(
                infected_files, "infected_files"
            ),
            "treated_threats": self._non_negative(
                treated_threats, "treated_threats"
            ),
            "failed_files": self._non_negative(failed_files, "failed_files"),
        }
        ended_at = self._as_iso(ended_at, "ended_at")
        error = str(error) if error else None

        try:
            with self.operation_connection() as conn:
                current = conn.execute(
                    "SELECT status FROM scan_history WHERE id = ?",
                    (scan_id,),
                ).fetchone()

                if current is None:
                    raise ValueError(f"Scan inexistente: scan_id={scan_id}.")

                current_status = self._normalize_status(current["status"])
                if current_status in self.FINAL_STATUSES:
                    return False
                if current_status != self.ACTIVE_STATUS:
                    raise RuntimeError(
                        "Estado atual do scan não permite finalização: "
                        f"scan_id={scan_id}, status={current['status']!r}."
                    )

                cursor = conn.execute(
                    """
                    UPDATE scan_history
                    SET end_time = ?, total_files = ?, infected_files = ?,
                        treated_threats = ?, failed_files = ?, status = ?,
                        error_message = ?
                    WHERE id = ? AND LOWER(status) = ?
                    """,
                    (
                        ended_at,
                        totals["total_files"],
                        totals["infected_files"],
                        totals["treated_threats"],
                        totals["failed_files"],
                        status,
                        error,
                        scan_id,
                        self.ACTIVE_STATUS,
                    ),
                )

                if cursor.rowcount != 1:
                    raise RuntimeError(
                        f"O scan mudou de estado durante a finalização: scan_id={scan_id}."
                    )
                return True
        except (TypeError, ValueError, RuntimeError):
            raise
        except sqlite3.Error as exc:
            raise RuntimeError(
                f"Falha ao finalizar histórico: scan_id={scan_id}, causa={exc}"
            ) from exc

    def get_scans(self, filters=None, limit=None, offset=0):
        filters = dict(filters or {})
        limit = self._page_limit(limit)
        offset = self._non_negative(offset, "offset")
        where = []
        params = []

        if filters.get("status"):
            where.append("LOWER(h.status) = ?")
            params.append(self._normalize_status(filters["status"]))
        if filters.get("scan_type"):
            where.append("LOWER(COALESCE(h.scan_type, '')) = ?")
            params.append(str(filters["scan_type"]).strip().lower())

        where_sql = f"WHERE {' AND '.join(where)}" if where else ""
        params.extend((limit, offset))

        query = f"""
            WITH scan_page AS (
                SELECT
                    h.id, h.user, h.scan_type, h.start_time, h.end_time,
                    h.directory_scanned, h.total_files, h.infected_files,
                    h.treated_threats, h.failed_files, h.status,
                    h.error_message
                FROM scan_history AS h
                {where_sql}
                ORDER BY h.start_time DESC, h.id DESC
                LIMIT ? OFFSET ?
            )
            SELECT
                h.id, h.user, h.scan_type, h.start_time, h.end_time,
                h.directory_scanned, h.total_files, h.infected_files,
                h.treated_threats, h.failed_files, h.status,
                h.error_message, COUNT(t.id) AS threat_count
            FROM scan_page AS h
            LEFT JOIN scan_threats AS t ON t.scan_id = h.id
            GROUP BY h.id
            ORDER BY h.start_time DESC, h.id DESC
        """

        try:
            with self.operation_connection() as conn:
                rows = conn.execute(query, tuple(params)).fetchall()
        except sqlite3.Error as exc:
            raise RuntimeError(f"Falha ao listar histórico de scans: {exc}") from exc

        return [ScanHistoryEntity.from_row(row) for row in rows]

    def get_scan_by_id(self, scan_id):
        scan_id = self._valid_scan_id(scan_id)
        try:
            with self.operation_connection() as conn:
                row = conn.execute(
                    """
                    SELECT
                        h.id, h.user, h.scan_type, h.start_time, h.end_time,
                        h.directory_scanned, h.total_files, h.infected_files,
                        h.treated_threats, h.failed_files, h.status,
                        h.error_message, COUNT(t.id) AS threat_count
                    FROM scan_history AS h
                    LEFT JOIN scan_threats AS t ON t.scan_id = h.id
                    WHERE h.id = ?
                    GROUP BY h.id
                    """,
                    (scan_id,),
                ).fetchone()
        except sqlite3.Error as exc:
            raise RuntimeError(
                f"Falha ao consultar scan: scan_id={scan_id}, causa={exc}"
            ) from exc

        return ScanHistoryEntity.from_row(row) if row else None

    def get_threats_by_scan(self, scan_id, limit=None, offset=0):
        scan_id = self._valid_scan_id(scan_id)
        offset = self._non_negative(offset, "offset")
        params = [scan_id]
        pagination = ""

        if limit is not None:
            pagination = "LIMIT ? OFFSET ?"
            params.extend((self._page_limit(limit), offset))

        try:
            with self.operation_connection() as conn:
                rows = conn.execute(
                    f"""
                    SELECT id, scan_id, file_path, virus_name, action,
                           detection_time
                    FROM scan_threats
                    WHERE scan_id = ?
                    ORDER BY detection_time ASC, id ASC
                    {pagination}
                    """,
                    tuple(params),
                ).fetchall()
        except sqlite3.Error as exc:
            raise RuntimeError(
                "Falha ao consultar ameaças do scan: "
                f"scan_id={scan_id}, causa={exc}"
            ) from exc

        return [ScanThreatEntity.from_row(row) for row in rows]

    def recover_interrupted_scans(self, recovered_at=None):
        recovered_at = self._as_iso(
            recovered_at or datetime.now(), "recovered_at"
        )

        try:
            with self.operation_connection() as conn:
                cursor = conn.execute(
                    """
                    UPDATE scan_history
                    SET status = 'interrupted', end_time = ?,
                        error_message = COALESCE(
                            error_message,
                            'Scan interrompido pelo encerramento da aplicação.'
                        )
                    WHERE LOWER(status) = 'running'
                    """,
                    (recovered_at,),
                )
                return cursor.rowcount
        except sqlite3.Error as exc:
            raise RuntimeError(
                f"Falha ao recuperar scans interrompidos: {exc}"
            ) from exc

    @staticmethod
    def _normalize_status(status):
        return str(status or "").strip().lower()

    @staticmethod
    def _valid_scan_id(scan_id):
        try:
            scan_id = int(scan_id)
        except (TypeError, ValueError) as exc:
            raise ValueError(f"scan_id inválido: {scan_id!r}.") from exc
        if scan_id <= 0:
            raise ValueError(f"scan_id inválido: {scan_id!r}.")
        return scan_id

    @staticmethod
    def _non_negative(value, field):
        try:
            value = int(value)
        except (TypeError, ValueError) as exc:
            raise ValueError(f"{field} inválido: {value!r}.") from exc
        if value < 0:
            raise ValueError(f"{field} não pode ser negativo.")
        return value

    @classmethod
    def _page_limit(cls, limit):
        if limit is None:
            return cls.DEFAULT_PAGE_SIZE
        limit = cls._non_negative(limit, "limit")
        if limit == 0:
            raise ValueError("limit deve ser maior que zero.")
        return min(limit, cls.MAX_PAGE_SIZE)

    @staticmethod
    def _as_iso(value, field):
        if isinstance(value, datetime):
            return value.isoformat()
        if isinstance(value, str) and value.strip():
            return value.strip()
        raise ValueError(f"{field} deve ser datetime ou texto ISO não vazio.")

    def _prepare_threat(self, item):
        try:
            detected_file, virus, action, detection_date = item
        except (TypeError, ValueError) as exc:
            raise ValueError(
                "Cada ameaça do lote deve conter detected_file, virus, "
                "action e detection_date."
            ) from exc

        if not isinstance(detected_file, DetectedFile):
            raise TypeError("detected_file deve ser uma instância de DetectedFile.")
        if not isinstance(virus, Virus):
            raise TypeError("virus deve ser uma instância de Virus.")

        file_path = str(detected_file.path or "").strip()
        virus_name = str(virus.name or "").strip()
        action = str(action or "").strip().lower()
        detected_at = detection_date or virus.detection_date or datetime.now()

        if not file_path:
            raise ValueError("Caminho vazio ao registrar ameaça.")
        if not virus_name:
            raise ValueError("Nome da ameaça vazio ao registrar histórico.")
        if action not in self.THREAT_ACTIONS:
            raise ValueError(f"Ação de ameaça inválida: {action!r}.")

        return file_path, virus_name, action, self._as_iso(
            detected_at, "detection_date"
        )
