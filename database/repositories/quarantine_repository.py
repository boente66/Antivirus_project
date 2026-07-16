# database/repository/quarantine_repository.py

from database.database import Database
from database.entity.quarantine_entity import QuarantineEntity


class QuarantineRepository(Database):
    """
    Repositório da Quarentena.
    Responsável apenas por operações no banco.
    """

    # ---------------------------
    # INSERT
    # ---------------------------
    def insert(self, entity: QuarantineEntity):
        cursor = self.execute_query(
            """
            INSERT INTO quarantine (
                original_path,
                quarantine_path,
                virus_name,
                date,
                status
            ) VALUES (?, ?, ?, ?, ?)
            """,
            entity.to_tuple()
        )

        if cursor is not None:
            entity.id = cursor.lastrowid

        return entity.id

    # ---------------------------
    # LISTAR TODOS
    # ---------------------------
    def list_all(self) -> list[QuarantineEntity]:
        rows = self.fetch_all(
            """
            SELECT
                id,
                original_path,
                quarantine_path,
                virus_name,
                date,
                status
            FROM quarantine
            ORDER BY date DESC
            """
        )

        return [
            QuarantineEntity(
                row["original_path"],
                row["quarantine_path"],
                row["virus_name"],
                row["date"],
                row["status"],
                id=row["id"]
            )
            for row in rows
        ]

    # ---------------------------
    # DELETE
    # ---------------------------
    def delete_by_path(self, quarantine_path: str):
        self.execute_query(
            "DELETE FROM quarantine WHERE quarantine_path = ?",
            (quarantine_path,)
        )

    def delete(self, entity_or_path):
        quarantine_path = getattr(
            entity_or_path,
            "quarantine_path",
            entity_or_path
        )

        self.delete_by_path(quarantine_path)

    # ---------------------------
    # UPDATE STATUS
    # ---------------------------
    def update_status(self, quarantine_path: str, status: str):
        self.execute_query(
            "UPDATE quarantine SET status = ? WHERE quarantine_path = ?",
            (status, quarantine_path)
        )
