"""Deterministic evaluation runner for benchmark suites (fixture-first)."""

from __future__ import annotations

import json
import time
from datetime import datetime, timezone
from pathlib import Path

import pandas as pd

from .analytical_checks import run_analytical_findings_checks
from .artifact_checks import validate_produced_artifact_schemas
from .orchestration_checks import validate_orchestration_output
from .orchestration_mocks import patched_mcp_tools
from .rubric import Rubric
from .schemas import (
    BenchmarkCase,
    BenchmarkSuite,
    CaseFailureBrief,
    EvaluationResult,
    EvaluationStatus,
    EvaluationSummary,
    InputMode,
    ValidationDegradationClass,
    ValidationObservation,
    ValueRange,
)
from .summary_report import failure_reason_short, render_markdown_report, summary_json_blob

_PROJECT_ROOT = Path(__file__).resolve().parents[2]
_TRUST_ARTIFACT_KEYS = frozenset({"data_quality_csv", "metric_coverage_summary_csv", "manual_validation_csv"})


class EvaluationRunner:
    """
    Run benchmark cases against the current analytical stack.

    Fixture mode executes local CSV inputs through ``src.*`` helpers and writes
    per-case artifacts under ``<suite.output_dir>/<suite_id>/<case_id>/``.

    ``orchestration_mocked`` runs :func:`edgar_project.orchestration.agent.run_analysis_agent`
    with patched MCP tools (no SEC). Live/hybrid analytical execution is still TODO.
    """

    def __init__(
        self,
        suite: BenchmarkSuite,
        rubric: Rubric | None = None,
        *,
        allow_live_cases: bool = False,
        update_regression_goldens: bool = False,
    ) -> None:
        self.suite = suite
        self.rubric = rubric
        self.allow_live_cases = allow_live_cases
        self.update_regression_goldens = update_regression_goldens
        self.latest_summary: EvaluationSummary | None = None
        self.latest_markdown_path: Path | None = None

    @classmethod
    def from_case_file(
        cls,
        case_file: str | Path,
        rubric: Rubric | None = None,
        *,
        allow_live_cases: bool = False,
        update_regression_goldens: bool = False,
    ) -> EvaluationRunner:
        """Convenience constructor for one-case local runs."""

        case = BenchmarkCase.model_validate_json(Path(case_file).read_text(encoding="utf-8"))
        suite = BenchmarkSuite(suite_id=f"single_case::{case.case_id}", cases=[case])
        return cls(
            suite=suite,
            rubric=rubric,
            allow_live_cases=allow_live_cases,
            update_regression_goldens=update_regression_goldens,
        )

    def run_suite(self) -> list[EvaluationResult]:
        """Execute all cases sequentially and persist a results summary."""

        results = [self.run_case(case) for case in self.suite.cases]
        summary = self._build_summary(results)
        self.latest_summary = summary
        self._write_results(results, summary)
        return results

    def run_case(self, case: BenchmarkCase) -> EvaluationResult:
        """
        Execute one benchmark case.

        Supported: ``fixture`` (analytical stack), ``orchestration_mocked`` (coordinator + mocked MCP).

        TODO: live/hybrid analytical runs via ``src.pipeline_runner`` / real MCP without mocks.
        """

        started = time.perf_counter()
        result = EvaluationResult(
            case_id=case.case_id,
            run_goal=case.input.goal,
            policy=case.input.policy,
            observation=self._build_observation(case),
        )
        failures: list[str] = []
        checks: dict[str, bool] = {}

        try:
            case_dir = self._case_output_dir(case.case_id)
            if case.input.mode in {InputMode.live, InputMode.hybrid}:
                result.status = EvaluationStatus.skipped
                if not self.allow_live_cases:
                    result.message = (
                        "policy skipped: live/hybrid validation requires explicit --allow-live "
                        "opt-in and remains non-merge-blocking by default."
                    )
                else:
                    result.message = (
                        f"skipped: input mode {case.input.mode.value!r} not implemented yet "
                        "(use fixture or orchestration_mocked)."
                    )
                result.checks = checks
                result.metadata = {
                    "input_mode": case.input.mode.value,
                    "tickers": case.input.tickers,
                    "refresh": case.input.refresh,
                    "fixture_id": case.input.fixture_id,
                    "tags": case.tags,
                    "output_dir": str(case_dir),
                }
            elif case.input.mode == InputMode.orchestration_mocked:
                scenario = case.input.orchestration_scenario or case.input.fixture_id
                if not scenario:
                    raise ValueError(
                        "orchestration_mocked requires input.orchestration_scenario or input.fixture_id (scenario id)"
                    )
                from edgar_project.orchestration.agent import run_analysis_agent
                from edgar_project.orchestration.schemas import OrchestrationInput

                goal = (case.input.goal or "").strip() or "find unusual financial changes"
                with patched_mcp_tools(scenario):
                    orch_out = run_analysis_agent(
                        OrchestrationInput(
                            tickers=list(case.input.tickers),
                            analysis_goal=goal,
                            refresh=case.input.refresh,
                        )
                    )
                result.artifacts = dict(orch_out.artifact_paths)
                if orch_out.final_report_path and "report_md" not in result.artifacts:
                    result.artifacts["report_md"] = str(orch_out.final_report_path)

                exp_orch = case.expected_orchestration
                if exp_orch is None:
                    failures.append("orchestration_mocked case is missing expected_orchestration expectations")
                else:
                    oc_checks, oc_fail = validate_orchestration_output(orch_out, exp_orch)
                    checks.update(oc_checks)
                    failures.extend(oc_fail)

                checks.update(
                    self._check_expected_artifacts(case, result.artifacts, failures, paths_must_exist=False)
                )

                unified_findings = None
                anomalies_df = None
                checks.update(
                    self._check_expected_findings(
                        case,
                        unified_findings,
                        anomalies_df,
                        result.artifacts,
                        result,
                        failures,
                    )
                )
                checks.update(self._check_expected_metrics(case, result, unified_findings, failures))

                result.checks = checks
                status = EvaluationStatus.passed if not failures else EvaluationStatus.failed
                if case.expected_artifacts.expected_statuses and status not in case.expected_artifacts.expected_statuses:
                    failures.append(
                        f"run status '{status.value}' not in expected statuses "
                        f"{[s.value for s in case.expected_artifacts.expected_statuses]}"
                    )
                    status = EvaluationStatus.failed
                result.status = status
                result.message = "passed" if status == EvaluationStatus.passed else "; ".join(failures)
                result.qualitative_notes.extend(case.qualitative_expectations)
                if case.expected_findings is not None:
                    result.qualitative_notes.extend(case.expected_findings.qualitative_expectations)
                result.qualitative_notes.extend(case.expected_artifacts.qualitative_checks)
                result.metadata = {
                    "input_mode": case.input.mode.value,
                    "tickers": case.input.tickers,
                    "refresh": case.input.refresh,
                    "fixture_id": case.input.fixture_id,
                    "orchestration_scenario": scenario,
                    "tags": case.tags,
                    "output_dir": str(case_dir),
                    "orchestration": {
                        "status": orch_out.status.value,
                        "message": orch_out.message,
                        "final_report_path": orch_out.final_report_path,
                        "artifact_keys": sorted(orch_out.artifact_paths.keys()),
                        "tool_call_sequence": [t.tool_name for t in orch_out.tool_call_sequence],
                    },
                    "results_json": str((Path(self.suite.output_dir) / f"{self.suite.suite_id}_results.json").resolve()),
                    "summary_json": str((Path(self.suite.output_dir) / f"{self.suite.suite_id}_summary.json").resolve()),
                }
            elif case.input.mode == InputMode.fixture:
                produced = self._execute_case(case, case_dir)
                result.artifacts = produced["artifacts"]
                unified_findings = produced.get("unified_findings")
                anomalies_df = produced.get("anomalies")

                checks.update(self._check_expected_artifacts(case, result.artifacts, failures))
                sf, sc = validate_produced_artifact_schemas(
                    result.artifacts,
                    enforce_schema=case.expected_artifacts.enforce_schema,
                    exempt_keys=frozenset(case.expected_artifacts.schema_exempt_keys),
                    case_id=case.case_id,
                )
                failures.extend(sf)
                checks.update(sc)
                checks.update(
                    self._check_expected_findings(
                        case,
                        unified_findings,
                        anomalies_df,
                        result.artifacts,
                        result,
                        failures,
                    )
                )
                checks.update(self._check_expected_metrics(case, result, unified_findings, failures))
                checks.update(
                    self._check_regression_golden(case, unified_findings, result.artifacts, failures)
                )

                result.checks = checks
                status = EvaluationStatus.passed if not failures else EvaluationStatus.failed
                if case.expected_artifacts.expected_statuses and status not in case.expected_artifacts.expected_statuses:
                    failures.append(
                        f"run status '{status.value}' not in expected statuses "
                        f"{[s.value for s in case.expected_artifacts.expected_statuses]}"
                    )
                    status = EvaluationStatus.failed
                result.status = status
                result.message = "passed" if status == EvaluationStatus.passed else "; ".join(failures)
                result.qualitative_notes.extend(case.qualitative_expectations)
                if case.expected_findings is not None:
                    result.qualitative_notes.extend(case.expected_findings.qualitative_expectations)
                result.qualitative_notes.extend(case.expected_artifacts.qualitative_checks)
                result.metadata = {
                    "input_mode": case.input.mode.value,
                    "tickers": case.input.tickers,
                    "refresh": case.input.refresh,
                    "fixture_id": case.input.fixture_id,
                    "tags": case.tags,
                    "output_dir": str(case_dir),
                    "results_json": str((Path(self.suite.output_dir) / f"{self.suite.suite_id}_results.json").resolve()),
                    "summary_json": str((Path(self.suite.output_dir) / f"{self.suite.suite_id}_summary.json").resolve()),
                }
            else:
                result.status = EvaluationStatus.skipped
                result.message = f"skipped: unknown input mode {case.input.mode.value!r}"
                result.checks = checks
                result.metadata = {
                    "input_mode": case.input.mode.value,
                    "tickers": case.input.tickers,
                    "tags": case.tags,
                    "output_dir": str(case_dir),
                }
        except Exception as exc:  # pragma: no cover - defensive wrapper
            result.status = EvaluationStatus.error
            result.message = (
                f"{case.case_id}: execution error: {type(exc).__name__}: {exc}"
            )
            result.checks = checks
            result.metadata = {
                "input_mode": case.input.mode.value,
                "tickers": case.input.tickers,
                "refresh": case.input.refresh,
                "fixture_id": case.input.fixture_id,
                "tags": case.tags,
            }
        finally:
            result.degradation_class = self._classify_degradation_class(case, result)
            result.elapsed_seconds = round(time.perf_counter() - started, 6)
            # Pandas/numpy may produce numpy.bool_ in checks; JSON serialization requires built-in bool.
            result.checks = {k: bool(v) for k, v in result.checks.items()}
        return result

    def _execute_case(self, case: BenchmarkCase, case_dir: Path) -> dict[str, object]:
        if case.input.mode != InputMode.fixture:
            return {
                "artifacts": {},
                "unified_findings": pd.DataFrame(),
            }

        fixture_features = case.input.fixture_paths.get("features_csv")
        if not fixture_features:
            raise ValueError("fixture mode requires input.fixture_paths.features_csv")
        features_path = self._resolve_path(fixture_features)
        if not features_path.is_file():
            raise FileNotFoundError(f"fixture features CSV not found: {features_path}")

        from src.anomaly import detect_anomalies
        from src.data_quality import compute_data_quality_summary
        from src.findings import build_unified_findings
        from src.manual_validation import candidate_records_from_panel
        from src.metric_coverage import compute_metric_coverage_summary
        from src.peer_signals import compute_peer_signals
        from src.trend_breaks import compute_trend_break_signals

        case_dir.mkdir(parents=True, exist_ok=True)
        features = pd.read_csv(features_path)
        peer_signals = compute_peer_signals(features)
        anomalies = detect_anomalies(features, peer_signals=peer_signals)
        trend_breaks_path = case.input.fixture_paths.get("trend_break_signals_csv")
        if trend_breaks_path:
            trend_breaks = pd.read_csv(self._resolve_path(trend_breaks_path))
        else:
            trend_breaks = compute_trend_break_signals(features)
        unified_findings = build_unified_findings(anomalies, trend_breaks=trend_breaks)
        data_quality = compute_data_quality_summary([], features, features, anomalies)
        metric_coverage = compute_metric_coverage_summary(features)
        manual_validation = candidate_records_from_panel(features)

        artifacts = {
            "features_csv": self._write_csv(case_dir, "features.csv", features),
            "peer_signals_csv": self._write_csv(case_dir, "peer_signals.csv", peer_signals),
            "anomalies_csv": self._write_csv(case_dir, "anomalies.csv", anomalies),
            "trend_break_signals_csv": self._write_csv(case_dir, "trend_break_signals.csv", trend_breaks),
            "unified_findings_csv": self._write_csv(case_dir, "unified_findings.csv", unified_findings),
            "data_quality_csv": self._write_csv(case_dir, "data_quality_summary.csv", data_quality),
            "metric_coverage_summary_csv": self._write_csv(case_dir, "metric_coverage_summary.csv", metric_coverage),
            "manual_validation_csv": self._write_csv(case_dir, "manual_validation.csv", manual_validation),
        }
        return {"artifacts": artifacts, "unified_findings": unified_findings, "anomalies": anomalies}

    def _check_expected_artifacts(
        self,
        case: BenchmarkCase,
        artifacts: dict[str, str],
        failures: list[str],
        *,
        paths_must_exist: bool = True,
    ) -> dict[str, bool]:
        checks: dict[str, bool] = {}
        required = set(case.expected_artifacts.required_keys)
        for item in case.expected_artifacts.items:
            if item.required:
                required.add(item.key)
        for key in sorted(required):
            if key not in artifacts or not str(artifacts[key]).strip():
                ok = False
            elif paths_must_exist:
                ok = Path(artifacts[key]).is_file()
            else:
                ok = True
            checks[f"artifact_present::{key}"] = ok
            if not ok:
                hint = ""
                if key in artifacts and str(artifacts[key]).strip():
                    hint = f" (path {artifacts[key]!r} missing or not a file)"
                failures.append(f"{case.case_id}: missing required artifact: {key}{hint}")

        for item in case.expected_artifacts.items:
            if item.key not in artifacts:
                if item.required:
                    failures.append(f"{case.case_id}: artifact not produced for checks: {item.key}")
                continue
            if not str(artifacts[item.key]).strip():
                if item.required:
                    failures.append(f"{case.case_id}: empty path for artifact: {item.key}")
                continue
            if not paths_must_exist:
                continue
            p = Path(artifacts[item.key])
            if not p.is_file():
                if item.required:
                    failures.append(f"{case.case_id}: artifact path does not exist: {item.key} -> {p}")
                continue
            if p.suffix.lower() == ".csv":
                try:
                    df = pd.read_csv(p)
                except Exception as exc:
                    failures.append(
                        f"{case.case_id}: cannot read {item.key} CSV at {p}: "
                        f"{type(exc).__name__}: {exc}"
                    )
                    continue
                rows = len(df)
                if item.min_rows is not None:
                    ok = rows >= item.min_rows
                    checks[f"artifact_min_rows::{item.key}"] = ok
                    if not ok:
                        failures.append(
                            f"{case.case_id}: {item.key} at {p}: rows {rows} < min_rows {item.min_rows}"
                        )
                if item.max_rows is not None:
                    ok = rows <= item.max_rows
                    checks[f"artifact_max_rows::{item.key}"] = ok
                    if not ok:
                        failures.append(
                            f"{case.case_id}: {item.key} at {p}: rows {rows} > max_rows {item.max_rows}"
                        )
            if item.must_contain:
                txt = p.read_text(encoding="utf-8")
                for needle in item.must_contain:
                    ok = needle in txt
                    checks[f"artifact_contains::{item.key}::{needle}"] = ok
                    if not ok:
                        failures.append(
                            f"{case.case_id}: {item.key} at {p} missing required content: {needle!r}"
                        )
        return checks

    def _check_expected_findings(
        self,
        case: BenchmarkCase,
        unified_findings: pd.DataFrame | None,
        anomalies_df: pd.DataFrame | None,
        artifacts: dict[str, str],
        result: EvaluationResult,
        failures: list[str],
    ) -> dict[str, bool]:
        checks: dict[str, bool] = {}
        exp = case.expected_findings
        if exp is None:
            return checks

        df = unified_findings if unified_findings is not None else pd.DataFrame()
        total = int(len(df))
        missing_finding_type_col = not df.empty and "finding_type" not in df.columns
        if missing_finding_type_col:
            cols = sorted(map(str, df.columns))
            failures.append(
                f"{case.case_id}: unified_findings has rows but no 'finding_type' column "
                f"(columns: {cols})"
            )
        type_counts = (
            df["finding_type"].astype(str).value_counts().to_dict() if "finding_type" in df.columns else {}
        )
        category_counts = self._derive_finding_categories(df, artifacts)
        cat_sorted = dict(sorted(category_counts.items()))
        type_sorted = dict(sorted(type_counts.items()))
        result.finding_counts = {
            "total": total,
            **{f"type::{k}": int(v) for k, v in type_counts.items()},
            **{f"category::{k}": int(v) for k, v in category_counts.items()},
        }

        if exp.total_count is not None:
            ok = self._in_range(total, exp.total_count)
            checks["findings_total_count_in_range"] = ok
            if not ok:
                failures.append(
                    f"{case.case_id}: findings total count {total} outside expected range "
                    f"[{exp.total_count.minimum}, {exp.total_count.maximum}]"
                )

        for t in exp.required_types:
            c = int(type_counts.get(t, 0))
            ok = (c > 0) and not missing_finding_type_col
            checks[f"findings_required_type::{t}"] = ok
            if not ok and not missing_finding_type_col:
                failures.append(
                    f"{case.case_id}: missing required finding type {t!r}; "
                    f"actual type counts: {type_sorted}"
                )
        for t, minimum in exp.by_type_min_counts.items():
            c = int(type_counts.get(t, 0))
            ok = (c >= int(minimum)) and not missing_finding_type_col
            checks[f"findings_type_min::{t}"] = ok
            if not ok and not missing_finding_type_col:
                failures.append(
                    f"{case.case_id}: finding type {t!r} count {c} < expected minimum {minimum}; "
                    f"actual type counts: {type_sorted}"
                )

        for cat in exp.required_categories:
            c = int(category_counts.get(cat, 0))
            ok = c > 0
            checks[f"findings_required_category::{cat}"] = ok
            if not ok:
                failures.append(
                    f"{case.case_id}: missing required finding category {cat!r}; "
                    f"actual category counts: {cat_sorted}"
                )
        for cat, minimum in exp.by_category_min_counts.items():
            c = int(category_counts.get(cat, 0))
            ok = c >= int(minimum)
            checks[f"findings_category_min::{cat}"] = ok
            if not ok:
                failures.append(
                    f"{case.case_id}: finding category {cat!r} count {c} < expected minimum {minimum}; "
                    f"actual category counts: {cat_sorted}"
                )

        aq, afail = run_analytical_findings_checks(
            unified_findings if unified_findings is not None else pd.DataFrame(),
            anomalies_df,
            exp,
            case_id=case.case_id,
        )
        checks.update(aq)
        failures.extend(afail)

        return checks

    def _check_regression_golden(
        self,
        case: BenchmarkCase,
        unified_findings: pd.DataFrame | None,
        artifacts: dict[str, str],
        failures: list[str],
    ) -> dict[str, bool]:
        if case.regression_golden is None:
            return {}
        from .regression_snapshot import (
            build_regression_blob,
            compare_regression_golden,
            dump_sorted_json,
            load_golden,
        )

        actual = build_regression_blob(
            case_id=case.case_id,
            unified_findings=unified_findings,
            artifacts=artifacts,
        )
        path = self._resolve_path(case.regression_golden.golden_json_path)
        checks: dict[str, bool] = {"regression_golden": False}
        if self.update_regression_goldens:
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(dump_sorted_json(actual), encoding="utf-8")
            checks["regression_golden"] = True
            checks["regression_golden_updated"] = True
            return checks
        if not path.is_file():
            failures.append(f"{case.case_id}: regression golden file missing: {path}")
            return checks
        golden = load_golden(path)
        reg_errs = compare_regression_golden(actual, golden, path_label=str(path))
        if reg_errs:
            failures.extend(f"{case.case_id}: {e}" for e in reg_errs)
            return checks
        checks["regression_golden"] = True
        return checks

    def _check_expected_metrics(
        self,
        case: BenchmarkCase,
        result: EvaluationResult,
        unified_findings: pd.DataFrame | None,
        failures: list[str],
    ) -> dict[str, bool]:
        checks: dict[str, bool] = {}
        metrics = {
            "runtime_seconds": float(result.elapsed_seconds or 0.0),
            "findings_total": float(0 if unified_findings is None else len(unified_findings)),
        }
        for name, expected in case.expected_metrics.items():
            actual = metrics.get(name)
            if actual is None:
                checks[f"metric_present::{name}"] = False
                failures.append(f"{case.case_id}: metric {name!r} not available for evaluation")
                continue
            ok = self._in_range(actual, expected)
            checks[f"metric_range::{name}"] = ok
            if not ok:
                failures.append(
                    f"{case.case_id}: metric {name}={actual:.6g} outside expected range "
                    f"[{expected.minimum}, {expected.maximum}]"
                )
        if case.max_runtime_seconds is not None:
            actual = float(result.elapsed_seconds or 0.0)
            ok = actual <= float(case.max_runtime_seconds)
            checks["metric_case_max_runtime_seconds"] = ok
            if not ok:
                failures.append(
                    f"{case.case_id}: runtime {actual:.6g}s exceeded max_runtime_seconds "
                    f"{case.max_runtime_seconds:.6g}s"
                )
        return checks

    def _build_summary(self, results: list[EvaluationResult]) -> EvaluationSummary:
        total_elapsed = round(sum((r.elapsed_seconds or 0.0) for r in results), 6)
        briefs = [
            CaseFailureBrief(
                case_id=r.case_id,
                status=r.status.value,
                reason_short=failure_reason_short(r.message),
            )
            for r in results
            if r.status in {EvaluationStatus.failed, EvaluationStatus.error}
        ]
        return EvaluationSummary(
            suite_id=self.suite.suite_id,
            total_cases=len(results),
            passed_cases=sum(1 for r in results if r.status == EvaluationStatus.passed),
            failed_cases=sum(1 for r in results if r.status == EvaluationStatus.failed),
            skipped_cases=sum(1 for r in results if r.status == EvaluationStatus.skipped),
            error_cases=sum(1 for r in results if r.status == EvaluationStatus.error),
            total_elapsed_seconds=total_elapsed,
            failed_case_briefs=briefs,
            generated_at=datetime.now(timezone.utc).isoformat(),
            notes="edgar_project evaluation benchmark run",
        )

    def _write_results(self, results: list[EvaluationResult], summary: EvaluationSummary) -> None:
        """Persist machine-readable case results and summary."""

        output_dir = Path(self.suite.output_dir)
        output_dir.mkdir(parents=True, exist_ok=True)
        results_payload = {
            "suite_id": self.suite.suite_id,
            "case_count": len(results),
            "results": [r.model_dump(mode="json") for r in results],
        }
        results_file = output_dir / f"{self.suite.suite_id}_results.json"
        results_file.write_text(json.dumps(results_payload, indent=2, sort_keys=True), encoding="utf-8")
        summary_file = output_dir / f"{self.suite.suite_id}_summary.json"
        summary_file.write_text(
            json.dumps(summary_json_blob(summary, results), indent=2, sort_keys=True),
            encoding="utf-8",
        )
        self.latest_markdown_path = None
        if self.suite.write_markdown_report:
            md_path = output_dir / f"{self.suite.suite_id}_report.md"
            md_path.write_text(render_markdown_report(summary, results), encoding="utf-8")
            self.latest_markdown_path = md_path.resolve()

    def _case_output_dir(self, case_id: str) -> Path:
        return Path(self.suite.output_dir) / self.suite.suite_id / case_id

    @staticmethod
    def _write_csv(case_dir: Path, filename: str, df: pd.DataFrame) -> str:
        out = case_dir / filename
        out.parent.mkdir(parents=True, exist_ok=True)
        df.to_csv(out, index=False)
        return str(out.resolve())

    @staticmethod
    def _in_range(value: float, expected: ValueRange) -> bool:
        if expected.minimum is not None and value < expected.minimum:
            return False
        if expected.maximum is not None and value > expected.maximum:
            return False
        return True

    def _build_observation(self, case: BenchmarkCase) -> ValidationObservation | None:
        if case.input.policy is None:
            return None
        return ValidationObservation(
            freshness_window_seconds=case.input.policy.freshness_window_seconds,
        )

    def _classify_degradation_class(
        self,
        case: BenchmarkCase,
        result: EvaluationResult,
    ) -> ValidationDegradationClass:
        if case.input.mode in {InputMode.live, InputMode.hybrid} and not self.allow_live_cases:
            return ValidationDegradationClass.policy_skipped

        upstream_error_code = str(result.metadata.get("upstream_error_code") or "")
        if upstream_error_code in {
            "sec_rate_limited",
            "sec_access_denied",
            "sec_unavailable",
            "upstream_unavailable",
        }:
            return ValidationDegradationClass.upstream_sec_degraded

        observation = result.observation
        if (
            observation is not None
            and observation.source_age_seconds is not None
            and observation.freshness_window_seconds is not None
            and observation.source_age_seconds > observation.freshness_window_seconds
        ):
            return ValidationDegradationClass.stale_source

        if result.status in {EvaluationStatus.failed, EvaluationStatus.error}:
            return ValidationDegradationClass.product_regression

        return ValidationDegradationClass.none

    @staticmethod
    def _derive_finding_categories(
        unified_findings: pd.DataFrame,
        artifacts: dict[str, str],
    ) -> dict[str, int]:
        counts: dict[str, int] = {}
        if unified_findings is not None and not unified_findings.empty:
            for _, row in unified_findings.iterrows():
                source = str(row.get("finding_source", ""))
                ftype = str(row.get("finding_type", ""))
                direction = str(row.get("direction", ""))
                caveats = str(row.get("caveat_codes", "none"))
                if source == "trend_break" or ftype in {"strong_shift", "moderate_shift"}:
                    cat = "trend_break"
                elif ftype == "peer_relative":
                    cat = "peer_outlier"
                elif "deteriorat" in direction or direction in {"low", "down"}:
                    cat = "deterioration"
                elif caveats and caveats != "none":
                    cat = "data_limitations"
                else:
                    cat = "other"
                counts[cat] = counts.get(cat, 0) + 1
                if caveats and caveats != "none":
                    counts["data_limitations"] = counts.get("data_limitations", 0) + 1

        if any(k in artifacts for k in _TRUST_ARTIFACT_KEYS):
            counts["trustworthiness"] = max(1, counts.get("trustworthiness", 0))
        return counts

    @staticmethod
    def _resolve_path(path_value: str | Path) -> Path:
        p = Path(path_value)
        return p if p.is_absolute() else (_PROJECT_ROOT / p)
