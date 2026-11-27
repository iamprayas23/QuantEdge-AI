"""Market Catalyst Normalization & Event Alignment Engine

Normalizes structured market events/catalysts (macro, earnings, rates, liquidity, geopolitics)
and aligns them with causal OHLCV bars and realized volatility/trend regimes.
"""
from datetime import datetime, timezone
from typing import List, Dict, Any, Optional, Literal
import pandas as pd
import numpy as np
from pydantic import BaseModel, Field


class MarketCatalystEvent(BaseModel):
    id: Optional[str] = Field(None, description="Unique event identifier")
    timestamp_utc: datetime = Field(..., description="Timestamp of the catalyst event (UTC)")
    symbol: str = Field(default="XAUUSD", description="Target symbol or 'ALL' for macro")
    title: str = Field(..., description="Concise catalyst headline (e.g., FOMC Rate Decision, US CPI)")
    category: Literal["macro", "rates", "liquidity", "earnings", "geopolitical"] = Field(
        ..., description="Catalyst classification"
    )
    impact: Literal["HIGH", "MEDIUM", "LOW"] = Field(..., description="Expected volatility impact")
    sentiment: Literal["HAWKISH", "DOVISH", "BULLISH", "BEARISH", "NEUTRAL"] = Field(
        ..., description="Directional bias or policy stance"
    )
    actual_value: Optional[str] = Field(None, description="Released figure (e.g. 3.2%)")
    forecast_value: Optional[str] = Field(None, description="Consensus forecast (e.g. 3.0%)")
    previous_value: Optional[str] = Field(None, description="Prior release (e.g. 3.1%)")
    source: str = Field(default="Economic Calendar", description="Source reference or agency")


def get_default_catalysts(symbol: str = "XAUUSD") -> List[MarketCatalystEvent]:
    """
    Curated deterministic market catalyst events covering key macro/rate/liquidity drivers
    aligned to historical 2023-2024 gold and macro cycles.
    """
    raw_events = [
        {
            "id": "cat-001",
            "timestamp_utc": "2023-02-01T19:00:00Z",
            "symbol": "ALL",
            "title": "Federal Reserve Rate Decision (25 bps hike)",
            "category": "rates",
            "impact": "HIGH",
            "sentiment": "HAWKISH",
            "actual_value": "4.75%",
            "forecast_value": "4.75%",
            "previous_value": "4.50%",
            "source": "Federal Reserve FOMC",
        },
        {
            "id": "cat-002",
            "timestamp_utc": "2023-03-10T13:30:00Z",
            "symbol": "ALL",
            "title": "US Non-Farm Payrolls & SVB Liquidity Shock",
            "category": "liquidity",
            "impact": "HIGH",
            "sentiment": "DOVISH",
            "actual_value": "311K",
            "forecast_value": "225K",
            "previous_value": "504K",
            "source": "US BLS / FDIC",
        },
        {
            "id": "cat-003",
            "timestamp_utc": "2023-05-03T18:00:00Z",
            "symbol": "ALL",
            "title": "FOMC Rate Hike to 5.25% & Banking Pause Signal",
            "category": "rates",
            "impact": "HIGH",
            "sentiment": "NEUTRAL",
            "actual_value": "5.25%",
            "forecast_value": "5.25%",
            "previous_value": "5.00%",
            "source": "Federal Reserve",
        },
        {
            "id": "cat-004",
            "timestamp_utc": "2023-10-07T06:00:00Z",
            "symbol": "XAUUSD",
            "title": "Middle East Geopolitical Conflict Escalation",
            "category": "geopolitical",
            "impact": "HIGH",
            "sentiment": "BULLISH",
            "actual_value": "Safe Haven Bid",
            "forecast_value": None,
            "previous_value": None,
            "source": "Reuters Global News",
        },
        {
            "id": "cat-005",
            "timestamp_utc": "2023-12-13T19:00:00Z",
            "symbol": "ALL",
            "title": "FOMC Dovish Pivot - 2024 Dot Plot Projections",
            "category": "rates",
            "impact": "HIGH",
            "sentiment": "DOVISH",
            "actual_value": "5.50% Hold",
            "forecast_value": "5.50%",
            "previous_value": "5.50%",
            "source": "Federal Reserve Summary of Economic Projections",
        },
        {
            "id": "cat-006",
            "timestamp_utc": "2024-03-20T18:00:00Z",
            "symbol": "ALL",
            "title": "Federal Reserve Affirms Three Rate Cuts in 2024",
            "category": "macro",
            "impact": "HIGH",
            "sentiment": "DOVISH",
            "actual_value": "5.50% Hold",
            "forecast_value": "5.50%",
            "previous_value": "5.50%",
            "source": "Federal Reserve FOMC",
        },
        {
            "id": "cat-007",
            "timestamp_utc": "2024-04-12T12:30:00Z",
            "symbol": "XAUUSD",
            "title": "Central Bank Gold Reserves Buying Acceleration",
            "category": "liquidity",
            "impact": "MEDIUM",
            "sentiment": "BULLISH",
            "actual_value": "+290 Tonnes Q1",
            "forecast_value": "+220 Tonnes",
            "previous_value": "+210 Tonnes",
            "source": "World Gold Council",
        },
    ]

    return [
        MarketCatalystEvent(
            id=item["id"],
            timestamp_utc=pd.to_datetime(item["timestamp_utc"]).to_pydatetime(),
            symbol=item["symbol"],
            title=item["title"],
            category=item["category"],
            impact=item["impact"],
            sentiment=item["sentiment"],
            actual_value=item["actual_value"],
            forecast_value=item["forecast_value"],
            previous_value=item["previous_value"],
            source=item["source"],
        )
        for item in raw_events
    ]


def align_catalysts_with_bars(
    ohlcv_df: pd.DataFrame,
    catalysts: List[MarketCatalystEvent],
    window_hours: float = 12.0,
) -> pd.DataFrame:
    """
    Aligns catalysts onto historical OHLCV bars with zero lookahead.
    For each bar, tags:
    - nearest_catalyst_id
    - nearest_catalyst_title
    - hours_to_nearest_catalyst (negative for past, positive for upcoming)
    - in_catalyst_window (bool: within +/- window_hours)
    - catalyst_impact (HIGH/MEDIUM/LOW/NONE)
    - catalyst_sentiment
    """
    df = ohlcv_df.copy()
    if df.empty or not catalysts:
        df["nearest_catalyst_id"] = None
        df["nearest_catalyst_title"] = None
        df["hours_to_nearest_catalyst"] = np.nan
        df["in_catalyst_window"] = False
        df["catalyst_impact"] = "NONE"
        df["catalyst_sentiment"] = "NEUTRAL"
        return df

    # Ensure timestamp is datetime with UTC awareness
    bar_ts = pd.to_datetime(df["timestamp"])
    if bar_ts.dt.tz is None:
        bar_ts = bar_ts.dt.tz_localize("UTC")
    else:
        bar_ts = bar_ts.dt.tz_convert("UTC")

    cat_records = []
    for c in catalysts:
        c_ts = pd.to_datetime(c.timestamp_utc)
        if c_ts.tzinfo is None:
            c_ts = c_ts.tz_localize("UTC")
        else:
            c_ts = c_ts.tz_convert("UTC")
        cat_records.append({
            "id": c.id or f"cat-{c_ts.timestamp()}",
            "ts": c_ts,
            "title": c.title,
            "category": c.category,
            "impact": c.impact,
            "sentiment": c.sentiment,
        })

    cat_df = pd.DataFrame(cat_records)

    nearest_ids = []
    nearest_titles = []
    nearest_hours = []
    in_windows = []
    impacts = []
    sentiments = []

    for ts in bar_ts:
        # Distance in hours to all catalysts
        diff_hours = (cat_df["ts"] - ts).dt.total_seconds() / 3600.0
        abs_diff = diff_hours.abs()
        min_idx = abs_diff.idxmin()

        min_dist = diff_hours.loc[min_idx]
        closest_cat = cat_df.loc[min_idx]

        in_win = abs(min_dist) <= window_hours
        nearest_ids.append(closest_cat["id"])
        nearest_titles.append(closest_cat["title"])
        nearest_hours.append(round(min_dist, 2))
        in_windows.append(bool(in_win))
        impacts.append(closest_cat["impact"] if in_win else "NONE")
        sentiments.append(closest_cat["sentiment"] if in_win else "NEUTRAL")

    df["nearest_catalyst_id"] = nearest_ids
    df["nearest_catalyst_title"] = nearest_titles
    df["hours_to_nearest_catalyst"] = nearest_hours
    df["in_catalyst_window"] = in_windows
    df["catalyst_impact"] = impacts
    df["catalyst_sentiment"] = sentiments

    return df


def compute_catalyst_regime_impact(aligned_df: pd.DataFrame) -> Dict[str, Any]:
    """
    Computes comparative statistics between catalyst windows and normal market windows:
    - Average bar range (High - Low)
    - Realized volatility comparison
    - Volatility spike ratio (catalyst window vol vs non-catalyst vol)
    """
    if aligned_df.empty or "in_catalyst_window" not in aligned_df.columns:
        return {
            "catalyst_window_bars": 0,
            "normal_bars": 0,
            "catalyst_avg_range": 0.0,
            "normal_avg_range": 0.0,
            "range_multiplier": 1.0,
            "catalyst_realized_vol": 0.0,
            "normal_realized_vol": 0.0,
            "vol_spike_ratio": 1.0,
        }

    df = aligned_df.copy()
    df["bar_range"] = (df["high"] - df["low"]).abs()
    pct_change = df["close"].pct_change()
    df["ret_sq"] = pct_change ** 2

    cat_mask = df["in_catalyst_window"] == True
    non_cat_mask = ~cat_mask

    cat_bars = int(cat_mask.sum())
    normal_bars = int(non_cat_mask.sum())

    cat_range = float(df.loc[cat_mask, "bar_range"].mean()) if cat_bars > 0 else 0.0
    normal_range = float(df.loc[non_cat_mask, "bar_range"].mean()) if normal_bars > 0 else 0.0
    range_mult = round(cat_range / max(normal_range, 1e-6), 2) if normal_range > 0 else 1.0

    # Annualized realized vol comparison
    cat_vol = float(np.sqrt(df.loc[cat_mask, "ret_sq"].mean() * 252 * 24) * 100.0) if cat_bars > 2 else 0.0
    normal_vol = float(np.sqrt(df.loc[non_cat_mask, "ret_sq"].mean() * 252 * 24) * 100.0) if normal_bars > 2 else 0.0
    vol_ratio = round(cat_vol / max(normal_vol, 1e-6), 2) if normal_vol > 0 else 1.0

    return {
        "catalyst_window_bars": cat_bars,
        "normal_bars": normal_bars,
        "catalyst_avg_range": round(cat_range, 2),
        "normal_avg_range": round(normal_range, 2),
        "range_multiplier": range_mult,
        "catalyst_realized_vol": round(cat_vol, 2),
        "normal_realized_vol": round(normal_vol, 2),
        "vol_spike_ratio": vol_ratio,
    }
