"""Market Data Router for Charting & Ingestion"""
from typing import List, Optional
from fastapi import APIRouter, Depends, Query, HTTPException
from sqlalchemy.orm import Session

from infrastructure.database.connection import get_db
from core.data.yfinance_loader import get_or_fetch_ohlcv_bars

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
    1. Checks PostgreSQL/SQLite ohlcv_bars cache.
    2. Fetches via yfinance if missing or insufficient.
    3. Idempotently caches bars into database.
    4. Provides deterministic fallback to CSV/synthetic bars on network disconnect.
    """
    return get_or_fetch_ohlcv_bars(
        db=db,
        symbol=symbol,
        timeframe=timeframe,
        limit=limit,
    )
