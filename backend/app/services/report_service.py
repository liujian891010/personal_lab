from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Any

from ..db import db_manager, row_to_dict
from ..workspace import get_current_user_context
from .file_service import read_report_text
from .storage_service import storage_pointer_from_mapping, storage_service


class ReportNotFoundError(LookupError):
    pass


class ReportAlreadyDeletedError(ValueError):
    pass


class ReportService:
    def list_reports(
        self,
        *,
        page: int = 1,
        page_size: int = 20,
        tag: str | None = None,
        source_domain: str | None = None,
        skill_name: str | None = None,
        status: str | None = None,
        folder_id: str | None = None,
        unfiled: bool = False,
    ) -> dict[str, Any]:
        page = max(page, 1)
        page_size = min(max(page_size, 1), 100)
        offset = (page - 1) * page_size

        joins: list[str] = []
        where_clauses: list[str] = ["r.deleted_at IS NULL"]
        params: list[Any] = []

        if tag:
            joins.append("JOIN report_tags rt ON rt.report_id_ref = r.report_id")
            where_clauses.append("rt.normalized_tag = ?")
            params.append(tag.strip().lower())
        if source_domain:
            where_clauses.append("r.source_domain = ?")
            params.append(source_domain)
        if skill_name:
            where_clauses.append("r.skill_name = ?")
            params.append(skill_name)
        if status:
            where_clauses.append("r.status = ?")
            params.append(status)
        if folder_id:
            where_clauses.append("r.folder_id_ref = ?")
            params.append(folder_id)
        elif unfiled:
            where_clauses.append("r.folder_id_ref IS NULL")

        join_sql = " ".join(joins)
        where_sql = f"WHERE {' AND '.join(where_clauses)}" if where_clauses else ""

        with db_manager.session() as connection:
            total = connection.execute(
                f"SELECT COUNT(DISTINCT r.report_id) FROM reports r {join_sql} {where_sql}",
                params,
            ).fetchone()[0]

            rows = connection.execute(
                f"""
                SELECT DISTINCT
                    r.report_id, r.title, r.source_ref, r.source_url, r.source_domain,
                    r.source_type, r.skill_name, r.generated_at, r.status, r.summary,
                    r.folder_id_ref,
                    f.folder_name AS folder_name_ref
                FROM reports r
                LEFT JOIN report_folders f ON f.folder_id = r.folder_id_ref
                {join_sql}
                {where_sql}
                ORDER BY r.generated_at DESC
                LIMIT ? OFFSET ?
                """,
                [*params, page_size, offset],
            ).fetchall()

            items = [row_to_dict(row) for row in rows]
            tags_map = self._load_tags(connection, [item["report_id"] for item in items if item])
            for item in items:
                item["tags"] = tags_map.get(item["report_id"], [])

            return {"items": items, "page": page, "page_size": page_size, "total": total}

    def get_report(self, report_id: str) -> dict[str, Any] | None:
        with db_manager.session() as connection:
            row = connection.execute(
                """
                SELECT
                    r.report_id, r.file_path, r.storage_provider, r.storage_bucket, r.object_key, r.storage_status,
                    r.title, r.source_ref, r.source_url, r.source_domain,
                    r.source_type, r.skill_name, r.generated_at, r.author, r.status, r.language,
                    r.summary, r.content_hash, r.body_size, r.created_at, r.updated_at,
                    r.folder_id_ref, f.folder_name AS folder_name_ref
                FROM reports r
                LEFT JOIN report_folders f ON f.folder_id = r.folder_id_ref
                WHERE r.report_id = ? AND r.deleted_at IS NULL
                """,
                (report_id,),
            ).fetchone()
            if row is None:
                return None

            item = row_to_dict(row)
            item["tags"] = self._load_tags(connection, [report_id]).get(report_id, [])
            item["links"] = [
                row_to_dict(link_row)
                for link_row in connection.execute(
                    """
                    SELECT url, link_type, anchor_text
                    FROM report_links
                    WHERE report_id_ref = ?
                    ORDER BY link_type, url
                    """,
                    (report_id,),
                ).fetchall()
            ]
            pointer = storage_pointer_from_mapping(item)
            item["content"] = storage_service.read_text(pointer) if pointer else read_report_text(item["file_path"])
            return item

    def get_report_raw(self, report_id: str) -> str | None:
        with db_manager.session() as connection:
            row = connection.execute(
                """
                SELECT file_path, storage_provider, storage_bucket, object_key, storage_status
                FROM reports
                WHERE report_id = ? AND deleted_at IS NULL
                """,
                (report_id,),
            ).fetchone()
            if row is None:
                return None
            pointer = storage_pointer_from_mapping(row)
            return storage_service.read_text(pointer) if pointer else read_report_text(row["file_path"])

    def delete_report(self, report_id: str) -> None:
        current_user = get_current_user_context()
        if current_user is None:
            raise ValueError("workspace context is required")

        now = self._now()
        purge_after = self._purge_after(now)

        with db_manager.session() as connection:
            row = connection.execute(
                """
                SELECT report_id, title, folder_id_ref, deleted_at
                FROM reports
                WHERE report_id = ?
                """,
                (report_id,),
            ).fetchone()
            if row is None:
                raise ReportNotFoundError(f"report not found: {report_id}")
            if row["deleted_at"]:
                raise ReportAlreadyDeletedError(f"report already deleted: {report_id}")

            connection.execute(
                """
                UPDATE reports
                SET deleted_at = ?,
                    deleted_by = ?,
                    purge_after = ?,
                    storage_cleanup_status = 'pending',
                    updated_at = ?
                WHERE report_id = ?
                """,
                (now, current_user.user_id, purge_after, now, report_id),
            )
            connection.execute("DELETE FROM search_index WHERE report_id = ?", (report_id,))
            connection.execute(
                "UPDATE upload_jobs SET report_id_ref = NULL, updated_at = ? WHERE report_id_ref = ?",
                (now, report_id),
            )
            if row["folder_id_ref"]:
                connection.execute(
                    """
                    UPDATE report_folders
                    SET report_count = MAX(0, report_count - 1),
                        updated_at = ?
                    WHERE folder_id = ?
                    """,
                    (now, row["folder_id_ref"]),
                )
            self._record_delete_audit(
                connection,
                report_id=report_id,
                action="soft_delete",
                actor_user_id=current_user.user_id,
                actor_workspace_id=current_user.workspace_id,
                detail=f"title={row['title']}; purge_after={purge_after}",
                created_at=now,
            )

    def purge_expired_reports(self, *, limit: int = 100) -> dict[str, Any]:
        current_user = get_current_user_context()
        if current_user is None:
            raise ValueError("workspace context is required")

        limit = min(max(limit, 1), 500)
        now = self._now()

        with db_manager.session() as connection:
            rows = connection.execute(
                """
                SELECT
                    report_id, file_path, storage_provider, storage_bucket, object_key,
                    storage_status, storage_cleanup_status
                FROM reports
                WHERE deleted_at IS NOT NULL
                  AND purge_after IS NOT NULL
                  AND purge_after <= ?
                ORDER BY purge_after ASC, id ASC
                LIMIT ?
                """,
                (now, limit),
            ).fetchall()

            purged_count = 0
            failed_count = 0
            failures: list[dict[str, str]] = []

            for row in rows:
                report_id = str(row["report_id"])
                try:
                    self._delete_report_files(row)
                    connection.execute("DELETE FROM search_index WHERE report_id = ?", (report_id,))
                    self._record_delete_audit(
                        connection,
                        report_id=report_id,
                        action="purge",
                        actor_user_id=current_user.user_id,
                        actor_workspace_id=current_user.workspace_id,
                        detail="purged after retention window",
                        created_at=now,
                    )
                    connection.execute("DELETE FROM reports WHERE report_id = ?", (report_id,))
                    purged_count += 1
                except Exception as exc:  # noqa: BLE001
                    failed_count += 1
                    failures.append({"report_id": report_id, "message": str(exc)})
                    connection.execute(
                        """
                        UPDATE reports
                        SET storage_cleanup_status = 'failed',
                            updated_at = ?
                        WHERE report_id = ?
                        """,
                        (now, report_id),
                    )
                    self._record_delete_audit(
                        connection,
                        report_id=report_id,
                        action="purge_failed",
                        actor_user_id=current_user.user_id,
                        actor_workspace_id=current_user.workspace_id,
                        detail=str(exc),
                        created_at=now,
                    )

            return {
                "scanned_count": len(rows),
                "purged_count": purged_count,
                "failed_count": failed_count,
                "failures": failures,
            }

    def _load_tags(self, connection, report_ids: list[str]) -> dict[str, list[str]]:
        if not report_ids:
            return {}
        placeholders = ", ".join("?" for _ in report_ids)
        rows = connection.execute(
            f"""
            SELECT report_id_ref, tag
            FROM report_tags
            WHERE report_id_ref IN ({placeholders})
            ORDER BY tag
            """,
            report_ids,
        ).fetchall()

        tags_map: dict[str, list[str]] = {}
        for row in rows:
            tags_map.setdefault(row["report_id_ref"], []).append(row["tag"])
        return tags_map

    def _record_delete_audit(
        self,
        connection,
        *,
        report_id: str,
        action: str,
        actor_user_id: str | None,
        actor_workspace_id: str | None,
        detail: str | None,
        created_at: str,
    ) -> None:
        connection.execute(
            """
            INSERT INTO report_delete_audit_logs (
                report_id, action, actor_user_id, actor_workspace_id, detail, created_at
            )
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            (report_id, action, actor_user_id, actor_workspace_id, detail, created_at),
        )

    def _delete_report_files(self, row) -> None:
        pointer = storage_pointer_from_mapping(row)
        if pointer is not None:
            storage_service.delete(pointer)

        from .file_service import resolve_report_storage_path

        file_path = resolve_report_storage_path(str(row["file_path"]))
        file_path.unlink(missing_ok=True)

    def _now(self) -> str:
        return datetime.now(timezone.utc).isoformat()

    def _purge_after(self, now: str) -> str:
        current = datetime.fromisoformat(now)
        return (current + timedelta(days=7)).isoformat()


report_service = ReportService()
