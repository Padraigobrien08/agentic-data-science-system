"""
Deterministic statistical helpers (numpy only, no LLM, no scipy).

p-values use a normal / large-sample approximation (documented as an assumption
on every result that reports one), so computation stays dependency-free and
fully deterministic. Effect sizes are the primary evidence-strength inputs.
"""

from __future__ import annotations

import math

import numpy as np

from agentic.domain.statistics import StatisticalSummary


def _finite(arr: np.ndarray) -> np.ndarray:
    return arr[np.isfinite(arr)]


def normal_cdf(z: float) -> float:
    """Standard normal CDF via the error function (deterministic)."""
    return 0.5 * (1.0 + math.erf(z / math.sqrt(2.0)))


def two_sided_p_from_z(z: float) -> float:
    """Two-sided p-value from a z statistic under a normal approximation."""
    return float(max(0.0, min(1.0, 2.0 * (1.0 - normal_cdf(abs(z))))))


def describe(values: np.ndarray) -> dict[str, float]:
    v = _finite(np.asarray(values, dtype=float))
    if v.size == 0:
        return {"count": 0.0}
    return {
        "count": float(v.size),
        "mean": float(np.mean(v)),
        "std": float(np.std(v, ddof=1)) if v.size > 1 else 0.0,
        "min": float(np.min(v)),
        "q25": float(np.quantile(v, 0.25)),
        "median": float(np.median(v)),
        "q75": float(np.quantile(v, 0.75)),
        "max": float(np.max(v)),
    }


def skewness(values: np.ndarray) -> float:
    v = _finite(np.asarray(values, dtype=float))
    n = v.size
    if n < 3:
        return 0.0
    m = np.mean(v)
    s = np.std(v, ddof=0)
    if s == 0:
        return 0.0
    return float(np.mean(((v - m) / s) ** 3))


def zscores(values: np.ndarray) -> np.ndarray:
    v = np.asarray(values, dtype=float)
    finite = _finite(v)
    if finite.size < 2:
        return np.full(v.shape, np.nan)
    m = np.mean(finite)
    s = np.std(finite, ddof=1)
    if s == 0:
        return np.zeros(v.shape)
    return (v - m) / s


def iqr_bounds(values: np.ndarray, k: float = 1.5) -> tuple[float, float]:
    v = _finite(np.asarray(values, dtype=float))
    q1, q3 = np.quantile(v, 0.25), np.quantile(v, 0.75)
    iqr = q3 - q1
    return float(q1 - k * iqr), float(q3 + k * iqr)


def pearson_r(x: np.ndarray, y: np.ndarray) -> float:
    x = np.asarray(x, dtype=float)
    y = np.asarray(y, dtype=float)
    mask = np.isfinite(x) & np.isfinite(y)
    x, y = x[mask], y[mask]
    if x.size < 2 or np.std(x) == 0 or np.std(y) == 0:
        return float("nan")
    return float(np.corrcoef(x, y)[0, 1])


def fisher_ci(r: float, n: int, confidence: float = 0.95) -> tuple[float, float] | None:
    """Confidence interval for Pearson r via the Fisher z-transform."""
    if not math.isfinite(r) or n < 4 or abs(r) >= 1.0:
        return None
    z = math.atanh(r)
    se = 1.0 / math.sqrt(n - 3)
    # two-sided normal critical value
    crit = _z_critical(confidence)
    lo, hi = z - crit * se, z + crit * se
    return math.tanh(lo), math.tanh(hi)


def _z_critical(confidence: float) -> float:
    # Inverse normal for common levels (deterministic table + fallback).
    table = {0.90: 1.6448536269, 0.95: 1.959963985, 0.99: 2.575829304}
    return table.get(round(confidence, 2), 1.959963985)


def ols_simple(x: np.ndarray, y: np.ndarray) -> dict[str, float]:
    """Ordinary least squares y ~ x. Returns slope, intercept, r2, slope_se, n."""
    x = np.asarray(x, dtype=float)
    y = np.asarray(y, dtype=float)
    mask = np.isfinite(x) & np.isfinite(y)
    x, y = x[mask], y[mask]
    n = x.size
    if n < 2 or np.std(x) == 0:
        return {"n": float(n), "slope": float("nan"), "intercept": float("nan"),
                "r2": float("nan"), "slope_se": float("nan"), "resid_std": float("nan")}
    slope, intercept = np.polyfit(x, y, 1)
    y_hat = slope * x + intercept
    resid = y - y_hat
    ss_res = float(np.sum(resid**2))
    ss_tot = float(np.sum((y - np.mean(y)) ** 2))
    r2 = 1.0 - ss_res / ss_tot if ss_tot > 0 else 0.0
    if n > 2:
        s_err = math.sqrt(ss_res / (n - 2))
        sxx = float(np.sum((x - np.mean(x)) ** 2))
        slope_se = s_err / math.sqrt(sxx) if sxx > 0 else float("nan")
    else:
        slope_se = float("nan")
    return {"n": float(n), "slope": float(slope), "intercept": float(intercept),
            "r2": float(r2), "slope_se": float(slope_se),
            "resid_std": float(np.std(resid, ddof=1)) if n > 1 else 0.0}


def cohens_d(a: np.ndarray, b: np.ndarray) -> dict[str, float]:
    a = _finite(np.asarray(a, dtype=float))
    b = _finite(np.asarray(b, dtype=float))
    na, nb = a.size, b.size
    if na < 2 or nb < 2:
        return {"d": float("nan"), "na": float(na), "nb": float(nb), "t": float("nan"), "pooled_sd": float("nan")}
    ma, mb = np.mean(a), np.mean(b)
    va, vb = np.var(a, ddof=1), np.var(b, ddof=1)
    pooled = math.sqrt(((na - 1) * va + (nb - 1) * vb) / (na + nb - 2))
    d = (ma - mb) / pooled if pooled > 0 else 0.0
    se = math.sqrt(va / na + vb / nb)
    t = (ma - mb) / se if se > 0 else 0.0
    return {"d": float(d), "na": float(na), "nb": float(nb), "t": float(t),
            "pooled_sd": float(pooled), "mean_a": float(ma), "mean_b": float(mb)}


def cramers_v(contingency: np.ndarray) -> dict[str, float]:
    """Chi-square statistic and Cramér's V for a contingency table."""
    obs = np.asarray(contingency, dtype=float)
    n = obs.sum()
    if n == 0 or obs.shape[0] < 2 or obs.shape[1] < 2:
        return {"chi2": float("nan"), "v": float("nan"), "n": float(n)}
    row = obs.sum(axis=1, keepdims=True)
    col = obs.sum(axis=0, keepdims=True)
    expected = row @ col / n
    with np.errstate(divide="ignore", invalid="ignore"):
        chi2 = float(np.nansum(np.where(expected > 0, (obs - expected) ** 2 / expected, 0.0)))
    k = min(obs.shape) - 1
    v = math.sqrt(chi2 / (n * k)) if k > 0 and n > 0 else float("nan")
    dof = (obs.shape[0] - 1) * (obs.shape[1] - 1)
    return {"chi2": chi2, "v": float(v), "n": float(n), "dof": float(dof)}


# ---------------------------------------------------------------------------
# Evidence strength inputs -> bounded (strength, reliability, coverage)
# ---------------------------------------------------------------------------

_EFFECT_NORMALIZERS = {
    "cohens_d": 0.8,      # |d| >= 0.8 is a large effect
    "pearson_r": 1.0,
    "cramers_v": 1.0,
    "r2": 1.0,
    "slope": None,        # unnormalizable without scale; fall back to p-value
}


def _clamp(x: float) -> float:
    return float(max(0.0, min(1.0, x)))


def evidence_strength(stats: StatisticalSummary) -> tuple[float, float, float]:
    """
    Deterministically map a statistical summary to bounded evidence scores.

    strength   — from normalized effect size (or 1 - p_value fallback);
    reliability — from sample size, penalized when assumptions/warnings apply;
    coverage    — from the summary's coverage (default 1.0).
    """
    # strength
    strength = 0.5
    if stats.effect_size is not None and stats.effect_size_kind:
        norm = _EFFECT_NORMALIZERS.get(stats.effect_size_kind, 1.0)
        if norm:
            strength = _clamp(abs(stats.effect_size) / norm)
        elif stats.p_value is not None:
            strength = _clamp(1.0 - stats.p_value)
    elif stats.p_value is not None:
        strength = _clamp(1.0 - stats.p_value)

    # reliability from sample size (n/(n+30)), penalized by assumptions/warnings
    n = stats.sample_size or 0
    reliability = n / (n + 30.0) if n > 0 else 0.0
    if stats.warnings:
        reliability *= 0.8
    reliability = _clamp(reliability)

    coverage = _clamp(stats.coverage if stats.coverage is not None else 1.0)
    return strength, reliability, coverage
