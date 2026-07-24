"""
Input-agnostic agentic data-science core.

This package generalizes the platform beyond EDGAR: typed, serializable domain
entities (:mod:`agentic.domain`) plus an input-adapter seam (:mod:`agentic.adapters`)
that lets any data source be described as a dataset manifest and investigated
with the same hypothesis/experiment/evidence machinery.

EDGAR remains a first-party adapter and reference template; the deterministic
computation layer under ``src`` is untouched.
"""

from __future__ import annotations

__all__: list[str] = []
