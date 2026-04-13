from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from ..db import db_manager
from .wiki_service import wiki_service


class LintService:
    def run(self, *, mode: str) -> dict[str, Any]:
        if mode not in {"light", "full"}:
            raise ValueError("mode must be light or full")

        wiki_service.refresh_index()

        findings: list[dict[str, Any]] = []
        created_task_ids: list[int] = []
        created_conflict_ids: list[int] = []

        unresolved = self._lint_unresolved_links()
        findings.extend(unresolved["findings"])
        created_task_ids.extend(unresolved["created_task_ids"])
        created_conflict_ids.extend(unresolved["created_conflict_ids"])

        question_writeback = self._lint_pending_question_writeback()
        findings.extend(question_writeback["findings"])
        created_task_ids.extend(question_writeback["created_task_ids"])

        if mode == "full":
            fill_gap = self._lint_report_gaps()
            findings.extend(fill_gap["findings"])
            created_task_ids.extend(fill_gap["created_task_ids"])

        return {
            "mode": mode,
            "created_task_ids": created_task_ids,
            "created_conflict_ids": created_conflict_ids,
            "findings": findings,
            "total_findings": len(findings),
            "llm_used": False,
            "message": f"lint completed with {len(findings)} finding(s)",
        }

    def _lint_unresolved_links(self) -> dict[str, Any]:
        findings: list[dict[str, Any]] = []
        created_task_ids: list[int] = []
        created_conflict_ids: list[int] = []

        with db_manager.session() as connection:
            rows = connection.execute(
                """
                SELECT source_page_id, target_id
                FROM wiki_links
                WHERE target_kind = 'wiki_page' AND is_resolved = 0
                ORDER BY source_page_id, target_id
                """
            ).fetchall()

        for row in rows:
            source_page_id = str(row["source_page_id"])
            target_id = str(row["target_id"])
            conflict_id, conflict_created = self._ensure_conflict(
                topic_key=f"unresolved_link:{source_page_id}:{target_id}",
                page_id_ref=source_page_id,
                old_claim="wiki link target could not be resolved",
                new_claim=f"missing wiki target: {target_id}",
                severity="low",
                evidence_report_id=None,
            )
            task_id, task_created = self._ensure_task(
                task_type="resolve_conflict",
                target_kind="wiki_page",
                target_id=source_page_id,
                title=f"Resolve unresolved wiki link in {source_page_id}",
                description=f"Unresolved wiki target: {target_id}",
                priority="medium",
            )
            if conflict_created:
                created_conflict_ids.append(conflict_id)
            if task_created:
                created_task_ids.append(task_id)
            findings.append(
                {
                    "rule_name": "unresolved_wiki_link",
                    "target_kind": "wiki_page",
                    "target_id": source_page_id,
                    "severity": "low",
                    "detail": f"Missing wiki target: {target_id}",
                    "created_task_id": task_id if task_created else None,
                    "created_conflict_id": conflict_id if conflict_created else None,
                }
            )

        return {
            "findings": findings,
            "created_task_ids": created_task_ids,
            "created_conflict_ids": created_conflict_ids,
        }

    def _lint_pending_question_writeback(self) -> dict[str, Any]:
        findings: list[dict[str, Any]] = []
        created_task_ids: list[int] = []

        with db_manager.session() as connection:
            rows = connection.execute(
                """
                SELECT
                    qr.id,
                    qr.question_text,
                    SUM(CASE WHEN qrs.source_kind = 'wiki_page' THEN 1 ELSE 0 END) AS wiki_source_count,
                    SUM(CASE WHEN qrs.source_kind = 'report' THEN 1 ELSE 0 END) AS report_source_count
                FROM question_runs qr
                LEFT JOIN question_run_sources qrs ON qrs.run_id = qr.id
                WHERE qr.wrote_back_page_id IS NULL
                GROUP BY qr.id, qr.question_text
                ORDER BY qr.id DESC
                """
            ).fetchall()

        for row in rows:
            run_id = int(row["id"])
            wiki_source_count = int(row["wiki_source_count"] or 0)
            report_source_count = int(row["report_source_count"] or 0)
            if not (wiki_source_count > 0 or report_source_count >= 2):
                continue

            task_id, task_created = self._ensure_task(
                task_type="review_answer_writeback",
                target_kind="question_run",
                target_id=str(run_id),
                title=f"Review writeback for question run {run_id}",
                description=str(row["question_text"]),
                priority="medium",
            )
            if task_created:
                created_task_ids.append(task_id)
            findings.append(
                {
                    "rule_name": "pending_question_writeback",
                    "target_kind": "question_run",
                    "target_id": str(run_id),
                    "severity": "medium",
                    "detail": str(row["question_text"]),
                    "created_task_id": task_id if task_created else None,
                    "created_conflict_id": None,
                }
            )

        return {
            "findings": findings,
            "created_task_ids": created_task_ids,
            "created_conflict_ids": [],
        }

    def _lint_report_gaps(self) -> dict[str, Any]:
        findings: list[dict[str, Any]] = []
        created_task_ids: list[int] = []

        with db_manager.session() as connection:
            rows = connection.execute(
                """
                SELECT r.report_id, r.title, r.summary
                FROM reports r
                LEFT JOIN page_sources ps ON ps.report_id_ref = r.report_id
                WHERE ps.report_id_ref IS NULL
                ORDER BY r.generated_at DESC, r.report_id DESC
                """
            ).fetchall()

        for row in rows:
            report_id = str(row["report_id"])
            description = f"{row['title']}\n\n{row['summary']}"
            task_id, task_created = self._ensure_task(
                task_type="fill_gap",
                target_kind="report",
                target_id=report_id,
                title=f"Fill knowledge gap for report {report_id}",
                description=description,
                priority="medium",
            )
            if task_created:
                created_task_ids.append(task_id)
            findings.append(
                {
                    "rule_name": "report_without_wiki_page",
                    "target_kind": "report",
                    "target_id": report_id,
                    "severity": "medium",
                    "detail": str(row["title"]),
                    "created_task_id": task_id if task_created else None,
                    "created_conflict_id": None,
                }
            )

        return {
            "findings": findings,
            "created_task_ids": created_task_ids,
            "created_conflict_ids": [],
        }

    def _ensure_task(
        self,
        *,
        task_type: str,
        target_kind: str,
        target_id: str | None,
        title: str,
        description: str,
        priority: str,
    ) -> tuple[int, bool]:
        with db_manager.session() as connection:
            existing = connection.execute(
                """
                SELECT id
                FROM knowledge_tasks
                WHERE task_type = ?
                  AND target_kind = ?
                  AND COALESCE(target_id, '') = COALESCE(?, '')
                  AND status = 'open'
                ORDER BY id DESC
                LIMIT 1
                """,
                (task_type, target_kind, target_id),
            ).fetchone()
            if existing is not None:
                return int(existing["id"]), False

            now = self._now()
            cursor = connection.execute(
                """
                INSERT INTO knowledge_tasks (
                    task_type, target_kind, target_id, title, description,
                    priority, status, created_by, created_at, updated_at
                )
                VALUES (?, ?, ?, ?, ?, ?, 'open', 'lint', ?, ?)
                """,
                (task_type, target_kind, target_id, title, description, priority, now, now),
            )
            return int(cursor.lastrowid), True

    def _ensure_conflict(
        self,
        *,
        topic_key: str,
        page_id_ref: str | None,
        old_claim: str,
        new_claim: str,
        severity: str,
        evidence_report_id: str | None,
    ) -> tuple[int, bool]:
        with db_manager.session() as connection:
            existing = connection.execute(
                """
                SELECT id
                FROM knowledge_conflicts
                WHERE topic_key = ?
                  AND COALESCE(page_id_ref, '') = COALESCE(?, '')
                  AND old_claim = ?
                  AND new_claim = ?
                  AND status = 'open'
                ORDER BY id DESC
                LIMIT 1
                """,
                (topic_key, page_id_ref, old_claim, new_claim),
            ).fetchone()
            if existing is not None:
                return int(existing["id"]), False

            cursor = connection.execute(
                """
                INSERT INTO knowledge_conflicts (
                    topic_key, page_id_ref, old_claim, new_claim,
                    evidence_report_id, severity, status, created_at, resolved_at
                )
                VALUES (?, ?, ?, ?, ?, ?, 'open', ?, NULL)
                """,
                (topic_key, page_id_ref, old_claim, new_claim, evidence_report_id, severity, self._now()),
            )
            return int(cursor.lastrowid), True

    def _now(self) -> str:
        return datetime.now(timezone.utc).isoformat()


lint_service = LintService()
