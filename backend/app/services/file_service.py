from __future__ import annotations

from pathlib import Path


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
