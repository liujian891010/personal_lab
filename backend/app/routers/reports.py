from __future__ import annotations

from urllib.parse import quote

from fastapi import APIRouter, Depends, HTTPException, Query, Request, Response, status
from fastapi.responses import PlainTextResponse

from .auth import require_user
from ..schemas.report import ReportDetail, ReportListResponse, ReportShareResponse
from ..services.report_service import ReportAlreadyDeletedError, ReportNotFoundError, report_service
from ..services.report_share_service import report_share_service
from ..workspace import get_current_user_context


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


@router.post("/reports/{report_id}/share", response_model=ReportShareResponse)
def create_report_share(
    report_id: str,
    request: Request,
    expires_in_hours: int = Query(default=168, ge=1, le=720),
) -> ReportShareResponse:
    data = report_service.get_report(report_id)
    if data is None:
        raise HTTPException(status_code=404, detail="report not found")
    current_user = get_current_user_context()
    if current_user is None:
        raise HTTPException(status_code=401, detail="authentication required")
    share = report_share_service.create_share_link(
        report_id=report_id,
        workspace_id=current_user.workspace_id,
        expires_in_hours=expires_in_hours,
    )
    share_url = (
        f"{str(request.base_url).rstrip('/')}/app/#/report-only/{quote(report_id, safe='')}"
        f"?share_token={quote(share.share_token, safe='')}"
    )
    return ReportShareResponse(
        report_id=report_id,
        share_token=share.share_token,
        share_url=share_url,
        expires_at=share.expires_at,
    )


@router.delete("/reports/{report_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_report(report_id: str) -> Response:
    try:
        report_service.delete_report(report_id)
    except ReportNotFoundError as exc:
        raise HTTPException(status_code=404, detail="report not found") from exc
    except ReportAlreadyDeletedError as exc:
        raise HTTPException(status_code=409, detail="report already deleted") from exc
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.post("/reports/purge-expired")
def purge_expired_reports(limit: int = Query(default=100, ge=1, le=500)) -> dict:
    return report_service.purge_expired_reports(limit=limit)
