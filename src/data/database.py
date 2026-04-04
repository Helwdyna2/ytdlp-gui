"""SQLite database connection management with thread-safe operations."""

import sqlite3
import threading
from pathlib import Path
from typing import Optional
import logging

from ..utils.platform_utils import get_db_path, ensure_dirs
from ..utils.constants import DB_VERSION

logger = logging.getLogger(__name__)


class Database:
    """
    SQLite connection management.

    Provides thread-safe database operations with connection pooling.
    """

    _instance: Optional['Database'] = None
    _lock = threading.Lock()
    _SAVED_TASKS_REQUIRED_COLUMNS = {
        "task_type",
        "title",
        "status",
        "summary_json",
        "payload_json",
        "created_at",
        "updated_at",
    }
    _SAVED_TASKS_LEGACY_COLUMNS = {"payload", "summary"}
    _SAVED_TASKS_CREATE_SQL = """
        CREATE TABLE IF NOT EXISTS saved_tasks (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            task_type TEXT NOT NULL,
            title TEXT NOT NULL,
            status TEXT NOT NULL DEFAULT 'active',
            summary_json TEXT NOT NULL DEFAULT '{}',
            payload_json TEXT NOT NULL DEFAULT '{}',
            created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
            deleted_at TIMESTAMP,
            CONSTRAINT chk_saved_task_status CHECK (status IN ('active', 'paused', 'completed', 'failed', 'deleted'))
        )
    """
    _SAVED_TASKS_INDEX_SQL = (
        "CREATE INDEX IF NOT EXISTS idx_saved_tasks_status ON saved_tasks(status)",
        "CREATE INDEX IF NOT EXISTS idx_saved_tasks_task_type ON saved_tasks(task_type)",
        "CREATE INDEX IF NOT EXISTS idx_saved_tasks_updated_at ON saved_tasks(updated_at DESC)",
        "CREATE INDEX IF NOT EXISTS idx_saved_tasks_deleted_at ON saved_tasks(deleted_at)",
    )

    def __new__(cls, db_path: Optional[str] = None):
        """Singleton pattern for database instance."""
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = super().__new__(cls)
                    cls._instance._initialized = False
        return cls._instance

    def __init__(self, db_path: Optional[str] = None):
        """Initialize database connection."""
        if self._initialized:
            return

        self._db_lock = threading.Lock()

        if db_path:
            self.db_path = Path(db_path)
        else:
            ensure_dirs()
            self.db_path = get_db_path()

        self._connection: Optional[sqlite3.Connection] = None
        self._local = threading.local()
        self._initialized = True

        # Initialize schema
        self.initialize()

    def _get_connection(self) -> sqlite3.Connection:
        """Get thread-local database connection."""
        if not hasattr(self._local, 'connection') or self._local.connection is None:
            self._local.connection = sqlite3.connect(
                str(self.db_path),
                check_same_thread=False,
                timeout=30.0
            )
            self._local.connection.row_factory = sqlite3.Row
            # Enable foreign keys
            self._local.connection.execute("PRAGMA foreign_keys = ON")

        return self._local.connection

    def execute(self, query: str, params: tuple = ()) -> sqlite3.Cursor:
        """Execute a query with thread-safe locking."""
        with self._db_lock:
            conn = self._get_connection()
            cursor = conn.execute(query, params)
            conn.commit()
            return cursor

    def executemany(self, query: str, params_list: list) -> None:
        """Execute a query with multiple parameter sets."""
        with self._db_lock:
            conn = self._get_connection()
            conn.executemany(query, params_list)
            conn.commit()

    def fetchone(self, query: str, params: tuple = ()) -> Optional[sqlite3.Row]:
        """Execute query and fetch one result."""
        with self._db_lock:
            conn = self._get_connection()
            cursor = conn.execute(query, params)
            return cursor.fetchone()

    def fetchall(self, query: str, params: tuple = ()) -> list:
        """Execute query and fetch all results."""
        with self._db_lock:
            conn = self._get_connection()
            cursor = conn.execute(query, params)
            return cursor.fetchall()

    def initialize(self) -> None:
        """Initialize database schema."""
        logger.info(f"Initializing database at {self.db_path}")

        # Create tables
        self._create_tables()

        # Check and run migrations
        self._run_migrations()

        # Repair compatibility with the earlier v4 saved_tasks shape if needed.
        self._ensure_saved_tasks_schema()

    def _create_tables(self) -> None:
        """Create database tables if they don't exist."""
        # Downloads table
        self.execute("""
            CREATE TABLE IF NOT EXISTS downloads (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                url TEXT NOT NULL UNIQUE,
                title TEXT,
                output_path TEXT,
                file_size INTEGER,
                status TEXT NOT NULL DEFAULT 'completed',
                error_message TEXT,
                created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
                completed_at TIMESTAMP,
                CONSTRAINT chk_status CHECK (status IN ('completed', 'failed', 'partial', 'pending', 'in_progress'))
            )
        """)

        self.execute("""
            CREATE INDEX IF NOT EXISTS idx_downloads_url ON downloads(url)
        """)

        self.execute("""
            CREATE INDEX IF NOT EXISTS idx_downloads_status ON downloads(status)
        """)

        self.execute("""
            CREATE INDEX IF NOT EXISTS idx_downloads_created_at ON downloads(created_at DESC)
        """)

        # Sessions table
        self.execute("""
            CREATE TABLE IF NOT EXISTS sessions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                pending_urls TEXT NOT NULL,
                completed_urls TEXT NOT NULL DEFAULT '[]',
                output_dir TEXT NOT NULL,
                concurrent_limit INTEGER NOT NULL DEFAULT 3,
                force_overwrite INTEGER NOT NULL DEFAULT 0,
                video_only INTEGER NOT NULL DEFAULT 0,
                cookies_path TEXT,
                is_active INTEGER NOT NULL DEFAULT 1,
                created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
            )
        """)

        self.execute("""
            CREATE INDEX IF NOT EXISTS idx_sessions_is_active ON sessions(is_active)
        """)

        # Saved tasks table
        if self._saved_tasks_table_is_current():
            self._create_saved_tasks_schema()
        elif not self._saved_tasks_table_exists():
            self._create_saved_tasks_schema()
        else:
            logger.info("Legacy saved_tasks schema detected; repair deferred")

        # Config table
        self.execute("""
            CREATE TABLE IF NOT EXISTS config (
                key TEXT PRIMARY KEY,
                value TEXT NOT NULL,
                updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
            )
        """)

        # Schema version table
        self.execute("""
            CREATE TABLE IF NOT EXISTS schema_version (
                version INTEGER PRIMARY KEY,
                applied_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
                description TEXT
            )
        """)

        # Insert initial version if not exists
        existing = self.fetchone("SELECT version FROM schema_version WHERE version = ?", (1,))
        if not existing:
            self.execute(
                "INSERT INTO schema_version (version, description) VALUES (?, ?)",
                (1, "Initial schema")
            )

    def _run_migrations(self) -> None:
        """Run any pending database migrations."""
        current_version = self.fetchone(
            "SELECT MAX(version) as version FROM schema_version"
        )
        current = current_version['version'] if current_version else 0

        if current < DB_VERSION:
            logger.info(f"Running migrations from version {current} to {DB_VERSION}")

            # Migration 2: Add updated_at column to downloads table
            if current < 2:
                self._migrate_to_v2()

            # Migration 3: Add conversion_jobs table
            if current < 3:
                self._migrate_to_v3()

            # Migration 4: Add saved_tasks table
            if current < 4:
                self._migrate_to_v4()

    def _migrate_to_v2(self) -> None:
        """Migration v2: Add updated_at column to downloads table."""
        logger.info("Running migration v2: Adding updated_at column to downloads table")

        # Check if the column already exists (in case of partial migration)
        columns = self.fetchall("PRAGMA table_info(downloads)")
        column_names = [col['name'] for col in columns]

        if 'updated_at' not in column_names:
            # SQLite doesn't allow non-constant defaults in ALTER TABLE,
            # so we add the column as nullable first, then backfill
            self.execute("""
                ALTER TABLE downloads
                ADD COLUMN updated_at TIMESTAMP
            """)
            # Backfill existing rows with created_at value
            self.execute("""
                UPDATE downloads
                SET updated_at = COALESCE(created_at, CURRENT_TIMESTAMP)
                WHERE updated_at IS NULL
            """)
            logger.info("Added updated_at column to downloads table")
        else:
            logger.info("updated_at column already exists, skipping")

        # Record the migration
        self.execute(
            "INSERT OR REPLACE INTO schema_version (version, description) VALUES (?, ?)",
            (2, "Add updated_at column to downloads table")
        )
        logger.info("Migration v2 completed")

    def _migrate_to_v3(self) -> None:
        """Migration v3: Add conversion_jobs table."""
        logger.info("Running migration v3: Adding conversion_jobs table")

        self.execute("""
            CREATE TABLE IF NOT EXISTS conversion_jobs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                input_path TEXT NOT NULL,
                output_path TEXT NOT NULL,
                status TEXT NOT NULL DEFAULT 'pending',
                output_codec TEXT NOT NULL DEFAULT 'h264',
                crf_value INTEGER NOT NULL DEFAULT 23,
                preset TEXT NOT NULL DEFAULT 'medium',
                hardware_encoder TEXT,
                progress_percent REAL NOT NULL DEFAULT 0.0,
                error_message TEXT,
                input_size INTEGER,
                output_size INTEGER,
                duration REAL,
                created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
                completed_at TIMESTAMP,
                CONSTRAINT chk_conv_status CHECK (status IN ('pending', 'in_progress', 'completed', 'failed', 'cancelled'))
            )
        """)

        self.execute("""
            CREATE INDEX IF NOT EXISTS idx_conversion_jobs_status ON conversion_jobs(status)
        """)

        self.execute("""
            CREATE INDEX IF NOT EXISTS idx_conversion_jobs_created_at ON conversion_jobs(created_at DESC)
        """)

        # Record the migration
        self.execute(
            "INSERT OR REPLACE INTO schema_version (version, description) VALUES (?, ?)",
            (3, "Add conversion_jobs table")
        )
        logger.info("Migration v3 completed")

    def _migrate_to_v4(self) -> None:
        """Migration v4: Add saved_tasks table."""
        logger.info("Running migration v4: Adding saved_tasks table")

        self._create_saved_tasks_schema()

        self.execute(
            "INSERT OR REPLACE INTO schema_version (version, description) VALUES (?, ?)",
            (4, "Add saved_tasks table")
        )
        logger.info("Migration v4 completed")

    def _create_saved_tasks_schema(self) -> None:
        """Create the current saved_tasks schema and supporting indexes."""
        self.execute(self._SAVED_TASKS_CREATE_SQL)
        for sql in self._SAVED_TASKS_INDEX_SQL:
            self.execute(sql)

    def _saved_tasks_table_exists(self) -> bool:
        """Check whether the saved_tasks table exists."""
        row = self.fetchone(
            "SELECT name FROM sqlite_master WHERE type = 'table' AND name = 'saved_tasks'"
        )
        return row is not None

    def _saved_tasks_table_is_current(self) -> bool:
        """Check whether saved_tasks already has the current column layout."""
        if not self._saved_tasks_table_exists():
            return False

        columns = self.fetchall("PRAGMA table_info(saved_tasks)")
        column_names = {col["name"] for col in columns}
        return self._SAVED_TASKS_REQUIRED_COLUMNS.issubset(column_names)

    def _ensure_saved_tasks_schema(self) -> None:
        """Repair older saved_tasks table shapes in-place when needed."""
        if not self._saved_tasks_table_exists():
            self._create_saved_tasks_schema()
            return

        columns = self.fetchall("PRAGMA table_info(saved_tasks)")
        column_names = [col["name"] for col in columns]

        if self._SAVED_TASKS_REQUIRED_COLUMNS.issubset(column_names):
            self._create_saved_tasks_schema()
            return

        if self._SAVED_TASKS_LEGACY_COLUMNS.intersection(column_names) or not self._SAVED_TASKS_REQUIRED_COLUMNS.issubset(column_names):
            self._repair_legacy_saved_tasks_schema(column_names)

    def _repair_legacy_saved_tasks_schema(self, existing_columns: list[str]) -> None:
        """Upgrade the earlier v4 saved_tasks table to the corrected schema."""
        logger.info("Repairing legacy saved_tasks schema")

        legacy_name = "saved_tasks_legacy_v4"
        conn = self._get_connection()
        with self._db_lock:
            try:
                conn.execute("BEGIN")
                conn.execute(f"ALTER TABLE saved_tasks RENAME TO {legacy_name}")
                conn.execute(self._SAVED_TASKS_CREATE_SQL)

                legacy_columns = set(existing_columns)
                rows = conn.execute(f"SELECT * FROM {legacy_name} ORDER BY id").fetchall()
                for row in rows:
                    raw_summary = row["summary"] if "summary" in legacy_columns else "{}"
                    raw_payload = row["payload"] if "payload" in legacy_columns else "{}"
                    status = self._normalize_saved_task_status(row["status"] if "status" in legacy_columns else None)
                    task_type, title = self._derive_saved_task_identity(raw_summary, raw_payload)
                    conn.execute(
                        """
                        INSERT INTO saved_tasks (
                            id, task_type, title, status, summary_json, payload_json,
                            created_at, updated_at, deleted_at
                        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                        """,
                        (
                            row["id"],
                            task_type,
                            title,
                            status,
                            raw_summary,
                            raw_payload,
                            row["created_at"],
                            row["updated_at"],
                            row["deleted_at"],
                        ),
                    )

                conn.execute(f"DROP TABLE {legacy_name}")
                for sql in self._SAVED_TASKS_INDEX_SQL:
                    conn.execute(sql)
                conn.execute(
                    "INSERT OR REPLACE INTO schema_version (version, description) VALUES (?, ?)",
                    (4, "Repair saved_tasks schema"),
                )
                conn.commit()
            except Exception:
                conn.rollback()
                raise

    @staticmethod
    def _normalize_saved_task_status(status: Optional[str]) -> str:
        """Map legacy saved task statuses to the unified vocabulary."""
        mapping = {
            "pending": "active",
            "in_progress": "paused",
            "active": "active",
            "paused": "paused",
            "completed": "completed",
            "failed": "failed",
            "deleted": "deleted",
        }
        return mapping.get(status or "", "active")

    @staticmethod
    def _derive_saved_task_identity(summary_json: str, payload_json: str) -> tuple[str, str]:
        """Infer task_type/title for legacy rows from their JSON blobs."""
        import json

        summary: dict = {}
        payload: dict = {}
        try:
            summary_obj = json.loads(summary_json or "{}")
            if isinstance(summary_obj, dict):
                summary = summary_obj
        except json.JSONDecodeError:
            summary = {}

        try:
            payload_obj = json.loads(payload_json or "{}")
            if isinstance(payload_obj, dict):
                payload = payload_obj
        except json.JSONDecodeError:
            payload = {}

        task_type = str(
            summary.get("task_type")
            or payload.get("task_type")
            or "legacy"
        )
        title = str(
            summary.get("title")
            or payload.get("title")
            or "Recovered saved task"
        )
        return task_type, title

    def close(self) -> None:
        """Close all database connections."""
        if hasattr(self._local, 'connection') and self._local.connection:
            self._local.connection.close()
            self._local.connection = None

    @classmethod
    def reset_instance(cls) -> None:
        """Reset the singleton instance (useful for testing)."""
        with cls._lock:
            if cls._instance is not None:
                cls._instance.close()
                cls._instance = None
