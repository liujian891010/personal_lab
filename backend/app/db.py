from __future__ import annotations

import sqlite3
from contextlib import contextmanager
from pathlib import Path
from typing import Iterator

from .config import settings


SCHEMA_PATH = Path(__file__).resolve().parent / "sql" / "schema.sql"


class DatabaseManager:
    def __init__(self, db_path: Path, schema_path: Path) -> None:
        self.db_path = db_path
        self.schema_path = schema_path

    def connect(self) -> sqlite3.Connection:
        connection = sqlite3.connect(self.db_path)
        connection.row_factory = sqlite3.Row
        connection.execute("PRAGMA foreign_keys = ON;")
        connection.execute("PRAGMA journal_mode = WAL;")
        return connection

    def initialize(self) -> None:
        schema_sql = self.schema_path.read_text(encoding="utf-8")
        with self.connect() as connection:
            connection.executescript(schema_sql)
            self._apply_post_schema_migrations(connection)
            connection.commit()

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
            table_name="upload_jobs",
            column_name="folder_id_ref",
            column_sql="TEXT REFERENCES report_folders(folder_id) ON DELETE SET NULL",
        )
        # indexes for folder_id_ref (ignore errors if already exist)
        for table in ("reports", "upload_jobs"):
            try:
                connection.execute(
                    f"CREATE INDEX IF NOT EXISTS idx_{table}_folder_id_ref ON {table}(folder_id_ref)"
                )
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
