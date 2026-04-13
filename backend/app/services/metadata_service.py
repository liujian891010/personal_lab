from __future__ import annotations

import hashlib
from dataclasses import dataclass
from pathlib import Path
from urllib.parse import urlparse

from ..indexing.frontmatter import parse_frontmatter
from ..indexing.markdown_parser import extract_urls


@dataclass(slots=True)
class ReportDocument:
    report_id: str
    file_path: str
    title: str
    source_ref: str
    source_url: str | None
    source_domain: str
    source_type: str
    skill_name: str
    generated_at: str
    author: str | None
    status: str
    language: str | None
    summary: str
    content_hash: str
    body_size: int
    body: str
    raw_content: str
    tags: list[str]
    related_urls: list[str]
    body_urls: list[str]


REQUIRED_FIELDS = (
    "report_id",
    "title",
    "source_ref",
    "skill_name",
    "generated_at",
    "status",
    "summary",
)


def parse_report_file(path: Path, root: Path) -> ReportDocument:
    raw_content = path.read_text(encoding="utf-8")
    parsed = parse_frontmatter(raw_content)
    metadata = dict(parsed.metadata)

    if "source_ref" not in metadata and metadata.get("source_url"):
        metadata["source_ref"] = metadata["source_url"]

    for field in REQUIRED_FIELDS:
        if not metadata.get(field):
            raise ValueError(f"missing required field: {field}")

    source_type = str(metadata.get("source_type", "url"))
    source_ref = str(metadata["source_ref"])
    source_url = metadata.get("source_url")
    if source_type == "url" and not source_url:
        source_url = source_ref

    source_domain = str(metadata.get("source_domain") or _derive_source_domain(source_ref, source_type))
    tags = _normalize_string_list(metadata.get("tags"))
    related_urls = _normalize_string_list(metadata.get("related_urls"))
    body = parsed.body.strip()
    body_size = len(body.encode("utf-8"))
    body_urls = extract_urls(body)
    content_hash = _calculate_content_hash(body)

    return ReportDocument(
        report_id=str(metadata["report_id"]),
        file_path=path.relative_to(root).as_posix(),
        title=str(metadata["title"]),
        source_ref=source_ref,
        source_url=str(source_url) if source_url else None,
        source_domain=source_domain,
        source_type=source_type,
        skill_name=str(metadata["skill_name"]),
        generated_at=str(metadata["generated_at"]),
        author=_maybe_string(metadata.get("author")),
        status=str(metadata["status"]),
        language=_maybe_string(metadata.get("language")),
        summary=str(metadata["summary"]),
        content_hash=content_hash,
        body_size=body_size,
        body=body,
        raw_content=raw_content,
        tags=tags,
        related_urls=related_urls,
        body_urls=body_urls,
    )


def normalize_tag(tag: str) -> str:
    return tag.strip().lower()


def _calculate_content_hash(body: str) -> str:
    digest = hashlib.sha256(body.encode("utf-8")).hexdigest()
    return f"sha256:{digest}"


def _derive_source_domain(source_ref: str, source_type: str) -> str:
    if source_type != "url":
        return "local"
    hostname = urlparse(source_ref).hostname
    return hostname or "unknown"


def _normalize_string_list(value: object) -> list[str]:
    if value is None:
        return []
    if isinstance(value, list):
        return [str(item).strip() for item in value if str(item).strip()]
    text = str(value).strip()
    return [text] if text else []


def _maybe_string(value: object) -> str | None:
    if value is None:
        return None
    text = str(value).strip()
    return text or None
