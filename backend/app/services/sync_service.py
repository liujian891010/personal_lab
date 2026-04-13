from __future__ import annotations

import sqlite3
from dataclasses import dataclass, field
from datetime import datetime, timezone

from ..config import settings
from ..config import encode_report_storage_path
from ..db import db_manager
from ..indexing.scanner import scan_markdown_files
from .metadata_service import ReportDocument, normalize_tag, parse_report_file


def utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


@dataclass(slots=True)
class SyncResult:
    job_id: int
    mode: str
    scanned_count: int = 0
    created_count: int = 0
    updated_count: int = 0
    deleted_count: int = 0
    failed_count: int = 0
    status: str = "success"
    took_ms: int = 0
    warnings: list[dict[str, str]] = field(default_factory=list)


class SyncService:
    def run(self, mode: str) -> SyncResult:
        if mode not in {"incremental", "full"}:
            raise ValueError("mode must be incremental or full")

        started_at = utc_now_iso()
        start_dt = datetime.now(timezone.utc)

        with db_manager.session() as connection:
            job_id = self._create_job(connection, mode, started_at)
            result = SyncResult(job_id=job_id, mode=mode)

            try:
                # Scan both primary reports_root and additional_report_roots
                all_roots = [settings.reports_root] + settings.additional_report_roots
                files = scan_markdown_files(all_roots, skip_top_level_dirs={"failed"})
                result.scanned_count = len(files)

                # Build a lookup: which root does each file belong to?
                root_for_file: dict[Path, Path] = {}
                for root in all_roots:
                    if not root.exists():
                        continue
                    for path in root.rglob("*.md"):
                        root_for_file[path] = root

                documents: list[ReportDocument] = []
                for file_path in files:
                    try:
                        doc_root = root_for_file.get(file_path, settings.reports_root)
                        document = parse_report_file(file_path, doc_root)
                        storage_path = encode_report_storage_path(
                            root=doc_root,
                            relative_path=document.file_path,
                            primary_root=settings.reports_root,
                        )
                        document.file_path = storage_path
                        documents.append(document)
                    except Exception as exc:  # noqa: BLE001
                        result.failed_count += 1
                        # Use the resolved root for relative path calculation
                        doc_root = root_for_file.get(file_path, settings.reports_root)
                        result.warnings.append(
                            {
                                "path": file_path.relative_to(doc_root).as_posix(),
                                "message": str(exc),
                            }
                        )

                if mode == "full":
                    self._clear_report_indexes(connection)

                existing_rows = self._load_existing_reports(connection) if mode == "incremental" else {}
                existing_tags = self._load_existing_tags(connection) if mode == "incremental" else {}
                current_paths = {document.file_path for document in documents}

                for document in documents:
                    previous = existing_rows.get(document.file_path)
                    previous_tags = existing_tags.get(document.report_id, set())

                    if previous is None:
                        self._upsert_report(connection, document, is_update=False)
                        result.created_count += 1
                    elif mode == "full" or self._document_changed(previous, previous_tags, document):
                        self._upsert_report(connection, document, is_update=True)
                        result.updated_count += 1

                if mode == "incremental":
                    for file_path, row in existing_rows.items():
                        if file_path not in current_paths:
                            self._delete_report(connection, row["report_id"])
                            result.deleted_count += 1

                result.took_ms = int((datetime.now(timezone.utc) - start_dt).total_seconds() * 1000)
                self._finalize_job(connection, result, utc_now_iso(), "success")
                return result
            except Exception as exc:  # noqa: BLE001
                result.status = "failed"
                result.took_ms = int((datetime.now(timezone.utc) - start_dt).total_seconds() * 1000)
                self._finalize_job(connection, result, utc_now_iso(), "failed", str(exc))
                raise

    def _create_job(self, connection: sqlite3.Connection, mode: str, started_at: str) -> int:
        cursor = connection.execute(
            """
            INSERT INTO sync_jobs (job_type, mode, started_at, status)
            VALUES (?, ?, ?, ?)
            """,
            ("report_sync", mode, started_at, "running"),
        )
        return int(cursor.lastrowid)

    def _finalize_job(
        self,
        connection: sqlite3.Connection,
        result: SyncResult,
        finished_at: str,
        status: str,
        message: str | None = None,
    ) -> None:
        connection.execute(
            """
            UPDATE sync_jobs
            SET finished_at = ?,
                scanned_count = ?,
                created_count = ?,
                updated_count = ?,
                deleted_count = ?,
                failed_count = ?,
                status = ?,
                message = ?
            WHERE id = ?
            """,
            (
                finished_at,
                result.scanned_count,
                result.created_count,
                result.updated_count,
                result.deleted_count,
                result.failed_count,
                status,
                message,
                result.job_id,
            ),
        )

    def _clear_report_indexes(self, connection: sqlite3.Connection) -> None:
        connection.execute("DELETE FROM report_links")
        connection.execute("DELETE FROM report_tags")
        connection.execute("DELETE FROM reports")
        connection.execute("DELETE FROM search_index")

    def _load_existing_reports(self, connection: sqlite3.Connection) -> dict[str, sqlite3.Row]:
        rows = connection.execute(
            """
            SELECT file_path, report_id, title, source_ref, source_url, source_domain,
                   source_type, skill_name, generated_at, author, status, language,
                   summary, content_hash, body_size
            FROM reports
            """
        ).fetchall()
        return {row["file_path"]: row for row in rows}

    def _load_existing_tags(self, connection: sqlite3.Connection) -> dict[str, set[str]]:
        tags_map: dict[str, set[str]] = {}
        rows = connection.execute("SELECT report_id_ref, normalized_tag FROM report_tags").fetchall()
        for row in rows:
            tags_map.setdefault(row["report_id_ref"], set()).add(row["normalized_tag"])
        return tags_map

    def _document_changed(
        self,
        previous: sqlite3.Row,
        previous_tags: set[str],
        document: ReportDocument,
    ) -> bool:
        comparable_fields = {
            "title": document.title,
            "source_ref": document.source_ref,
            "source_url": document.source_url,
            "source_domain": document.source_domain,
            "source_type": document.source_type,
            "skill_name": document.skill_name,
            "generated_at": document.generated_at,
            "author": document.author,
            "status": document.status,
            "language": document.language,
            "summary": document.summary,
            "content_hash": document.content_hash,
            "body_size": document.body_size,
        }
        for key, value in comparable_fields.items():
            if previous[key] != value:
                return True
        return previous_tags != {normalize_tag(tag) for tag in document.tags}

    def _upsert_report(self, connection: sqlite3.Connection, document: ReportDocument, *, is_update: bool) -> None:
        now = utc_now_iso()
        created_at = now
        if is_update:
            existing = connection.execute(
                "SELECT created_at FROM reports WHERE report_id = ?",
                (document.report_id,),
            ).fetchone()
            if existing is not None:
                created_at = existing["created_at"]

        connection.execute(
            """
            INSERT INTO reports (
                report_id, file_path, title, source_ref, source_url, source_domain, source_type,
                skill_name, generated_at, author, status, language, summary, content_hash,
                body_size, created_at, updated_at
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(report_id) DO UPDATE SET
                file_path = excluded.file_path,
                title = excluded.title,
                source_ref = excluded.source_ref,
                source_url = excluded.source_url,
                source_domain = excluded.source_domain,
                source_type = excluded.source_type,
                skill_name = excluded.skill_name,
                generated_at = excluded.generated_at,
                author = excluded.author,
                status = excluded.status,
                language = excluded.language,
                summary = excluded.summary,
                content_hash = excluded.content_hash,
                body_size = excluded.body_size,
                updated_at = excluded.updated_at
            """,
            (
                document.report_id,
                document.file_path,
                document.title,
                document.source_ref,
                document.source_url,
                document.source_domain,
                document.source_type,
                document.skill_name,
                document.generated_at,
                document.author,
                document.status,
                document.language,
                document.summary,
                document.content_hash,
                document.body_size,
                created_at,
                now,
            ),
        )

        connection.execute("DELETE FROM report_tags WHERE report_id_ref = ?", (document.report_id,))
        for tag in document.tags:
            connection.execute(
                """
                INSERT INTO report_tags (report_id_ref, tag, normalized_tag)
                VALUES (?, ?, ?)
                """,
                (document.report_id, tag, normalize_tag(tag)),
            )

        connection.execute("DELETE FROM report_links WHERE report_id_ref = ?", (document.report_id,))
        collected_links: list[tuple[str, str]] = []
        if document.source_url:
            collected_links.append((document.source_url, "source"))
        collected_links.extend((url, "reference") for url in document.related_urls)
        collected_links.extend((url, "body_link") for url in document.body_urls)

        seen: set[tuple[str, str]] = set()
        for url, link_type in collected_links:
            if (url, link_type) in seen:
                continue
            seen.add((url, link_type))
            connection.execute(
                """
                INSERT INTO report_links (report_id_ref, url, link_type, anchor_text)
                VALUES (?, ?, ?, NULL)
                """,
                (document.report_id, url, link_type),
            )

        connection.execute("DELETE FROM search_index WHERE report_id = ?", (document.report_id,))
        connection.execute(
            """
            INSERT INTO search_index (report_id, title, summary, body, tags, source_domain, skill_name)
            VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            (
                document.report_id,
                document.title,
                document.summary,
                document.body,
                " ".join(document.tags),
                document.source_domain,
                document.skill_name,
            ),
        )

    def _delete_report(self, connection: sqlite3.Connection, report_id: str) -> None:
        connection.execute("DELETE FROM report_links WHERE report_id_ref = ?", (report_id,))
        connection.execute("DELETE FROM report_tags WHERE report_id_ref = ?", (report_id,))
        connection.execute("DELETE FROM search_index WHERE report_id = ?", (report_id,))
        connection.execute("DELETE FROM reports WHERE report_id = ?", (report_id,))


sync_service = SyncService()
