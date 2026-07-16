# database/database.py
import sqlite3
from pathlib import Path


class Database:
    """
    Classe base de persistência de dados.
    Equivalente ao Connection/JDBC.
    """

    def __init__(self, db_name="antivirus_system.db"):
        self.conn = None
        self.db_name = db_name
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
                timeout=30,
                check_same_thread=False
            )
            self.conn.execute("PRAGMA foreign_keys = ON;")
            self.conn.execute("PRAGMA journal_mode = WAL;")
            self.conn.execute("PRAGMA synchronous = NORMAL;")
            self.conn.row_factory = sqlite3.Row
        return self.conn


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
            start_time TEXT,
            end_time TEXT,
            directory_scanned TEXT,
            total_files INTEGER,
            infected_files INTEGER,
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

        CREATE INDEX IF NOT EXISTS idx_scan_history_start_time
            ON scan_history(start_time DESC);

        CREATE INDEX IF NOT EXISTS idx_scan_threats_scan_id
            ON scan_threats(scan_id);

        CREATE INDEX IF NOT EXISTS idx_scan_threats_detection_time
            ON scan_threats(detection_time DESC);

        CREATE INDEX IF NOT EXISTS idx_quarantine_date
            ON quarantine(date DESC);

        CREATE INDEX IF NOT EXISTS idx_clean_history_timestamp
            ON clean_history(timestamp DESC);
        """)
        conn.commit()

        self._set_schema_version(conn, 1)

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
