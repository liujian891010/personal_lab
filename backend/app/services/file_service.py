from __future__ import annotations

from pathlib import Path

from ..config import report_root_key, settings


class UnsafePathError(ValueError):
    """Raised when a requested path escapes the configured root."""


def resolve_safe_path(root: Path, relative_path: str) -> Path:
    candidate = (root / relative_path).resolve()
    root_resolved = root.resolve()

    if candidate == root_resolved:
        return candidate

    try:
        candidate.relative_to(root_resolved)
    except ValueError as exc:
        raise UnsafePathError(f"path escapes root: {relative_path}") from exc

    return candidate


def read_text(root: Path, relative_path: str) -> str:
    path = resolve_safe_path(root, relative_path)
    return path.read_text(encoding="utf-8")


def resolve_report_storage_path(storage_path: str) -> Path:
    normalized = storage_path.replace("\\", "/")
    if normalized.startswith("@"):
        prefix, _, relative_path = normalized[1:].partition("/")
        if not prefix or not relative_path:
            raise UnsafePathError(f"invalid additional report storage path: {storage_path}")
        for root in settings.additional_report_roots:
            if report_root_key(root) == prefix:
                return resolve_safe_path(root, relative_path)
        raise UnsafePathError(f"unknown additional report root for path: {storage_path}")
    return resolve_safe_path(settings.reports_root, normalized)


def read_report_text(storage_path: str) -> str:
    path = resolve_report_storage_path(storage_path)
    return path.read_text(encoding="utf-8")
