from __future__ import annotations

from fastapi import APIRouter, File, Form, HTTPException, Query, UploadFile, status
from fastapi.responses import PlainTextResponse

from ..schemas.upload import UploadCreateResponse, UploadDetail, UploadListResponse, UploadProcessRequest, UploadRetryRequest
from ..services.upload_service import UploadNotFoundError, UploadValidationError, upload_service


router = APIRouter(prefix="/api", tags=["uploads"])


@router.post("/uploads", response_model=UploadCreateResponse, status_code=status.HTTP_201_CREATED)
async def create_upload(
    file: UploadFile = File(...),
    auto_process: bool = Form(default=False),
    auto_compile: bool = Form(default=False),
    compile_mode: str | None = Form(default=None),
    title: str | None = Form(default=None),
    tags: str | None = Form(default=None),
    folder_id: str | None = Form(default=None),
) -> UploadCreateResponse:
    try:
        payload = upload_service.create_upload(
            upload_file=file,
            auto_process=auto_process,
            auto_compile=auto_compile,
            compile_mode=compile_mode,
            title=title,
            tags=tags,
            folder_id=folder_id,
        )
    except UploadValidationError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    finally:
        await file.close()

    if auto_process:
        processed = upload_service.process_upload(
            payload["upload_id"],
            auto_compile=auto_compile,
            compile_mode=compile_mode,
        )
        payload["upload_status"] = processed["upload_status"]
        payload["processing_stage"] = processed["processing_stage"]

    return UploadCreateResponse(**payload)


@router.get("/uploads", response_model=UploadListResponse)
def list_uploads(
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
    status: str | None = None,
    stage: str | None = None,
    q: str | None = None,
) -> UploadListResponse:
    data = upload_service.list_uploads(
        page=page,
        page_size=page_size,
        status=status,
        stage=stage,
        q=q,
    )
    return UploadListResponse(**data)


@router.get("/uploads/{upload_id}", response_model=UploadDetail)
def get_upload(upload_id: str) -> UploadDetail:
    try:
        data = upload_service.get_upload(upload_id)
    except UploadNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc

    if data is None:
        raise HTTPException(status_code=404, detail="upload not found")
    return UploadDetail(**data)


@router.post("/uploads/{upload_id}/process", response_model=UploadDetail)
def process_upload(upload_id: str, payload: UploadProcessRequest) -> UploadDetail:
    try:
        data = upload_service.process_upload(
            upload_id,
            auto_compile=payload.auto_compile,
            compile_mode=payload.compile_mode,
        )
    except UploadNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except UploadValidationError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    return UploadDetail(**data)


@router.get("/uploads/{upload_id}/raw", response_class=PlainTextResponse)
def get_upload_raw(upload_id: str) -> PlainTextResponse:
    try:
        content = upload_service.get_upload_raw(upload_id)
    except UploadValidationError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    if content is None:
        raise HTTPException(status_code=404, detail="upload raw text not found")
    return PlainTextResponse(content)


@router.get("/uploads/{upload_id}/report-preview", response_class=PlainTextResponse)
def get_upload_report_preview(upload_id: str) -> PlainTextResponse:
    try:
        content = upload_service.get_upload_report_preview(upload_id)
    except UploadValidationError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    if content is None:
        raise HTTPException(status_code=404, detail="upload report preview not found")
    return PlainTextResponse(content)


@router.post("/uploads/{upload_id}/retry", response_model=UploadDetail)
def retry_upload(upload_id: str, payload: UploadRetryRequest) -> UploadDetail:
    try:
        data = upload_service.retry_upload(
            upload_id,
            from_stage=payload.from_stage,
            auto_compile=payload.auto_compile,
            compile_mode=payload.compile_mode,
        )
    except UploadNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except UploadValidationError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    return UploadDetail(**data)
