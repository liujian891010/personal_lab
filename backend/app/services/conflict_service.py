from __future__ import annotations

from typing import Any

from ..db import db_manager, row_to_dict


class ConflictService:
    def list_conflicts(
        self,
        *,
        status: str | None = None,
        severity: str | None = None,
        page: int = 1,
        page_size: int = 20,
    ) -> dict[str, Any]:
        page = max(page, 1)
        page_size = min(max(page_size, 1), 100)
        offset = (page - 1) * page_size

        where_clauses: list[str] = []
        params: list[Any] = []

        if status:
            where_clauses.append("status = ?")
            params.append(status)
        if severity:
            where_clauses.append("severity = ?")
            params.append(severity)

        where_sql = f"WHERE {' AND '.join(where_clauses)}" if where_clauses else ""

        with db_manager.session() as connection:
            total = connection.execute(
                f"""
                SELECT COUNT(*)
                FROM knowledge_conflicts
                {where_sql}
                """,
                params,
            ).fetchone()[0]

            rows = connection.execute(
                f"""
                SELECT
                    id, topic_key, page_id_ref, old_claim, new_claim,
                    evidence_report_id, severity, status, created_at, resolved_at
                FROM knowledge_conflicts
                {where_sql}
                ORDER BY
                    CASE status
                        WHEN 'open' THEN 0
                        WHEN 'in_progress' THEN 1
                        WHEN 'resolved' THEN 2
                        ELSE 3
                    END,
                    CASE severity
                        WHEN 'high' THEN 0
                        WHEN 'medium' THEN 1
                        WHEN 'low' THEN 2
                        ELSE 3
                    END,
                    created_at DESC,
                    id DESC
                LIMIT ? OFFSET ?
                """,
                [*params, page_size, offset],
            ).fetchall()

        return {
            "items": [row_to_dict(row) for row in rows],
            "page": page,
            "page_size": page_size,
            "total": total,
        }


conflict_service = ConflictService()
