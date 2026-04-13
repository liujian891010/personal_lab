from __future__ import annotations

import os
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


@dataclass(frozen=True)
class Settings:
    project_root: Path
    raw_root: Path
    reports_root: Path
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
