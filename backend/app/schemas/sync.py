from __future__ import annotations

from pydantic import BaseModel, Field


class SyncRequest(BaseModel):
    mode: str = Field(default="incremental")


class SyncResponse(BaseModel):
    job_id: int
    mode: str
    scanned_count: int
    created_count: int
    updated_count: int
    deleted_count: int
    failed_count: int
    status: str
    took_ms: int
    warnings: list[dict[str, str]] = Field(default_factory=list)
