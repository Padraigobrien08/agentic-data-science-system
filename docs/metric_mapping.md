# EDGAR pipeline: metric → XBRL mapping

This file is **generated** from `src/metric_mapping.py` — edit that module, then run:

```bash
python -m src.metric_mapping
```

## Global rules

- **Taxonomy**: `us-gaap` (companyfacts path `facts["us-gaap"][<tag>]`).
- **Accepted units**: 'USD' (other unit keys are skipped).
- **Selection**: Facts must use form 10-K or 10-Q, fiscal period fp in {Q1, Q2, Q3, Q4}, and fiscal year fy within the configured lookback window. Per (canonical_metric, fy, fp), the first tag in priority order with at least one qualifying fact wins; if multiple facts remain for the same tag, the row with the latest ``filed`` date wins.

## Metrics (tag priority: 1 = highest)

### `revenue`

Common revenue concepts under ASC 606 and legacy labels; including-assessed-tax variant is lowest priority. Issuers may report under different tags over time—priority order picks one concept per quarter.

| Priority | XBRL tag (local name) |
|----------|------------------------|
| 1 | `Revenues` |
| 2 | `RevenueFromContractWithCustomerExcludingAssessedTax` |
| 3 | `SalesRevenueNet` |
| 4 | `RevenueFromContractWithCustomerIncludingAssessedTax` |

### `net_income`

ProfitLoss is a broader fallback when NetIncomeLoss is absent.

| Priority | XBRL tag (local name) |
|----------|------------------------|
| 1 | `NetIncomeLoss` |
| 2 | `ProfitLoss` |

### `total_assets`

Consolidated assets; point-in-time balance sheet fact matched to fiscal quarter metadata.

| Priority | XBRL tag (local name) |
|----------|------------------------|
| 1 | `Assets` |

### `total_liabilities`

Consolidated liabilities; point-in-time, same period rules as total_assets.

| Priority | XBRL tag (local name) |
|----------|------------------------|
| 1 | `Liabilities` |

### `operating_cash_flow`

Operating cash flow line; in filings, cumulative-YTD vs single-quarter presentation varies by issuer—facts are still keyed by SEC fy/fp in companyfacts.

| Priority | XBRL tag (local name) |
|----------|------------------------|
| 1 | `NetCashProvidedByUsedInOperatingActivities` |

### `current_assets`

Current assets for liquidity ratios.

| Priority | XBRL tag (local name) |
|----------|------------------------|
| 1 | `AssetsCurrent` |

### `current_liabilities`

Current liabilities for liquidity ratios.

| Priority | XBRL tag (local name) |
|----------|------------------------|
| 1 | `LiabilitiesCurrent` |

---

_Single source of truth: `src/metric_mapping.py` (`METRIC_SPECS`)._
