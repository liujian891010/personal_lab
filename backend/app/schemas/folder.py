from __future__ import annotations

from pydantic import BaseModel


class FolderSummary(BaseModel):
    folder_id: str
    folder_name: str
    folder_slug: str
    description: str | None = None
    sort_order: int
    report_count: int
    created_at: str
    updated_at: str


class FolderListResponse(BaseModel):
    items: list[FolderSummary]
    total: int


class FolderCreateRequest(BaseModel):
    folder_name: str
    description: str | None = None
    sort_order: int = 0


class FolderUpdateRequest(BaseModel):
    folder_name: str | None = None
    description: str | None = None
    sort_order: int | None = None


class ReportMoveFolderRequest(BaseModel):
    folder_id: str | None = None  # None = move to Unfiled
