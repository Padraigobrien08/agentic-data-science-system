"""Extract JSON object from model text (optional fenced code block)."""

from __future__ import annotations

import json
import re
from typing import Any


def parse_json_object(text: str) -> dict[str, Any]:
    t = text.strip()
    if t.startswith("```"):
        t = re.sub(r"^```(?:json)?\s*\n", "", t, flags=re.IGNORECASE)
        t = re.sub(r"\n```\s*$", "", t)
        t = t.strip()
    return json.loads(t)
