"""Skeleton runner for deterministic evaluation and benchmark execution."""

from __future__ import annotations

import json
import time
from datetime import datetime, timezone
from pathlib import Path

import pandas as pd

from .rubric import Rubric
from .schemas import (
    BenchmarkCase,
    BenchmarkSuite,
    EvaluationResult,
    EvaluationStatus,
    EvaluationSummary,
    InputMode,
    ValueRange,
)

_PROJECT_ROOT = Path(__file__).resolve().parents[2]
_TRUST_ARTIFACT_KEYS = frozenset({"data_quality_csv", "metric_coverage_summary_csv", "manual_validation_csv"})


class EvaluationRunner:
    """
    Lightweight runner that will orchestrate benchmark cases.

    This scaffold intentionally avoids wiring production execution until
    benchmark cases and fixtures are finalized.
    """

    def __init__(self, suite: BenchmarkSuite, rubric: Rubric | None = None) -> None:
        self.suite = suite
        self.rubric = rubric
        self.latest_summary: EvaluationSummary | None = None

    @classmethod
    def from_case_file(cls, case_file: str | Path, rubric: Rubric | None = None) -> EvaluationRunner:
        """Convenience constructor for one-case local runs."""

        case = BenchmarkCase.model_validate_json(Path(case_file).read_text(encoding="utf-8"))
        suite = BenchmarkSuite(suite_id=f"single_case::{case.case_id}", cases=[case])
        return cls(suite=suite, rubric=rubric)

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

        Fixture mode is fully supported in this runner.

        TODO: invoke existing deterministic pipeline path via `src.pipeline_runner` for live mode.
        TODO: invoke MCP tool wrapper path via `edgar_project.mcp.tools` when required.
        TODO: invoke orchestration path via `edgar_project.orchestration.agent` for E2E scenarios.
        """

        started = time.perf_counter()
        result = EvaluationResult(case_id=case.case_id, run_goal=case.input.goal)
        failures: list[str] = []
        checks: dict[str, bool] = {}

        try:
            case_dir = self._case_output_dir(case.case_id)
            produced = self._execute_case(case, case_dir)
            result.artifacts = produced["artifacts"]
            unified_findings = produced.get("unified_findings")

            checks.update(self._check_expected_artifacts(case, result.artifacts, failures))
            checks.update(self._check_expected_findings(case, unified_findings, result.artifacts, result, failures))
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
                "tags": case.tags,
                "output_dir": str(case_dir),
            }
        except Exception as exc:  # pragma: no cover - defensive wrapper
            result.status = EvaluationStatus.error
            result.message = f"execution error: {type(exc).__name__}: {exc}"
            result.checks = checks
            result.metadata = {
                "input_mode": case.input.mode.value,
                "tickers": case.input.tickers,
                "refresh": case.input.refresh,
                "fixture_id": case.input.fixture_id,
                "tags": case.tags,
            }
        finally:
            result.elapsed_seconds = round(time.perf_counter() - started, 6)
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
        return {"artifacts": artifacts, "unified_findings": unified_findings}

    def _check_expected_artifacts(
        self,
        case: BenchmarkCase,
        artifacts: dict[str, str],
        failures: list[str],
    ) -> dict[str, bool]:
        checks: dict[str, bool] = {}
        required = set(case.expected_artifacts.required_keys)
        for item in case.expected_artifacts.items:
            if item.required:
                required.add(item.key)
        for key in sorted(required):
            ok = key in artifacts and Path(artifacts[key]).is_file()
            checks[f"artifact_present::{key}"] = ok
            if not ok:
                failures.append(f"missing required artifact: {key}")

        for item in case.expected_artifacts.items:
            if item.key not in artifacts:
                if item.required:
                    failures.append(f"artifact not produced for checks: {item.key}")
                continue
            p = Path(artifacts[item.key])
            if not p.is_file():
                if item.required:
                    failures.append(f"artifact path does not exist: {item.key} -> {p}")
                continue
            if p.suffix.lower() == ".csv":
                df = pd.read_csv(p)
                rows = len(df)
                if item.min_rows is not None:
                    ok = rows >= item.min_rows
                    checks[f"artifact_min_rows::{item.key}"] = ok
                    if not ok:
                        failures.append(f"{item.key} rows {rows} < min_rows {item.min_rows}")
                if item.max_rows is not None:
                    ok = rows <= item.max_rows
                    checks[f"artifact_max_rows::{item.key}"] = ok
                    if not ok:
                        failures.append(f"{item.key} rows {rows} > max_rows {item.max_rows}")
            if item.must_contain:
                txt = p.read_text(encoding="utf-8")
                for needle in item.must_contain:
                    ok = needle in txt
                    checks[f"artifact_contains::{item.key}::{needle}"] = ok
                    if not ok:
                        failures.append(f"{item.key} missing required content: {needle!r}")
        return checks

    def _check_expected_findings(
        self,
        case: BenchmarkCase,
        unified_findings: pd.DataFrame | None,
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
        type_counts = df["finding_type"].astype(str).value_counts().to_dict() if "finding_type" in df.columns else {}
        category_counts = self._derive_finding_categories(df, artifacts)
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
                    f"findings total count {total} outside expected range "
                    f"[{exp.total_count.minimum}, {exp.total_count.maximum}]"
                )

        for t in exp.required_types:
            c = int(type_counts.get(t, 0))
            ok = c > 0
            checks[f"findings_required_type::{t}"] = ok
            if not ok:
                failures.append(f"missing required finding type: {t}")
        for t, minimum in exp.by_type_min_counts.items():
            c = int(type_counts.get(t, 0))
            ok = c >= int(minimum)
            checks[f"findings_type_min::{t}"] = ok
            if not ok:
                failures.append(f"finding type {t} count {c} < expected minimum {minimum}")

        for cat in exp.required_categories:
            c = int(category_counts.get(cat, 0))
            ok = c > 0
            checks[f"findings_required_category::{cat}"] = ok
            if not ok:
                failures.append(f"missing required finding category: {cat}")
        for cat, minimum in exp.by_category_min_counts.items():
            c = int(category_counts.get(cat, 0))
            ok = c >= int(minimum)
            checks[f"findings_category_min::{cat}"] = ok
            if not ok:
                failures.append(f"finding category {cat} count {c} < expected minimum {minimum}")

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
                failures.append(f"metric {name!r} not available for evaluation")
                continue
            ok = self._in_range(actual, expected)
            checks[f"metric_range::{name}"] = ok
            if not ok:
                failures.append(
                    f"metric {name}={actual:.6g} outside expected range "
                    f"[{expected.minimum}, {expected.maximum}]"
                )
        if case.max_runtime_seconds is not None:
            actual = float(result.elapsed_seconds or 0.0)
            ok = actual <= float(case.max_runtime_seconds)
            checks["metric_case_max_runtime_seconds"] = ok
            if not ok:
                failures.append(
                    f"runtime {actual:.6g}s exceeded max_runtime_seconds {case.max_runtime_seconds:.6g}s"
                )
        return checks

    def _build_summary(self, results: list[EvaluationResult]) -> EvaluationSummary:
        return EvaluationSummary(
            suite_id=self.suite.suite_id,
            total_cases=len(results),
            passed_cases=sum(1 for r in results if r.status == EvaluationStatus.passed),
            failed_cases=sum(1 for r in results if r.status == EvaluationStatus.failed),
            skipped_cases=sum(1 for r in results if r.status == EvaluationStatus.skipped),
            error_cases=sum(1 for r in results if r.status == EvaluationStatus.error),
            generated_at=datetime.now(timezone.utc).isoformat(),
            notes="fixture-first deterministic evaluation summary",
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
        summary_file.write_text(json.dumps(summary.model_dump(mode="json"), indent=2, sort_keys=True), encoding="utf-8")

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
