"""Background worker package (DB-backed run execution queue)."""

from __future__ import annotations

from importlib import import_module

__all__ = ["process_next_job", "run_forever"]


def __getattr__(name: str):
    if name in {"process_next_job", "run_forever"}:
        loop = import_module("backend.worker.loop")
        return getattr(loop, name)
    raise AttributeError(name)
