from __future__ import annotations

import re
from dataclasses import dataclass
from datetime import datetime, timezone
from ..config import get_workspace_knowledge_root
from ..db import db_manager
from .llm_service import LLMUnavailableError, llm_service
from .report_service import report_service
from .wiki_service import wiki_service


TOPIC_STOPWORDS = {
    "report",
    "summary",
    "总结",
    "方案",
    "设计",
    "system",
    "overview",
}


@dataclass(slots=True)
class PageProposal:
    page_id: str
    page_type: str
    title: str
    slug: str
    summary: str
    tags: list[str]
    source_report_ids: list[str]
    body: str


class CompileService:
    def compile(self, *, report_id: str | None, mode: str) -> dict:
        if mode not in {"propose", "apply_safe"}:
            raise ValueError("mode must be propose or apply_safe")

        report_ids = [report_id] if report_id else self._load_pending_report_ids()
        if not report_ids:
            return {
                "mode": mode,
                "processed_reports": [],
                "created_page_ids": [],
                "updated_page_ids": [],
                "task_ids": [],
                "conflict_ids": [],
                "llm_used": False,
                "message": "no reports to compile",
            }

        created_page_ids: list[str] = []
        updated_page_ids: list[str] = []
        task_ids: list[int] = []
        conflict_ids: list[int] = []
        llm_used = False

        for current_report_id in report_ids:
            report = report_service.get_report(current_report_id)
            if report is None:
                raise ValueError(f"report not found: {current_report_id}")

            proposals, used_llm = self._build_proposals(report)
            llm_used = llm_used or used_llm

            for proposal in proposals:
                if mode == "propose":
                    task_ids.append(self._create_compile_task(current_report_id, proposal))
                    continue

                action = self._apply_safe_update(current_report_id, proposal)
                if action["kind"] == "created":
                    created_page_ids.append(action["page_id"])
                elif action["kind"] == "updated":
                    updated_page_ids.append(action["page_id"])
                elif action["kind"] == "conflict":
                    conflict_ids.append(action["conflict_id"])
                    task_ids.append(action["task_id"])

            if mode == "apply_safe":
                wiki_service.refresh_index()

        return {
            "mode": mode,
            "processed_reports": report_ids,
            "created_page_ids": created_page_ids,
            "updated_page_ids": updated_page_ids,
            "task_ids": task_ids,
            "conflict_ids": conflict_ids,
            "llm_used": llm_used,
            "message": f"processed {len(report_ids)} report(s)",
        }

    def _build_proposals(self, report: dict) -> tuple[list[PageProposal], bool]:
        report_context = self._render_report_context(report)
        llm_used = False
        try:
            llm_service.complete("compile/generate_page_proposal", {"report_context": report_context})
            llm_used = True
        except LLMUnavailableError:
            llm_used = False

        proposals: list[PageProposal] = []
        seen_slugs: set[str] = set()

        topic_title = str(report["title"]).strip()
        topic_slug = self._slugify(topic_title, fallback=report["report_id"])
        topic_proposal = PageProposal(
            page_id=f"pg_topic_{topic_slug}",
            page_type="topic",
            title=topic_title,
            slug=topic_slug,
            summary=report["summary"],
            tags=report.get("tags", []),
            source_report_ids=[report["report_id"]],
            body=self._build_topic_body(report),
        )
        proposals.append(topic_proposal)
        seen_slugs.add(topic_slug)

        for entity_title in self._extract_entities(report):
            slug = self._slugify(entity_title, fallback=entity_title)
            if slug in seen_slugs:
                continue
            seen_slugs.add(slug)
            proposals.append(
                PageProposal(
                    page_id=f"pg_entity_{slug}",
                    page_type="entity",
                    title=entity_title,
                    slug=slug,
                    summary=report["summary"],
                    tags=report.get("tags", []),
                    source_report_ids=[report["report_id"]],
                    body=self._build_entity_body(report, entity_title),
                )
            )

        for concept_title in self._extract_concepts(report):
            slug = self._slugify(concept_title, fallback=concept_title)
            if slug in seen_slugs:
                continue
            seen_slugs.add(slug)
            proposals.append(
                PageProposal(
                    page_id=f"pg_concept_{slug}",
                    page_type="concept",
                    title=concept_title,
                    slug=slug,
                    summary=report["summary"],
                    tags=report.get("tags", []),
                    source_report_ids=[report["report_id"]],
                    body=self._build_concept_body(report, concept_title),
                )
            )

        return proposals, llm_used

    def _apply_safe_update(self, report_id: str, proposal: PageProposal) -> dict:
        existing = wiki_service.get_page_by_slug(proposal.slug)
        if existing is None:
            self._write_new_page(proposal)
            return {"kind": "created", "page_id": proposal.page_id}

        if existing["page_type"] != proposal.page_type:
            conflict_id = self._create_conflict(
                topic_key=proposal.slug,
                page_id=existing["page_id"],
                old_claim=f"existing page type is {existing['page_type']}",
                new_claim=f"new proposal page type is {proposal.page_type}",
                evidence_report_id=report_id,
                severity="medium",
            )
            task_id = self._create_task(
                task_type="resolve_conflict",
                target_kind="wiki_page",
                target_id=existing["page_id"],
                title=f"Resolve page type conflict for {proposal.slug}",
                description=f"Existing page_type={existing['page_type']}, proposed={proposal.page_type}",
            )
            return {"kind": "conflict", "conflict_id": conflict_id, "task_id": task_id}

        self._append_safe_evidence(existing, proposal)
        return {"kind": "updated", "page_id": existing["page_id"]}

    def _write_new_page(self, proposal: PageProposal) -> None:
        subdir = {
            "entity": "entities",
            "concept": "concepts",
            "topic": "topics",
            "question": "questions",
            "timeline": "timelines",
        }[proposal.page_type]
        target_path = get_workspace_knowledge_root(self._workspace_id()) / subdir / f"{proposal.slug}.md"
        target_path.parent.mkdir(parents=True, exist_ok=True)
        content = self._render_page_markdown(proposal)
        target_path.write_text(content, encoding="utf-8")

    def _append_safe_evidence(self, existing_page: dict, proposal: PageProposal) -> None:
        file_path = get_workspace_knowledge_root(self._workspace_id()) / existing_page["file_path"]
        raw_text = file_path.read_text(encoding="utf-8")

        if proposal.source_report_ids[0] in raw_text:
            return

        evidence_block = f"\n- [[{proposal.source_report_ids[0]}]]"
        if "## Evidence" in raw_text:
            updated = raw_text.rstrip() + evidence_block + "\n"
        else:
            updated = raw_text.rstrip() + "\n\n## Evidence\n\n" + evidence_block.strip() + "\n"

        file_path.write_text(updated, encoding="utf-8")

    def _render_page_markdown(self, proposal: PageProposal) -> str:
        timestamp = self._now()
        tags_block = "\n".join(f"  - {tag}" for tag in proposal.tags) or "  - compiled"
        reports_block = "\n".join(f"  - {report_id}" for report_id in proposal.source_report_ids)
        return (
            "---\n"
            f"page_id: {proposal.page_id}\n"
            f"page_type: {proposal.page_type}\n"
            f"title: {proposal.title}\n"
            f"slug: {proposal.slug}\n"
            "status: needs_review\n"
            f"created_at: {timestamp}\n"
            f"updated_at: {timestamp}\n"
            "confidence: 0.5\n"
            "tags:\n"
            f"{tags_block}\n"
            "source_report_ids:\n"
            f"{reports_block}\n"
            "---\n\n"
            f"{proposal.body.strip()}\n"
        )

    def _create_compile_task(self, report_id: str, proposal: PageProposal) -> int:
        description = (
            f"[{proposal.page_type}] {proposal.title}\n"
            f"slug: {proposal.slug}\n"
            f"source_report: {report_id}\n\n"
            f"{proposal.summary}"
        )
        return self._create_task(
            task_type="compile_page",
            target_kind="report",
            target_id=report_id,
            title=f"Compile {proposal.page_type} page for {proposal.title}",
            description=description,
        )

    def _create_task(
        self,
        *,
        task_type: str,
        target_kind: str,
        target_id: str | None,
        title: str,
        description: str,
    ) -> int:
        now = self._now()
        with db_manager.session() as connection:
            cursor = connection.execute(
                """
                INSERT INTO knowledge_tasks (
                    task_type, target_kind, target_id, title, description,
                    priority, status, created_by, created_at, updated_at
                )
                VALUES (?, ?, ?, ?, ?, 'medium', 'open', 'system', ?, ?)
                """,
                (task_type, target_kind, target_id, title, description, now, now),
            )
            return int(cursor.lastrowid)

    def _create_conflict(
        self,
        *,
        topic_key: str,
        page_id: str,
        old_claim: str,
        new_claim: str,
        evidence_report_id: str,
        severity: str,
    ) -> int:
        with db_manager.session() as connection:
            cursor = connection.execute(
                """
                INSERT INTO knowledge_conflicts (
                    topic_key, page_id_ref, old_claim, new_claim,
                    evidence_report_id, severity, status, created_at
                )
                VALUES (?, ?, ?, ?, ?, ?, 'open', ?)
                """,
                (topic_key, page_id, old_claim, new_claim, evidence_report_id, severity, self._now()),
            )
            return int(cursor.lastrowid)

    def _load_pending_report_ids(self) -> list[str]:
        with db_manager.session() as connection:
            rows = connection.execute(
                """
                SELECT target_id
                FROM knowledge_tasks
                WHERE task_type = 'compile_page'
                  AND target_kind = 'report'
                  AND status = 'open'
                  AND target_id IS NOT NULL
                ORDER BY id ASC
                """
            ).fetchall()
            return [str(row["target_id"]) for row in rows]

    def _extract_entities(self, report: dict) -> list[str]:
        title = str(report["title"])
        candidates = re.findall(r"\b[A-Z][A-Za-z0-9_-]{2,}\b", title)
        if candidates:
            return candidates[:3]
        if title and title not in TOPIC_STOPWORDS:
            return [title[:48]]
        return []

    def _extract_concepts(self, report: dict) -> list[str]:
        tags = [tag for tag in report.get("tags", []) if tag.strip()]
        concepts = [tag for tag in tags if tag.lower() not in {"report", "summary"}]
        return concepts[:5]

    def _build_topic_body(self, report: dict) -> str:
        return (
            f"# {report['title']}\n\n"
            "## Overview\n\n"
            f"{report['summary']}\n\n"
            "## Evidence\n\n"
            f"- [[{report['report_id']}]]\n"
        )

    def _build_entity_body(self, report: dict, entity_title: str) -> str:
        return (
            f"# {entity_title}\n\n"
            "## Overview\n\n"
            f"{report['summary']}\n\n"
            "## Source Reports\n\n"
            f"- [[{report['report_id']}]]\n"
        )

    def _build_concept_body(self, report: dict, concept_title: str) -> str:
        return (
            f"# {concept_title}\n\n"
            "## Overview\n\n"
            f"{report['summary']}\n\n"
            "## Source Reports\n\n"
            f"- [[{report['report_id']}]]\n"
        )

    def _render_report_context(self, report: dict) -> str:
        return (
            f"title: {report['title']}\n"
            f"summary: {report['summary']}\n"
            f"source_ref: {report['source_ref']}\n"
            f"tags: {', '.join(report.get('tags', []))}\n"
        )

    def _slugify(self, text: str, *, fallback: str) -> str:
        lowered = text.lower()
        cleaned = re.sub(r"[^a-z0-9\u4e00-\u9fff]+", "-", lowered).strip("-")
        cleaned = re.sub(r"-{2,}", "-", cleaned)
        return (cleaned[:64] or fallback.lower()).strip("-")

    def _now(self) -> str:
        return datetime.now(timezone.utc).isoformat()

    def _workspace_id(self) -> str:
        from ..workspace import get_current_workspace_id

        workspace_id = get_current_workspace_id()
        if not workspace_id:
            raise ValueError("workspace context is required")
        return workspace_id


compile_service = CompileService()
