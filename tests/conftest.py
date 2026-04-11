"""Pytest hooks — set auth-related env before ``backend.config.settings`` is first loaded."""

from __future__ import annotations

import os

# Stable secret for JWT in tests (must be ≥32 chars when debug is false).
os.environ.setdefault(
    "EDGAR_BACKEND_JWT_SECRET",
    "pytest-jwt-secret-minimum-32-characters-long-x",
)
