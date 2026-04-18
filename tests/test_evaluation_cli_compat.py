"""CLI compatibility coverage for the evaluation control plane."""

from __future__ import annotations

from uuid import uuid4

import pytest

import edgar_project.cli as cli


def test_evaluate_parser_defaults_to_supported_suite_id() -> None:
    args = cli.build_parser().parse_args(["evaluate"])

    assert args.suite_id == "suite_fixtures_v1"
    assert args.suite is None
    assert args.project_id is None


def test_evaluate_parser_keeps_suite_path_fallback() -> None:
    args = cli.build_parser().parse_args(
        ["evaluate", "--suite", "custom-suite.json"]
    )

    assert str(args.suite) == "custom-suite.json"
    assert args.suite_id == "suite_fixtures_v1"


def test_evaluate_unknown_suite_id_returns_error(capsys) -> None:
    rc = cli.main(["evaluate", "--suite-id", "not-real"])

    assert rc == 2
    assert "Unsupported evaluation suite" in capsys.readouterr().err


def test_evaluate_with_project_id_delegates_to_control_plane(monkeypatch, capsys) -> None:
    captured: dict[str, object] = {}

    class FakeSession:
        def __enter__(self):
            return self

        def __exit__(self, exc_type, exc, tb):
            return None

        def add(self, row):
            self.row = row
            if getattr(row, "id", None) is None:
                row.id = uuid4()

        def flush(self):
            if getattr(self.row, "id", None) is None:
                self.row.id = uuid4()

        def commit(self):
            captured["committed"] = True

        def refresh(self, row):
            captured["refreshed"] = row.id

    fake_session = FakeSession()

    class FakeService:
        def __init__(self, session):
            captured["service_session"] = session

        def start_evaluation_run(self, evaluation_run_id, *, allow_live: bool):
            captured["evaluation_run_id"] = evaluation_run_id
            captured["allow_live"] = allow_live
            fake_session.row.status = cli.EvaluationRunStatus.passed
            return fake_session.row

        def count_case_results(self, evaluation_run_id):
            captured["count_case_results"] = evaluation_run_id
            return 3

    monkeypatch.setattr(cli, "SessionLocal", lambda: fake_session)
    monkeypatch.setattr(cli, "EvaluationControlPlaneService", FakeService)

    project_id = str(uuid4())
    rc = cli.main(["evaluate", "--project-id", project_id, "--suite-id", "suite_fixtures_v1"])

    stdout = capsys.readouterr().out
    assert rc == 0
    assert captured["allow_live"] is False
    assert captured["committed"] is True
    assert "Persisted evaluation run" in stdout
    assert "status:" in stdout
