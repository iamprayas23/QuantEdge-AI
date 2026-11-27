"""yfinance Market Data Provider, Normalizer & PostgreSQL Caching Engine

Provides grounded market data ingestion with:
1. Symbol and timeframe mapping for Yahoo Finance limits.
2. MultiIndex column flattening and timestamp UTC Unix second normalization.
3. Deduplication and strictly ascending sort order.
4. Idempotent PostgreSQL/SQLite persistence via ohlcv_bars table.
5. Deterministic offline/error fallback for zero-downtime charting.
"""
from __future__ import annotations

import logging
import os
from datetime import datetime, timezone, timedelta
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import numpy as np
import pandas as pd
from sqlalchemy import text
from sqlalchemy.orm import Session

from infrastructure.database.models import OHLCVBar

logger = logging.getLogger("quantedge.data.yfinance")

# Default Symbol Map (Common ForexFuturesCryptoIndices to Yahoo Finance tickers)
DEFAULT_SYMBOL_MAP: Dict[str, str] = {
    "XAUUSD": os.getenv("YFINANCE_GOLD_TICKER", "GC=F"),
    "GOLD": os.getenv("YFINANCE_GOLD_TICKER", "GC=F"),
    "XAU/USD": os.getenv("YFINANCE_GOLD_TICKER", "GC=F"),
    "BTCUSD": "BTC-USD",
    "BTC/USD": "BTC-USD",
    "ETHUSD": "ETH-USD",
    "ETH/USD": "ETH-USD",
    "EURUSD": "EURUSD=X",
    "EUR/USD": "EURUSD=X",
    "GBPUSD": "GBPUSD=X",
    "GBP/USD": "GBPUSD=X",
    "USDJPY": "JPY=X",
    "USD/JPY": "JPY=X",
    "USDCAD": "CAD=X",
    "USD/CAD": "CAD=X",
    "AUDUSD": "AUDUSD=X",
    "AUD/USD": "AUDUSD=X",
    "SPX": "^GSPC",
    "SP500": "^GSPC",
    "NDX": "^IXIC",
    "NASDAQ": "^IXIC",
    "DJI": "^DJI",
    "DOW": "^DJI",
    "RUT": "^RUT",
    "VIX": "^VIX",
    "USO": "USO",
    "SLV": "SLV",
    "GLD": "GLD",
    "SPY": "SPY",
    "QQQ": "QQQ",
}

# Timeframe to yfinance interval and safe maximum historical period
TIMEFRAME_CONFIG: Dict[str, Tuple[str, str]] = {
    "1M": ("1m", "7d"),      # Intraday 1m max is 7 days
    "5M": ("5m", "60d"),     # Intraday 5m max is 60 days
    "15M": ("15m", "60d"),   # Intraday 15m max is 60 days
    "30M": ("30m", "60d"),   # Intraday 30m max is 60 days
    "1H": ("1h", "730d"),    # Intraday 1h max is 730 days (~2 years)
    "60M": ("1h", "730d"),
    "4H": ("1h", "730d"),    # Fetched as 1h
    "1D": ("1d", "2y"),
    "D": ("1d", "2y"),
    "1W": ("1wk", "5y"),
    "W": ("1wk", "5y"),
    "1MO": ("1mo", "10y"),
}


def map_symbol(symbol: str) -> str:
    """Map internal symbol format to Yahoo Finance ticker."""
    s_upper = (symbol or "").strip().upper()
    if s_upper in DEFAULT_SYMBOL_MAP:
        return DEFAULT_SYMBOL_MAP[s_upper]

    # Convert slash to dash (e.g., SOL/USD -> SOL-USD)
    if "/" in s_upper:
        s_upper = s_upper.replace("/", "-")

    return s_upper


def map_timeframe(timeframe: str, limit: int = 500) -> Tuple[str, str]:
    """
    Map internal timeframe to Yahoo Finance interval and safe period.
    Respects intraday historical boundaries.
    """
    tf_upper = (timeframe or "1H").strip().upper()
    interval, max_period = TIMEFRAME_CONFIG.get(tf_upper, ("1h", "730d"))

    # For 1h, if limit is small (e.g., 300 bars), 60d is ~1440 bars, fast to download
    if interval == "1h":
        if limit <= 300:
            period = "60d"
        elif limit <= 1000:
            period = "180d"
        else:
            period = "730d"
    elif interval in {"5m", "15m", "30m"}:
        if limit <= 200:
            period = "14d"
        else:
            period = "60d"
    elif interval == "1m":
        period = "7d"
    else:
        period = max_period

    return interval, period


def flatten_yfinance_columns(df: pd.DataFrame) -> pd.DataFrame:
    """
    Flatten and normalize yfinance columns regardless of whether they are
    MultiIndex ('Price', 'Ticker') or standard single-level headers.
    """
    df = df.copy()
    if df.empty:
        return df

    if isinstance(df.columns, pd.MultiIndex):
        new_cols: List[str] = []
        for col in df.columns:
            matched = False
            for part in col:
                part_str = str(part).lower().strip()
                if part_str in {"open", "high", "low", "close", "volume", "adj close"}:
                    new_cols.append("close" if part_str == "adj close" and "close" not in [str(p).lower() for p in col] else part_str)
                    matched = True
                    break
            if not matched:
                new_cols.append("_".join(str(p) for p in col).lower())
        df.columns = new_cols
        # Deduplicate columns if both close and adj close matched
        df = df.loc[:, ~df.columns.duplicated(keep="first")]
    else:
        df.columns = [str(c).lower().strip() for c in df.columns]

    return df


def clean_and_normalize_df(df: pd.DataFrame) -> pd.DataFrame:
    """
    Clean, normalize timestamps to UTC Unix seconds, deduplicate,
    drop NaN rows, and sort chronologically ascending.
    """
    if df.empty:
        return pd.DataFrame(columns=["timestamp", "time", "open", "high", "low", "close", "volume"])

    df = flatten_yfinance_columns(df)

    # 1. Resolve datetime timestamp
    if isinstance(df.index, pd.DatetimeIndex):
        dt_series = df.index
    else:
        dt_col = next((c for c in df.columns if c in {"datetime", "date", "timestamp"}), None)
        if dt_col:
            dt_series = pd.to_datetime(df[dt_col])
        else:
            dt_series = pd.to_datetime(df.index)

    # Convert to timezone-aware UTC
    if dt_series.tz is None:
        dt_series = dt_series.tz_localize("UTC")
    else:
        dt_series = dt_series.tz_convert("UTC")

    df["timestamp"] = dt_series
    df["time"] = [int(ts.timestamp()) for ts in dt_series]

    # 2. Validate price numeric columns
    for price_col in ["open", "high", "low", "close"]:
        if price_col not in df.columns:
            logger.warning(f"Required price column '{price_col}' missing from data.")
            return pd.DataFrame(columns=["timestamp", "time", "open", "high", "low", "close", "volume"])
        df[price_col] = pd.to_numeric(df[price_col], errors="coerce")

    if "volume" not in df.columns:
        df["volume"] = 0.0
    else:
        df["volume"] = pd.to_numeric(df["volume"], errors="coerce").fillna(0.0)

    # 3. Drop rows with NaN in any OHLC or time
    df = df.dropna(subset=["open", "high", "low", "close", "time"])

    # 4. Deduplicate timestamps keeping last
    df = df.drop_duplicates(subset=["time"], keep="last")

    # 5. Sort ascending by time
    df = df.sort_values("time", ascending=True).reset_index(drop=True)

    return df[["timestamp", "time", "open", "high", "low", "close", "volume"]]


def fetch_yfinance_ohlcv(
    symbol: str,
    timeframe: str = "1H",
    limit: int = 500,
    ticker_override: Optional[str] = None,
) -> pd.DataFrame:
    """
    Safely download and normalize OHLCV data from Yahoo Finance.
    Handles network/parsing/rate-limit errors gracefully.
    """
    ticker = ticker_override or map_symbol(symbol)
    interval, period = map_timeframe(timeframe, limit=limit)

    logger.info(f"Fetching yfinance market data: ticker={ticker}, interval={interval}, period={period}")

    try:
        import yfinance as yf
    except ImportError:
        logger.warning("yfinance package is not installed; returning empty DataFrame.")
        return pd.DataFrame(columns=["timestamp", "time", "open", "high", "low", "close", "volume"])

    try:
        raw_df = yf.download(
            tickers=ticker,
            period=period,
            interval=interval,
            progress=False,
            auto_adjust=False,
        )
        if raw_df is None or raw_df.empty:
            logger.warning(f"yfinance returned empty data for {ticker} ({interval}, {period})")
            return pd.DataFrame(columns=["timestamp", "time", "open", "high", "low", "close", "volume"])

        clean_df = clean_and_normalize_df(raw_df)
        if len(clean_df) > limit:
            clean_df = clean_df.tail(limit).reset_index(drop=True)

        return clean_df

    except Exception as exc:
        logger.warning(f"Error fetching data from yfinance for {ticker}: {exc}")
        return pd.DataFrame(columns=["timestamp", "time", "open", "high", "low", "close", "volume"])


def generate_deterministic_fallback_bars(
    symbol: str = "XAUUSD",
    timeframe: str = "1H",
    count: int = 200,
) -> pd.DataFrame:
    """
    Generate deterministic synthetic OHLCV bars for offline development,
    testing, and fallback when network is unreachable.
    """
    sym_upper = (symbol or "").strip().upper()
    if any(k in sym_upper for k in ["XAU", "GOLD"]):
        base_price = 2025.0
        drift = 0.5
        vol = 5.0
    elif "BTC" in sym_upper:
        base_price = 65000.0
        drift = 25.0
        vol = 350.0
    elif "ETH" in sym_upper:
        base_price = 3500.0
        drift = 2.0
        vol = 25.0
    elif "EUR" in sym_upper:
        base_price = 1.0850
        drift = 0.0001
        vol = 0.0015
    else:
        base_price = 150.0
        drift = 0.1
        vol = 1.5

    # Deterministic seed based on symbol name
    seed = sum(ord(c) for c in sym_upper) % 10000
    rng = np.random.RandomState(seed)

    # End timestamp is now truncated to hourly
    now = datetime.now(timezone.utc).replace(minute=0, second=0, microsecond=0)
    timestamps = [now - timedelta(hours=(count - 1 - i)) for i in range(count)]

    rows = []
    curr = base_price
    for ts in timestamps:
        step = rng.normal(0.05 * drift, vol)
        o = curr
        c = max(0.01, o + step)
        h = max(o, c) + abs(rng.normal(0, vol * 0.5))
        l = min(o, c) - abs(rng.normal(0, vol * 0.5))
        v = float(rng.randint(500, 5000))

        rows.append({
            "timestamp": ts,
            "time": int(ts.timestamp()),
            "open": round(float(o), 4),
            "high": round(float(h), 4),
            "low": round(float(l), 4),
            "close": round(float(c), 4),
            "volume": v,
        })
        curr = c

    return pd.DataFrame(rows)


def upsert_ohlcv_bars(
    db: Session,
    df: pd.DataFrame,
    symbol: str,
    timeframe: str,
    source: str = "yfinance",
    batch_size: int = 1000,
) -> int:
    """
    Idempotently batch upsert OHLCV bars into PostgreSQL/SQLite ohlcv_bars table.
    """
    if df.empty:
        return 0

    records = []
    for _, row in df.iterrows():
        ts_val = row["timestamp"]
        if hasattr(ts_val, "to_pydatetime"):
            ts_pydt = ts_val.to_pydatetime()
        elif isinstance(ts_val, datetime):
            ts_pydt = ts_val
        else:
            ts_pydt = datetime.fromtimestamp(int(row["time"]), tz=timezone.utc)

        # Ensure tz-aware UTC
        if ts_pydt.tzinfo is None:
            ts_pydt = ts_pydt.replace(tzinfo=timezone.utc)

        records.append({
            "symbol": symbol.strip().upper(),
            "timeframe": timeframe.strip().upper(),
            "ts_utc": ts_pydt,
            "open": float(row["open"]),
            "high": float(row["high"]),
            "low": float(row["low"]),
            "close": float(row["close"]),
            "volume": float(row["volume"]) if "volume" in row and not pd.isna(row["volume"]) else 0.0,
            "source": source,
        })

    dialect = db.bind.dialect.name
    total_inserted = 0

    for i in range(0, len(records), batch_size):
        chunk = records[i : i + batch_size]
        if dialect == "postgresql":
            sql = text("""
                INSERT INTO ohlcv_bars (symbol, timeframe, ts_utc, open, high, low, close, volume, source)
                VALUES (:symbol, :timeframe, :ts_utc, :open, :high, :low, :close, :volume, :source)
                ON CONFLICT (symbol, timeframe, ts_utc)
                DO UPDATE SET
                    open = EXCLUDED.open,
                    high = EXCLUDED.high,
                    low = EXCLUDED.low,
                    close = EXCLUDED.close,
                    volume = EXCLUDED.volume,
                    source = EXCLUDED.source
            """)
            db.execute(sql, chunk)
        else:
            # SQLite upsert
            sql = text("""
                INSERT INTO ohlcv_bars (symbol, timeframe, ts_utc, open, high, low, close, volume, source)
                VALUES (:symbol, :timeframe, :ts_utc, :open, :high, :low, :close, :volume, :source)
                ON CONFLICT (symbol, timeframe, ts_utc)
                DO UPDATE SET
                    open = excluded.open,
                    high = excluded.high,
                    low = excluded.low,
                    close = excluded.close,
                    volume = excluded.volume,
                    source = excluded.source
            """)
            db.execute(sql, chunk)

        db.commit()
        total_inserted += len(chunk)

    return total_inserted


def get_or_fetch_ohlcv_bars(
    db: Session,
    symbol: str = "XAUUSD",
    timeframe: str = "1H",
    limit: int = 500,
) -> List[Dict[str, Any]]:
    """
    Main entry point for chart bars:
    1. Query PostgreSQL/SQLite ohlcv_bars first.
    2. If fewer than limit bars exist, fetch via yfinance and cache in DB.
    3. If yfinance returns empty (offline, network block, or rate limit),
       check local CSV or fallback synthetic generator.
    4. Return ascending list of bars formatted for Lightweight Charts.
    """
    sym = symbol.strip().upper()
    tf = timeframe.strip().upper()

    # 1. Query existing DB bars
    db_bars = (
        db.query(OHLCVBar)
        .filter(OHLCVBar.symbol == sym, OHLCVBar.timeframe == tf)
        .order_by(OHLCVBar.ts_utc.desc())
        .limit(limit)
        .all()
    )

    if len(db_bars) >= min(limit, 100):
        # Database already has sufficient bars
        db_bars = list(reversed(db_bars))
        return [
            {
                "time": int(b.ts_utc.timestamp()),
                "open": b.open,
                "high": b.high,
                "low": b.low,
                "close": b.close,
                "volume": b.volume,
            }
            for b in db_bars
        ]

    # 2. Fetch from yfinance
    yf_df = fetch_yfinance_ohlcv(symbol=sym, timeframe=tf, limit=limit)
    if not yf_df.empty:
        try:
            upsert_ohlcv_bars(db, yf_df, symbol=sym, timeframe=tf, source="yfinance")
        except Exception as e:
            logger.warning(f"Failed to cache yfinance bars to database: {e}")

        # Return fetched bars
        return [
            {
                "time": int(row["time"]),
                "open": float(row["open"]),
                "high": float(row["high"]),
                "low": float(row["low"]),
                "close": float(row["close"]),
                "volume": float(row["volume"]),
            }
            for _, row in yf_df.iterrows()
        ]

    # 3. Fallback: check local historical CSV for gold if symbol is XAUUSD / GOLD
    if sym in {"XAUUSD", "GOLD", "XAU/USD"}:
        csv_file = Path("data/XAUUSD_1H_merged.csv")
        if csv_file.exists():
            try:
                from core.backtesting.data_loader import load_and_normalize_ohlcv
                csv_df = load_and_normalize_ohlcv(csv_file).tail(limit)
                csv_clean = pd.DataFrame({
                    "timestamp": csv_df["timestamp"],
                    "time": [int(ts.timestamp()) for ts in csv_df["timestamp"]],
                    "open": csv_df["open"],
                    "high": csv_df["high"],
                    "low": csv_df["low"],
                    "close": csv_df["close"],
                    "volume": csv_df["volume"],
                })
                upsert_ohlcv_bars(db, csv_clean, symbol=sym, timeframe=tf, source="local_csv")
                return [
                    {
                        "time": int(row["time"]),
                        "open": float(row["open"]),
                        "high": float(row["high"]),
                        "low": float(row["low"]),
                        "close": float(row["close"]),
                        "volume": float(row["volume"]),
                    }
                    for _, row in csv_clean.iterrows()
                ]
            except Exception as e:
                logger.warning(f"Failed to load local CSV fallback: {e}")

    # 4. If DB has any bars at all, return what we have
    if db_bars:
        db_bars = list(reversed(db_bars))
        return [
            {
                "time": int(b.ts_utc.timestamp()),
                "open": b.open,
                "high": b.high,
                "low": b.low,
                "close": b.close,
                "volume": b.volume,
            }
            for b in db_bars
        ]

    # 5. Deterministic synthetic fallback (ensures chart never breaks with 0 bars)
    synth_df = generate_deterministic_fallback_bars(symbol=sym, timeframe=tf, count=min(limit, 200))
    try:
        upsert_ohlcv_bars(db, synth_df, symbol=sym, timeframe=tf, source="synthetic_fallback")
    except Exception as e:
        logger.warning(f"Failed to cache synthetic bars: {e}")

    return [
        {
            "time": int(row["time"]),
            "open": float(row["open"]),
            "high": float(row["high"]),
            "low": float(row["low"]),
            "close": float(row["close"]),
            "volume": float(row["volume"]),
        }
        for _, row in synth_df.iterrows()
    ]
