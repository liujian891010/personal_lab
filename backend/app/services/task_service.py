from __future__ import annotations

from typing import Any

from ..db import db_manager, row_to_dict


class TaskService:
    def list_tasks(
        self,
        *,
        status: str | None = None,
        task_type: str | None = None,
        target_kind: str | None = None,
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
        if task_type:
            where_clauses.append("task_type = ?")
            params.append(task_type)
        if target_kind:
            where_clauses.append("target_kind = ?")
            params.append(target_kind)

        where_sql = f"WHERE {' AND '.join(where_clauses)}" if where_clauses else ""

        with db_manager.session() as connection:
            total = connection.execute(
                f"""
                SELECT COUNT(*)
                FROM knowledge_tasks
                {where_sql}
                """,
                params,
            ).fetchone()[0]

            rows = connection.execute(
                f"""
                SELECT
                    id, task_type, target_kind, target_id, title, description,
                    priority, status, created_by, created_at, updated_at
                FROM knowledge_tasks
                {where_sql}
                ORDER BY
                    CASE status
                        WHEN 'open' THEN 0
                        WHEN 'in_progress' THEN 1
                        WHEN 'done' THEN 2
                        ELSE 3
                    END,
                    CASE priority
                        WHEN 'high' THEN 0
                        WHEN 'medium' THEN 1
                        WHEN 'low' THEN 2
                        ELSE 3
                    END,
                    updated_at DESC,
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


task_service = TaskService()
