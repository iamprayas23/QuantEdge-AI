"""Market Data Models and Types"""
from dataclasses import dataclass
from datetime import datetime
from typing import Optional


@dataclass
class Bar:
    symbol: str
    timeframe: str
    timestamp: datetime
    open: float
    high: float
    low: float
    close: float
    volume: float = 0.0
    source: Optional[str] = "historical"
