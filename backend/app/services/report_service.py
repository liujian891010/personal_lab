from __future__ import annotations

from typing import Any

from ..db import db_manager, row_to_dict
from .file_service import read_report_text


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
        where_clauses: list[str] = []
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
                    r.report_id, r.file_path, r.title, r.source_ref, r.source_url, r.source_domain,
                    r.source_type, r.skill_name, r.generated_at, r.author, r.status, r.language,
                    r.summary, r.content_hash, r.body_size, r.created_at, r.updated_at,
                    r.folder_id_ref, f.folder_name AS folder_name_ref
                FROM reports r
                LEFT JOIN report_folders f ON f.folder_id = r.folder_id_ref
                WHERE r.report_id = ?
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
            item["content"] = read_report_text(item["file_path"])
            return item

    def get_report_raw(self, report_id: str) -> str | None:
        with db_manager.session() as connection:
            row = connection.execute("SELECT file_path FROM reports WHERE report_id = ?", (report_id,)).fetchone()
            if row is None:
                return None
            return read_report_text(row["file_path"])

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


report_service = ReportService()
