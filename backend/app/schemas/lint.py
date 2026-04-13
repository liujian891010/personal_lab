from __future__ import annotations

from pydantic import BaseModel, Field


class LintRequest(BaseModel):
    mode: str = Field(default="light")


class LintFinding(BaseModel):
    rule_name: str
    target_kind: str
    target_id: str
    severity: str
    detail: str
    created_task_id: int | None = None
    created_conflict_id: int | None = None


class LintResponse(BaseModel):
    mode: str
    created_task_ids: list[int] = Field(default_factory=list)
    created_conflict_ids: list[int] = Field(default_factory=list)
    findings: list[LintFinding] = Field(default_factory=list)
    total_findings: int
    llm_used: bool = False
    message: str
