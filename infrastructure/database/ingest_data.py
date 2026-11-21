"""Market Data Ingestion CLI & Historical Store Loader

Idempotently ingests CSV/Parquet OHLCV data into the database ohlcv_bars table,
eliminating duplicates and supporting high-speed batch imports.
"""
import os
import sys
import glob
import argparse
from pathlib import Path
from typing import List, Optional
import pandas as pd
from sqlalchemy import text
from sqlalchemy.orm import Session

# Ensure root is on path
sys.path.insert(0, os.path.abspath("."))

from infrastructure.database.connection import SessionLocal, engine
from infrastructure.database.models import OHLCVBar, Base
from core.backtesting.data_loader import load_and_normalize_ohlcv


def ingest_dataframe(
    db: Session,
    df: pd.DataFrame,
    symbol: str = "XAUUSD",
    timeframe: str = "1H",
    source: str = "raw_csv",
    batch_size: int = 5000,
) -> int:
    """
    Idempotently batch-insert OHLCV bars into ohlcv_bars table.
    Works across PostgreSQL and SQLite.
    """
    total_inserted = 0
    records = []

    for _, row in df.iterrows():
        records.append({
            "symbol": symbol,
            "timeframe": timeframe,
            "ts_utc": row["timestamp"].to_pydatetime() if hasattr(row["timestamp"], "to_pydatetime") else row["timestamp"],
            "open": float(row["open"]),
            "high": float(row["high"]),
            "low": float(row["low"]),
            "close": float(row["close"]),
            "volume": float(row["volume"]) if "volume" in row and not pd.isna(row["volume"]) else 0.0,
            "source": source,
        })

    dialect = db.bind.dialect.name

    for i in range(0, len(records), batch_size):
        chunk = records[i : i + batch_size]
        if dialect == "postgresql":
            # ON CONFLICT DO UPDATE for idempotency
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
            # SQLite compatible upsert
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


def ingest_file_or_dir(
    path: str,
    symbol: str = "XAUUSD",
    timeframe: str = "1H",
    export_parquet: Optional[str] = None,
) -> int:
    """Ingest a CSV file, a glob pattern, or raw monthly directory."""
    target_path = Path(path)
    files: List[Path] = []

    if "*" in path:
        files = [Path(f) for f in sorted(glob.glob(path))]
    elif target_path.is_dir():
        files = sorted(list(target_path.glob("*.csv")))
    elif target_path.is_file():
        files = [target_path]
    else:
        # Check if glob matches
        matched = glob.glob(path)
        if matched:
            files = [Path(f) for f in sorted(matched)]
        else:
            raise FileNotFoundError(f"No files matched path: {path}")

    print(f"Found {len(files)} files to ingest for {symbol} ({timeframe})...")

    dfs = []
    for f in files:
        print(f"Loading {f.name}...")
        df_part = load_and_normalize_ohlcv(f)
        dfs.append(df_part)

    if not dfs:
        print("No valid data loaded.")
        return 0

    full_df = pd.concat(dfs, ignore_index=True)
    full_df.drop_duplicates(subset=["timestamp"], inplace=True)
    full_df.sort_values("timestamp", inplace=True)
    full_df.reset_index(drop=True, inplace=True)

    print(f"Aggregated {len(full_df)} total clean bars from {full_df['timestamp'].min()} to {full_df['timestamp'].max()}")

    if export_parquet:
        out_pq = Path(export_parquet)
        out_pq.parent.mkdir(parents=True, exist_ok=True)
        try:
            full_df.to_parquet(out_pq, index=False)
            print(f"Exported Parquet dump to: {out_pq}")
        except Exception as e:
            print(f"Parquet export skipped (optional dependency not installed): {e}")

    # Ensure tables exist
    Base.metadata.create_all(bind=engine)

    db = SessionLocal()
    try:
        inserted = ingest_dataframe(
            db=db,
            df=full_df,
            symbol=symbol,
            timeframe=timeframe,
            source=f"batch_{len(files)}_files",
        )
        print(f"Successfully ingested {inserted} bars into ohlcv_bars table.")
        return inserted
    finally:
        db.close()


def main():
    parser = argparse.ArgumentParser(description="QuantEdge Market Data Ingestor")
    parser.add_argument("--source", type=str, default="data/XAUUSD_1H_merged.csv", help="Path to CSV, glob, or dir")
    parser.add_argument("--symbol", type=str, default="XAUUSD", help="Ticker symbol")
    parser.add_argument("--timeframe", type=str, default="1H", help="Timeframe (1H, 1D, etc.)")
    parser.add_argument("--export-parquet", type=str, default="data/XAUUSD_1H.parquet", help="Optional Parquet dump destination")

    args = parser.parse_args()
    ingest_file_or_dir(
        path=args.source,
        symbol=args.symbol,
        timeframe=args.timeframe,
        export_parquet=args.export_parquet,
    )


if __name__ == "__main__":
    main()
