from __future__ import annotations

from collections.abc import AsyncIterator

from fastapi import APIRouter, Depends, HTTPException, Query, status

from ..config import ensure_workspace_dirs, get_workspace_sqlite_path
from ..db import db_manager
from ..schemas.report import ReportDetail
from ..services.report_service import report_service
from ..services.report_share_service import (
    ReportShareTokenError,
    ReportShareTokenExpiredError,
    report_share_service,
)
from ..workspace import UserContext, reset_current_user_context, set_current_user_context


router = APIRouter(prefix="/api/public", tags=["public-reports"])


async def bind_share_context(
    report_id: str,
    share_token: str = Query(..., min_length=1),
) -> AsyncIterator[UserContext]:
    try:
        payload = report_share_service.verify_share_token(share_token, report_id=report_id)
    except ReportShareTokenExpiredError as exc:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail=str(exc)) from exc
    except ReportShareTokenError as exc:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail=str(exc)) from exc

    ensure_workspace_dirs(payload.workspace_id)
    db_manager.initialize(db_path=get_workspace_sqlite_path(payload.workspace_id))
    public_user = UserContext(
        user_id="public-share",
        user_name="Public Share",
        workspace_id=payload.workspace_id,
        workspace_name=payload.workspace_id,
        roles=["public_share"],
        appkey_status="shared",
    )
    token = set_current_user_context(public_user)
    try:
        yield public_user
    finally:
        reset_current_user_context(token)


@router.get("/reports/{report_id}", response_model=ReportDetail)
def get_public_report(
    report_id: str,
    _: UserContext = Depends(bind_share_context),
) -> ReportDetail:
    data = report_service.get_report(report_id)
    if data is None:
        raise HTTPException(status_code=404, detail="report not found")
    return ReportDetail(**data)
