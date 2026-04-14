from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import PlainTextResponse

from .auth import require_user
from ..schemas.report import ReportDetail, ReportListResponse
from ..services.report_service import report_service


router = APIRouter(prefix="/api", tags=["reports"], dependencies=[Depends(require_user)])


@router.get("/reports", response_model=ReportListResponse)
def list_reports(
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
    tag: str | None = None,
    source_domain: str | None = None,
    skill_name: str | None = None,
    status: str | None = None,
    folder_id: str | None = None,
    unfiled: bool = False,
) -> ReportListResponse:
    data = report_service.list_reports(
        page=page,
        page_size=page_size,
        tag=tag,
        source_domain=source_domain,
        skill_name=skill_name,
        status=status,
        folder_id=folder_id,
        unfiled=unfiled,
    )
    return ReportListResponse(**data)


@router.get("/reports/{report_id}", response_model=ReportDetail)
def get_report(report_id: str) -> ReportDetail:
    data = report_service.get_report(report_id)
    if data is None:
        raise HTTPException(status_code=404, detail="report not found")
    return ReportDetail(**data)


@router.get("/reports/{report_id}/raw", response_class=PlainTextResponse)
def get_report_raw(report_id: str) -> PlainTextResponse:
    content = report_service.get_report_raw(report_id)
    if content is None:
        raise HTTPException(status_code=404, detail="report not found")
    return PlainTextResponse(content)
