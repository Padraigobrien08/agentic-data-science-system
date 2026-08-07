"""
Contract tests for the committed observability assets (``ops/``).

A dashboard or alert rule referencing a metric the code no longer emits fails silently:
the panel just goes blank and the alert never fires. These tests bind the assets to the
Prometheus registry so a renamed or deleted metric breaks the build instead of quietly
breaking the dashboard.

Structural validity (PromQL parsing, Prometheus config syntax, compose merging) is
covered by ``promtool`` and ``docker compose config``; what those cannot check is
whether the metric names are real. That is what this file is for.
"""

from __future__ import annotations

import json
import re
from pathlib import Path

import pytest
import yaml
from prometheus_client import REGISTRY

# Importing the module registers every metric family used by the assets.
import backend.observability.metrics  # noqa: F401

REPO = Path(__file__).resolve().parents[1]
OPS = REPO / "ops"
DASHBOARD = OPS / "grafana/dashboards/agent-loop.json"
RULES = OPS / "prometheus/rules/agent_loop.rules.yml"
PROM_CONFIG = OPS / "prometheus/prometheus.yml"
DATASOURCES = OPS / "grafana/provisioning/datasources/datasources.yml"
DASHBOARD_PROVIDER = OPS / "grafana/provisioning/dashboards/dashboards.yml"

#: Suffixes prometheus_client appends to a family name in the exposition format.
_SAMPLE_SUFFIXES = ("_total", "_bucket", "_sum", "_count", "_created")

_METRIC_REF = re.compile(r"\b(edgar_[a-z0-9_]+)\b")


def _registered_family_names() -> set[str]:
    return {family.name for family in REGISTRY.collect()}


def _is_known_metric(name: str, families: set[str]) -> bool:
    """A reference is valid if it names a family directly or a sample of one."""
    if name in families:
        return True
    return any(
        name.endswith(suffix) and name[: -len(suffix)] in families
        for suffix in _SAMPLE_SUFFIXES
    )


@pytest.fixture(scope="module")
def dashboard() -> dict:
    return json.loads(DASHBOARD.read_text())


@pytest.fixture(scope="module")
def rules() -> dict:
    return yaml.safe_load(RULES.read_text())


def _dashboard_exprs(dashboard: dict) -> list[tuple[str, str]]:
    return [
        (panel["title"], target["expr"])
        for panel in dashboard["panels"]
        for target in panel.get("targets", [])
    ]


def _rule_exprs(rules: dict) -> list[tuple[str, str]]:
    return [
        (rule["alert"], rule["expr"])
        for group in rules["groups"]
        for rule in group["rules"]
    ]


# -- the assets exist and parse ---------------------------------------------


@pytest.mark.parametrize("path", [DASHBOARD, RULES, PROM_CONFIG, DATASOURCES, DASHBOARD_PROVIDER])
def test_observability_assets_are_present(path: Path) -> None:
    assert path.is_file(), f"missing committed observability asset: {path.relative_to(REPO)}"


# -- metric references are real ---------------------------------------------


def test_dashboard_only_references_registered_metrics(dashboard: dict) -> None:
    families = _registered_family_names()
    unknown: list[str] = []
    for title, expr in _dashboard_exprs(dashboard):
        for name in _METRIC_REF.findall(expr):
            if not _is_known_metric(name, families):
                unknown.append(f"{title!r} references unknown metric {name!r}")
    assert not unknown, "dashboard references metrics the code does not emit:\n" + "\n".join(unknown)


def test_alert_rules_only_reference_registered_metrics(rules: dict) -> None:
    families = _registered_family_names()
    unknown: list[str] = []
    for alert, expr in _rule_exprs(rules):
        for name in _METRIC_REF.findall(expr):
            if not _is_known_metric(name, families):
                unknown.append(f"alert {alert!r} references unknown metric {name!r}")
    assert not unknown, "alert rules reference metrics the code does not emit:\n" + "\n".join(unknown)


def test_the_agent_metric_families_are_actually_covered(dashboard: dict, rules: dict) -> None:
    """Every edgar_agent_* family should appear somewhere, or it is unobserved in practice."""
    agent_families = {n for n in _registered_family_names() if n.startswith("edgar_agent_")}
    assert agent_families, "no agent metric families registered"

    referenced = {
        name
        for _title, expr in _dashboard_exprs(dashboard) + _rule_exprs(rules)
        for name in _METRIC_REF.findall(expr)
    }
    covered = {
        family
        for family in agent_families
        if any(ref == family or ref.startswith(family) for ref in referenced)
    }
    assert agent_families == covered, (
        "agent metrics emitted but never surfaced in a dashboard or alert: "
        f"{sorted(agent_families - covered)}"
    )


# -- alert rule hygiene ------------------------------------------------------


def test_every_alert_carries_severity_and_a_summary(rules: dict) -> None:
    for group in rules["groups"]:
        for rule in group["rules"]:
            name = rule["alert"]
            assert rule.get("labels", {}).get("severity") in {"critical", "warning", "info"}, (
                f"alert {name!r} needs a severity label"
            )
            assert rule.get("annotations", {}).get("summary"), f"alert {name!r} needs a summary"
            assert rule.get("for"), f"alert {name!r} needs a 'for' duration to avoid flapping"


def test_ratio_alerts_guard_against_a_zero_denominator(rules: dict) -> None:
    """A bare x/y ratio yields NaN with no traffic; every ratio here must clamp."""
    for alert, expr in _rule_exprs(rules):
        if "/" in expr and "rate(" in expr:
            assert "clamp_min" in expr, (
                f"alert {alert!r} divides rates without clamp_min on the denominator"
            )


# -- wiring between the assets ----------------------------------------------


def test_prometheus_scrapes_both_processes() -> None:
    config = yaml.safe_load(PROM_CONFIG.read_text())
    jobs = {job["job_name"] for job in config["scrape_configs"]}
    assert {"edgar-api", "edgar-worker"} <= jobs

    api_job = next(j for j in config["scrape_configs"] if j["job_name"] == "edgar-api")
    # GET /metrics is behind OpsTokenDep; without credentials every agent panel is empty.
    assert api_job["authorization"]["credentials_file"], "api scrape must send the ops token"
    assert "credentials" not in api_job["authorization"], "the ops token must not be committed"

    assert any("rules" in p for p in config["rule_files"]), "alert rules are not loaded"


def test_dashboard_datasource_uids_are_provisioned(dashboard: dict) -> None:
    provisioned = {ds["uid"] for ds in yaml.safe_load(DATASOURCES.read_text())["datasources"]}
    used = {
        target["datasource"]["uid"]
        for panel in dashboard["panels"]
        for target in panel.get("targets", [])
        if isinstance(target.get("datasource"), dict)
    }
    assert used <= provisioned, f"dashboard uses unprovisioned datasources: {sorted(used - provisioned)}"


def test_dashboard_provider_path_matches_the_mounted_directory() -> None:
    provider = yaml.safe_load(DASHBOARD_PROVIDER.read_text())["providers"][0]
    assert provider["options"]["path"] == "/var/lib/grafana/dashboards"


def test_dashboard_panels_fit_the_grid(dashboard: dict) -> None:
    ids = [panel["id"] for panel in dashboard["panels"]]
    assert len(ids) == len(set(ids)), "duplicate panel ids"
    for panel in dashboard["panels"]:
        pos = panel["gridPos"]
        assert pos["x"] + pos["w"] <= 24, f"panel {panel['title']!r} overflows the 24-column grid"


def test_dashboard_uid_is_stable(dashboard: dict) -> None:
    """The uid is the dashboard's identity across re-provisioning; changing it orphans links."""
    assert dashboard["uid"] == "edgar-agent-loop"
