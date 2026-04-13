from __future__ import annotations

import sqlite3

from fastapi import APIRouter

from ..config import settings
from ..db import db_manager, row_to_dict
from ..schemas.health import DirectoryStatus, HealthResponse


router = APIRouter(prefix="/api", tags=["health"])


@router.get("/health", response_model=HealthResponse)
def get_health() -> HealthResponse:
    latest_sync = None
    database_ready = False

    try:
        with db_manager.session() as connection:
            connection.execute("SELECT 1")
            database_ready = True
            row = connection.execute(
                """
                SELECT id, mode, started_at, finished_at, status, scanned_count,
                       created_count, updated_count, deleted_count, failed_count, message
                FROM sync_jobs
                ORDER BY id DESC
                LIMIT 1
                """
            ).fetchone()
            latest_sync = row_to_dict(row)
    except sqlite3.Error:
        database_ready = False

    return HealthResponse(
        status="ok" if database_ready else "degraded",
        service=settings.api_title,
        version=settings.api_version,
        database_path=str(settings.sqlite_path),
        database_ready=database_ready,
        raw_root=DirectoryStatus(path=str(settings.raw_root), exists=settings.raw_root.exists()),
        reports_root=DirectoryStatus(path=str(settings.reports_root), exists=settings.reports_root.exists()),
        knowledge_root=DirectoryStatus(path=str(settings.knowledge_root), exists=settings.knowledge_root.exists()),
        latest_sync=latest_sync,
    )
