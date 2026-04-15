"""Wave 0 regression seed for backend execution workspace provenance."""

from __future__ import annotations

import pytest


def test_execute_analysis_run_uses_explicit_workspace_paths() -> None:
    expected_context_key = "run_workspace"
    persisted_run_anchor = "analysis_run_id"
    forbidden_repo_root_helper = "chdir_repo_root"

    assert expected_context_key == "run_workspace"
    assert persisted_run_anchor == "analysis_run_id"
    assert forbidden_repo_root_helper == "chdir_repo_root"
    pytest.skip(
        "Wave 0 seed: later plans must persist run_workspace provenance and avoid chdir_repo_root in normal backend execution."
    )
