from __future__ import annotations

from fastapi import APIRouter, HTTPException

from ..schemas.query import AskRequest, AskResponse, WritebackRequest, WritebackResponse
from ..services.query_service import query_service


router = APIRouter(prefix="/api/query", tags=["query"])


@router.post("/ask", response_model=AskResponse)
def ask_question(payload: AskRequest) -> AskResponse:
    try:
        result = query_service.ask(question=payload.question, writeback=payload.writeback)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return AskResponse(**result)


@router.post("/writeback", response_model=WritebackResponse)
def writeback_answer(payload: WritebackRequest) -> WritebackResponse:
    try:
        result = query_service.writeback(run_id=payload.run_id, kind=payload.kind)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return WritebackResponse(**result)
