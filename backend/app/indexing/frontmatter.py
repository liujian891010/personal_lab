from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass(slots=True)
class ParsedFrontmatter:
    metadata: dict[str, Any]
    body: str


def parse_frontmatter(content: str) -> ParsedFrontmatter:
    if not content.startswith("---\n"):
        return ParsedFrontmatter(metadata={}, body=content)

    lines = content.splitlines()
    if not lines or lines[0].strip() != "---":
        return ParsedFrontmatter(metadata={}, body=content)

    closing_index = None
    for index in range(1, len(lines)):
        if lines[index].strip() == "---":
            closing_index = index
            break

    if closing_index is None:
        return ParsedFrontmatter(metadata={}, body=content)

    metadata_lines = lines[1:closing_index]
    body = "\n".join(lines[closing_index + 1 :])
    return ParsedFrontmatter(metadata=_parse_simple_yaml(metadata_lines), body=body)


def _parse_simple_yaml(lines: list[str]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    current_list_key: str | None = None

    for raw_line in lines:
        line = raw_line.rstrip()
        if not line.strip():
            continue

        if line.lstrip().startswith("- "):
            if current_list_key is None:
                continue
            result.setdefault(current_list_key, [])
            result[current_list_key].append(_coerce_scalar(line.lstrip()[2:].strip()))
            continue

        current_list_key = None
        if ":" not in line:
            continue

        key, value = line.split(":", 1)
        key = key.strip()
        value = value.strip()

        if value == "":
            result[key] = []
            current_list_key = key
        else:
            result[key] = _coerce_scalar(value)

    return result


def _coerce_scalar(value: str) -> Any:
    cleaned = value.strip().strip("\"'")
    lowered = cleaned.lower()
    if lowered == "true":
        return True
    if lowered == "false":
        return False
    return cleaned
