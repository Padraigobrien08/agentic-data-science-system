"""Project configuration — paths, tickers, SEC client settings."""

from pathlib import Path

# Repo root = parent of this file
PROJECT_ROOT = Path(__file__).resolve().parent

# --- Data layout (see data/README.md) ---------------------------------------
# raw/        — SEC JSON cache (live fetch).
# runs/       — durable per-run processed/artifacts workspaces.
# processed/  — legacy/dev-only shared Phase 1 processed outputs.
# artifacts/  — legacy/dev-only shared Phase 1 pipeline outputs.
# evaluation/ — benchmark JSON + per-case dirs (not main pipeline; suite-driven).

DATA_RAW = PROJECT_ROOT / "data" / "raw"
DATA_RUNS = PROJECT_ROOT / "data" / "runs"
DATA_PROCESSED = PROJECT_ROOT / "data" / "processed"
DATA_ARTIFACTS = PROJECT_ROOT / "data" / "artifacts"

for _p in (DATA_RAW, DATA_RUNS, DATA_PROCESSED, DATA_ARTIFACTS):
    _p.mkdir(parents=True, exist_ok=True)

# V1 default input (max 5 companies)
DEFAULT_TICKERS = ["AAPL", "MSFT", "NVDA"]

# Analysis window
YEARS_LOOKBACK = 5

# SEC requires a descriptive User-Agent with a reachable contact (see sec.gov/os/accessing-edgar-data).
SEC_USER_AGENT = "EDGAR-Anomaly-Detector/1.0 (contact: dev@example.com)"

SEC_TICKER_MAP_URL = "https://www.sec.gov/files/company_tickers.json"
SEC_SUBMISSIONS_URL = "https://data.sec.gov/submissions/CIK{cik10}.json"
SEC_COMPANYFACTS_URL = "https://data.sec.gov/api/xbrl/companyfacts/CIK{cik10}.json"

# Anomaly detection
ZSCORE_WINDOW = 4
ZSCORE_THRESHOLD = 2.5

# Panel caveat: flag CIKs with fewer than this many (cik, period) rows after the revenue filter.
CAVEAT_MIN_PERIODS_PER_CIK = 4
