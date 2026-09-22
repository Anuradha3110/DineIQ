import sqlite3
import os
import threading
from config import GOOGLE_SHEETS_SYNC

class SQLiteClient:
    """
    Singleton class to manage SQLite connection in WAL mode.
    Maintains a single connection to DineIQ_Database.db.
    """
    def __init__(self, db_path: str = "sqliteDB/DineIQ_Database.db"):
        self.db_path = db_path
        # Using check_same_thread=False because FastAPI routes run in different worker threads,
        # but SQLite is safe in WAL mode if we manage transactions correctly.
        self.conn = sqlite3.connect(
            self.db_path,
            check_same_thread=False,
            isolation_level=None # Autocommit mode
        )
        self.conn.row_factory = sqlite3.Row
        self._setup_pragmas()
        self._bootstrap_schema()

        # Thread lock for thread-safe operations
        self.lock = threading.Lock()
        
        # In-memory queue for progressive sync
        # Items are dicts: {"table": str, "action": "INSERT"|"UPDATE"|"DELETE", "data": dict, "condition": dict}
        self.sync_queue = []

    def _setup_pragmas(self):
        cursor = self.conn.cursor()
        cursor.execute("PRAGMA journal_mode=WAL;")
        cursor.execute("PRAGMA synchronous=NORMAL;")
        cursor.execute("PRAGMA foreign_keys=ON;")
        cursor.close()

    def _bootstrap_schema(self):
        """
        On a brand-new DB file (fresh deploy, empty filesystem) sqliteDB/*.db
        is gitignored so no tables exist yet. Load schema.sql once so the app
        doesn't crash the first time a route touches a table.
        """
        exists = self.conn.execute(
            "SELECT name FROM sqlite_master WHERE type='table' AND name='orders'"
        ).fetchone()
        if exists:
            return

        schema_path = os.path.join(os.path.dirname(self.db_path) or ".", "schema.sql")
        if not os.path.isfile(schema_path):
            return

        with open(schema_path, "r") as f:
            self.conn.executescript(f.read())

    def fetch_all(self, query: str, params: tuple = ()) -> list[dict]:
        """Fetch all rows for a query and return as a list of dicts."""
        with self.lock:
            cursor = self.conn.cursor()
            cursor.execute(query, params)
            rows = cursor.fetchall()
            cursor.close()
            return [dict(row) for row in rows]

    def fetch_one(self, query: str, params: tuple = ()) -> dict | None:
        """Fetch a single row for a query and return as a dict."""
        with self.lock:
            cursor = self.conn.cursor()
            cursor.execute(query, params)
            row = cursor.fetchone()
            cursor.close()
            return dict(row) if row else None

    def execute(self, query: str, params: tuple = ()) -> int:
        """Execute a query and return the number of affected rows."""
        with self.lock:
            cursor = self.conn.cursor()
            cursor.execute(query, params)
            rowcount = cursor.rowcount
            cursor.close()
            return rowcount

    def insert(self, table: str, data: dict, queue_for_sync: bool = True) -> int:
        """
        Helper to insert a single dict into a table.
        """
        columns = ", ".join(data.keys())
        placeholders = ", ".join(["?"] * len(data))
        query = f"INSERT INTO {table} ({columns}) VALUES ({placeholders})"
        values = tuple(data.values())
        
        with self.lock:
            cursor = self.conn.cursor()
            cursor.execute(query, values)
            rowcount = cursor.rowcount
            cursor.close()
            
        if GOOGLE_SHEETS_SYNC and queue_for_sync and rowcount > 0:
            self.sync_queue.append({
                "table": table,
                "action": "INSERT",
                "data": data
            })
            
        return rowcount

    def update(self, table: str, data: dict, condition: dict, queue_for_sync: bool = True) -> int:
        """
        Helper to update rows in a table.
        condition defines the WHERE clause with ANDs.
        """
        set_clause = ", ".join([f"{k} = ?" for k in data.keys()])
        where_clause = " AND ".join([f"{k} = ?" for k in condition.keys()])
        query = f"UPDATE {table} SET {set_clause} WHERE {where_clause}"
        values = tuple(data.values()) + tuple(condition.values())
        
        with self.lock:
            cursor = self.conn.cursor()
            cursor.execute(query, values)
            rowcount = cursor.rowcount
            cursor.close()
            
        if GOOGLE_SHEETS_SYNC and queue_for_sync and rowcount > 0:
            self.sync_queue.append({
                "table": table,
                "action": "UPDATE",
                "data": data,
                "condition": condition
            })
            
        return rowcount

    def close(self):
        """Close the database connection."""
        self.conn.close()
