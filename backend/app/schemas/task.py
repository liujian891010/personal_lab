from __future__ import annotations

from pydantic import BaseModel


class TaskItem(BaseModel):
    id: int
    task_type: str
    target_kind: str
    target_id: str | None = None
    title: str
    description: str | None = None
    priority: str
    status: str
    created_by: str
    created_at: str
    updated_at: str


class TaskListResponse(BaseModel):
    items: list[TaskItem]
    page: int
    page_size: int
    total: int
