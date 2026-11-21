"""Unified Deterministic Backtest Engine

Orchestrates data preparation, strategy execution, cost models, and metrics calculation.
"""
from dataclasses import dataclass, asdict
from typing import Dict, Any, Optional, Union, List
from pathlib import Path
import pandas as pd

from core.execution.cost_model import CostModel
from core.portfolio.state import PortfolioState, TradeRecord, EquityPoint
from core.backtesting.metrics import calculate_comprehensive_metrics
from core.backtesting.data_loader import load_and_normalize_ohlcv
from core.backtesting.strategies.registry import get_strategy_class


@dataclass
class BacktestResult:
    strategy_type: str
    symbol: str
    timeframe: str
    parameters: Dict[str, Any]
    cost_model: Dict[str, Any]
    metrics: Dict[str, Any]
    trades: List[TradeRecord]
    equity_series: List[EquityPoint]

    def to_dict(self) -> Dict[str, Any]:
        return {
            "strategy_type": self.strategy_type,
            "symbol": self.symbol,
            "timeframe": self.timeframe,
            "parameters": self.parameters,
            "cost_model": self.cost_model,
            "metrics": self.metrics,
            "trades": [asdict(t) for t in self.trades],
            "equity_series": [
                {
                    "timestamp": pt.timestamp.isoformat(),
                    "equity": pt.equity,
                    "cash": pt.cash,
                    "drawdown": pt.drawdown,
                    "drawdown_pct": pt.drawdown_pct,
                    "returns": pt.returns,
                }
                for pt in self.equity_series
            ],
        }


class BacktestEngine:
    def __init__(
        self,
        cost_model: Optional[CostModel] = None,
        initial_capital: float = 10000.0,
        risk_per_trade_pct: float = 0.01,
        symbol: str = "XAUUSD",
        timeframe: str = "1H",
    ):
        self.cost_model = cost_model or CostModel()
        self.initial_capital = initial_capital
        self.risk_per_trade_pct = risk_per_trade_pct
        self.symbol = symbol
        self.timeframe = timeframe

    def run(
        self,
        strategy_type: str,
        data: Union[str, Path, pd.DataFrame],
        params: Optional[Dict[str, Any]] = None,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
    ) -> BacktestResult:
        """
        Execute deterministic backtest.
        """
        df = load_and_normalize_ohlcv(data)

        # Date filtering
        if start_date:
            df = df[df["timestamp"] >= pd.to_datetime(start_date)]
        if end_date:
            df = df[df["timestamp"] <= pd.to_datetime(end_date)]

        df.reset_index(drop=True, inplace=True)
        if len(df) < 50:
            raise ValueError(f"Insufficient bars for backtesting after filtering: {len(df)} bars found (minimum 50 required)")

        strategy_cls = get_strategy_class(strategy_type)
        strategy = strategy_cls(params=params)

        portfolio_state: PortfolioState = strategy.run(
            df=df,
            cost_model=self.cost_model,
            initial_capital=self.initial_capital,
            risk_per_trade_pct=self.risk_per_trade_pct,
            symbol=self.symbol,
        )

        metrics = calculate_comprehensive_metrics(
            initial_capital=self.initial_capital,
            trades=portfolio_state.trades,
            equity_curve=portfolio_state.equity_curve,
        )

        return BacktestResult(
            strategy_type=strategy_type,
            symbol=self.symbol,
            timeframe=self.timeframe,
            parameters=strategy.params,
            cost_model=asdict(self.cost_model),
            metrics=metrics,
            trades=portfolio_state.trades,
            equity_series=portfolio_state.equity_curve,
        )
