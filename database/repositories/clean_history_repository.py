# database/clean_history_db.py
from database.database import Database
from database.entity.clean_entity import CleanEntity

class CleanHistoryRepository(Database):
    # ============================
    # ➕ INSERT
    # ============================
    def insert(self, entity: CleanEntity):
        with self.connect() as conn:
            cursor = conn.execute(
                """
                INSERT INTO clean_history
                (user, timestamp, total_items, total_size, permanent, details)
                VALUES (?, ?, ?, ?, ?, ?)
                """,
                entity.to_tuple()
            )
            entity.id = cursor.lastrowid

        return entity.id

    # ============================
    # 📄 LISTAR
    # ============================
    def list_all(self):
        with self.connect() as conn:
            rows = conn.execute("""
                SELECT id, user, timestamp, total_items, total_size, permanent, details
                FROM clean_history
                ORDER BY id DESC
            """).fetchall()

        return [
            CleanEntity(
                user=row["user"],
                timestamp=row["timestamp"],
                total_items=row["total_items"],
                total_size=row["total_size"],
                permanent=row["permanent"],
                details=row["details"],
                id=row["id"]
            )
            for row in rows
        ]
