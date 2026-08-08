"""
The committed Grafana dashboard must be renderable by the Grafana version we pin.

An invalid value in `fieldConfig` does not degrade one panel — it throws inside
`applyFieldConfig` and takes the **entire dashboard** down to "An unexpected error happened".
The stack looks healthy, Prometheus has every series, the datasource proxy answers, and the
page still shows nothing.

That is what shipped: all four stat panels declared `color.mode: "text"`, which is not a
Grafana colour mode, so `ops/grafana/dashboards/agent-loop.json` could not render at all in
`prom/grafana:11.3.0`. Nothing caught it because nothing had opened the dashboard with data
behind it.

These checks are static — no Grafana required — so they run in CI alongside everything else.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

_DASHBOARD = (
    Path(__file__).resolve().parents[1] / "ops" / "grafana" / "dashboards" / "agent-loop.json"
)

#: Field colour modes Grafana accepts. Taken from the error Grafana itself raises when given
#: something else, so this list is the product's, not our guess at it.
VALID_COLOR_MODES = frozenset(
    {
        "fixed",
        "shades",
        "thresholds",
        "palette-classic",
        "palette-classic-by-name",
        "continuous-GrYlRd",
        "continuous-RdYlGr",
        "continuous-BlYlRd",
        "continuous-YlRd",
        "continuous-BlPu",
        "continuous-YlBl",
        "continuous-blues",
        "continuous-reds",
        "continuous-greens",
        "continuous-purples",
    }
)

#: Valid `options.colorMode` for stat panels — a different field with a different vocabulary,
#: which is how "text" ended up in the wrong one.
VALID_STAT_COLOR_MODES = frozenset({"value", "background", "background_solid", "none"})


def _dashboard() -> dict:
    return json.loads(_DASHBOARD.read_text(encoding="utf-8"))


def _panels() -> list[dict]:
    return _dashboard().get("panels", [])


def test_the_dashboard_is_valid_json() -> None:
    assert _panels(), "dashboard has no panels"


@pytest.mark.parametrize("panel", _panels(), ids=lambda p: p.get("title", "?"))
def test_every_field_colour_mode_is_one_grafana_accepts(panel) -> None:
    mode = panel.get("fieldConfig", {}).get("defaults", {}).get("color", {}).get("mode")
    if mode is None:
        return

    assert mode in VALID_COLOR_MODES, (
        f"panel {panel.get('title')!r} uses colour mode {mode!r}, which Grafana rejects — "
        "this throws in applyFieldConfig and blanks the whole dashboard, not just this panel"
    )


@pytest.mark.parametrize("panel", _panels(), ids=lambda p: p.get("title", "?"))
def test_stat_panels_use_a_valid_display_colour_mode(panel) -> None:
    if panel.get("type") != "stat":
        return
    mode = panel.get("options", {}).get("colorMode")
    if mode is None:
        return

    assert mode in VALID_STAT_COLOR_MODES, (
        f"panel {panel.get('title')!r} uses options.colorMode={mode!r}"
    )


@pytest.mark.parametrize("panel", _panels(), ids=lambda p: p.get("title", "?"))
def test_every_panel_targets_the_provisioned_datasource(panel) -> None:
    """
    A dashboard referencing a uid the provisioning file does not create renders empty, which
    looks identical to having no data.
    """
    provisioned = (
        Path(__file__).resolve().parents[1]
        / "ops"
        / "grafana"
        / "provisioning"
        / "datasources"
        / "datasources.yml"
    ).read_text(encoding="utf-8")

    for target in panel.get("targets", []):
        uid = target.get("datasource", {}).get("uid")
        if uid:
            assert f"uid: {uid}" in provisioned, (
                f"panel {panel.get('title')!r} targets datasource {uid!r}, "
                "which datasources.yml does not provision"
            )
