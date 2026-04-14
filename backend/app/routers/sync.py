from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException

from .auth import require_user
from ..schemas.sync import SyncRequest, SyncResponse
from ..services.sync_service import sync_service


router = APIRouter(prefix="/api", tags=["sync"], dependencies=[Depends(require_user)])


@router.post("/sync", response_model=SyncResponse)
def run_sync(payload: SyncRequest) -> SyncResponse:
    try:
        result = sync_service.run(payload.mode)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    return SyncResponse(
        job_id=result.job_id,
        mode=result.mode,
        scanned_count=result.scanned_count,
        created_count=result.created_count,
        updated_count=result.updated_count,
        deleted_count=result.deleted_count,
        failed_count=result.failed_count,
        status=result.status,
        took_ms=result.took_ms,
        warnings=result.warnings,
    )
