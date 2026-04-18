"""Worker boot regressions around import safety and settings posture."""

from __future__ import annotations

import os
import subprocess
import sys


def test_worker_boot_imports_are_safe(monkeypatch) -> None:
    env = os.environ.copy()
    env["EDGAR_BACKEND_ALLOW_INSECURE_DEV_JWT"] = "true"
    env["EDGAR_BACKEND_BOOTSTRAP_ADMIN_TOKEN"] = "worker-runtime-bootstrap-token"
    env["EDGAR_BACKEND_OPS_API_TOKEN"] = "worker-runtime-ops-token"

    script = """
from backend.config.settings import get_settings

get_settings.cache_clear()

import backend.worker.__main__
import backend.worker.loop
import backend.observability.metrics

assert callable(backend.worker.__main__.main)
assert backend.worker.loop.process_next_job is not None
assert backend.observability.metrics.observe_worker_job is not None
"""

    result = subprocess.run(
        [sys.executable, "-c", script],
        env=env,
        capture_output=True,
        text=True,
        check=False,
    )

    assert result.returncode == 0, result.stderr or result.stdout
