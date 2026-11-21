"""Zero-Lookahead Signal Generation & Technical Indicators

Strictly causal indicator computations. In causal swing detection, a swing point at
index (i - window) is only confirmed at index i once window subsequent bars have closed.
"""
from typing import Tuple, List, Optional
import numpy as np
import pandas as pd


def compute_rsi(series: pd.Series, period: int = 14) -> pd.Series:
    """
    Compute Wilder's smoothed RSI (zero lookahead).
    """
    delta = series.diff()
    gain = delta.clip(lower=0.0)
    loss = -delta.clip(upper=0.0)

    # Wilder's exponential moving average
    alpha = 1.0 / period
    avg_gain = gain.ewm(alpha=alpha, adjust=False, min_periods=period).mean()
    avg_loss = loss.ewm(alpha=alpha, adjust=False, min_periods=period).mean()

    rs = avg_gain / avg_loss.replace(0, np.nan)
    rsi = 100.0 - (100.0 / (1.0 + rs))
    return rsi.fillna(50.0)


def compute_atr(df: pd.DataFrame, period: int = 14) -> pd.Series:
    """
    Compute Average True Range (ATR) with Wilder's smoothing.
    """
    high = df["high"]
    low = df["low"]
    prev_close = df["close"].shift(1)

    tr1 = high - low
    tr2 = (high - prev_close).abs()
    tr3 = (low - prev_close).abs()
    tr = pd.concat([tr1, tr2, tr3], axis=1).max(axis=1)

    atr = tr.ewm(alpha=1.0 / period, adjust=False, min_periods=period).mean()
    return atr.bfill()


def detect_causal_pivots(
    df: pd.DataFrame, window: int = 5
) -> Tuple[pd.Series, pd.Series]:
    """
    Detect swing highs and swing lows without lookahead bias.
    
    A bar at index `k = i - window` is declared a swing high/low ONLY when candle `i`
    closes, verifying that all bars in `[k - window, k + window]` are lower (for swing high)
    or higher (for swing low).
    
    The returned series has the value at index `i` representing the confirmed pivot price,
    or NaN if no pivot was confirmed at bar `i`.
    """
    swing_highs = pd.Series(index=df.index, dtype=float)
    swing_lows = pd.Series(index=df.index, dtype=float)

    highs = df["high"].values
    lows = df["low"].values
    n = len(df)

    for i in range(window * 2, n):
        k = i - window  # Candidate bar
        candidate_high = highs[k]
        candidate_low = lows[k]

        is_high = True
        is_low = True

        for j in range(k - window, k + window + 1):
            if j == k:
                continue
            if highs[j] >= candidate_high:
                is_high = False
            if lows[j] <= candidate_low:
                is_low = False

        if is_high:
            swing_highs.iloc[i] = candidate_high
        if is_low:
            swing_lows.iloc[i] = candidate_low

    return swing_highs, swing_lows


def is_bullish_engulfing(df: pd.DataFrame, i: int) -> bool:
    """Check if candle i is bullish engulfing candle i-1."""
    if i < 1:
        return False
    o1, c1 = df["open"].iloc[i - 1], df["close"].iloc[i - 1]
    o2, c2 = df["open"].iloc[i], df["close"].iloc[i]
    return (c1 < o1) and (c2 > o2) and (c2 >= o1) and (o2 <= c1)


def is_bearish_engulfing(df: pd.DataFrame, i: int) -> bool:
    """Check if candle i is bearish engulfing candle i-1."""
    if i < 1:
        return False
    o1, c1 = df["open"].iloc[i - 1], df["close"].iloc[i - 1]
    o2, c2 = df["open"].iloc[i], df["close"].iloc[i]
    return (c1 > o1) and (c2 < o2) and (c2 <= o1) and (o2 >= c1)


def is_bullish_marubozu(df: pd.DataFrame, i: int, threshold: float = 0.70) -> bool:
    """Check if candle i has a strong bullish body exceeding threshold % of range."""
    o = df["open"].iloc[i]
    c = df["close"].iloc[i]
    h = df["high"].iloc[i]
    l = df["low"].iloc[i]
    rng = h - l
    if rng <= 1e-6:
        return False
    body = c - o
    return (body > 0) and ((body / rng) >= threshold)


def is_bearish_marubozu(df: pd.DataFrame, i: int, threshold: float = 0.70) -> bool:
    """Check if candle i has a strong bearish body exceeding threshold % of range."""
    o = df["open"].iloc[i]
    c = df["close"].iloc[i]
    h = df["high"].iloc[i]
    l = df["low"].iloc[i]
    rng = h - l
    if rng <= 1e-6:
        return False
    body = o - c
    return (body > 0) and ((body / rng) >= threshold)
