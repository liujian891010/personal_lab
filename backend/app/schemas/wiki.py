from __future__ import annotations

from pydantic import BaseModel, Field


class WikiPageSummary(BaseModel):
    page_id: str
    page_type: str
    file_path: str
    slug: str
    title: str
    status: str
    summary: str | None = None
    confidence: float | None = None
    created_at: str
    updated_at: str
    tags: list[str] = Field(default_factory=list)
    source_report_count: int = 0


class WikiPageListResponse(BaseModel):
    items: list[WikiPageSummary]
    page: int
    page_size: int
    total: int


class WikiSourceReport(BaseModel):
    report_id: str
    title: str
    source_ref: str
    source_domain: str
    generated_at: str
    evidence_role: str


class WikiRelatedPage(BaseModel):
    page_id: str
    slug: str
    title: str
    page_type: str
    link_type: str


class WikiPageDetail(WikiPageSummary):
    content_hash: str
    content: str
    source_reports: list[WikiSourceReport] = Field(default_factory=list)
    related_pages: list[WikiRelatedPage] = Field(default_factory=list)
