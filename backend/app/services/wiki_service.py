from __future__ import annotations

import hashlib
import re
import sqlite3
import unicodedata
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from ..config import settings
from ..db import db_manager, row_to_dict
from ..indexing.frontmatter import parse_frontmatter
from ..indexing.scanner import scan_markdown_files
from .file_service import read_text
from .fts_utils import build_fts_query


WIKILINK_PATTERN = re.compile(r"\[\[([^\]]+)\]\]")
KNOWN_PAGE_TYPES = {"entity", "concept", "topic", "question", "timeline"}
KNOWN_KNOWLEDGE_DIRS = (
    "entities",
    "concepts",
    "topics",
    "questions",
    "timelines",
    "conflicts",
    "digests",
)


@dataclass(slots=True)
class WikiDocument:
    page_id: str
    page_type: str
    file_path: str
    slug: str
    title: str
    status: str
    summary: str | None
    confidence: float | None
    content_hash: str
    created_at: str
    updated_at: str
    body: str
    raw_content: str
    tags: list[str]
    source_report_ids: list[str]
    related_targets: list[str]


class WikiService:
    def ensure_knowledge_dirs(self) -> None:
        for subdir in KNOWN_KNOWLEDGE_DIRS:
            (settings.knowledge_root / subdir).mkdir(parents=True, exist_ok=True)

    def refresh_index(self) -> None:
        self.ensure_knowledge_dirs()
        files = scan_markdown_files(settings.knowledge_root)
        documents: list[WikiDocument] = [self._parse_wiki_file(path) for path in files]
        self._validate_unique_constraints(documents)

        with db_manager.session() as connection:
            self._clear_wiki_indexes(connection)
            page_id_map = {document.page_id: document.page_id for document in documents}
            slug_map = {document.slug: document.page_id for document in documents}
            existing_reports = {
                row["report_id"]
                for row in connection.execute("SELECT report_id FROM reports").fetchall()
            }
            for document in documents:
                self._insert_document(
                    connection,
                    document,
                    page_id_map=page_id_map,
                    slug_map=slug_map,
                    existing_reports=existing_reports,
                )

    def list_pages(
        self,
        *,
        page_type: str | None = None,
        tag: str | None = None,
        status: str | None = None,
        q: str | None = None,
        page: int = 1,
        page_size: int = 20,
    ) -> dict[str, Any]:
        self.refresh_index()
        page = max(page, 1)
        page_size = min(max(page_size, 1), 100)
        offset = (page - 1) * page_size
        fts_query = build_fts_query(q, limit=8) if q else None

        if q and not fts_query:
            return {"items": [], "page": page, "page_size": page_size, "total": 0}

        joins: list[str] = []
        where_clauses: list[str] = []
        params: list[Any] = []

        if tag:
            joins.append("JOIN wiki_page_tags wt ON wt.page_id_ref = w.page_id")
            where_clauses.append("wt.normalized_tag = ?")
            params.append(tag.strip().lower())
        if page_type:
            where_clauses.append("w.page_type = ?")
            params.append(page_type)
        if status:
            where_clauses.append("w.status = ?")
            params.append(status)
        if q:
            joins.append("JOIN wiki_search_index ws ON ws.page_id = w.page_id")
            where_clauses.append("wiki_search_index MATCH ?")
            params.append(fts_query)

        join_sql = " ".join(dict.fromkeys(joins))
        where_sql = f"WHERE {' AND '.join(where_clauses)}" if where_clauses else ""

        with db_manager.session() as connection:
            total = connection.execute(
                f"""
                SELECT COUNT(DISTINCT w.page_id)
                FROM wiki_pages w
                {join_sql}
                {where_sql}
                """,
                params,
            ).fetchone()[0]

            rows = connection.execute(
                f"""
                SELECT DISTINCT
                    w.page_id, w.page_type, w.file_path, w.slug, w.title,
                    w.status, w.summary, w.confidence, w.created_at, w.updated_at
                FROM wiki_pages w
                {join_sql}
                {where_sql}
                ORDER BY w.updated_at DESC, w.title ASC
                LIMIT ? OFFSET ?
                """,
                [*params, page_size, offset],
            ).fetchall()

            items = [row_to_dict(row) for row in rows]
            tags_map = self._load_tags(connection, [item["page_id"] for item in items if item])
            source_counts = self._load_source_counts(connection, [item["page_id"] for item in items if item])
            for item in items:
                item["tags"] = tags_map.get(item["page_id"], [])
                item["source_report_count"] = source_counts.get(item["page_id"], 0)

            return {"items": items, "page": page, "page_size": page_size, "total": total}

    def get_page(self, page_id: str) -> dict[str, Any] | None:
        self.refresh_index()
        with db_manager.session() as connection:
            row = connection.execute(
                """
                SELECT
                    page_id, page_type, file_path, slug, title, status,
                    summary, confidence, content_hash, created_at, updated_at
                FROM wiki_pages
                WHERE page_id = ?
                """,
                (page_id,),
            ).fetchone()
            if row is None:
                return None
            return self._build_page_detail(connection, row_to_dict(row))

    def get_page_by_slug(self, slug: str) -> dict[str, Any] | None:
        self.refresh_index()
        with db_manager.session() as connection:
            row = connection.execute(
                """
                SELECT
                    page_id, page_type, file_path, slug, title, status,
                    summary, confidence, content_hash, created_at, updated_at
                FROM wiki_pages
                WHERE slug = ?
                """,
                (slug,),
            ).fetchone()
            if row is None:
                return None
            return self._build_page_detail(connection, row_to_dict(row))

    def _build_page_detail(self, connection: sqlite3.Connection, item: dict[str, Any]) -> dict[str, Any]:
        item["tags"] = self._load_tags(connection, [item["page_id"]]).get(item["page_id"], [])
        item["source_reports"] = [
            row_to_dict(row)
            for row in connection.execute(
                """
                SELECT r.report_id, r.title, r.source_ref, r.source_domain, r.generated_at, ps.evidence_role
                FROM page_sources ps
                JOIN reports r ON r.report_id = ps.report_id_ref
                WHERE ps.page_id_ref = ?
                ORDER BY r.generated_at DESC
                """,
                (item["page_id"],),
            ).fetchall()
        ]
        item["related_pages"] = [
            row_to_dict(row)
            for row in connection.execute(
                """
                SELECT wl.target_id AS page_id, wp.slug, wp.title, wp.page_type, wl.link_type
                FROM wiki_links wl
                JOIN wiki_pages wp ON wp.page_id = wl.target_id
                WHERE wl.source_page_id = ? AND wl.target_kind = 'wiki_page'
                ORDER BY wp.title
                """,
                (item["page_id"],),
            ).fetchall()
        ]
        item["content"] = read_text(settings.knowledge_root, item["file_path"])
        return item

    def _parse_wiki_file(self, path: Path) -> WikiDocument:
        raw_content = path.read_text(encoding="utf-8")
        parsed = parse_frontmatter(raw_content)
        metadata = dict(parsed.metadata)
        body = parsed.body.strip()
        relative_path = path.relative_to(settings.knowledge_root).as_posix()

        page_id = str(metadata.get("page_id") or self._derive_page_id(relative_path))
        page_type = str(metadata.get("page_type") or self._derive_page_type(path))
        title = str(metadata.get("title") or path.stem)
        slug = str(metadata.get("slug") or self._slugify(title, fallback=page_id))
        status = str(metadata.get("status") or "active")
        summary = self._maybe_string(metadata.get("summary")) or self._extract_summary(body)
        confidence = self._maybe_float(metadata.get("confidence"))
        created_at = str(metadata.get("created_at") or self._current_time())
        updated_at = str(metadata.get("updated_at") or self._current_time())
        tags = self._normalize_string_list(metadata.get("tags"))
        source_report_ids = self._normalize_string_list(metadata.get("source_report_ids"))
        body_links = self._extract_wikilinks(body)
        related_targets = [target for target in body_links if not target.startswith("rpt_")]
        inferred_reports = [target for target in body_links if target.startswith("rpt_")]
        for report_id in inferred_reports:
            if report_id not in source_report_ids:
                source_report_ids.append(report_id)

        return WikiDocument(
            page_id=page_id,
            page_type=page_type,
            file_path=relative_path,
            slug=slug,
            title=title,
            status=status,
            summary=summary,
            confidence=confidence,
            content_hash=self._hash_body(body),
            created_at=created_at,
            updated_at=updated_at,
            body=body,
            raw_content=raw_content,
            tags=tags,
            source_report_ids=source_report_ids,
            related_targets=related_targets,
        )

    def _validate_unique_constraints(self, documents: list[WikiDocument]) -> None:
        seen_page_ids: set[str] = set()
        seen_slugs: set[str] = set()
        for document in documents:
            if document.page_type not in KNOWN_PAGE_TYPES:
                raise ValueError(f"invalid page_type '{document.page_type}' in {document.file_path}")
            if document.page_id in seen_page_ids:
                raise ValueError(f"duplicate page_id '{document.page_id}'")
            if document.slug in seen_slugs:
                raise ValueError(f"duplicate slug '{document.slug}'")
            seen_page_ids.add(document.page_id)
            seen_slugs.add(document.slug)

    def _clear_wiki_indexes(self, connection: sqlite3.Connection) -> None:
        connection.execute("DELETE FROM page_sources")
        connection.execute("DELETE FROM wiki_links")
        connection.execute("DELETE FROM wiki_page_tags")
        connection.execute("DELETE FROM wiki_pages")
        connection.execute("DELETE FROM wiki_search_index")

    def _insert_document(
        self,
        connection: sqlite3.Connection,
        document: WikiDocument,
        *,
        page_id_map: dict[str, str],
        slug_map: dict[str, str],
        existing_reports: set[str],
    ) -> None:
        connection.execute(
            """
            INSERT INTO wiki_pages (
                page_id, page_type, file_path, slug, title, status, summary,
                confidence, content_hash, created_at, updated_at
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                document.page_id,
                document.page_type,
                document.file_path,
                document.slug,
                document.title,
                document.status,
                document.summary,
                document.confidence,
                document.content_hash,
                document.created_at,
                document.updated_at,
            ),
        )

        for tag in document.tags:
            connection.execute(
                """
                INSERT INTO wiki_page_tags (page_id_ref, tag, normalized_tag)
                VALUES (?, ?, ?)
                """,
                (document.page_id, tag, tag.strip().lower()),
            )

        for report_id in document.source_report_ids:
            if report_id not in existing_reports:
                continue
            connection.execute(
                """
                INSERT OR IGNORE INTO page_sources (page_id_ref, report_id_ref, evidence_role)
                VALUES (?, ?, ?)
                """,
                (document.page_id, report_id, "primary"),
            )

        for target in document.related_targets:
            resolved_target = slug_map.get(target) or page_id_map.get(target)
            connection.execute(
                """
                INSERT INTO wiki_links (source_page_id, target_kind, target_id, link_type, anchor_text, is_resolved)
                VALUES (?, 'wiki_page', ?, 'related', NULL, ?)
                """,
                (document.page_id, resolved_target or target, 1 if resolved_target else 0),
            )

        for report_id in document.source_report_ids:
            if report_id not in existing_reports:
                continue
            connection.execute(
                """
                INSERT INTO wiki_links (source_page_id, target_kind, target_id, link_type, anchor_text, is_resolved)
                VALUES (?, 'report', ?, 'supports', NULL, 1)
                """,
                (document.page_id, report_id),
            )

        connection.execute(
            """
            INSERT INTO wiki_search_index (page_id, title, summary, body, tags, page_type)
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            (
                document.page_id,
                document.title,
                document.summary or "",
                document.body,
                " ".join(document.tags),
                document.page_type,
            ),
        )

    def _load_tags(self, connection: sqlite3.Connection, page_ids: list[str]) -> dict[str, list[str]]:
        if not page_ids:
            return {}
        placeholders = ", ".join("?" for _ in page_ids)
        rows = connection.execute(
            f"""
            SELECT page_id_ref, tag
            FROM wiki_page_tags
            WHERE page_id_ref IN ({placeholders})
            ORDER BY tag
            """,
            page_ids,
        ).fetchall()
        tags_map: dict[str, list[str]] = {}
        for row in rows:
            tags_map.setdefault(row["page_id_ref"], []).append(row["tag"])
        return tags_map

    def _load_source_counts(self, connection: sqlite3.Connection, page_ids: list[str]) -> dict[str, int]:
        if not page_ids:
            return {}
        placeholders = ", ".join("?" for _ in page_ids)
        rows = connection.execute(
            f"""
            SELECT page_id_ref, COUNT(*) AS count
            FROM page_sources
            WHERE page_id_ref IN ({placeholders})
            GROUP BY page_id_ref
            """,
            page_ids,
        ).fetchall()
        return {row["page_id_ref"]: row["count"] for row in rows}

    def _derive_page_id(self, relative_path: str) -> str:
        stem = Path(relative_path).stem
        return f"pg_{stem}".lower().replace(" ", "_")

    def _derive_page_type(self, path: Path) -> str:
        parent = path.parent.name.lower()
        mapping = {
            "entities": "entity",
            "concepts": "concept",
            "topics": "topic",
            "questions": "question",
            "timelines": "timeline",
        }
        return mapping.get(parent, "topic")

    def _slugify(self, title: str, *, fallback: str) -> str:
        normalized = unicodedata.normalize("NFKD", title)
        ascii_text = normalized.encode("ascii", "ignore").decode("ascii").lower()
        cleaned = re.sub(r"[^a-z0-9]+", "-", ascii_text).strip("-")
        return cleaned[:64] or fallback.lower()

    def _extract_summary(self, body: str) -> str | None:
        for line in body.splitlines():
            stripped = line.strip()
            if stripped and not stripped.startswith("#"):
                return stripped[:240]
        return None

    def _extract_wikilinks(self, body: str) -> list[str]:
        seen: set[str] = set()
        results: list[str] = []
        for match in WIKILINK_PATTERN.finditer(body):
            raw = match.group(1).strip()
            target = raw.split("|", 1)[0].split("#", 1)[0].strip()
            if not target or target in seen:
                continue
            seen.add(target)
            results.append(target)
        return results

    def _normalize_string_list(self, value: object) -> list[str]:
        if value is None:
            return []
        if isinstance(value, list):
            return [str(item).strip() for item in value if str(item).strip()]
        text = str(value).strip()
        return [text] if text else []

    def _maybe_string(self, value: object) -> str | None:
        if value is None:
            return None
        text = str(value).strip()
        return text or None

    def _maybe_float(self, value: object) -> float | None:
        if value is None or value == "":
            return None
        return float(value)

    def _hash_body(self, body: str) -> str:
        return f"sha256:{hashlib.sha256(body.encode('utf-8')).hexdigest()}"

    def _current_time(self) -> str:
        return datetime.now(timezone.utc).isoformat()


wiki_service = WikiService()
