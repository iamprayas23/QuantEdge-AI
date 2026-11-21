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
