"""Pytest hooks — set auth-related env before ``backend.config.settings`` is first loaded."""

from __future__ import annotations

import os

# Stable secret for JWT in tests (must be ≥32 chars when debug is false).
os.environ.setdefault(
    "EDGAR_BACKEND_JWT_SECRET",
    "pytest-jwt-secret-minimum-32-characters-long-x",
)
os.environ.setdefault("EDGAR_BACKEND_ALLOW_OPEN_REGISTRATION", "true")
os.environ.setdefault("EDGAR_BACKEND_BOOTSTRAP_ADMIN_TOKEN", "pytest-bootstrap-token")
os.environ.setdefault("EDGAR_BACKEND_OPS_API_TOKEN", "pytest-ops-token")
