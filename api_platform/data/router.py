"""Market Data Router for Charting & Ingestion"""
from typing import List, Optional
from datetime import datetime
from pathlib import Path
from fastapi import APIRouter, Depends, Query, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy import desc

from infrastructure.database.connection import get_db
from infrastructure.database.models import OHLCVBar
from core.backtesting.data_loader import load_and_normalize_ohlcv

router = APIRouter(prefix="/data", tags=["Market Data"])


@router.get("/bars")
def get_ohlcv_bars(
    symbol: str = Query("XAUUSD", description="Asset symbol"),
    timeframe: str = Query("1H", description="Timeframe"),
    limit: int = Query(500, ge=10, le=5000, description="Max bars to return"),
    db: Session = Depends(get_db),
):
    """
    Fetch historical OHLCV bars formatted for Lightweight Charts.
    """
    bars = (
        db.query(OHLCVBar)
        .filter(OHLCVBar.symbol == symbol, OHLCVBar.timeframe == timeframe)
        .order_by(OHLCVBar.ts_utc.desc())
        .limit(limit)
        .all()
    )

    if bars:
        bars = list(reversed(bars))
        return [
            {
                "time": int(b.ts_utc.timestamp()),
                "open": b.open,
                "high": b.high,
                "low": b.low,
                "close": b.close,
                "volume": b.volume,
            }
            for b in bars
        ]

    # Fallback to local CSV if DB not ingested yet
    csv_file = Path("data/XAUUSD_1H_merged.csv")
    if csv_file.exists():
        df = load_and_normalize_ohlcv(csv_file).tail(limit)
        return [
            {
                "time": int(row["timestamp"].timestamp()),
                "open": float(row["open"]),
                "high": float(row["high"]),
                "low": float(row["low"]),
                "close": float(row["close"]),
                "volume": float(row["volume"]),
            }
            for _, row in df.iterrows()
        ]

    return []
