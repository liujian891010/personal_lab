from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Query

from .auth import require_user
from ..schemas.conflict import ConflictListResponse
from ..schemas.lint import LintRequest, LintResponse
from ..schemas.task import TaskListResponse
from ..schemas.wiki import WikiPageDetail, WikiPageListResponse
from ..services.conflict_service import conflict_service
from ..services.lint_service import lint_service
from ..services.task_service import task_service
from ..services.wiki_service import wiki_service


router = APIRouter(prefix="/api/wiki", tags=["wiki"], dependencies=[Depends(require_user)])


@router.get("/pages", response_model=WikiPageListResponse)
def list_wiki_pages(
    page_type: str | None = None,
    tag: str | None = None,
    status: str | None = None,
    q: str | None = None,
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
) -> WikiPageListResponse:
    return WikiPageListResponse(
        **wiki_service.list_pages(
            page_type=page_type,
            tag=tag,
            status=status,
            q=q,
            page=page,
            page_size=page_size,
        )
    )


@router.get("/pages/{page_id}", response_model=WikiPageDetail)
def get_wiki_page(page_id: str) -> WikiPageDetail:
    data = wiki_service.get_page(page_id)
    if data is None:
        raise HTTPException(status_code=404, detail="wiki page not found")
    return WikiPageDetail(**data)


@router.get("/by-slug/{slug}", response_model=WikiPageDetail)
def get_wiki_page_by_slug(slug: str) -> WikiPageDetail:
    data = wiki_service.get_page_by_slug(slug)
    if data is None:
        raise HTTPException(status_code=404, detail="wiki page not found")
    return WikiPageDetail(**data)


@router.get("/tasks", response_model=TaskListResponse)
def list_knowledge_tasks(
    status: str | None = None,
    task_type: str | None = None,
    target_kind: str | None = None,
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
) -> TaskListResponse:
    return TaskListResponse(
        **task_service.list_tasks(
            status=status,
            task_type=task_type,
            target_kind=target_kind,
            page=page,
            page_size=page_size,
        )
    )


@router.get("/conflicts", response_model=ConflictListResponse)
def list_knowledge_conflicts(
    status: str | None = None,
    severity: str | None = None,
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
) -> ConflictListResponse:
    return ConflictListResponse(
        **conflict_service.list_conflicts(
            status=status,
            severity=severity,
            page=page,
            page_size=page_size,
        )
    )


@router.post("/lint", response_model=LintResponse)
def run_wiki_lint(payload: LintRequest) -> LintResponse:
    try:
        result = lint_service.run(mode=payload.mode)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return LintResponse(**result)
