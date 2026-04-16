from __future__ import annotations

import os
import sysconfig
from pathlib import Path


PACKAGE_ROOT = Path(__file__).resolve().parent
SOURCE_ROOT = PACKAGE_ROOT.parents[1]
INSTALLED_SHARE_ROOT = Path(sysconfig.get_path("data")).resolve() / "share" / "personal_lab"


def _resolve_explicit_path(env_name: str) -> Path | None:
    raw_value = os.getenv(env_name, "").strip()
    if not raw_value:
        return None
    candidate = Path(os.path.expandvars(raw_value))
    if not candidate.is_absolute():
        candidate = Path.cwd() / candidate
    return candidate.resolve()


def get_frontend_root() -> Path | None:
    explicit = _resolve_explicit_path("PERSONAL_LAB_FRONTEND_ROOT")
    if explicit and explicit.exists():
        return explicit

    for candidate in (
        SOURCE_ROOT / "frontend",
        INSTALLED_SHARE_ROOT / "frontend",
    ):
        if candidate.exists():
            return candidate
    return None


def get_prompts_root() -> Path | None:
    explicit = _resolve_explicit_path("PERSONAL_LAB_PROMPTS_ROOT")
    if explicit and explicit.exists():
        return explicit

    for candidate in (
        SOURCE_ROOT / "prompts",
        INSTALLED_SHARE_ROOT / "prompts",
    ):
        if candidate.exists():
            return candidate
    return None
