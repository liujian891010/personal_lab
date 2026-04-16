from __future__ import annotations

import os
import re
from hashlib import sha1
from dataclasses import dataclass
from pathlib import Path

from dotenv import load_dotenv

from .resources import SOURCE_ROOT


def _resolve_runtime_root() -> Path:
    raw_value = os.getenv("PERSONAL_LAB_HOME", "").strip()
    if raw_value:
        candidate = Path(os.path.expandvars(raw_value))
        if not candidate.is_absolute():
            candidate = Path.cwd() / candidate
        return candidate.resolve()

    if (SOURCE_ROOT / "frontend").exists() and (SOURCE_ROOT / "backend").exists():
        return SOURCE_ROOT.resolve()

    return (Path.cwd() / ".personal_lab").resolve()


RUNTIME_ROOT = _resolve_runtime_root()

for dotenv_path in (
    SOURCE_ROOT / ".env",
    Path.cwd() / ".env",
    RUNTIME_ROOT / ".env",
):
    if dotenv_path.exists():
        load_dotenv(dotenv_path, override=False)


def _resolve_path(env_name: str, default_relative: str) -> Path:
    raw_value = os.getenv(env_name)
    if raw_value:
        candidate = Path(raw_value)
        if not candidate.is_absolute():
            candidate = RUNTIME_ROOT / candidate
    else:
        candidate = RUNTIME_ROOT / default_relative
    return candidate.resolve()


def _resolve_additional_paths(env_name: str) -> list[Path]:
    """解析额外的报告根路径列表，支持多个路径用逗号分隔，支持环境变量如 ${HOME}"""
    raw_value = os.getenv(env_name, "")
    if not raw_value:
        return []
    paths = []
    for part in raw_value.split(","):
        part = part.strip()
        if not part:
            continue
        # 展开环境变量
        expanded = os.path.expandvars(part)
        candidate = Path(expanded)
        if candidate.is_absolute():
            resolved = candidate.resolve()
        else:
            # Relative path: resolve from runtime root.
            resolved = (RUNTIME_ROOT / candidate).resolve()
        paths.append(resolved)
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
    source_root: Path
    runtime_root: Path
    raw_root: Path
    raw_uploads_root: Path
    reports_root: Path
    additional_report_roots: list[Path]
    knowledge_root: Path
    uploads_root: Path
    upload_inbox_root: Path
    upload_working_root: Path
    upload_processed_root: Path
    upload_failed_root: Path
    data_root: Path
    logs_root: Path
    object_storage_root: Path
    sqlite_path: Path
    llm_model: str
    session_secret: str
    object_storage_provider: str
    object_storage_bucket: str
    appkey_login_url: str
    appkey_query_param: str
    appkey_app_code: str
    auth_http_timeout_sec: float
    api_title: str = "Report Center API"
    api_version: str = "0.1.0"


def get_settings() -> Settings:
    data_root = _resolve_path("DATA_ROOT", "data")
    raw_root = _resolve_path("RAW_ROOT", "raw")
    uploads_root = _resolve_path("UPLOADS_ROOT", "uploads")
    return Settings(
        source_root=SOURCE_ROOT,
        runtime_root=RUNTIME_ROOT,
        raw_root=raw_root,
        raw_uploads_root=_resolve_path("RAW_UPLOADS_ROOT", str(raw_root / "uploads")),
        reports_root=_resolve_path("REPORTS_ROOT", "reports"),
        additional_report_roots=_resolve_additional_paths("ADDITIONAL_REPORT_ROOTS"),
        knowledge_root=_resolve_path("KNOWLEDGE_ROOT", "knowledge"),
        uploads_root=uploads_root,
        upload_inbox_root=_resolve_path("UPLOAD_INBOX_ROOT", str(uploads_root / "inbox")),
        upload_working_root=_resolve_path("UPLOAD_WORKING_ROOT", str(uploads_root / "working")),
        upload_processed_root=_resolve_path("UPLOAD_PROCESSED_ROOT", str(uploads_root / "processed")),
        upload_failed_root=_resolve_path("UPLOAD_FAILED_ROOT", str(uploads_root / "failed")),
        data_root=data_root,
        logs_root=_resolve_path("LOGS_ROOT", "logs"),
        object_storage_root=_resolve_path("OBJECT_STORAGE_ROOT", str(data_root / "object_store")),
        sqlite_path=_resolve_path("SQLITE_PATH", str(data_root / "reports.db")),
        llm_model=os.getenv("LLM_MODEL", "claude-sonnet-4-6"),
        session_secret=os.getenv("SESSION_SECRET", "report-center-dev-secret"),
        object_storage_provider=os.getenv("OBJECT_STORAGE_PROVIDER", "local").strip().lower(),
        object_storage_bucket=os.getenv("OBJECT_STORAGE_BUCKET", "personal-lab").strip() or "personal-lab",
        appkey_login_url=os.getenv(
            "APPKEY_LOGIN_URL",
            "https://sg-al-cwork-web.mediportal.com.cn/user/login/appkey",
        ),
        appkey_query_param=os.getenv("APPKEY_QUERY_PARAM", "appKey"),
        appkey_app_code=os.getenv("APPKEY_APP_CODE", "personal_lab"),
        auth_http_timeout_sec=float(os.getenv("AUTH_HTTP_TIMEOUT_SEC", "10")),
    )


settings = get_settings()


def ensure_runtime_dirs(current_settings: Settings) -> None:
    for directory in (
        current_settings.raw_root,
        current_settings.raw_uploads_root,
        current_settings.reports_root,
        current_settings.knowledge_root,
        current_settings.uploads_root,
        current_settings.upload_inbox_root,
        current_settings.upload_working_root,
        current_settings.upload_processed_root,
        current_settings.upload_failed_root,
        current_settings.data_root,
        current_settings.logs_root,
        current_settings.object_storage_root,
    ):
        directory.mkdir(parents=True, exist_ok=True)

    for subdir in ("entities", "concepts", "topics", "questions", "timelines", "conflicts", "digests"):
        (current_settings.knowledge_root / subdir).mkdir(parents=True, exist_ok=True)


def sanitize_workspace_id(workspace_id: str) -> str:
    normalized = re.sub(r"[^A-Za-z0-9._-]+", "_", workspace_id.strip()).strip("._-")
    if not normalized:
        raise ValueError("workspace_id must not be empty")
    return normalized[:80]


def get_workspace_root(workspace_id: str) -> Path:
    return settings.data_root / "workspaces" / sanitize_workspace_id(workspace_id)


def get_workspace_reports_root(workspace_id: str) -> Path:
    return get_workspace_root(workspace_id) / "reports"


def get_workspace_knowledge_root(workspace_id: str) -> Path:
    return get_workspace_root(workspace_id) / "knowledge"


def get_workspace_uploads_root(workspace_id: str) -> Path:
    return get_workspace_root(workspace_id) / "uploads"


def get_workspace_upload_inbox_root(workspace_id: str) -> Path:
    return get_workspace_uploads_root(workspace_id) / "inbox"


def get_workspace_upload_working_root(workspace_id: str) -> Path:
    return get_workspace_uploads_root(workspace_id) / "working"


def get_workspace_upload_processed_root(workspace_id: str) -> Path:
    return get_workspace_uploads_root(workspace_id) / "processed"


def get_workspace_upload_failed_root(workspace_id: str) -> Path:
    return get_workspace_uploads_root(workspace_id) / "failed"


def get_workspace_raw_root(workspace_id: str) -> Path:
    return get_workspace_root(workspace_id) / "raw"


def get_workspace_raw_uploads_root(workspace_id: str) -> Path:
    return get_workspace_raw_root(workspace_id) / "uploads"


def get_workspace_logs_root(workspace_id: str) -> Path:
    return get_workspace_root(workspace_id) / "logs"


def get_workspace_sqlite_path(workspace_id: str) -> Path:
    return get_workspace_root(workspace_id) / "data" / "reports.db"


def ensure_workspace_dirs(workspace_id: str) -> None:
    knowledge_root = get_workspace_knowledge_root(workspace_id)
    for directory in (
        get_workspace_reports_root(workspace_id),
        knowledge_root,
        get_workspace_uploads_root(workspace_id),
        get_workspace_upload_inbox_root(workspace_id),
        get_workspace_upload_working_root(workspace_id),
        get_workspace_upload_processed_root(workspace_id),
        get_workspace_upload_failed_root(workspace_id),
        get_workspace_raw_root(workspace_id),
        get_workspace_raw_uploads_root(workspace_id),
        get_workspace_logs_root(workspace_id),
        get_workspace_sqlite_path(workspace_id).parent,
    ):
        directory.mkdir(parents=True, exist_ok=True)

    for subdir in ("entities", "concepts", "topics", "questions", "timelines", "conflicts", "digests"):
        (knowledge_root / subdir).mkdir(parents=True, exist_ok=True)
