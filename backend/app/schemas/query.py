from __future__ import annotations

from pydantic import BaseModel, Field


class AskRequest(BaseModel):
    question: str
    writeback: str = Field(default="suggest")


class QuerySourceWikiPage(BaseModel):
    page_id: str
    slug: str
    title: str
    page_type: str
    summary: str | None = None
    score: float


class QuerySourceReport(BaseModel):
    report_id: str
    title: str
    source_ref: str
    source_domain: str
    generated_at: str
    summary: str
    score: float


class AskResponse(BaseModel):
    run_id: int
    question: str
    answer: str
    answer_summary: str
    source_wiki_pages: list[QuerySourceWikiPage] = Field(default_factory=list)
    source_reports: list[QuerySourceReport] = Field(default_factory=list)
    should_writeback: bool
    suggested_writeback_kind: str | None = None


class WritebackRequest(BaseModel):
    run_id: int
    kind: str = Field(default="question_page")


class WritebackResponse(BaseModel):
    run_id: int
    kind: str
    status: str
    page_id: str | None = None
    task_id: int | None = None
    message: str
