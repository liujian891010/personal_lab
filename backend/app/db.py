from __future__ import annotations

import sqlite3
from contextlib import contextmanager
from pathlib import Path
from typing import Iterator

from .config import ensure_workspace_dirs, get_workspace_sqlite_path, settings
from .workspace import get_current_workspace_id


SCHEMA_PATH = Path(__file__).resolve().parent / "sql" / "schema.sql"


class DatabaseManager:
    def __init__(self, db_path: Path, schema_path: Path) -> None:
        self.default_db_path = db_path
        self.schema_path = schema_path
        self._initialized_paths: set[str] = set()

    def _resolve_db_path(self) -> Path:
        workspace_id = get_current_workspace_id()
        if not workspace_id:
            return self.default_db_path
        ensure_workspace_dirs(workspace_id)
        return get_workspace_sqlite_path(workspace_id)

    def current_db_path(self) -> Path:
        return self._resolve_db_path()

    def connect(self) -> sqlite3.Connection:
        db_path = self._resolve_db_path()
        db_path.parent.mkdir(parents=True, exist_ok=True)
        self.initialize(db_path=db_path)
        connection = sqlite3.connect(db_path)
        connection.row_factory = sqlite3.Row
        connection.execute("PRAGMA foreign_keys = ON;")
        connection.execute("PRAGMA journal_mode = WAL;")
        return connection

    def initialize(self, db_path: Path | None = None) -> None:
        actual_db_path = db_path or self.default_db_path
        cache_key = str(actual_db_path.resolve())
        if cache_key in self._initialized_paths:
            return
        actual_db_path.parent.mkdir(parents=True, exist_ok=True)
        schema_sql = self.schema_path.read_text(encoding="utf-8")
        connection = sqlite3.connect(actual_db_path)
        connection.row_factory = sqlite3.Row
        connection.execute("PRAGMA foreign_keys = ON;")
        connection.execute("PRAGMA journal_mode = WAL;")
        with connection:
            connection.executescript(schema_sql)
            self._apply_post_schema_migrations(connection)
            connection.commit()
        self._initialized_paths.add(cache_key)

    def _apply_post_schema_migrations(self, connection: sqlite3.Connection) -> None:
        self._ensure_column(
            connection,
            table_name="upload_jobs",
            column_name="auto_process",
            column_sql="INTEGER NOT NULL DEFAULT 0",
        )
        self._ensure_column(
            connection,
            table_name="reports",
            column_name="folder_id_ref",
            column_sql="TEXT REFERENCES report_folders(folder_id) ON DELETE SET NULL",
        )
        self._ensure_column(
            connection,
            table_name="reports",
            column_name="deleted_at",
            column_sql="TEXT",
        )
        self._ensure_column(
            connection,
            table_name="reports",
            column_name="deleted_by",
            column_sql="TEXT",
        )
        self._ensure_column(
            connection,
            table_name="reports",
            column_name="purge_after",
            column_sql="TEXT",
        )
        self._ensure_column(
            connection,
            table_name="reports",
            column_name="storage_cleanup_status",
            column_sql="TEXT NOT NULL DEFAULT 'pending'",
        )
        self._ensure_column(
            connection,
            table_name="upload_jobs",
            column_name="folder_id_ref",
            column_sql="TEXT REFERENCES report_folders(folder_id) ON DELETE SET NULL",
        )
        connection.execute(
            """
            CREATE TABLE IF NOT EXISTS report_delete_audit_logs (
                id                 INTEGER PRIMARY KEY AUTOINCREMENT,
                report_id          TEXT NOT NULL,
                action             TEXT NOT NULL,
                actor_user_id      TEXT,
                actor_workspace_id TEXT,
                detail             TEXT,
                created_at         TEXT NOT NULL
            )
            """
        )
        for table_name in ("reports", "wiki_pages", "upload_jobs", "upload_artifacts"):
            self._ensure_column(connection, table_name=table_name, column_name="storage_provider", column_sql="TEXT")
            self._ensure_column(connection, table_name=table_name, column_name="storage_bucket", column_sql="TEXT")
            self._ensure_column(connection, table_name=table_name, column_name="object_key", column_sql="TEXT")
            self._ensure_column(
                connection,
                table_name=table_name,
                column_name="storage_status",
                column_sql="TEXT NOT NULL DEFAULT 'legacy'",
            )
        # indexes for folder_id_ref (ignore errors if already exist)
        for table in ("reports", "upload_jobs"):
            try:
                connection.execute(
                    f"CREATE INDEX IF NOT EXISTS idx_{table}_folder_id_ref ON {table}(folder_id_ref)"
                )
            except Exception:
                pass
        for index_sql in (
            "CREATE INDEX IF NOT EXISTS idx_reports_deleted_at ON reports(deleted_at)",
            "CREATE INDEX IF NOT EXISTS idx_reports_purge_after ON reports(purge_after)",
            "CREATE INDEX IF NOT EXISTS idx_reports_storage_cleanup_status ON reports(storage_cleanup_status)",
            "CREATE INDEX IF NOT EXISTS idx_report_delete_audit_logs_report_id "
            "ON report_delete_audit_logs(report_id, created_at DESC)",
        ):
            try:
                connection.execute(index_sql)
            except Exception:
                pass
        for table in ("reports", "wiki_pages", "upload_jobs", "upload_artifacts"):
            try:
                connection.execute(f"CREATE INDEX IF NOT EXISTS idx_{table}_object_key ON {table}(object_key)")
            except Exception:
                pass

    def _ensure_column(
        self,
        connection: sqlite3.Connection,
        *,
        table_name: str,
        column_name: str,
        column_sql: str,
    ) -> None:
        rows = connection.execute(f"PRAGMA table_info({table_name})").fetchall()
        if not rows:
            return
        existing = {str(row["name"]) for row in rows}
        if column_name in existing:
            return
        connection.execute(f"ALTER TABLE {table_name} ADD COLUMN {column_name} {column_sql}")

    @contextmanager
    def session(self) -> Iterator[sqlite3.Connection]:
        connection = self.connect()
        try:
            yield connection
            connection.commit()
        finally:
            connection.close()


db_manager = DatabaseManager(settings.sqlite_path, SCHEMA_PATH)


def row_to_dict(row: sqlite3.Row | None) -> dict | None:
    if row is None:
        return None
    return {key: row[key] for key in row.keys()}
