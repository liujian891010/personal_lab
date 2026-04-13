from __future__ import annotations

from pathlib import Path
from typing import Iterable


def scan_markdown_files(
    root: Path | Iterable[Path], *, skip_top_level_dirs: set[str] | None = None
) -> list[Path]:
    skip_top_level_dirs = skip_top_level_dirs or set()
    files: list[Path] = []

    # Support single Path or multiple Paths
    roots: list[Path] = [root] if isinstance(root, Path) else list(root)

    for r in roots:
        if not r.exists():
            continue
        for path in r.rglob("*.md"):
            relative = path.relative_to(r)
            if relative.parts and relative.parts[0] in skip_top_level_dirs:
                continue
            files.append(path)

    files.sort()
    return files
