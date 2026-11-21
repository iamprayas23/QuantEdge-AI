"""Backtesting API Schemas"""
from typing import Optional, Dict, Any, List
from uuid import UUID
from datetime import datetime
from pydantic import BaseModel, Field


class BacktestLaunchRequest(BaseModel):
    strategy_version_id: UUID = Field(..., description="Target immutable strategy version ID")
    symbol: str = Field("XAUUSD", description="Asset symbol")
    timeframe: str = Field("1H", description="Bar timeframe")
    start_date: Optional[str] = Field(None, description="Start date (YYYY-MM-DD)")
    end_date: Optional[str] = Field(None, description="End date (YYYY-MM-DD)")
    initial_capital: float = Field(10000.0, ge=100.0, description="Starting cash capital")
    slippage_bps: float = Field(1.0, ge=0.0, description="Execution slippage in basis points")
    commission_per_trade: float = Field(0.0, ge=0.0, description="Fixed commission per order")
    spread_pips: float = Field(0.0, ge=0.0, description="Bid-ask spread delta")
    risk_per_trade_pct: float = Field(0.01, ge=0.0001, le=0.1, description="Risk percentage per trade")


class BacktestJobResponse(BaseModel):
    job_id: UUID
    status: str
    message: str


class BacktestTradeItem(BaseModel):
    trade_number: int
    symbol: str
    side: str
    entry_ts: datetime
    exit_ts: datetime
    entry_price: float
    exit_price: float
    size: float
    pnl: float
    gross_pnl: float
    return_pct: float
    commission: float
    slippage: float
    exit_reason: str
    bars_held: int

    class Config:
        from_attributes = True


class EquityPointItem(BaseModel):
    ts: datetime
    equity: float
    cash: float
    drawdown: float
    drawdown_pct: float
    returns: float

    class Config:
        from_attributes = True


class BacktestRunResponse(BaseModel):
    id: UUID
    strategy_version_id: UUID
    workspace_id: UUID
    status: str
    config_hash: str
    symbol: str
    timeframe: str
    start_ts: Optional[datetime]
    end_ts: Optional[datetime]
    initial_capital: float
    final_equity: Optional[float]
    slippage_bps: float
    commission_per_trade: float
    spread_pips: float
    total_return: Optional[float]
    cagr: Optional[float]
    sharpe_ratio: Optional[float]
    sortino_ratio: Optional[float]
    calmar_ratio: Optional[float]
    max_drawdown: Optional[float]
    win_rate: Optional[float]
    profit_factor: Optional[float]
    total_trades: Optional[int]
    winning_trades: Optional[int]
    losing_trades: Optional[int]
    error_message: Optional[str]
    created_at: datetime
    completed_at: Optional[datetime]

    class Config:
        from_attributes = True


class BacktestTearsheetResponse(BaseModel):
    run: BacktestRunResponse
    strategy_name: str
    strategy_type: str
    parameters: Dict[str, Any]
    metrics: Dict[str, Any]
    recent_trades: List[BacktestTradeItem] = []
    equity_curve: List[EquityPointItem] = []
