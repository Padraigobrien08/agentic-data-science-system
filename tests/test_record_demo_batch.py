"""
The batch recorder's guard rails.

This script spends real money unattended, so the properties worth pinning are the ones that
stop it: the manifest is validated before anything runs, nothing is ever published
implicitly, and the spend ceiling is enforced between runs.
"""

from __future__ import annotations

import textwrap

import pytest

from scripts.record_demo_batch import Recording, _argv_for, load_stack


def _write(tmp_path, body: str):
    path = tmp_path / "stack.toml"
    path.write_text(textwrap.dedent(body), encoding="utf-8")
    return path


# ------------------------------------------------------------------ manifest validation


def test_loads_the_committed_stack() -> None:
    """The real file must stay loadable — it is the input to a paid, unattended run."""
    stack = load_stack()

    assert stack, "the committed stack should not be empty"
    assert all(r.goal.strip() for r in stack)
    assert {r.command for r in stack} <= {"csv", "edgar"}


def test_committed_stack_covers_more_than_one_intent_and_one_outcome() -> None:
    """A set that probes one intent, or aims at one outcome, is a demo rig rather than evidence."""
    stack = load_stack()

    assert len({r.intent for r in stack if r.intent}) >= 4
    # The declining run is the point of the whole showcase; it must be represented.
    assert any("insufficient" in r.expect for r in stack)


def test_committed_stack_ids_are_unique_and_every_entry_explains_itself() -> None:
    stack = load_stack()

    assert len({r.id for r in stack}) == len(stack)
    assert all(r.why.strip() for r in stack), "an entry that cannot justify its cost should not run"


def test_missing_required_field_is_rejected(tmp_path) -> None:
    path = _write(tmp_path, """
        [[recording]]
        id = "a"
        command = "csv"
    """)

    with pytest.raises(SystemExit, match="goal"):
        load_stack(path)


def test_unknown_command_is_rejected(tmp_path) -> None:
    path = _write(tmp_path, """
        [[recording]]
        id = "a"
        command = "sqlite"
        goal = "why"
    """)

    with pytest.raises(SystemExit, match="unknown command"):
        load_stack(path)


def test_duplicate_ids_are_rejected(tmp_path) -> None:
    """Two entries sharing an id would silently collide when publishing by slug."""
    path = _write(tmp_path, """
        [[recording]]
        id = "a"
        command = "csv"
        goal = "one"

        [[recording]]
        id = "a"
        command = "csv"
        goal = "two"
    """)

    with pytest.raises(SystemExit, match="duplicate id"):
        load_stack(path)


def test_empty_stack_is_rejected(tmp_path) -> None:
    with pytest.raises(SystemExit, match="no \\[\\[recording\\]\\]"):
        load_stack(_write(tmp_path, "# nothing here\n"))


# ------------------------------------------------------------------ invocation shape


def test_never_passes_publish() -> None:
    """Publishing is a claim about the system and must stay a reviewed second step."""
    argv = _argv_for(Recording(id="a", command="csv", goal="g", slug="a-slug"), dump=True)

    assert "--publish" not in argv
    assert "a-slug" not in argv


def test_tickers_only_reach_edgar_recordings() -> None:
    csv_argv = _argv_for(Recording(id="a", command="csv", goal="g", tickers="AAPL"), dump=False)
    edgar_argv = _argv_for(Recording(id="b", command="edgar", goal="g", tickers="AAPL"), dump=False)

    assert "--tickers" not in csv_argv
    assert edgar_argv[edgar_argv.index("--tickers") + 1] == "AAPL"


def test_dump_is_opt_out_not_opt_in() -> None:
    assert "--dump" in _argv_for(Recording(id="a", command="csv", goal="g"), dump=True)
    assert "--dump" not in _argv_for(Recording(id="a", command="csv", goal="g"), dump=False)


def test_every_recording_captures_the_chat_turn() -> None:
    assert "--chat" in _argv_for(Recording(id="a", command="csv", goal="g"), dump=False)


# ------------------------------------------------------------------ spend ceiling


def test_batch_stops_once_recorded_spend_passes_the_ceiling(monkeypatch, capsys) -> None:
    """The guard that makes unattended running safe: a runaway cost stops the batch."""
    import scripts.record_demo_batch as batch

    calls: list[list[str]] = []

    def fake_main(argv):
        calls.append(argv)
        return 0

    monkeypatch.setattr(batch.record_demo, "main", fake_main)
    monkeypatch.setattr(batch, "_now", lambda: None)
    monkeypatch.setattr(batch, "_latest_run_id", lambda after: None)
    # Each run reports $4, so the second run pushes past a $5 ceiling.
    monkeypatch.setattr(batch, "_outcome", lambda run_id: ("concluded", "sufficient_evidence", 4.0, 3))
    monkeypatch.setattr(
        batch,
        "load_stack",
        lambda: [Recording(id=f"r{i}", command="csv", goal="g") for i in range(5)],
    )

    batch.main(["--max-spend-usd", "5", "--no-dump"])

    out = capsys.readouterr().out
    assert len(calls) == 2, "should stop once cumulative spend exceeds the ceiling"
    assert "exceeds the $5.00 ceiling" in out
    assert "not run" in out


def test_a_failing_recording_does_not_abandon_the_rest(monkeypatch, capsys) -> None:
    """A failed run was still charged; the remaining goals should still be recorded."""
    import scripts.record_demo_batch as batch

    seen: list[str] = []

    def fake_main(argv):
        goal = argv[argv.index("--goal") + 1]
        seen.append(goal)
        if goal == "boom":
            raise RuntimeError("provider exploded")
        return 0

    monkeypatch.setattr(batch.record_demo, "main", fake_main)
    monkeypatch.setattr(batch, "_now", lambda: None)
    monkeypatch.setattr(batch, "_latest_run_id", lambda after: None)
    monkeypatch.setattr(batch, "_outcome", lambda run_id: ("concluded", "sufficient_evidence", 0.01, 1))
    monkeypatch.setattr(
        batch,
        "load_stack",
        lambda: [
            Recording(id="ok1", command="csv", goal="fine"),
            Recording(id="bad", command="csv", goal="boom"),
            Recording(id="ok2", command="csv", goal="also fine"),
        ],
    )

    batch.main(["--no-dump"])

    assert seen == ["fine", "boom", "also fine"]
    assert "FAILED" in capsys.readouterr().out


def test_summary_flags_a_set_where_nothing_declined(monkeypatch, capsys) -> None:
    import scripts.record_demo_batch as batch

    monkeypatch.setattr(batch.record_demo, "main", lambda argv: 0)
    monkeypatch.setattr(batch, "_now", lambda: None)
    monkeypatch.setattr(batch, "_latest_run_id", lambda after: None)
    monkeypatch.setattr(batch, "_outcome", lambda run_id: ("concluded", "sufficient_evidence", 0.0, 1))
    monkeypatch.setattr(batch, "load_stack", lambda: [Recording(id="a", command="csv", goal="g")])

    batch.main(["--no-dump"])

    assert "nothing declined" in capsys.readouterr().out
