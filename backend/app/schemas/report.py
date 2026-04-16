from __future__ import annotations

from pydantic import BaseModel, Field


class ReportSummary(BaseModel):
    report_id: str
    title: str
    source_ref: str
    source_url: str | None = None
    source_domain: str
    source_type: str
    skill_name: str
    generated_at: str
    status: str
    summary: str
    tags: list[str] = Field(default_factory=list)
    folder_id_ref: str | None = None
    folder_name_ref: str | None = None


class ReportListResponse(BaseModel):
    items: list[ReportSummary]
    page: int
    page_size: int
    total: int


class ReportLink(BaseModel):
    url: str
    link_type: str
    anchor_text: str | None = None


class ReportDetail(ReportSummary):
    file_path: str
    author: str | None = None
    language: str | None = None
    content_hash: str
    body_size: int
    created_at: str
    updated_at: str
    content: str
    links: list[ReportLink] = Field(default_factory=list)


class ReportShareResponse(BaseModel):
    report_id: str
    share_token: str
    share_url: str
    expires_at: str
