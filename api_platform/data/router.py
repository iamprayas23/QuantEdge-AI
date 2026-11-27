"""Market Data Router for Charting & Ingestion"""
from typing import List, Optional
from fastapi import APIRouter, Depends, Query, HTTPException
from sqlalchemy.orm import Session

from infrastructure.database.connection import get_db
from core.data.yfinance_loader import (
    get_or_fetch_ohlcv_bars,
    get_watchlist_quotes,
    get_asset_info,
)

router = APIRouter(prefix="/data", tags=["Market Data"])


@router.get("/bars")
def get_ohlcv_bars(
    symbol: str = Query("XAUUSD", description="Asset symbol"),
    timeframe: str = Query("1H", description="Timeframe"),
    limit: int = Query(500, ge=10, le=5000, description="Max bars to return"),
    refresh: bool = Query(False, description="Force refresh from live provider"),
    db: Session = Depends(get_db),
):
    """
    Fetch real-time OHLCV bars formatted for Lightweight Charts.
    """
    return get_or_fetch_ohlcv_bars(
        db=db,
        symbol=symbol,
        timeframe=timeframe,
        limit=limit,
        force_refresh=refresh,
    )


@router.get("/watchlist")
def get_watchlist(
    db: Session = Depends(get_db),
):
    """
    Fetch real-time watchlist snapshot quotes across Commodities, Crypto, Indexes, and Stocks.
    """
    return get_watchlist_quotes(db)


@router.get("/info/{symbol}")
def get_symbol_info(
    symbol: str,
):
    """
    Fetch descriptive asset metadata (name, exchange, category, precision).
    """
    return get_asset_info(symbol)
