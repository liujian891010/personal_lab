from __future__ import annotations

from typing import Any

from ..db import db_manager, row_to_dict


class SearchService:
    def search_reports(
        self,
        *,
        q: str,
        tag: str | None = None,
        source_domain: str | None = None,
        skill_name: str | None = None,
        status: str | None = None,
        limit: int = 20,
    ) -> dict[str, Any]:
        limit = min(max(limit, 1), 100)
        joins: list[str] = []
        where_clauses = ["search_index MATCH ?"]
        params: list[Any] = [q]

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

        join_sql = " ".join(joins)
        where_sql = f"WHERE {' AND '.join(where_clauses)}"

        with db_manager.session() as connection:
            rows = connection.execute(
                f"""
                SELECT DISTINCT
                    s.report_id,
                    r.title,
                    r.source_ref,
                    r.source_domain,
                    r.source_type,
                    r.generated_at,
                    snippet(search_index, 3, '<mark>', '</mark>', '...', 16) AS snippet,
                    bm25(search_index) AS score
                FROM search_index s
                JOIN reports r ON r.report_id = s.report_id
                {join_sql}
                {where_sql}
                ORDER BY score
                LIMIT ?
                """,
                [*params, limit],
            ).fetchall()

            return {
                "items": [row_to_dict(row) for row in rows],
                "total": len(rows),
                "took_ms": 0,
            }

    def get_tags(self) -> dict[str, list[dict[str, Any]]]:
        with db_manager.session() as connection:
            rows = connection.execute(
                """
                SELECT tag, COUNT(*) AS count
                FROM report_tags
                GROUP BY normalized_tag, tag
                ORDER BY count DESC, tag ASC
                """
            ).fetchall()
            return {"items": [row_to_dict(row) for row in rows]}

    def get_domains(self) -> dict[str, list[dict[str, Any]]]:
        with db_manager.session() as connection:
            rows = connection.execute(
                """
                SELECT source_domain, COUNT(*) AS count
                FROM reports
                GROUP BY source_domain
                ORDER BY count DESC, source_domain ASC
                """
            ).fetchall()
            return {"items": [row_to_dict(row) for row in rows]}


search_service = SearchService()
