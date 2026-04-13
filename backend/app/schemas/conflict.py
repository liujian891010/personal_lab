from __future__ import annotations

from pydantic import BaseModel


class ConflictItem(BaseModel):
    id: int
    topic_key: str
    page_id_ref: str | None = None
    old_claim: str
    new_claim: str
    evidence_report_id: str | None = None
    severity: str
    status: str
    created_at: str
    resolved_at: str | None = None


class ConflictListResponse(BaseModel):
    items: list[ConflictItem]
    page: int
    page_size: int
    total: int
