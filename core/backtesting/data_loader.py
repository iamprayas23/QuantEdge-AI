"""Data Loader and Normalizer for Quantitative Strategies"""
from pathlib import Path
from typing import Union
import pandas as pd


def load_and_normalize_ohlcv(data_source: Union[str, Path, pd.DataFrame]) -> pd.DataFrame:
    """
    Load data from CSV, Parquet, or pandas DataFrame and normalize into a standardized OHLCV structure:
    columns: ['timestamp', 'open', 'high', 'low', 'close', 'volume']
    sorted chronologically, with duplicates dropped and zero lookahead integrity.
    """
    if isinstance(data_source, (str, Path)):
        p = Path(data_source)
        if not p.exists():
            raise FileNotFoundError(f"Data source file does not exist: {p}")
        if p.suffix in (".parquet", ".pq"):
            df = pd.read_parquet(p)
        else:
            df = pd.read_csv(p)
    elif isinstance(data_source, pd.DataFrame):
        df = data_source.copy()
    else:
        raise ValueError(f"Unsupported data source type: {type(data_source)}")

    # Normalize column names to lowercase
    df.columns = [str(c).strip().lower() for c in df.columns]

    # Map timestamp variants
    ts_col = None
    for cand in ["timestamp", "ts_utc", "utc", "datetime", "date", "time"]:
        if cand in df.columns:
            ts_col = cand
            break

    if ts_col is None:
        if isinstance(df.index, pd.DatetimeIndex):
            df["timestamp"] = df.index
            ts_col = "timestamp"
        else:
            raise ValueError("Data must contain a timestamp column (timestamp, ts_utc, datetime, date)")

    if ts_col != "timestamp":
        df["timestamp"] = df[ts_col]

    # Clean up string timestamps if format has " UTC"
    if df["timestamp"].dtype == object:
        df["timestamp"] = df["timestamp"].astype(str).str.replace(" UTC", "", regex=False)
        # Try standard parsing or european format
        try:
            df["timestamp"] = pd.to_datetime(df["timestamp"])
        except Exception:
            df["timestamp"] = pd.to_datetime(df["timestamp"], format="%d.%m.%Y %H:%M:%S.%f")
    else:
        df["timestamp"] = pd.to_datetime(df["timestamp"])

    required_cols = ["open", "high", "low", "close"]
    for col in required_cols:
        if col not in df.columns:
            raise ValueError(f"Missing required price column: {col}")
        df[col] = pd.to_numeric(df[col], errors="coerce")

    if "volume" not in df.columns:
        df["volume"] = 0.0
    else:
        df["volume"] = pd.to_numeric(df["volume"], errors="coerce").fillna(0.0)

    # Clean NaNs, drop duplicates, sort
    df.dropna(subset=["timestamp", "open", "high", "low", "close"], inplace=True)
    df.drop_duplicates(subset=["timestamp"], inplace=True)
    df.sort_values("timestamp", inplace=True)
    df.reset_index(drop=True, inplace=True)

    return df[["timestamp", "open", "high", "low", "close", "volume"]]
