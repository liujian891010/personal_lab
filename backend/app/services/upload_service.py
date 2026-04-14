from __future__ import annotations

import hashlib
import mimetypes
import re
import sqlite3
from datetime import datetime
from pathlib import Path
from typing import Any, BinaryIO

from bs4 import BeautifulSoup
from fastapi import UploadFile
from docx import Document as DocxDocument
import fitz
from pypdf import PdfReader
from rapidocr_onnxruntime import RapidOCR

from ..config import settings
from ..db import db_manager, row_to_dict
from .file_service import resolve_raw_upload_path, resolve_upload_storage_path, resolve_upload_working_path
from .compile_service import compile_service
from .sync_service import sync_service


MAX_UPLOAD_BYTES = 50 * 1024 * 1024
MIN_EXTRACTED_TEXT_LENGTH = 40
PDF_TEXT_LAYER_MIN_LENGTH = 120
PDF_OCR_ZOOM = 1.2
PDF_OCR_MAX_PAGES = 8
PDF_OCR_TARGET_TEXT_LENGTH = 1200
ALLOWED_EXTENSIONS = {"txt", "md", "html", "htm", "pdf", "docx"}
ALLOWED_MIME_TYPES: dict[str, set[str]] = {
    "txt": {"text/plain", "application/octet-stream"},
    "md": {"text/markdown", "text/plain", "application/octet-stream"},
    "html": {"text/html", "application/xhtml+xml", "application/octet-stream"},
    "htm": {"text/html", "application/xhtml+xml", "application/octet-stream"},
    "pdf": {"application/pdf", "application/octet-stream"},
    "docx": {
        "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        "application/zip",
        "application/octet-stream",
    },
}


class UploadValidationError(ValueError):
    """Raised when upload input is invalid."""


class UploadNotFoundError(LookupError):
    """Raised when an upload job cannot be found."""


class UploadReviewRequiredError(ValueError):
    """Raised when extraction succeeded technically but needs human review."""


class UploadService:
    def __init__(self) -> None:
        self._ocr_engine: RapidOCR | None = None

    def create_upload(
        self,
        *,
        upload_file: UploadFile,
        auto_process: bool,
        auto_compile: bool,
        compile_mode: str | None,
        title: str | None,
        tags: str | None,
        folder_id: str | None = None,
    ) -> dict[str, Any]:
        original_filename = self._normalize_original_filename(upload_file.filename)
        file_ext = self._validate_file_extension(original_filename)
        mime_type = self._normalize_optional_string(upload_file.content_type)
        self._validate_mime_type(file_ext, mime_type)
        normalized_title = self._normalize_optional_string(title)
        _ = self._normalize_optional_string(tags)
        normalized_compile_mode = self._validate_compile_mode(compile_mode, auto_compile)

        upload_id = self._generate_upload_id()
        now = self._now()
        storage_dir = now.strftime("inbox/%Y/%m")
        stored_filename = f"{upload_id}__{self._sanitize_filename(original_filename)}"
        storage_path = f"{storage_dir}/{stored_filename}"
        source_ref = f"upload://{upload_id}/{original_filename}"
        destination = resolve_upload_storage_path(storage_path)
        destination.parent.mkdir(parents=True, exist_ok=True)

        try:
            file_size_bytes, content_hash = self._write_upload_file(upload_file.file, destination)
        except Exception:
            if destination.exists():
                destination.unlink(missing_ok=True)
            raise

        upload_status = "queued" if auto_process else "uploaded"
        processing_stage = "stored"

        try:
            with db_manager.session() as connection:
                connection.execute(
                    """
                    INSERT INTO upload_jobs (
                        upload_id, original_filename, stored_filename, storage_path,
                        mime_type, file_ext, file_size_bytes, source_ref, source_type,
                        title, upload_status, processing_stage, report_id_ref,
                        auto_process, compile_mode, auto_compile, triggered_by,
                        error_code, error_message, retry_count, content_hash,
                        created_at, updated_at, completed_at, folder_id_ref
                    )
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, NULL, ?, ?, ?, ?, NULL, NULL, 0, ?, ?, ?, NULL, ?)
                    """,
                    (
                        upload_id,
                        original_filename,
                        stored_filename,
                        storage_path,
                        mime_type,
                        file_ext,
                        file_size_bytes,
                        source_ref,
                        "upload_file",
                        normalized_title,
                        upload_status,
                        processing_stage,
                        1 if auto_process else 0,
                        normalized_compile_mode,
                        1 if auto_compile else 0,
                        "user_upload",
                        content_hash,
                        now.isoformat(),
                        now.isoformat(),
                        folder_id,
                    ),
                )
                self._upsert_artifact(
                    connection,
                    upload_id=upload_id,
                    artifact_kind="original_file",
                    file_path=f"uploads/{storage_path}",
                    content_hash=content_hash,
                    byte_size=file_size_bytes,
                    created_at=now.isoformat(),
                )
        except sqlite3.Error:
            destination.unlink(missing_ok=True)
            raise

        return {
            "upload_id": upload_id,
            "original_filename": original_filename,
            "source_ref": source_ref,
            "upload_status": upload_status,
            "processing_stage": processing_stage,
            "auto_process": auto_process,
            "auto_compile": auto_compile,
            "compile_mode": normalized_compile_mode,
            "created_at": now.isoformat(),
        }

    def list_uploads(
        self,
        *,
        page: int,
        page_size: int,
        status: str | None,
        stage: str | None,
        q: str | None,
    ) -> dict[str, Any]:
        where_clauses: list[str] = []
        parameters: list[Any] = []

        if status:
            where_clauses.append("upload_status = ?")
            parameters.append(status)
        if stage:
            where_clauses.append("processing_stage = ?")
            parameters.append(stage)
        normalized_q = self._normalize_optional_string(q)
        if normalized_q:
            where_clauses.append("(original_filename LIKE ? OR COALESCE(title, '') LIKE ? OR source_ref LIKE ?)")
            like_value = f"%{normalized_q}%"
            parameters.extend([like_value, like_value, like_value])

        where_sql = f"WHERE {' AND '.join(where_clauses)}" if where_clauses else ""
        offset = (page - 1) * page_size

        with db_manager.session() as connection:
            total = int(
                connection.execute(
                    f"SELECT COUNT(*) FROM upload_jobs {where_sql}",
                    parameters,
                ).fetchone()[0]
            )
            rows = connection.execute(
                f"""
                SELECT uj.upload_id, uj.original_filename, uj.title, uj.source_ref, uj.file_ext, uj.file_size_bytes,
                       uj.upload_status, uj.processing_stage, uj.report_id_ref, uj.retry_count, uj.created_at, uj.updated_at,
                       uj.folder_id_ref, f.folder_name AS folder_name_ref
                FROM upload_jobs uj
                LEFT JOIN report_folders f ON f.folder_id = uj.folder_id_ref
                {where_sql}
                ORDER BY uj.created_at DESC, uj.id DESC
                LIMIT ? OFFSET ?
                """,
                [*parameters, page_size, offset],
            ).fetchall()

        items = [self._serialize_summary_row(row) for row in rows]
        return {
            "items": items,
            "page": page,
            "page_size": page_size,
            "total": total,
        }

    def get_upload(self, upload_id: str) -> dict[str, Any] | None:
        with db_manager.session() as connection:
            row = connection.execute(
                """
                SELECT uj.upload_id, uj.original_filename, uj.title, uj.stored_filename, uj.storage_path, uj.mime_type,
                       uj.file_ext, uj.file_size_bytes, uj.source_ref, uj.source_type, uj.upload_status,
                       uj.processing_stage, uj.report_id_ref, uj.auto_process, uj.compile_mode, uj.auto_compile,
                       uj.triggered_by, uj.error_code, uj.error_message, uj.retry_count, uj.content_hash,
                       uj.created_at, uj.updated_at, uj.completed_at,
                       uj.folder_id_ref, f.folder_name AS folder_name_ref
                FROM upload_jobs uj
                LEFT JOIN report_folders f ON f.folder_id = uj.folder_id_ref
                WHERE uj.upload_id = ?
                """,
                (upload_id,),
            ).fetchone()
            if row is None:
                return None

            artifacts = connection.execute(
                """
                SELECT artifact_kind, file_path, content_hash, byte_size, created_at
                FROM upload_artifacts
                WHERE upload_id_ref = ?
                ORDER BY id ASC
                """,
                (upload_id,),
            ).fetchall()

        item = row_to_dict(row) or {}
        item["auto_process"] = bool(item["auto_process"])
        item["auto_compile"] = bool(item["auto_compile"])
        item["report_detail_url"] = (
            f"/api/reports/{item['report_id_ref']}" if item.get("report_id_ref") else None
        )
        item["raw_preview_available"] = any(str(artifact["artifact_kind"]) == "extracted_text" for artifact in artifacts)
        item["artifacts"] = [row_to_dict(artifact) for artifact in artifacts if artifact is not None]
        return item

    def process_upload(
        self,
        upload_id: str,
        *,
        auto_compile: bool | None,
        compile_mode: str | None,
    ) -> dict[str, Any]:
        with db_manager.session() as connection:
            job = self._load_upload_job(connection, upload_id)
            self._ensure_processable(job)

            updated_auto_compile = bool(job["auto_compile"]) if auto_compile is None else auto_compile
            updated_compile_mode = self._validate_compile_mode(
                compile_mode if compile_mode is not None else job["compile_mode"],
                updated_auto_compile,
            )
            self._update_upload_status(
                connection,
                upload_id=upload_id,
                upload_status="processing",
                processing_stage="extracting",
                auto_compile=updated_auto_compile,
                compile_mode=updated_compile_mode,
                error_code=None,
                error_message=None,
                completed_at=None,
            )

        try:
            extracted_text, output_ext = self._extract_text(upload_id)
            normalized_text = self._normalize_extracted_text(extracted_text)
            if len(normalized_text) < MIN_EXTRACTED_TEXT_LENGTH:
                raise UploadReviewRequiredError("extracted text is too short and needs manual review")

            created_at = self._now().isoformat()
            working_relative = f"{upload_id}/extracted_text.{output_ext}"
            working_path = resolve_upload_working_path(working_relative)
            working_path.parent.mkdir(parents=True, exist_ok=True)
            working_path.write_text(normalized_text, encoding="utf-8")

            raw_relative = f"{self._now().strftime('%Y/%m')}/{upload_id}.{output_ext}"
            raw_path = resolve_raw_upload_path(raw_relative)
            raw_path.parent.mkdir(parents=True, exist_ok=True)
            raw_path.write_text(normalized_text, encoding="utf-8")

            with db_manager.session() as connection:
                self._upsert_artifact(
                    connection,
                    upload_id=upload_id,
                    artifact_kind="extracted_text",
                    file_path=f"raw/uploads/{raw_relative}",
                    content_hash=hashlib.sha1(normalized_text.encode("utf-8")).hexdigest(),
                    byte_size=len(normalized_text.encode("utf-8")),
                    created_at=created_at,
                )
                self._update_upload_status(
                    connection,
                    upload_id=upload_id,
                    upload_status="processing",
                    processing_stage="summarizing",
                    auto_compile=updated_auto_compile,
                    compile_mode=updated_compile_mode,
                    error_code=None,
                    error_message=None,
                    completed_at=None,
                )

            report_metadata = self._build_report_metadata(upload_id, normalized_text)
            report_relative_path = self._write_report_preview(upload_id, report_metadata, normalized_text)

            with db_manager.session() as connection:
                self._upsert_artifact(
                    connection,
                    upload_id=upload_id,
                    artifact_kind="report_preview",
                    file_path=f"reports/{report_relative_path}",
                    content_hash=hashlib.sha1(normalized_text.encode("utf-8")).hexdigest(),
                    byte_size=len(normalized_text.encode("utf-8")),
                    created_at=self._now().isoformat(),
                )
                self._update_upload_status(
                    connection,
                    upload_id=upload_id,
                    upload_status="processing",
                    processing_stage="syncing",
                    auto_compile=updated_auto_compile,
                    compile_mode=updated_compile_mode,
                    error_code=None,
                    error_message=None,
                    completed_at=None,
                )

            sync_service.run("incremental")

            with db_manager.session() as connection:
                connection.execute(
                    "UPDATE upload_jobs SET report_id_ref = ?, updated_at = ? WHERE upload_id = ?",
                    (report_metadata["report_id"], self._now().isoformat(), upload_id),
                )
                # inherit folder from upload job
                job_row = connection.execute(
                    "SELECT folder_id_ref FROM upload_jobs WHERE upload_id = ?", (upload_id,)
                ).fetchone()
                if job_row and job_row["folder_id_ref"]:
                    fid = job_row["folder_id_ref"]
                    connection.execute(
                        "UPDATE reports SET folder_id_ref = ?, updated_at = ? WHERE report_id = ?",
                        (fid, self._now().isoformat(), report_metadata["report_id"]),
                    )
                    connection.execute(
                        "UPDATE report_folders SET report_count = report_count + 1, updated_at = ? WHERE folder_id = ?",
                        (self._now().isoformat(), fid),
                    )

            compile_error_message: str | None = None
            if updated_auto_compile:
                try:
                    current_report_id = report_metadata["report_id"]
                    with db_manager.session() as connection:
                        self._update_upload_status(
                            connection,
                            upload_id=upload_id,
                            upload_status="processing",
                            processing_stage="compiling",
                            auto_compile=updated_auto_compile,
                            compile_mode=updated_compile_mode,
                            error_code=None,
                            error_message=None,
                            completed_at=None,
                        )
                    compile_service.compile(report_id=current_report_id, mode=updated_compile_mode or "propose")
                except Exception as exc:
                    compile_error_message = str(exc)

            final_error_code = "compile_failed" if compile_error_message else None
            final_error_message = compile_error_message
            completed_at = self._now().isoformat()
            with db_manager.session() as connection:
                self._update_upload_status(
                    connection,
                    upload_id=upload_id,
                    upload_status="completed",
                    processing_stage="done",
                    auto_compile=updated_auto_compile,
                    compile_mode=updated_compile_mode,
                    error_code=final_error_code,
                    error_message=final_error_message,
                    completed_at=completed_at,
                )
        except UploadReviewRequiredError as exc:
            with db_manager.session() as connection:
                self._update_upload_status(
                    connection,
                    upload_id=upload_id,
                    upload_status="needs_review",
                    processing_stage="error",
                    auto_compile=updated_auto_compile,
                    compile_mode=updated_compile_mode,
                    error_code="needs_review",
                    error_message=str(exc),
                    completed_at=None,
                )
            return self.get_upload(upload_id) or {}
        except Exception as exc:
            with db_manager.session() as connection:
                self._update_upload_status(
                    connection,
                    upload_id=upload_id,
                    upload_status="failed",
                    processing_stage="error",
                    auto_compile=updated_auto_compile,
                    compile_mode=updated_compile_mode,
                    error_code="extract_failed",
                    error_message=str(exc),
                    completed_at=None,
                )
            return self.get_upload(upload_id) or {}

        return self.get_upload(upload_id) or {}

    def get_upload_raw(self, upload_id: str) -> str | None:
        with db_manager.session() as connection:
            row = connection.execute(
                """
                SELECT file_path
                FROM upload_artifacts
                WHERE upload_id_ref = ? AND artifact_kind = 'extracted_text'
                ORDER BY id DESC
                LIMIT 1
                """,
                (upload_id,),
            ).fetchone()
        if row is None:
            return None
        file_path = str(row["file_path"])
        prefix = "raw/uploads/"
        if not file_path.startswith(prefix):
            raise UploadValidationError(f"unexpected extracted text path: {file_path}")
        relative_path = file_path[len(prefix) :]
        return resolve_raw_upload_path(relative_path).read_text(encoding="utf-8")

    def get_upload_report_preview(self, upload_id: str) -> str | None:
        with db_manager.session() as connection:
            row = connection.execute(
                """
                SELECT file_path
                FROM upload_artifacts
                WHERE upload_id_ref = ? AND artifact_kind = 'report_preview'
                ORDER BY id DESC
                LIMIT 1
                """,
                (upload_id,),
            ).fetchone()
        if row is None:
            return None
        file_path = str(row["file_path"])
        prefix = "reports/"
        if not file_path.startswith(prefix):
            raise UploadValidationError(f"unexpected report preview path: {file_path}")
        relative_path = file_path[len(prefix) :]
        return (settings.reports_root / relative_path).read_text(encoding="utf-8")

    def retry_upload(
        self,
        upload_id: str,
        *,
        from_stage: str | None,
        auto_compile: bool | None,
        compile_mode: str | None,
    ) -> dict[str, Any]:
        _ = self._normalize_optional_string(from_stage)

        with db_manager.session() as connection:
            row = self._load_upload_job(connection, upload_id)
            if str(row["upload_status"]) == "completed":
                raise UploadValidationError("completed uploads do not need retry")
            connection.execute(
                """
                UPDATE upload_jobs
                SET retry_count = retry_count + 1,
                    upload_status = 'uploaded',
                    processing_stage = 'stored',
                    report_id_ref = NULL,
                    error_code = NULL,
                    error_message = NULL,
                    completed_at = NULL,
                    updated_at = ?
                WHERE upload_id = ?
                """,
                (self._now().isoformat(), upload_id),
            )

        return self.process_upload(upload_id, auto_compile=auto_compile, compile_mode=compile_mode)

    def _serialize_summary_row(self, row: sqlite3.Row) -> dict[str, Any]:
        return {
            "upload_id": str(row["upload_id"]),
            "original_filename": str(row["original_filename"]),
            "title": row["title"],
            "source_ref": str(row["source_ref"]),
            "file_ext": str(row["file_ext"]),
            "file_size_bytes": int(row["file_size_bytes"]),
            "upload_status": str(row["upload_status"]),
            "processing_stage": str(row["processing_stage"]),
            "report_id_ref": row["report_id_ref"],
            "retry_count": int(row["retry_count"]),
            "created_at": str(row["created_at"]),
            "updated_at": str(row["updated_at"]),
            "folder_id_ref": row["folder_id_ref"],
            "folder_name_ref": row["folder_name_ref"],
        }

    def _load_upload_job(self, connection: sqlite3.Connection, upload_id: str) -> sqlite3.Row:
        row = connection.execute(
            """
            SELECT upload_id, original_filename, stored_filename, storage_path, mime_type, file_ext,
                   file_size_bytes, source_ref, source_type, title, upload_status,
                   processing_stage, report_id_ref, auto_process, compile_mode,
                   auto_compile, triggered_by, error_code, error_message, retry_count,
                   content_hash, created_at, updated_at, completed_at
            FROM upload_jobs
            WHERE upload_id = ?
            """,
            (upload_id,),
        ).fetchone()
        if row is None:
            raise UploadNotFoundError("upload not found")
        return row

    def _ensure_processable(self, row: sqlite3.Row) -> None:
        status = str(row["upload_status"])
        if status == "completed":
            raise UploadValidationError("upload is already completed")
        if status == "processing":
            raise UploadValidationError("upload is already processing")

    def _update_upload_status(
        self,
        connection: sqlite3.Connection,
        *,
        upload_id: str,
        upload_status: str,
        processing_stage: str,
        auto_compile: bool,
        compile_mode: str | None,
        error_code: str | None,
        error_message: str | None,
        completed_at: str | None,
    ) -> None:
        connection.execute(
            """
            UPDATE upload_jobs
            SET upload_status = ?,
                processing_stage = ?,
                auto_compile = ?,
                compile_mode = ?,
                error_code = ?,
                error_message = ?,
                completed_at = ?,
                updated_at = ?
            WHERE upload_id = ?
            """,
            (
                upload_status,
                processing_stage,
                1 if auto_compile else 0,
                compile_mode,
                error_code,
                error_message,
                completed_at,
                self._now().isoformat(),
                upload_id,
            ),
        )

    def _upsert_artifact(
        self,
        connection: sqlite3.Connection,
        *,
        upload_id: str,
        artifact_kind: str,
        file_path: str,
        content_hash: str | None,
        byte_size: int | None,
        created_at: str,
    ) -> None:
        connection.execute(
            """
            INSERT INTO upload_artifacts (
                upload_id_ref, artifact_kind, file_path, content_hash, byte_size, created_at
            )
            VALUES (?, ?, ?, ?, ?, ?)
            ON CONFLICT(upload_id_ref, artifact_kind, file_path) DO UPDATE SET
                content_hash = excluded.content_hash,
                byte_size = excluded.byte_size,
                created_at = excluded.created_at
            """,
            (upload_id, artifact_kind, file_path, content_hash, byte_size, created_at),
        )

    def _build_report_metadata(self, upload_id: str, extracted_text: str) -> dict[str, str]:
        with db_manager.session() as connection:
            row = self._load_upload_job(connection, upload_id)

        generated_at = self._now().isoformat()
        title = str(row["title"] or Path(str(row["original_filename"])).stem).strip() or "Uploaded Report"
        source_ref = str(row["source_ref"])
        report_id = self._generate_report_id(source_ref)
        summary = self._build_summary(extracted_text)
        return {
            "report_id": report_id,
            "title": title,
            "source_ref": source_ref,
            "generated_at": generated_at,
            "summary": summary,
            "source_domain": "upload",
            "skill_name": "upload_center",
            "status": "published",
            "source_type": "upload_file",
            "tags": f"  - upload\n  - {row['file_ext']}",
        }

    def _write_report_preview(self, upload_id: str, metadata: dict[str, str], extracted_text: str) -> str:
        report_relative_path = f"{self._now().strftime('%Y/%m')}/{metadata['report_id']}.md"
        report_path = settings.reports_root / report_relative_path
        report_path.parent.mkdir(parents=True, exist_ok=True)
        content = self._render_report_markdown(metadata, extracted_text)
        report_path.write_text(content, encoding="utf-8")

        return report_relative_path

    def _generate_upload_id(self) -> str:
        now = self._now()
        stamp = now.strftime("%Y%m%d_%H%M%S")
        suffix = hashlib.sha1(now.isoformat(timespec="microseconds").encode("utf-8")).hexdigest()[:8]
        return f"upl_{stamp}_{suffix}"

    def _normalize_original_filename(self, filename: str | None) -> str:
        normalized = Path(filename or "").name.strip()
        if not normalized:
            raise UploadValidationError("filename is required")
        return normalized

    def _validate_file_extension(self, filename: str) -> str:
        suffix = Path(filename).suffix.lower().lstrip(".")
        if not suffix:
            raise UploadValidationError("file extension is required")
        if suffix not in ALLOWED_EXTENSIONS:
            allowed = ", ".join(sorted(ALLOWED_EXTENSIONS))
            raise UploadValidationError(f"unsupported file extension: {suffix}; allowed: {allowed}")
        return suffix

    def _validate_mime_type(self, file_ext: str, mime_type: str | None) -> None:
        if not mime_type:
            return
        if mime_type in ALLOWED_MIME_TYPES.get(file_ext, set()):
            return
        guessed_mime_type, _ = mimetypes.guess_type(f"upload.{file_ext}")
        if guessed_mime_type and guessed_mime_type == mime_type:
            return
        if file_ext in {"txt", "md"} and mime_type.startswith("text/"):
            return
        raise UploadValidationError(f"mime type {mime_type!r} does not match file extension {file_ext!r}")

    def _validate_compile_mode(self, compile_mode: str | None, auto_compile: bool) -> str | None:
        normalized = self._normalize_optional_string(compile_mode)
        if normalized is None:
            return "propose" if auto_compile else None
        if normalized not in {"propose", "apply_safe"}:
            raise UploadValidationError("compile_mode must be propose or apply_safe")
        return normalized

    def _write_upload_file(self, source: BinaryIO, destination: Path) -> tuple[int, str]:
        hasher = hashlib.sha1()
        total_size = 0

        with destination.open("wb") as target:
            while True:
                chunk = source.read(1024 * 1024)
                if not chunk:
                    break
                total_size += len(chunk)
                if total_size > MAX_UPLOAD_BYTES:
                    raise UploadValidationError(f"file exceeds maximum size of {MAX_UPLOAD_BYTES} bytes")
                hasher.update(chunk)
                target.write(chunk)

        if total_size <= 0:
            raise UploadValidationError("uploaded file is empty")

        return total_size, hasher.hexdigest()

    def _extract_text(self, upload_id: str) -> tuple[str, str]:
        with db_manager.session() as connection:
            row = self._load_upload_job(connection, upload_id)

        file_ext = str(row["file_ext"])
        storage_path = str(row["storage_path"])
        source_path = resolve_upload_storage_path(storage_path)

        if file_ext in {"txt", "md"}:
            return source_path.read_text(encoding="utf-8"), "txt"
        if file_ext in {"html", "htm"}:
            html = source_path.read_text(encoding="utf-8")
            soup = BeautifulSoup(html, "html.parser")
            return soup.get_text("\n"), "txt"
        if file_ext == "docx":
            document = DocxDocument(str(source_path))
            text = "\n\n".join(paragraph.text for paragraph in document.paragraphs if paragraph.text.strip())
            return text, "txt"
        if file_ext == "pdf":
            return self._extract_pdf_text(source_path), "txt"
        raise UploadValidationError(f"unsupported file extension for extraction: {file_ext}")

    def _normalize_extracted_text(self, text: str) -> str:
        lines = [line.rstrip() for line in text.replace("\r\n", "\n").replace("\r", "\n").split("\n")]
        collapsed = "\n".join(lines)
        collapsed = re.sub(r"\n{3,}", "\n\n", collapsed)
        return collapsed.strip()

    def _extract_pdf_text(self, source_path: Path) -> str:
        text_layer = self._extract_pdf_text_layer(source_path)
        normalized_text_layer = self._normalize_extracted_text(text_layer)
        if len(normalized_text_layer) >= PDF_TEXT_LAYER_MIN_LENGTH:
            return normalized_text_layer

        ocr_text = self._extract_pdf_text_via_ocr(source_path)
        normalized_ocr_text = self._normalize_extracted_text(ocr_text)
        if len(normalized_ocr_text) > len(normalized_text_layer):
            return normalized_ocr_text
        return normalized_text_layer

    def _extract_pdf_text_layer(self, source_path: Path) -> str:
        reader = PdfReader(str(source_path))
        parts = []
        for page in reader.pages:
            parts.append(page.extract_text() or "")
        return "\n\n".join(parts)

    def _extract_pdf_text_via_ocr(self, source_path: Path) -> str:
        ocr_engine = self._get_ocr_engine()
        document = fitz.open(source_path)
        parts: list[str] = []

        try:
            for page_index, page in enumerate(document):
                if page_index >= PDF_OCR_MAX_PAGES:
                    break
                matrix = fitz.Matrix(PDF_OCR_ZOOM, PDF_OCR_ZOOM)
                pixmap = page.get_pixmap(matrix=matrix, alpha=False)
                image_bytes = pixmap.tobytes("png")
                ocr_result, _ = ocr_engine(image_bytes)
                page_text = self._flatten_ocr_result(ocr_result)
                if page_text:
                    parts.append(page_text)
                if sum(len(part) for part in parts) >= PDF_OCR_TARGET_TEXT_LENGTH:
                    break
        finally:
            document.close()

        return "\n\n".join(parts)

    def _flatten_ocr_result(self, ocr_result: Any) -> str:
        if not ocr_result:
            return ""

        lines: list[str] = []
        for item in ocr_result:
            if not isinstance(item, (list, tuple)) or len(item) < 2:
                continue
            text = str(item[1]).strip()
            if text:
                lines.append(text)
        return "\n".join(lines)

    def _get_ocr_engine(self) -> RapidOCR:
        if self._ocr_engine is None:
            self._ocr_engine = RapidOCR()
        return self._ocr_engine

    def _generate_report_id(self, source_ref: str) -> str:
        now = self._now()
        stamp = now.strftime("%Y%m%d_%H%M%S")
        suffix = hashlib.sha1(f"{source_ref}|{now.isoformat()}".encode("utf-8")).hexdigest()[:8]
        return f"rpt_{stamp}_{suffix}"

    def _build_summary(self, extracted_text: str) -> str:
        lines = [line.strip() for line in extracted_text.splitlines() if line.strip()]
        summary = " ".join(lines[:3]).strip()
        return summary[:280] if len(summary) > 280 else summary

    def _render_report_markdown(self, metadata: dict[str, str], extracted_text: str) -> str:
        return (
            "---\n"
            f"report_id: {metadata['report_id']}\n"
            f"title: {metadata['title']}\n"
            f"source_ref: {metadata['source_ref']}\n"
            "source_domain: upload\n"
            "source_type: upload_file\n"
            f"skill_name: {metadata['skill_name']}\n"
            f"generated_at: {metadata['generated_at']}\n"
            f"status: {metadata['status']}\n"
            "language: text\n"
            f"summary: {metadata['summary']}\n"
            "tags:\n"
            f"{metadata['tags']}\n"
            "---\n\n"
            f"# {metadata['title']}\n\n"
            "## Summary\n\n"
            f"{metadata['summary']}\n\n"
            "## Source\n\n"
            f"- upload_id: {metadata['source_ref'].split('/')[2]}\n"
            f"- source_ref: {metadata['source_ref']}\n\n"
            "## Extracted Content\n\n"
            f"{extracted_text.strip()}\n"
        )

    def _sanitize_filename(self, filename: str) -> str:
        suffix = Path(filename).suffix.lower()
        stem = Path(filename).stem or "upload"
        safe_stem = re.sub(r"[^\w.-]+", "_", stem, flags=re.UNICODE).strip("._")
        if not safe_stem:
            safe_stem = "upload"
        safe_stem = safe_stem[:80]
        return f"{safe_stem}{suffix}"

    def _normalize_optional_string(self, value: str | None) -> str | None:
        if value is None:
            return None
        normalized = value.strip()
        return normalized or None

    def _now(self) -> datetime:
        return datetime.now().astimezone()


upload_service = UploadService()
