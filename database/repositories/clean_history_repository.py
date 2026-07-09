# database/clean_history_db.py
from database.database import Database
from database.entity.clean_entity import CleanEntity

class CleanHistoryRepository(Database):
    

    
    # ============================
    # ➕ INSERT
    # ============================
    def insert(self, entity: CleanEntity):
        self.execute_query(
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
        return entity.to_tuple()

    # ============================
    # 📄 LISTAR
    # ============================
    def list_all(self):
        rows = self.execute_query("""
            SELECT id, user, timestamp, total_items, total_size, permanent, details
            FROM clean_history
            ORDER BY id DESC
        """)
        return [CleanEntity(*row) for row in rows]