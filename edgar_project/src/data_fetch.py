"""
Retrieve SEC structured data: ticker → CIK, submissions, company facts.
Caches raw JSON under data/raw/.
"""

from __future__ import annotations

import json
import re
import time
from pathlib import Path
from typing import Any

import requests

import config

_SESSION = requests.Session()
_SESSION.headers.update(
    {
        "User-Agent": config.SEC_USER_AGENT,
        "Accept-Encoding": "gzip, deflate",
    }
)
_WWW_SESSION = requests.Session()
_WWW_SESSION.headers.update(
    {
        "User-Agent": config.SEC_USER_AGENT,
        "Accept-Encoding": "gzip, deflate",
    }
)

_TICKER_CACHE: dict[str, int] | None = None


def _cik_to_10digit(cik: int | str) -> str:
    return f"{int(cik):010d}"


def _load_ticker_map() -> dict[str, int]:
    global _TICKER_CACHE
    if _TICKER_CACHE is not None:
        return _TICKER_CACHE
    path = config.DATA_RAW / "company_tickers.json"
    if path.exists():
        with open(path, encoding="utf-8") as f:
            data = json.load(f)
    else:
        r = _WWW_SESSION.get(config.SEC_TICKER_MAP_URL, timeout=60)
        r.raise_for_status()
        data = r.json()
        path.parent.mkdir(parents=True, exist_ok=True)
        with open(path, "w", encoding="utf-8") as f:
            json.dump(data, f)
        time.sleep(0.15)

    # company_tickers.json: {"0": {"cik_str": ..., "ticker": "AAPL", ...}, ...}
    m: dict[str, int] = {}
    for _k, v in data.items():
        if not isinstance(v, dict):
            continue
        t = v.get("ticker")
        c = v.get("cik_str")
        if t and c is not None:
            m[str(t).upper()] = int(c)
    _TICKER_CACHE = m
    return m


def resolve_ticker_to_cik(ticker: str) -> int:
    t = ticker.strip().upper()
    m = _load_ticker_map()
    if t not in m:
        raise ValueError(f"Unknown ticker: {ticker!r} (not in SEC company_tickers.json)")
    return m[t]


def _facts_session_get(url: str) -> requests.Response:
    """data.sec.gov requests: Host must match; use a session scoped to data.sec.gov."""
    r = _SESSION.get(url, timeout=120)
    return r


def _save_json(path: Path, obj: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(obj, f, indent=2)


def get_company_data(ticker: str, *, refresh: bool = False) -> dict[str, Any]:
    """
    Fetch submissions + companyfacts for one ticker. Returns dict with keys:
    cik (int), cik10 (str), submissions (dict), facts (dict).
    Raw JSON is written under data/raw/{TICKER}/.
    """
    cik = resolve_ticker_to_cik(ticker)
    cik10 = _cik_to_10digit(cik)
    sub_url = config.SEC_SUBMISSIONS_URL.format(cik10=cik10)
    facts_url = config.SEC_COMPANYFACTS_URL.format(cik10=cik10)

    tdir = config.DATA_RAW / ticker.upper()
    sub_path = tdir / f"CIK{cik10}_submissions.json"
    facts_path = tdir / f"CIK{cik10}_companyfacts.json"

    if not refresh and sub_path.exists() and facts_path.exists():
        with open(sub_path, encoding="utf-8") as f:
            submissions = json.load(f)
        with open(facts_path, encoding="utf-8") as f:
            facts = json.load(f)
        return {
            "ticker": ticker.upper(),
            "cik": cik,
            "cik10": cik10,
            "submissions": submissions,
            "facts": facts,
        }

    time.sleep(0.2)
    r1 = _facts_session_get(sub_url)
    r1.raise_for_status()
    submissions = r1.json()
    _save_json(sub_path, submissions)

    time.sleep(0.2)
    r2 = _facts_session_get(facts_url)
    r2.raise_for_status()
    facts = r2.json()
    _save_json(facts_path, facts)

    return {
        "ticker": ticker.upper(),
        "cik": cik,
        "cik10": cik10,
        "submissions": submissions,
        "facts": facts,
    }


def safe_filename_ticker(ticker: str) -> str:
    return re.sub(r"[^A-Za-z0-9_-]", "_", ticker.upper())
