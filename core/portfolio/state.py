"""Portfolio & Trade State Data Structures"""
from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional, List


@dataclass
class TradeRecord:
    trade_id: int
    symbol: str
    side: str                          # "long" or "short"
    entry_time: datetime
    exit_time: datetime
    entry_price: float
    exit_price: float
    size: float
    pnl: float                         # Net PnL after costs
    gross_pnl: float
    return_pct: float
    commission: float
    slippage: float
    exit_reason: str                   # "take_profit", "stop_loss", "signal_exit", "end_of_data"
    bars_held: int


@dataclass
class EquityPoint:
    timestamp: datetime
    equity: float
    cash: float
    drawdown: float
    drawdown_pct: float
    returns: float


@dataclass
class PortfolioState:
    initial_capital: float
    cash: float
    equity: float
    peak_equity: float
    open_position: Optional[dict] = None
    trades: List[TradeRecord] = field(default_factory=list)
    equity_curve: List[EquityPoint] = field(default_factory=list)

    def record_equity(self, ts: datetime, unrealized_pnl: float = 0.0):
        self.equity = self.cash + unrealized_pnl
        if self.equity > self.peak_equity:
            self.peak_equity = self.equity
        dd = self.peak_equity - self.equity
        dd_pct = (dd / self.peak_equity) * 100.0 if self.peak_equity > 0 else 0.0

        prev_equity = self.equity_curve[-1].equity if self.equity_curve else self.initial_capital
        ret = (self.equity - prev_equity) / prev_equity if prev_equity > 0 else 0.0

        self.equity_curve.append(
            EquityPoint(
                timestamp=ts,
                equity=round(self.equity, 2),
                cash=round(self.cash, 2),
                drawdown=round(dd, 2),
                drawdown_pct=round(dd_pct, 4),
                returns=round(ret, 6),
            )
        )
