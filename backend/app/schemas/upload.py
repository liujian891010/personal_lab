from __future__ import annotations

from pydantic import BaseModel, Field


class UploadArtifact(BaseModel):
    artifact_kind: str
    file_path: str
    content_hash: str | None = None
    byte_size: int | None = None
    created_at: str | None = None


class UploadSummary(BaseModel):
    upload_id: str
    original_filename: str
    title: str | None = None
    source_ref: str
    file_ext: str
    file_size_bytes: int
    upload_status: str
    processing_stage: str
    report_id_ref: str | None = None
    retry_count: int
    created_at: str
    updated_at: str


class UploadListResponse(BaseModel):
    items: list[UploadSummary]
    page: int
    page_size: int
    total: int


class UploadCreateResponse(BaseModel):
    upload_id: str
    original_filename: str
    source_ref: str
    upload_status: str
    processing_stage: str
    auto_process: bool
    auto_compile: bool
    compile_mode: str | None = None
    created_at: str


class UploadProcessRequest(BaseModel):
    auto_compile: bool | None = None
    compile_mode: str | None = None


class UploadRetryRequest(BaseModel):
    from_stage: str | None = None
    auto_compile: bool | None = None
    compile_mode: str | None = None


class UploadDetail(UploadSummary):
    stored_filename: str
    storage_path: str
    mime_type: str | None = None
    source_type: str
    auto_process: bool
    auto_compile: bool
    compile_mode: str | None = None
    triggered_by: str
    error_code: str | None = None
    error_message: str | None = None
    content_hash: str | None = None
    completed_at: str | None = None
    report_detail_url: str | None = None
    raw_preview_available: bool = False
    artifacts: list[UploadArtifact] = Field(default_factory=list)
