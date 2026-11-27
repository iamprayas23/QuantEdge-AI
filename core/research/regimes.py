"""Market Regime & Volatility Analysis

Calculates volatility and trend regimes to evaluate strategy performance
across varying market conditions (e.g. high vol vs low vol, trending vs ranging).
"""
from typing import Dict, Any
import numpy as np
import pandas as pd


def compute_market_regimes(df: pd.DataFrame, period: int = 24) -> pd.DataFrame:
    """
    Computes rolling realized volatility and trend strength (ADX approximation / Directional Index)
    to classify each candle into:
    - Volatility Regime: "low_vol", "medium_vol", "high_vol"
    - Trend Regime: "trending_bull", "trending_bear", "ranging"
    """
    df = df.copy()
    ret = df["close"].pct_change()
    rolling_vol = ret.rolling(period).std() * np.sqrt(252 * 24) * 100.0  # Annualized %

    vol_p33 = rolling_vol.quantile(0.33)
    vol_p66 = rolling_vol.quantile(0.66)

    def classify_vol(v):
        if pd.isna(v):
            return "medium_vol"
        if v < vol_p33:
            return "low_vol"
        elif v > vol_p66:
            return "high_vol"
        return "medium_vol"

    df["realized_vol"] = rolling_vol
    df["vol_regime"] = rolling_vol.apply(classify_vol)

    # 50-period EMA slope for trend
    ema50 = df["close"].ewm(span=50, adjust=False).mean()
    ema200 = df["close"].ewm(span=200, adjust=False).mean()

    def classify_trend(row):
        c = row["close"]
        e50 = ema50.loc[row.name]
        e200 = ema200.loc[row.name]
        if c > e50 > e200:
            return "trending_bull"
        elif c < e50 < e200:
            return "trending_bear"
        else:
            return "ranging"

    df["trend_regime"] = [classify_trend(df.iloc[idx]) for idx in range(len(df))]
    return df


def summarize_regime_distribution(df: pd.DataFrame) -> Dict[str, Any]:
    """
    Summarize percentage time spent in each volatility and trend regime,
    including average realized volatility per regime.
    """
    if "vol_regime" not in df.columns or "trend_regime" not in df.columns:
        df = compute_market_regimes(df)

    n = len(df)
    if n == 0:
        return {"vol_distribution": {}, "trend_distribution": {}, "mean_realized_vol": 0.0}

    vol_counts = df["vol_regime"].value_counts(normalize=True).to_dict()
    trend_counts = df["trend_regime"].value_counts(normalize=True).to_dict()

    vol_dist = {str(k): round(float(v) * 100.0, 1) for k, v in vol_counts.items()}
    trend_dist = {str(k): round(float(v) * 100.0, 1) for k, v in trend_counts.items()}

    mean_vol = float(df["realized_vol"].dropna().mean()) if "realized_vol" in df.columns else 0.0

    return {
        "vol_distribution_pct": vol_dist,
        "trend_distribution_pct": trend_dist,
        "mean_realized_vol_pct": round(mean_vol, 2),
        "total_bars_analyzed": n,
    }


def compute_regime_transition_matrix(df: pd.DataFrame) -> Dict[str, Dict[str, float]]:
    """
    Computes empirical transition probabilities from regime t to regime t+1.
    """
    if "trend_regime" not in df.columns:
        df = compute_market_regimes(df)

    series = df["trend_regime"].dropna()
    if len(series) < 2:
        return {}

    states = ["trending_bull", "trending_bear", "ranging"]
    transitions = {s1: {s2: 0 for s2 in states} for s1 in states}

    s_arr = series.values
    for i in range(len(s_arr) - 1):
        curr_state = s_arr[i]
        next_state = s_arr[i + 1]
        if curr_state in transitions and next_state in transitions[curr_state]:
            transitions[curr_state][next_state] += 1

    prob_matrix = {}
    for s1, counts in transitions.items():
        total = sum(counts.values())
        prob_matrix[s1] = {
            s2: round(count / total, 3) if total > 0 else 0.0
            for s2, count in counts.items()
        }

    return prob_matrix
