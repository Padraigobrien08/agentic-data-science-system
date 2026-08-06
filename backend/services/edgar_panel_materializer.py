"""
Materialize the deterministic EDGAR panel so the investigation loop can run over it.

Without this, an EDGAR-adapter run reaches the loop as a *schema-only* manifest: the
columns are declared but ``frame`` is ``None``, so every EDGAR experiment degrades and
the adaptive loop can never actually analyze SEC data. This module closes that gap by
running the existing deterministic pipeline (panel → features) into the run's workspace
and handing back a CSV path the EDGAR adapter can profile.

No numerical logic lives here. Acquisition and computation stay in ``src`` / the MCP
adapters exactly as the EDGAR pipeline uses them, so both engines compute identically.

The frame written is the **features** frame, not the raw panel: it carries the identity
columns plus ``src.anomaly.FEATURE_COLS``, which is precisely the schema
``agentic.adapters.edgar.EDGARAdapter`` declares and the EDGAR experiment tools require.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Protocol

import structlog

from edgar_project.run_workspace import RunWorkspace

log = structlog.get_logger(__name__)


class EdgarPanelUnavailable(RuntimeError):
    """
    The EDGAR panel could not be materialized (no tickers, no extractable data, or an
    upstream SEC/IO failure).

    Raised rather than silently degrading to a schema-only manifest: an investigation
    that runs with no data reaches a confident-looking "insufficient evidence"
    conclusion, which is indistinguishable from a real analytical finding. Failing
    loudly keeps the run's outcome honest.
    """


@dataclass(frozen=True)
class MaterializedEdgarPanel:
    """Where the materialized features frame landed, plus what went into it."""

    features_csv: Path
    row_count: int
    tickers: list[str]


class EdgarPanelMaterializer(Protocol):
    """Seam so tests can supply a fixture panel instead of reaching the SEC."""

    def materialize(
        self, *, tickers: list[str], workspace: RunWorkspace, refresh: bool
    ) -> MaterializedEdgarPanel: ...


class DeterministicEdgarPanelMaterializer:
    """Runs the real pipeline: SEC companyfacts → panel → features → CSV."""

    def materialize(
        self, *, tickers: list[str], workspace: RunWorkspace, refresh: bool
    ) -> MaterializedEdgarPanel:
        normalized = [t.strip().upper() for t in tickers if t.strip()]
        if not normalized:
            raise EdgarPanelUnavailable(
                "No tickers to analyze: provide dataset.entities or the run's tickers."
            )

        # Imported lazily: this pulls in the pandas/SEC stack, which the agentic path
        # should not require when a non-EDGAR adapter is in use.
        from edgar_project.mcp import adapters as ad

        ad.ensure_sys_path()
        workspace.ensure_directories()

        try:
            panel = ad.build_panel_dataframe(normalized, refresh=refresh)
        except Exception as exc:  # noqa: BLE001 - boundary: upstream SEC/IO failure
            raise EdgarPanelUnavailable(
                f"Could not build the EDGAR panel for {', '.join(normalized)}: {exc}"
            ) from exc

        if panel.empty:
            raise EdgarPanelUnavailable(
                f"No extractable quarterly metrics for {', '.join(normalized)} "
                "(the SEC filings yielded an empty panel)."
            )

        features = ad.compute_features_dataframe(panel)
        features_csv = ad.write_features_csv(features, workspace=workspace)

        log.info(
            "agentic_edgar_panel_materialized",
            tickers=normalized,
            row_count=int(len(features)),
            features_csv=str(features_csv),
            refresh=refresh,
        )
        return MaterializedEdgarPanel(
            features_csv=Path(features_csv),
            row_count=int(len(features)),
            tickers=normalized,
        )
