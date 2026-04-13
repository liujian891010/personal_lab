from __future__ import annotations

import re
from datetime import datetime, timezone
from typing import Any

from ..config import settings
from ..db import db_manager, row_to_dict
from .fts_utils import build_fts_query
from .llm_service import LLMUnavailableError, llm_service
from .wiki_service import wiki_service


class QueryService:
    def ask(self, *, question: str, writeback: str) -> dict[str, Any]:
        normalized_question = question.strip()
        if not normalized_question:
            raise ValueError("question must not be empty")
        if writeback not in {"never", "suggest", "always"}:
            raise ValueError("writeback must be never, suggest, or always")

        wiki_service.refresh_index()
        source_wiki_pages = self._search_wiki(normalized_question)
        source_reports = self._search_reports(normalized_question)

        answer, answer_summary, should_writeback, suggested_kind = self._build_answer(
            normalized_question,
            source_wiki_pages,
            source_reports,
            writeback,
        )
        run_id = self._record_run(
            normalized_question,
            answer_summary,
            source_wiki_pages,
            source_reports,
        )

        return {
            "run_id": run_id,
            "question": normalized_question,
            "answer": answer,
            "answer_summary": answer_summary,
            "source_wiki_pages": source_wiki_pages,
            "source_reports": source_reports,
            "should_writeback": should_writeback,
            "suggested_writeback_kind": suggested_kind,
        }

    def writeback(self, *, run_id: int, kind: str) -> dict[str, Any]:
        if kind not in {"question_page", "task"}:
            raise ValueError("kind must be question_page or task")

        run = self._load_run(run_id)
        if run is None:
            raise ValueError(f"question run not found: {run_id}")

        if kind == "task":
            task_id = self._create_review_task(run)
            return {
                "run_id": run_id,
                "kind": kind,
                "status": "created",
                "task_id": task_id,
                "message": "review task created",
            }

        page = self._write_question_page(run)
        return {
            "run_id": run_id,
            "kind": kind,
            "status": page["status"],
            "page_id": page["page_id"],
            "task_id": page.get("task_id"),
            "message": page["message"],
        }

    def _search_wiki(self, question: str) -> list[dict[str, Any]]:
        query = self._fts_query(question)
        if not query:
            return []

        with db_manager.session() as connection:
            rows = connection.execute(
                """
                SELECT
                    w.page_id, w.slug, w.title, w.page_type, w.summary,
                    bm25(wiki_search_index) AS raw_score
                FROM wiki_search_index
                JOIN wiki_pages w ON w.page_id = wiki_search_index.page_id
                WHERE wiki_search_index MATCH ?
                LIMIT 8
                """,
                (query,),
            ).fetchall()

        items: list[dict[str, Any]] = []
        for row in rows:
            item = row_to_dict(row)
            score = float(item.pop("raw_score"))
            if item["page_type"] == "question":
                score -= 1.0
            item["score"] = score
            items.append(item)

        items.sort(key=lambda item: item["score"])
        return items[:5]

    def _search_reports(self, question: str) -> list[dict[str, Any]]:
        query = self._fts_query(question)
        if not query:
            return []

        with db_manager.session() as connection:
            rows = connection.execute(
                """
                SELECT
                    r.report_id, r.title, r.source_ref, r.source_domain,
                    r.generated_at, r.summary,
                    bm25(search_index) AS score
                FROM search_index
                JOIN reports r ON r.report_id = search_index.report_id
                WHERE search_index MATCH ?
                ORDER BY score
                LIMIT 5
                """,
                (query,),
            ).fetchall()
        return [row_to_dict(row) for row in rows]

    def _build_answer(
        self,
        question: str,
        source_wiki_pages: list[dict[str, Any]],
        source_reports: list[dict[str, Any]],
        writeback: str,
    ) -> tuple[str, str, bool, str | None]:
        context = self._render_question_context(question, source_wiki_pages, source_reports)
        llm_answer = None
        try:
            llm_answer = llm_service.complete("query/answer_with_context", {"question_context": context})
        except LLMUnavailableError:
            llm_answer = None

        if llm_answer:
            answer = llm_answer.strip()
        else:
            answer = self._fallback_answer(source_wiki_pages, source_reports)

        answer_summary = answer.splitlines()[0][:240] if answer else "No answer"
        should_writeback = False
        if writeback == "always":
            should_writeback = True
        elif writeback == "suggest":
            should_writeback = bool(source_wiki_pages or len(source_reports) >= 2)

        suggested_kind = "question_page" if should_writeback else None
        return answer, answer_summary, should_writeback, suggested_kind

    def _fallback_answer(
        self,
        source_wiki_pages: list[dict[str, Any]],
        source_reports: list[dict[str, Any]],
    ) -> str:
        lines: list[str] = []
        if source_wiki_pages:
            top_page = source_wiki_pages[0]
            summary = top_page.get("summary") or f"Matched wiki page {top_page['title']}."
            lines.append(f"结论：当前问题优先命中了知识页《{top_page['title']}》，说明这个主题已经沉淀进 Wiki。")
            lines.append(f"依据：{summary}")
        elif source_reports:
            top_report = source_reports[0]
            lines.append(f"结论：当前问题还没有稳定的知识页，答案主要来自报告《{top_report['title']}》。")
            lines.append(f"依据：{top_report['summary']}")
        else:
            lines.append("结论：当前知识库里没有足够证据回答这个问题。")
            lines.append("依据：Wiki 和 Report 两层检索都没有命中有效内容。")

        if source_reports:
            report_titles = "、".join(item["title"] for item in source_reports[:3])
            lines.append(f"补充证据：相关报告包括 {report_titles}。")
        if not source_wiki_pages:
            lines.append("下一步建议：补充相关来源并触发 ingest/compile，让这个问题沉淀成知识页。")
        else:
            lines.append("下一步建议：如果这是高频问题，可以把这次答案回写成 question 页面。")
        return "\n".join(lines)

    def _record_run(
        self,
        question: str,
        answer_summary: str,
        source_wiki_pages: list[dict[str, Any]],
        source_reports: list[dict[str, Any]],
    ) -> int:
        now = self._now()
        with db_manager.session() as connection:
            cursor = connection.execute(
                """
                INSERT INTO question_runs (question_text, answer_summary, wrote_back_page_id, created_at)
                VALUES (?, ?, NULL, ?)
                """,
                (question, answer_summary, now),
            )
            run_id = int(cursor.lastrowid)

            for page in source_wiki_pages:
                connection.execute(
                    """
                    INSERT INTO question_run_sources (run_id, source_kind, source_id)
                    VALUES (?, 'wiki_page', ?)
                    """,
                    (run_id, page["page_id"]),
                )
            for report in source_reports:
                connection.execute(
                    """
                    INSERT INTO question_run_sources (run_id, source_kind, source_id)
                    VALUES (?, 'report', ?)
                    """,
                    (run_id, report["report_id"]),
                )
            return run_id

    def _load_run(self, run_id: int) -> dict[str, Any] | None:
        with db_manager.session() as connection:
            row = connection.execute(
                """
                SELECT id, question_text, answer_summary, wrote_back_page_id, created_at
                FROM question_runs
                WHERE id = ?
                """,
                (run_id,),
            ).fetchone()
            if row is None:
                return None
            run = row_to_dict(row)
            run["sources"] = [
                row_to_dict(source_row)
                for source_row in connection.execute(
                    """
                    SELECT source_kind, source_id
                    FROM question_run_sources
                    WHERE run_id = ?
                    ORDER BY source_kind, source_id
                    """,
                    (run_id,),
                ).fetchall()
            ]
            return run

    def _write_question_page(self, run: dict[str, Any]) -> dict[str, Any]:
        existing_page_id = run.get("wrote_back_page_id")
        if existing_page_id:
            return {
                "page_id": existing_page_id,
                "status": "exists",
                "message": "question page already linked",
            }

        title = run["question_text"].strip()
        base_slug = self._slugify(title, fallback=str(run["id"]))
        slug = f"question-{base_slug}" if base_slug else f"question-{run['id']}"
        existing_page = wiki_service.get_page_by_slug(slug)
        if existing_page is not None:
            task_id = self._create_review_task(
                run,
                note=f"Question page slug already exists: {existing_page['page_id']}",
            )
            with db_manager.session() as connection:
                connection.execute(
                    "UPDATE question_runs SET wrote_back_page_id = ? WHERE id = ?",
                    (existing_page["page_id"], run["id"]),
                )
            return {
                "page_id": existing_page["page_id"],
                "status": "needs_review",
                "task_id": task_id,
                "message": "question page slug already exists; created review task",
            }

        target_path = settings.knowledge_root / "questions" / f"{slug}.md"
        source_report_ids = [source["source_id"] for source in run["sources"] if source["source_kind"] == "report"]
        tags = ["question", "writeback"]
        page_id = f"pg_question_{slug}"
        timestamp = self._now()
        report_block = "\n".join(f"  - {report_id}" for report_id in source_report_ids)
        tags_block = "\n".join(f"  - {tag}" for tag in tags)
        evidence_lines = "\n".join(f"- [[{source['source_id']}]]" for source in run["sources"]) or "- none"

        content = (
            "---\n"
            f"page_id: {page_id}\n"
            "page_type: question\n"
            f"title: {title}\n"
            f"slug: {slug}\n"
            "status: needs_review\n"
            f"created_at: {timestamp}\n"
            f"updated_at: {timestamp}\n"
            "confidence: 0.5\n"
            "tags:\n"
            f"{tags_block}\n"
            "source_report_ids:\n"
            f"{report_block}\n"
            "---\n\n"
            f"# {title}\n\n"
            "## Answer\n\n"
            f"{run['answer_summary']}\n\n"
            "## Evidence\n\n"
            f"{evidence_lines}\n"
        )
        target_path.write_text(content, encoding="utf-8")

        with db_manager.session() as connection:
            connection.execute(
                "UPDATE question_runs SET wrote_back_page_id = ? WHERE id = ?",
                (page_id, run["id"]),
            )

        wiki_service.refresh_index()
        return {
            "page_id": page_id,
            "slug": slug,
            "status": "created",
            "message": "question page created",
        }

    def _create_review_task(self, run: dict[str, Any], *, note: str | None = None) -> int:
        now = self._now()
        description = run["question_text"]
        if note:
            description = f"{description}\n\n{note}"

        with db_manager.session() as connection:
            cursor = connection.execute(
                """
                INSERT INTO knowledge_tasks (
                    task_type, target_kind, target_id, title, description,
                    priority, status, created_by, created_at, updated_at
                )
                VALUES (?, ?, ?, ?, ?, 'medium', 'open', 'system', ?, ?)
                """,
                (
                    "review_answer_writeback",
                    "question_run",
                    str(run["id"]),
                    f"Review writeback for question run {run['id']}",
                    description,
                    now,
                    now,
                ),
            )
            return int(cursor.lastrowid)

    def _fts_query(self, question: str) -> str | None:
        return build_fts_query(question, limit=8)

    def _render_question_context(
        self,
        question: str,
        source_wiki_pages: list[dict[str, Any]],
        source_reports: list[dict[str, Any]],
    ) -> str:
        wiki_lines = [f"- {item['title']} ({item['page_type']}): {item.get('summary') or ''}" for item in source_wiki_pages]
        report_lines = [f"- {item['title']}: {item['summary']}" for item in source_reports]
        return (
            f"question: {question}\n"
            "wiki_pages:\n"
            f"{chr(10).join(wiki_lines) if wiki_lines else '- none'}\n"
            "reports:\n"
            f"{chr(10).join(report_lines) if report_lines else '- none'}\n"
        )

    def _slugify(self, text: str, *, fallback: str) -> str:
        lowered = text.lower()
        cleaned = re.sub(r"[^a-z0-9\u4e00-\u9fff]+", "-", lowered).strip("-")
        cleaned = re.sub(r"-{2,}", "-", cleaned)
        return (cleaned[:64] or fallback.lower()).strip("-")

    def _now(self) -> str:
        return datetime.now(timezone.utc).isoformat()


query_service = QueryService()
