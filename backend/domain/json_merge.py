"""Shallow merge helpers for JSON columns stored as dict/list."""


def merge_dict_json(existing: dict | list | None, patch: dict | None) -> dict | None:
    """Deep-enough merge for top-level keys; returns a new dict."""
    if patch is None:
        return existing if isinstance(existing, dict) else None
    if not isinstance(existing, dict):
        return dict(patch)
    return {**existing, **patch}
