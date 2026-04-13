from __future__ import annotations

from pydantic import BaseModel, Field


class CompileRequest(BaseModel):
    report_id: str | None = None
    mode: str = Field(default="propose")


class CompileResponse(BaseModel):
    mode: str
    processed_reports: list[str] = Field(default_factory=list)
    created_page_ids: list[str] = Field(default_factory=list)
    updated_page_ids: list[str] = Field(default_factory=list)
    task_ids: list[int] = Field(default_factory=list)
    conflict_ids: list[int] = Field(default_factory=list)
    llm_used: bool = False
    message: str
