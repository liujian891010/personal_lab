from __future__ import annotations

import re


FTS_TOKEN_PATTERN = re.compile(r"[A-Za-z0-9_]+|[\u4e00-\u9fff]+")


def build_fts_query(text: str, *, limit: int = 8) -> str | None:
    seen: set[str] = set()
    tokens: list[str] = []

    for token in FTS_TOKEN_PATTERN.findall(text.lower()):
        normalized = token.strip()
        if not normalized or normalized in seen:
            continue
        seen.add(normalized)
        tokens.append(normalized)
        if len(tokens) >= limit:
            break

    if not tokens:
        return None

    return " OR ".join(_quote_fts_token(token) for token in tokens)


def _quote_fts_token(token: str) -> str:
    escaped = token.replace('"', '""')
    return f'"{escaped}"'
