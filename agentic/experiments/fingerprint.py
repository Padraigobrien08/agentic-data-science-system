"""
Deterministic fingerprints for experiment inputs and outputs.

The *input* fingerprint identifies the computation (dataset fingerprint + tool
name/version + canonical params). The *output* fingerprint hashes the content of
the result **excluding** volatile ids and timestamps, so repeatability can be
asserted even though ids/timestamps differ between runs.
"""

from __future__ import annotations

import hashlib

from agentic.domain.evidence import Evidence
from agentic.domain.observation import Observation

from .artifacts import ArtifactRecord, canonical_json


def _sha256(text: str) -> str:
    return "sha256:" + hashlib.sha256(text.encode("utf-8")).hexdigest()


def params_fingerprint(params: dict) -> str:
    return _sha256(canonical_json(params))


def input_fingerprint(*, dataset_fingerprint: str | None, tool_name: str, tool_version: str, params: dict) -> str:
    payload = canonical_json(
        {
            "dataset": dataset_fingerprint or "",
            "tool": tool_name,
            "version": tool_version,
            "params": params,
        }
    )
    return _sha256(payload)


def _observation_key(o: Observation) -> dict:
    return {
        "statement": o.statement,
        "type": o.observation_type.value,
        "magnitude": o.magnitude,
        "entity": o.entity_ref,
        "metric": o.metric_ref,
    }


def _evidence_key(e: Evidence) -> dict:
    return {
        "type": e.evidence_type.value,
        "claim": e.claim,
        "direction": e.direction.value,
        "strength": round(e.strength, 9),
        "reliability": round(e.reliability, 9),
        "coverage": round(e.coverage, 9),
        "statistics": e.statistics.model_dump(mode="json", exclude={"schema_version"}) if e.statistics else None,
    }


def output_fingerprint(
    *,
    observations: list[Observation],
    evidence: list[Evidence],
    metrics: dict[str, float],
    artifacts: list[ArtifactRecord],
) -> str:
    payload = canonical_json(
        {
            "observations": [_observation_key(o) for o in observations],
            "evidence": [_evidence_key(e) for e in evidence],
            "metrics": {k: round(v, 9) for k, v in sorted(metrics.items())},
            "artifacts": sorted(a.fingerprint for a in artifacts),
        }
    )
    return _sha256(payload)
