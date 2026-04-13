from __future__ import annotations

import os
from hashlib import sha1
from dataclasses import dataclass
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[2]


def _resolve_path(env_name: str, default_relative: str) -> Path:
    raw_value = os.getenv(env_name)
    if raw_value:
        candidate = Path(raw_value)
        if not candidate.is_absolute():
            candidate = PROJECT_ROOT / candidate
    else:
        candidate = PROJECT_ROOT / default_relative
    return candidate.resolve()


def _resolve_additional_paths(env_name: str) -> list[Path]:
    """解析额外的报告根路径列表，支持多个路径用逗号分隔"""
    raw_value = os.getenv(env_name, "")
    if not raw_value:
        return []
    paths = []
    for part in raw_value.split(","):
        part = part.strip()
        if not part:
            continue
        candidate = Path(part)
        if not candidate.is_absolute():
            candidate = PROJECT_ROOT / candidate
        paths.append(candidate.resolve())
    return paths


def report_root_key(root: Path) -> str:
    digest = sha1(str(root.resolve()).encode("utf-8")).hexdigest()[:12]
    return f"ext-{digest}"


def encode_report_storage_path(*, root: Path, relative_path: str, primary_root: Path) -> str:
    normalized_relative_path = relative_path.replace("\\", "/").lstrip("/")
    if root.resolve() == primary_root.resolve():
        return normalized_relative_path
    return f"@{report_root_key(root)}/{normalized_relative_path}"


@dataclass(frozen=True)
class Settings:
    project_root: Path
    raw_root: Path
    reports_root: Path
    additional_report_roots: list[Path]
    knowledge_root: Path
    data_root: Path
    logs_root: Path
    sqlite_path: Path
    llm_model: str
    api_title: str = "Report Center API"
    api_version: str = "0.1.0"


def get_settings() -> Settings:
    data_root = _resolve_path("DATA_ROOT", "data")
    return Settings(
        project_root=PROJECT_ROOT,
        raw_root=_resolve_path("RAW_ROOT", "raw"),
        reports_root=_resolve_path("REPORTS_ROOT", "reports"),
        additional_report_roots=_resolve_additional_paths("ADDITIONAL_REPORT_ROOTS"),
        knowledge_root=_resolve_path("KNOWLEDGE_ROOT", "knowledge"),
        data_root=data_root,
        logs_root=_resolve_path("LOGS_ROOT", "logs"),
        sqlite_path=_resolve_path("SQLITE_PATH", str(data_root / "reports.db")),
        llm_model=os.getenv("LLM_MODEL", "claude-sonnet-4-6"),
    )


settings = get_settings()


def ensure_runtime_dirs(current_settings: Settings) -> None:
    for directory in (
        current_settings.raw_root,
        current_settings.reports_root,
        current_settings.knowledge_root,
        current_settings.data_root,
        current_settings.logs_root,
    ):
        directory.mkdir(parents=True, exist_ok=True)

    for subdir in ("entities", "concepts", "topics", "questions", "timelines", "conflicts", "digests"):
        (current_settings.knowledge_root / subdir).mkdir(parents=True, exist_ok=True)
