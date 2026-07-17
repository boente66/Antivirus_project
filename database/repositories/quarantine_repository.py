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
        if self.find_by_path(entity.quarantine_path) is not None:
            raise ValueError(
                f"Já existe registro para o caminho de quarentena: "
                f"{entity.quarantine_path}"
            )

        with self.connect() as conn:
            cursor = conn.execute(
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
            entity.id = cursor.lastrowid

        return entity.id

    # ---------------------------
    # LISTAR TODOS
    # ---------------------------
    def list_all(self) -> list[QuarantineEntity]:
        with self.connect() as conn:
            rows = conn.execute(
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
            ).fetchall()

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
    # LOCALIZAR
    # ---------------------------
    def find_by_path(self, quarantine_path: str):
        with self.connect() as conn:
            row = conn.execute(
                """
                SELECT
                    id,
                    original_path,
                    quarantine_path,
                    virus_name,
                    date,
                    status
                FROM quarantine
                WHERE quarantine_path = ?
                """,
                (quarantine_path,)
            ).fetchone()

        if row is None:
            return None

        return QuarantineEntity(
            row["original_path"],
            row["quarantine_path"],
            row["virus_name"],
            row["date"],
            row["status"],
            id=row["id"]
        )

    # ---------------------------
    # DELETE
    # ---------------------------
    def delete_by_path(self, quarantine_path: str) -> bool:
        with self.connect() as conn:
            cursor = conn.execute(
                "DELETE FROM quarantine WHERE quarantine_path = ?",
                (quarantine_path,)
            )

        return cursor.rowcount == 1

    # ---------------------------
    # UPDATE STATUS
    # ---------------------------
    def update_status(self, quarantine_path: str, status: str) -> bool:
        with self.connect() as conn:
            cursor = conn.execute(
                "UPDATE quarantine SET status = ? WHERE quarantine_path = ?",
                (status, quarantine_path)
            )

        return cursor.rowcount == 1
