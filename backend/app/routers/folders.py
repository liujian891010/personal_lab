from __future__ import annotations

from fastapi import APIRouter, HTTPException, status

from ..schemas.folder import (
    FolderCreateRequest,
    FolderListResponse,
    FolderSummary,
    FolderUpdateRequest,
    ReportMoveFolderRequest,
)
from ..services.folder_service import (
    FolderConflictError,
    FolderNotEmptyError,
    FolderNotFoundError,
    folder_service,
)

router = APIRouter(prefix="/api", tags=["folders"])


@router.get("/report-folders", response_model=FolderListResponse)
def list_folders() -> FolderListResponse:
    return FolderListResponse(**folder_service.list_folders())


@router.post("/report-folders", response_model=FolderSummary, status_code=status.HTTP_201_CREATED)
def create_folder(payload: FolderCreateRequest) -> FolderSummary:
    try:
        data = folder_service.create_folder(
            folder_name=payload.folder_name,
            description=payload.description,
            sort_order=payload.sort_order,
        )
    except FolderConflictError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    return FolderSummary(**data)


@router.get("/report-folders/{folder_id}", response_model=FolderSummary)
def get_folder(folder_id: str) -> FolderSummary:
    try:
        return FolderSummary(**folder_service.get_folder(folder_id))
    except FolderNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.patch("/report-folders/{folder_id}", response_model=FolderSummary)
def update_folder(folder_id: str, payload: FolderUpdateRequest) -> FolderSummary:
    try:
        data = folder_service.update_folder(
            folder_id,
            folder_name=payload.folder_name,
            description=payload.description,
            sort_order=payload.sort_order,
        )
    except FolderNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except FolderConflictError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    return FolderSummary(**data)


@router.delete("/report-folders/{folder_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_folder(folder_id: str) -> None:
    try:
        folder_service.delete_folder(folder_id)
    except FolderNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except FolderNotEmptyError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc


@router.post("/reports/{report_id}/move-folder", status_code=status.HTTP_204_NO_CONTENT)
def move_report_folder(report_id: str, payload: ReportMoveFolderRequest) -> None:
    try:
        folder_service.move_report(report_id, payload.folder_id)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except FolderNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
