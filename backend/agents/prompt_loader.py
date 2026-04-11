"""
Load versioned, inspectable prompt templates from ``backend/agents/prompts/<agent>/<version>.md``.

Each file may start with optional YAML-style front matter between ``---`` lines:

  ---
  template_id: intent
  version: 1.1.0
  ---
  <markdown body>
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path

_PROMPTS_ROOT = Path(__file__).resolve().parent / "prompts"


@dataclass(frozen=True)
class AgentPromptTemplate:
    """Resolved template for one agent version (path is inspectable on disk)."""

    agent: str
    version: str
    template_id: str
    system_body: str
    path: Path

    @property
    def source_uri(self) -> str:
        """Stable locator for logs (repo-relative style)."""
        try:
            return str(self.path.relative_to(Path(__file__).resolve().parents[2]))
        except ValueError:
            return str(self.path)


def _parse_front_matter(raw: str) -> tuple[dict[str, str], str]:
    text = raw.strip()
    if not text.startswith("---"):
        return {}, text
    m = re.match(r"^---\s*\n(.*?)\n---\s*\n?(.*)$", text, re.DOTALL)
    if not m:
        return {}, text
    meta_block, body = m.group(1), m.group(2).strip()
    meta: dict[str, str] = {}
    for line in meta_block.splitlines():
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        if ":" in line:
            k, v = line.split(":", 1)
            meta[k.strip()] = v.strip().strip('"').strip("'")
    return meta, body


def list_prompt_versions(agent: str) -> list[str]:
    """Sorted semver-ish list from ``prompts/<agent>/*.md`` basename without extension."""
    d = _PROMPTS_ROOT / agent
    if not d.is_dir():
        return []
    versions = []
    for p in sorted(d.glob("*.md")):
        versions.append(p.stem)
    return versions


def load_agent_prompt(agent: str, version: str) -> AgentPromptTemplate:
    """
    Load ``prompts/{agent}/{version}.md``.

    Raises:
        FileNotFoundError: missing file
    """
    path = _PROMPTS_ROOT / agent / f"{version}.md"
    if not path.is_file():
        raise FileNotFoundError(f"Agent prompt not found: {path}")
    raw = path.read_text(encoding="utf-8")
    meta, body = _parse_front_matter(raw)
    tid = meta.get("template_id", agent)
    ver = meta.get("version", version)
    return AgentPromptTemplate(
        agent=agent,
        version=ver,
        template_id=tid,
        system_body=body.strip(),
        path=path,
    )
