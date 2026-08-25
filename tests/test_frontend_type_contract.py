"""
The frontend's TypeScript view of ``/v1`` must match the schema the API actually serves.

``frontend/src/lib/api/types.ts`` is hand-written. That is a deliberate choice — generated
clients are noisy and this codebase reads its types — but it means the mirror can drift, and
drift here is silent in both directions: TypeScript compiles happily against a field the API
stopped sending, and a field the API added is simply invisible to every component.

CI already fails when ``docs/api/openapi.json`` goes stale against the app, so the committed
schema is trustworthy. This closes the other half of the loop by comparing the mirror to it.

Deliberately field-level and not type-level. Checking that ``string | null`` matches
``anyOf: [string, null]`` means reimplementing a schema compiler in a test, and the failure
this exists to catch is a *missing or renamed field*, not a widened union. Names are where the
drift was: ``ModelCallApiItem.payloads_redacted_at`` was served by the API and absent from the
mirror, so no component could distinguish "payloads cleared by retention" from "never captured".
"""

from __future__ import annotations

import json
import re
from pathlib import Path

import pytest

_ROOT = Path(__file__).resolve().parents[1]
_OPENAPI = _ROOT / "docs" / "api" / "openapi.json"
_TYPES = _ROOT / "frontend" / "src" / "lib" / "api" / "types.ts"

#: Python schema name -> TypeScript interface name. Most match; the investigation read model
#: prefixes its names in TS because they sit alongside unrelated run types in one namespace.
_MIRRORED = {
    "InvestigationSummary": "InvestigationSummary",
    "InvestigationDetail": "InvestigationDetail",
    "InvestigationCounts": "InvestigationCounts",
    "InvestigationOutcome": "InvestigationOutcome",
    "HypothesisItem": "HypothesisItem",
    "EvidenceItem": "EvidenceItem",
    "ExperimentItem": "ExperimentItem",
    "CritiqueItem": "CritiqueItem",
    "DecisionItem": "DecisionItem",
    "ConclusionItem": "ConclusionItem",
    "ObservationItem": "ObservationItem",
    "OpenQuestionItem": "OpenQuestionItem",
    "DatasetItem": "DatasetItem",
    "EventItem": "InvestigationEventItem",
    "TerminationView": "InvestigationTermination",
    "ArtifactRef": "InvestigationArtifactRef",
    "ModelCallApiItem": "ModelCallApiItem",
}


def _api_schemas() -> dict[str, set[str]]:
    spec = json.loads(_OPENAPI.read_text())
    return {
        name: set(schema.get("properties", {}))
        for name, schema in spec["components"]["schemas"].items()
    }


def _ts_interfaces() -> dict[str, tuple[set[str], str | None]]:
    """Interface name -> (own field names, the interface it extends)."""
    source = _TYPES.read_text()
    out: dict[str, tuple[set[str], str | None]] = {}
    for match in re.finditer(
        r"export interface (\w+)(?: extends (\w+))? \{(.*?)\n\}", source, re.S
    ):
        name, extends, body = match.group(1), match.group(2), match.group(3)
        fields = set(re.findall(r"^\s{2}(\w+)\??\s*:", body, re.M))
        out[name] = (fields, extends)
    return out


def _fields(name: str, interfaces: dict[str, tuple[set[str], str | None]]) -> set[str]:
    """Field names including anything inherited via ``extends``."""
    seen: set[str] = set()
    fields: set[str] = set()
    while name in interfaces and name not in seen:
        seen.add(name)
        own, parent = interfaces[name]
        fields |= own
        name = parent or ""
    return fields


@pytest.fixture(scope="module")
def api() -> dict[str, set[str]]:
    return _api_schemas()


@pytest.fixture(scope="module")
def ts() -> dict[str, tuple[set[str], str | None]]:
    return _ts_interfaces()


def test_the_mirror_map_still_refers_to_real_types(api, ts) -> None:
    """A rename would otherwise turn every check below into a silent no-op."""
    missing_api = sorted(name for name in _MIRRORED if name not in api)
    missing_ts = sorted(name for name in _MIRRORED.values() if name not in ts)

    assert not missing_api, f"no such schema in openapi.json: {missing_api}"
    assert not missing_ts, f"no such interface in types.ts: {missing_ts}"


@pytest.mark.parametrize("schema_name,interface_name", sorted(_MIRRORED.items()))
def test_the_frontend_mirrors_every_field_the_api_serves(
    schema_name: str, interface_name: str, api, ts
) -> None:
    served = api[schema_name]
    mirrored = _fields(interface_name, ts)

    missing = sorted(served - mirrored)
    invented = sorted(mirrored - served)

    assert not missing, (
        f"{interface_name} is missing fields the API serves: {missing} — "
        "components cannot read what the mirror does not declare"
    )
    assert not invented, (
        f"{interface_name} declares fields the API does not serve: {invented} — "
        "TypeScript will compile against them and they will be undefined at runtime"
    )
