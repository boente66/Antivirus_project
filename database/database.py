# database/database.py
import sqlite3
from contextlib import contextmanager
from pathlib import Path


class Database:
    """
    Classe base de persistência de dados.
    Equivalente ao Connection/JDBC.
    """

    def __init__(self, db_name="antivirus_system.db", timeout=30):
        self.conn = None
        self.db_name = db_name
        self.timeout = max(0.1, float(timeout))
        self.connect()
        self.create_tables()

    # ============================
    # 🔌 CONEXÃO
    # ============================
    def connect(self):
        if self.conn is None:
            db_path = Path(self.db_name)

            if db_path.parent != Path("."):
                db_path.parent.mkdir(parents=True, exist_ok=True)

            self.conn = sqlite3.connect(
                self.db_name,
                timeout=self.timeout,
                check_same_thread=False
            )
            self._configure_connection(self.conn, configure_journal=True)
        return self.conn

    def _configure_connection(self, conn, configure_journal=False):
        conn.execute("PRAGMA foreign_keys = ON;")
        conn.execute(f"PRAGMA busy_timeout = {int(self.timeout * 1000)};")
        if configure_journal:
            conn.execute("PRAGMA journal_mode = WAL;")
        conn.execute("PRAGMA synchronous = NORMAL;")
        conn.row_factory = sqlite3.Row

    @contextmanager
    def operation_connection(self):
        """Fornece uma conexão curta e segura para a thread da operação."""
        conn = sqlite3.connect(self.db_name, timeout=self.timeout)
        self._configure_connection(conn)

        try:
            yield conn
            conn.commit()
        except Exception:
            conn.rollback()
            raise
        finally:
            conn.close()


    # ============================
    # 🧱 TABELAS
    # ============================
    def create_tables(self):
        """Cria todas as tabelas do sistema"""

        with self.connect() as conn:
            cursor = conn.cursor()

        cursor.executescript("""
        CREATE TABLE IF NOT EXISTS quarantine (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            original_path TEXT NOT NULL,
            quarantine_path TEXT NOT NULL,
            virus_name TEXT,
            date TEXT,
            status TEXT
        );

        CREATE TABLE IF NOT EXISTS scan_history (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user TEXT,
            scan_type TEXT,
            start_time TEXT,
            end_time TEXT,
            directory_scanned TEXT,
            total_files INTEGER NOT NULL DEFAULT 0,
            infected_files INTEGER NOT NULL DEFAULT 0,
            treated_threats INTEGER NOT NULL DEFAULT 0,
            failed_files INTEGER NOT NULL DEFAULT 0,
            status TEXT,
            error_message TEXT
        );

        CREATE TABLE IF NOT EXISTS scan_threats (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            scan_id INTEGER NOT NULL,
            file_path TEXT NOT NULL,
            virus_name TEXT,
            action TEXT,
            detection_time TEXT,
            FOREIGN KEY(scan_id) REFERENCES scan_history(id) ON DELETE CASCADE
        );

        CREATE TABLE IF NOT EXISTS clean_history (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user TEXT,
            timestamp TEXT,
            total_items INTEGER,
            total_size INTEGER,
            permanent INTEGER,
            details TEXT
        );

        CREATE INDEX IF NOT EXISTS idx_quarantine_date
            ON quarantine(date DESC);

        CREATE INDEX IF NOT EXISTS idx_clean_history_timestamp
            ON clean_history(timestamp DESC);
        """)

        self._migrate_scan_schema(conn)
        conn.commit()

        self._set_schema_version(conn, 2)

    def _migrate_scan_schema(self, conn):
        """Migração incremental e idempotente do histórico de scans."""
        history_columns = self._table_columns(conn, "scan_history")
        if "id" not in history_columns:
            raise RuntimeError(
                "Migração não destrutiva impossível: scan_history não possui id."
            )
        history_additions = {
            "user": "TEXT",
            "scan_type": "TEXT",
            "start_time": "TEXT",
            "end_time": "TEXT",
            "directory_scanned": "TEXT",
            "total_files": "INTEGER NOT NULL DEFAULT 0",
            "infected_files": "INTEGER NOT NULL DEFAULT 0",
            "treated_threats": "INTEGER NOT NULL DEFAULT 0",
            "failed_files": "INTEGER NOT NULL DEFAULT 0",
            "status": "TEXT",
            "error_message": "TEXT",
        }

        for column, definition in history_additions.items():
            if column not in history_columns:
                conn.execute(
                    f"ALTER TABLE scan_history ADD COLUMN {column} {definition}"
                )

        threat_columns = self._table_columns(conn, "scan_threats")
        if "id" not in threat_columns:
            raise RuntimeError(
                "Migração não destrutiva impossível: scan_threats não possui id."
            )
        threat_additions = {
            "scan_id": "INTEGER",
            "file_path": "TEXT",
            "virus_name": "TEXT",
            "action": "TEXT",
            "detection_time": "TEXT",
        }

        for column, definition in threat_additions.items():
            if column not in threat_columns:
                conn.execute(
                    f"ALTER TABLE scan_threats ADD COLUMN {column} {definition}"
                )

        conn.execute(
            "CREATE INDEX IF NOT EXISTS idx_scan_history_start_time "
            "ON scan_history(start_time DESC)"
        )
        conn.execute(
            "CREATE INDEX IF NOT EXISTS idx_scan_threats_scan_id "
            "ON scan_threats(scan_id)"
        )
        conn.execute(
            "CREATE INDEX IF NOT EXISTS idx_scan_threats_scan_time "
            "ON scan_threats(scan_id, detection_time, id)"
        )

    @staticmethod
    def _table_columns(conn, table_name):
        return {
            row["name"]
            for row in conn.execute(f"PRAGMA table_info({table_name})")
        }

    def _set_schema_version(self, conn, version):
        conn.execute(f"PRAGMA user_version = {int(version)};")
        conn.commit()

    
    # --------------------------------------------------------------
    # MÉTODOS DE EXECUÇÃO
    # --------------------------------------------------------------

    def execute_query(self, query: str, params: tuple = ()):
        try:
            with self.connect() as conn:
                cursor = conn.cursor()
                cursor.execute(query, params)
                conn.commit()
                return cursor
        except sqlite3.Error as e:
            print(f"Erro ao executar a consulta: {e}")
            return None

    def fetch_all(self, query, params=None):
        try:
            with self.connect() as conn:
                cursor = conn.cursor()
                cursor.execute(query, params or ())
                return cursor.fetchall()
        except sqlite3.Error as e:
            print(f"Erro ao buscar dados: {e}")
            return []

    def fetch_one(self, query, params=None):
        try:
            with self.connect() as conn:
                cursor = conn.cursor()
                cursor.execute(query, params or ())
                return cursor.fetchone()
        except sqlite3.Error as e:
            print(f"Erro ao buscar dado: {e}")
            return None

    # ============================
    # ❌ FECHAR
    # ============================
    def close(self):
        if self.conn:
            self.conn.close()
            self.conn = None
