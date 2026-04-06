"""
Derived features from the normalized panel.
"""

from __future__ import annotations

import numpy as np
import pandas as pd


def compute_features(panel: pd.DataFrame) -> pd.DataFrame:
    """
    Adds:
      revenue_growth_qoq, net_margin, current_ratio, debt_to_assets
    """
    df = panel.copy()
    df = df.sort_values(["cik", "period"])
    df["revenue_growth_qoq"] = df.groupby("cik")["revenue"].pct_change()

    df["net_margin"] = np.where(
        df["revenue"].replace(0, np.nan).notna(),
        df["net_income"].astype(float) / df["revenue"].astype(float),
        np.nan,
    )

    ca = df["current_assets"].astype(float)
    cl = df["current_liabilities"].astype(float)
    df["current_ratio"] = np.where(cl.replace(0, np.nan).notna(), ca / cl, np.nan)

    tl = df["total_liabilities"].astype(float)
    ta = df["total_assets"].astype(float)
    df["debt_to_assets"] = np.where(ta.replace(0, np.nan).notna(), tl / ta, np.nan)

    return df.reset_index(drop=True)
