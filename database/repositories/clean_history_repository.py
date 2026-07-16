# database/clean_history_db.py
from database.database import Database
from database.entity.clean_entity import CleanEntity

class CleanHistoryRepository(Database):
    # ============================
    # ➕ INSERT
    # ============================
    def insert(self, entity: CleanEntity):
        cursor = self.execute_query(
            """
            INSERT INTO clean_history
            (user, timestamp, total_items, total_size, permanent, details)
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            (
                entity.user,
                entity.timestamp,
                entity.total_items,
                entity.total_size,
                entity.permanent,
                entity.details
            )
        )

        if cursor is not None:
            entity.id = cursor.lastrowid

        return entity.to_tuple()

    # ============================
    # 📄 LISTAR
    # ============================
    def list_all(self):
        rows = self.fetch_all("""
            SELECT id, user, timestamp, total_items, total_size, permanent, details
            FROM clean_history
            ORDER BY id DESC
        """)

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
