"""
Orchestration MCP server — the investigation platform as MCP tools.

This is the counterpart to ``edgar_project/mcp/server.py``. That server exposes the
deterministic EDGAR *computation*; this one exposes the *platform*: commissioning an
investigation, reading its hypotheses and evidence, and fetching the artifacts behind them.
Together they let an external agent both compute and reason over persisted, auditable runs.

Every tool is a call to the ``/v1`` API (see :mod:`backend.mcp.client`), so authentication,
owner scoping, and the API's 404-for-unauthorized semantics apply unchanged — the MCP server
grants no access the token does not already have.

Run from the repository root::

    EDGAR_MCP_TOKEN=... python -m backend.mcp

Responses use the same :class:`~edgar_project.mcp.schemas.ToolResponseEnvelope` contract as
the EDGAR server, so a client sees one response shape across both.
"""

from __future__ import annotations

import argparse
import logging
import os
from typing import Any

from mcp.server.fastmcp import FastMCP

from backend.mcp.auth import TokenUnavailable, TransportMode, resolve_token, set_transport_mode
from backend.mcp.client import PlatformApiError, PlatformClient, PlatformNotConfigured
from backend.mcp.rate_limit import McpRateLimited, get_limiter
from edgar_project.mcp.schemas import (
    CODE_INTERNAL,
    CODE_VALIDATION,
    ErrorInfo,
    ToolResponseEnvelope,
    ToolStatus,
)

logger = logging.getLogger(__name__)

mcp = FastMCP("edgar-investigation-platform")

CODE_API = "PLATFORM_API_ERROR"
CODE_NOT_CONFIGURED = "PLATFORM_NOT_CONFIGURED"
CODE_RATE_LIMITED = "PLATFORM_RATE_LIMITED"

#: Cap list responses so a tool call never floods an agent's context.
MAX_LIST_LIMIT = 100


def _client() -> PlatformClient:
    """
    A client authenticated as **the current caller**.

    Under HTTP transport the token comes from this request's ``Authorization`` header, so a
    hosted server acts only ever as the calling user; under stdio it comes from the
    environment. See :mod:`backend.mcp.auth`.
    """
    client = PlatformClient.from_env()
    client.token = resolve_token()
    return client


def _ok(message: str, data: dict[str, Any], artifacts: dict[str, Any] | None = None) -> dict[str, Any]:
    return ToolResponseEnvelope(
        status=ToolStatus.success, message=message, data=data, artifacts=artifacts or {}
    ).model_dump(mode="json")


def _error(code: str, message: str, *, detail: str | None = None, http_status: int | None = None) -> dict[str, Any]:
    return ToolResponseEnvelope(
        status=ToolStatus.error,
        message=message,
        errors=[ErrorInfo(code=code, message=message, detail=detail, http_status=http_status)],
    ).model_dump(mode="json")


def _rate_limit_key() -> str | None:
    """
    The caller's token, for rate-limit keying only — never logged or stored raw.

    Resolution failures are swallowed: an unresolvable caller still gets *a* budget (the
    anonymous one) rather than an unlimited one. Refusing here instead would turn the limiter
    into a second authentication path, which is not its job.
    """
    try:
        return resolve_token()
    except Exception:  # noqa: BLE001 — no token is a valid state; it buckets as anonymous
        return None


def _guarded(action: str, fn) -> dict[str, Any]:
    """
    Run one API-backed action, mapping failures onto the envelope contract.

    Errors never cross the MCP boundary as exceptions: an agent gets a typed envelope it
    can reason about instead of a transport-level failure.

    The rate-limit check lives here rather than on each tool, so a tool added later is bounded
    by construction — the same reason the engine gate sits inside ``select_run_engine``.
    """
    try:
        get_limiter().check(_rate_limit_key())
    except McpRateLimited as exc:
        return _error(
            CODE_RATE_LIMITED,
            str(exc),
            detail=f"retry_after_seconds={exc.retry_after_seconds}",
            http_status=429,
        )
    try:
        return fn()
    except (TokenUnavailable, PlatformNotConfigured) as exc:
        return _error(CODE_NOT_CONFIGURED, str(exc))
    except PlatformApiError as exc:
        # 404 covers both "missing" and "not yours" by design; relay it without speculating.
        return _error(
            CODE_API, f"{action} failed: {exc.detail}", detail=exc.detail, http_status=exc.status_code
        )
    except Exception as exc:  # noqa: BLE001 - boundary: never raise across MCP
        logger.exception("%s failed", action)
        return _error(CODE_INTERNAL, f"{action} failed", detail=f"{type(exc).__name__}: {exc}")


# ---------------------------------------------------------------------------
# Commissioning work
# ---------------------------------------------------------------------------


@mcp.tool()
def start_investigation(
    project_id: str,
    goal: str,
    csv_text: str | None = None,
    records: list[dict] | None = None,
    name: str = "dataset",
    time_field: str | None = None,
    entity_id_fields: list[str] | None = None,
    async_execution: bool = False,
) -> dict[str, Any]:
    """Commission an adaptive investigation over a dataset and run it.

    Supply the data either as ``csv_text`` or as ``records`` (a list of row objects).
    ``time_field`` and ``entity_id_fields`` are structural hints: which column orders the
    data in time, and which identify an entity. Set ``async_execution`` to queue the run for
    the background worker instead of waiting for it.

    Returns the analysis run id and investigation id; poll ``get_investigation`` for progress.
    """
    if not csv_text and not records:
        return _error(CODE_VALIDATION, "Provide either csv_text or records.")
    if csv_text and records:
        return _error(CODE_VALIDATION, "Provide csv_text or records, not both.")

    dataset: dict[str, Any] = {
        "format": "csv" if csv_text else "records",
        "name": name,
        "entity_id_fields": entity_id_fields or [],
    }
    if csv_text:
        dataset["csv_text"] = csv_text
    else:
        dataset["records"] = records
    if time_field:
        dataset["time_field"] = time_field

    payload = {
        "project_id": project_id,
        "goal": goal,
        "dataset": dataset,
        "async_execution": async_execution,
    }

    def _run() -> dict[str, Any]:
        body = _client().create_investigation(payload)
        return _ok("Investigation started.", body)

    return _guarded("start_investigation", _run)


# ---------------------------------------------------------------------------
# Reading investigations
# ---------------------------------------------------------------------------


@mcp.tool()
def list_investigations(
    project_id: str | None = None,
    analysis_run_id: str | None = None,
    limit: int = 20,
    offset: int = 0,
) -> dict[str, Any]:
    """List investigations visible to the token, newest first.

    Optionally scope to one project, or resolve the investigation belonging to a run.
    """
    bounded = max(1, min(int(limit), MAX_LIST_LIMIT))

    def _run() -> dict[str, Any]:
        rows = _client().list_investigations(
            project_id=project_id, analysis_run_id=analysis_run_id, limit=bounded, offset=offset
        )
        return _ok(
            f"{len(rows)} investigation(s).",
            {"count": len(rows), "limit": bounded, "offset": offset, "investigations": rows},
        )

    return _guarded("list_investigations", _run)


@mcp.tool()
def get_investigation(investigation_id: str) -> dict[str, Any]:
    """Full investigation state: hypotheses, evidence, experiments, decisions, conclusion.

    This is the largest response the server produces. Prefer ``get_conclusion``,
    ``list_hypotheses``, or ``get_evidence`` when you only need one slice.
    """

    def _run() -> dict[str, Any]:
        return _ok("Investigation detail.", _client().get_investigation(investigation_id))

    return _guarded("get_investigation", _run)


@mcp.tool()
def get_conclusion(investigation_id: str) -> dict[str, Any]:
    """The investigation's answer: conclusion, disposition, confidence, and why it stopped.

    A disposition of ``insufficient_evidence`` is a valid, honest outcome — it means the
    evidence did not support a conclusion, not that the run failed.
    """

    def _run() -> dict[str, Any]:
        detail = _client().get_investigation(investigation_id)
        return _ok(
            "Investigation conclusion.",
            {
                "investigation_id": investigation_id,
                "status": detail.get("status"),
                "objective": detail.get("objective"),
                "conclusion": detail.get("conclusion"),
                "termination": detail.get("termination"),
                "confidence": detail.get("confidence"),
                "counts": detail.get("counts"),
            },
        )

    return _guarded("get_conclusion", _run)


@mcp.tool()
def list_hypotheses(investigation_id: str) -> dict[str, Any]:
    """The investigation's hypotheses with their status and confidence.

    Status tells you how the evidence landed: ``supported``, ``weakened``, ``rejected``,
    or still ``active`` / ``unresolved``.
    """

    def _run() -> dict[str, Any]:
        detail = _client().get_investigation(investigation_id)
        hypotheses = detail.get("hypotheses") or []
        return _ok(
            f"{len(hypotheses)} hypothesis/es.",
            {"investigation_id": investigation_id, "count": len(hypotheses), "hypotheses": hypotheses},
        )

    return _guarded("list_hypotheses", _run)


@mcp.tool()
def get_evidence(investigation_id: str, hypothesis_id: str | None = None) -> dict[str, Any]:
    """Evidence recorded by the investigation, optionally filtered to one hypothesis.

    Each item carries a direction relative to the hypothesis it bears on (``supports``,
    ``refutes``, ``neutral``) plus strength, reliability, and coverage.
    """

    def _run() -> dict[str, Any]:
        detail = _client().get_investigation(investigation_id)
        evidence = detail.get("evidence") or []
        if hypothesis_id:
            evidence = [e for e in evidence if hypothesis_id in (e.get("hypothesis_ids") or [])]
        return _ok(
            f"{len(evidence)} evidence item(s).",
            {
                "investigation_id": investigation_id,
                "hypothesis_id": hypothesis_id,
                "count": len(evidence),
                "evidence": evidence,
            },
        )

    return _guarded("get_evidence", _run)


# ---------------------------------------------------------------------------
# Runs and artifacts
# ---------------------------------------------------------------------------


@mcp.tool()
def get_run_status(analysis_run_id: str) -> dict[str, Any]:
    """Current status of an analysis run — poll this after an async investigation."""

    def _run() -> dict[str, Any]:
        return _ok("Run status.", _client().get_run_status(analysis_run_id))

    return _guarded("get_run_status", _run)


@mcp.tool()
def list_artifacts(analysis_run_id: str) -> dict[str, Any]:
    """Artifacts produced by a run: tables, charts, and reports the analysis rests on.

    Fetch one with ``get_artifact_preview``, or read the ``artifact://{id}`` resource.
    """

    def _run() -> dict[str, Any]:
        rows = _client().list_run_artifacts(analysis_run_id)
        return _ok(
            f"{len(rows)} artifact(s).",
            {"analysis_run_id": analysis_run_id, "count": len(rows), "artifacts": rows},
            artifacts={str(a.get("id")): a.get("name") for a in rows if a.get("id")},
        )

    return _guarded("list_artifacts", _run)


@mcp.tool()
def get_artifact_preview(artifact_id: str) -> dict[str, Any]:
    """A bounded text preview of one artifact (markdown, CSV, JSON, or text).

    Bounded on the server side, so this is safe to call on large artifacts.
    """

    def _run() -> dict[str, Any]:
        return _ok("Artifact preview.", _client().get_artifact_preview(artifact_id))

    return _guarded("get_artifact_preview", _run)


# ---------------------------------------------------------------------------
# Resources
# ---------------------------------------------------------------------------


@mcp.resource("artifact://{artifact_id}")
def artifact_resource(artifact_id: str) -> str:
    """One artifact's preview text, addressable as an MCP resource.

    Resources are the natural fit for evidence an agent wants to *read* rather than call,
    so an artifact can be attached to a conversation by URI.
    """
    try:
        preview = _client().get_artifact_preview(artifact_id)
    except (PlatformApiError, PlatformNotConfigured, TokenUnavailable) as exc:
        return f"Artifact unavailable: {exc}"
    content = preview.get("content")
    if isinstance(content, str):
        return content
    return str(preview)


@mcp.resource("investigation://{investigation_id}/conclusion")
def conclusion_resource(investigation_id: str) -> str:
    """An investigation's conclusion as readable text, addressable by URI."""
    try:
        detail = _client().get_investigation(investigation_id)
    except (PlatformApiError, PlatformNotConfigured, TokenUnavailable) as exc:
        return f"Investigation unavailable: {exc}"
    lines = [
        f"# Investigation {investigation_id}",
        f"Objective: {detail.get('objective') or '(none recorded)'}",
        f"Status: {detail.get('status')}",
        f"Conclusion: {detail.get('conclusion') or '(none yet)'}",
    ]
    termination = detail.get("termination")
    if termination:
        lines.append(f"Stopped because: {termination}")
    return "\n".join(lines)


def main(argv: list[str] | None = None) -> None:
    """
    Entry point for both transports.

    ``stdio`` (default) is the per-user subprocess model an MCP host launches directly.
    ``streamable-http`` hosts the server for many callers, each authenticating with their own
    bearer token; the environment token is not used in that mode (see :mod:`backend.mcp.auth`).
    """
    parser = argparse.ArgumentParser(prog="python -m backend.mcp", description=__doc__)
    parser.add_argument(
        "--transport",
        choices=["stdio", "streamable-http", "sse"],
        default=os.getenv("EDGAR_MCP_TRANSPORT", "stdio"),
        help="stdio (default) for a per-user subprocess; streamable-http to host the server.",
    )
    parser.add_argument("--host", default=os.getenv("EDGAR_MCP_HOST", "127.0.0.1"),
                        help="Bind address for HTTP transports (default: loopback).")
    parser.add_argument("--port", type=int, default=int(os.getenv("EDGAR_MCP_PORT", "8765")),
                        help="Bind port for HTTP transports.")
    args = parser.parse_args(argv)

    logging.basicConfig(level=logging.INFO)

    if args.transport == "stdio":
        set_transport_mode(TransportMode.stdio)
        logger.info("Starting investigation-platform MCP server (stdio)")
        mcp.run()
        return

    # Hosted: every request authenticates itself, so the process holds no ambient identity.
    set_transport_mode(TransportMode.http)
    mcp.settings.host = args.host
    mcp.settings.port = args.port
    if os.getenv("EDGAR_MCP_TOKEN"):
        logger.warning(
            "EDGAR_MCP_TOKEN is set but ignored under %s: hosted requests must each carry "
            "their own Authorization: Bearer header.",
            args.transport,
        )
    logger.info(
        "Starting investigation-platform MCP server (%s) on %s:%s%s",
        args.transport, args.host, args.port, mcp.settings.streamable_http_path,
    )
    mcp.run(transport=args.transport)


if __name__ == "__main__":
    main()
