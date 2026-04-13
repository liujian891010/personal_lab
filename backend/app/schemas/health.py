from __future__ import annotations

from pydantic import BaseModel


class DirectoryStatus(BaseModel):
    path: str
    exists: bool


class HealthResponse(BaseModel):
    status: str
    service: str
    version: str
    database_path: str
    database_ready: bool
    raw_root: DirectoryStatus
    raw_uploads_root: DirectoryStatus
    reports_root: DirectoryStatus
    knowledge_root: DirectoryStatus
    uploads_root: DirectoryStatus
    upload_inbox_root: DirectoryStatus
    upload_working_root: DirectoryStatus
    upload_processed_root: DirectoryStatus
    upload_failed_root: DirectoryStatus
    latest_sync: dict | None = None
