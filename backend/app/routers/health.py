from __future__ import annotations

import sqlite3

from fastapi import APIRouter, Depends

from ..config import settings
from ..db import db_manager, row_to_dict
from ..routers.auth import bind_optional_user_context
from ..schemas.health import DirectoryStatus, HealthResponse
from ..workspace import UserContext


router = APIRouter(prefix="/api", tags=["health"])


@router.get("/health", response_model=HealthResponse)
def get_health(_: UserContext | None = Depends(bind_optional_user_context)) -> HealthResponse:
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
        database_path=str(db_manager.current_db_path()),
        database_ready=database_ready,
        raw_root=DirectoryStatus(path=str(settings.raw_root), exists=settings.raw_root.exists()),
        raw_uploads_root=DirectoryStatus(
            path=str(settings.raw_uploads_root),
            exists=settings.raw_uploads_root.exists(),
        ),
        reports_root=DirectoryStatus(path=str(settings.reports_root), exists=settings.reports_root.exists()),
        knowledge_root=DirectoryStatus(path=str(settings.knowledge_root), exists=settings.knowledge_root.exists()),
        uploads_root=DirectoryStatus(path=str(settings.uploads_root), exists=settings.uploads_root.exists()),
        upload_inbox_root=DirectoryStatus(
            path=str(settings.upload_inbox_root),
            exists=settings.upload_inbox_root.exists(),
        ),
        upload_working_root=DirectoryStatus(
            path=str(settings.upload_working_root),
            exists=settings.upload_working_root.exists(),
        ),
        upload_processed_root=DirectoryStatus(
            path=str(settings.upload_processed_root),
            exists=settings.upload_processed_root.exists(),
        ),
        upload_failed_root=DirectoryStatus(
            path=str(settings.upload_failed_root),
            exists=settings.upload_failed_root.exists(),
        ),
        latest_sync=latest_sync,
    )
