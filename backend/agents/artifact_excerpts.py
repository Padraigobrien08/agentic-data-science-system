"""Load bounded text excerpts from on-disk artifact paths (for critic / report context)."""

from __future__ import annotations

from pathlib import Path


def read_text_excerpt(path_str: str, *, max_chars: int = 8000) -> str:
    """Read UTF-8 text up to ``max_chars`` (for CSV/Markdown previews)."""
    p = Path(path_str)
    if not p.is_file():
        return ""
    try:
        raw = p.read_text(encoding="utf-8", errors="replace")
    except OSError:
        return ""
    if len(raw) <= max_chars:
        return raw
    return raw[:max_chars] + f"\n… ({len(raw) - max_chars} more characters truncated)"
