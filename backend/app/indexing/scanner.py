from __future__ import annotations

from pathlib import Path


def scan_markdown_files(root: Path, *, skip_top_level_dirs: set[str] | None = None) -> list[Path]:
    skip_top_level_dirs = skip_top_level_dirs or set()
    files: list[Path] = []
    for path in root.rglob("*.md"):
        relative = path.relative_to(root)
        if relative.parts and relative.parts[0] in skip_top_level_dirs:
            continue
        files.append(path)
    files.sort()
    return files
