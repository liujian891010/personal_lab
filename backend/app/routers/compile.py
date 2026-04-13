from __future__ import annotations

from fastapi import APIRouter, HTTPException

from ..schemas.compile import CompileRequest, CompileResponse
from ..services.compile_service import compile_service


router = APIRouter(prefix="/api/wiki", tags=["compile"])


@router.post("/compile", response_model=CompileResponse)
def compile_report(payload: CompileRequest) -> CompileResponse:
    try:
        result = compile_service.compile(report_id=payload.report_id, mode=payload.mode)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    return CompileResponse(**result)
