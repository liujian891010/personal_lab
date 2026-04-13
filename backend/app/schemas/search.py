from __future__ import annotations

from pydantic import BaseModel, Field


class SearchItem(BaseModel):
    report_id: str
    title: str
    source_ref: str
    source_domain: str
    source_type: str
    generated_at: str
    snippet: str
    score: float


class SearchResponse(BaseModel):
    items: list[SearchItem]
    total: int
    took_ms: int


class CountItem(BaseModel):
    tag: str | None = None
    source_domain: str | None = None
    count: int


class CountListResponse(BaseModel):
    items: list[dict] = Field(default_factory=list)
