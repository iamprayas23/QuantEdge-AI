"""Base Strategy Interface"""
from abc import ABC, abstractmethod
from typing import Dict, Any, List, Optional
import pandas as pd
from core.execution.cost_model import CostModel
from core.portfolio.state import TradeRecord, PortfolioState


class BaseStrategy(ABC):
    """
    Abstract Base Class for quantitative trading strategies.
    Strategies must be strictly causal, evaluating completed bars.
    """
    def __init__(self, name: str, params: Optional[Dict[str, Any]] = None):
        self.name = name
        self.params = params or {}

    @abstractmethod
    def run(
        self,
        df: pd.DataFrame,
        cost_model: CostModel,
        initial_capital: float = 10000.0,
        risk_per_trade_pct: float = 0.01,
        symbol: str = "XAUUSD",
    ) -> PortfolioState:
        """
        Execute strategy on the given OHLCV DataFrame and return PortfolioState.
        """
        pass
