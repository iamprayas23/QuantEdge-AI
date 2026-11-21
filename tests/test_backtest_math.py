"""Unit Tests for Backtesting Mathematics, Cost Models & Zero Lookahead"""
import pytest
import numpy as np
import pandas as pd
from datetime import datetime, timedelta

from core.execution.cost_model import CostModel
from core.risk.position_sizer import calculate_position_size
from core.portfolio.state import TradeRecord, EquityPoint
from core.backtesting.metrics import calculate_comprehensive_metrics
from core.backtesting.signals import compute_rsi, compute_atr, detect_causal_pivots
from core.backtesting.engine import BacktestEngine


def test_cost_model_adjustments():
    cm = CostModel(slippage_bps=2.0, commission_per_trade=1.5, spread_pips=0.4, point_value=1.0)
    raw_price = 2000.0

    # Long entry: ask + slippage
    # Spread delta = 0.4 / 2 = 0.2
    # Slippage delta = 2000.0 * (2 / 10000) = 0.4
    long_entry = cm.calculate_entry_price(raw_price, "long")
    assert long_entry == pytest.approx(2000.6, abs=1e-4)

    # Short entry: bid - slippage
    short_entry = cm.calculate_entry_price(raw_price, "short")
    assert short_entry == pytest.approx(1999.4, abs=1e-4)

    # Long exit: bid - slippage
    long_exit = cm.calculate_exit_price(raw_price, "long")
    assert long_exit == pytest.approx(1999.4, abs=1e-4)

    # Commission calculation
    comm = cm.calculate_commission(price=2000.0, size=2.0)
    assert comm == 1.5


def test_position_sizing():
    capital = 10000.0
    risk_pct = 0.01  # $100 risk
    entry = 2000.0
    sl = 1990.0      # $10 sl distance
    size = calculate_position_size(capital, risk_pct, entry, sl, point_value=1.0)
    # Risk = 100 / 10 = 10 units
    assert size == 10.0


def test_zero_lookahead_causal_pivots():
    """Verify that causal pivots never look forward beyond confirmed window."""
    dates = [datetime(2023, 1, 1) + timedelta(hours=i) for i in range(30)]
    # Create price with a spike at index 10
    highs = [100.0] * 30
    highs[10] = 120.0  # Pivot high at index 10

    lows = [95.0] * 30
    closes = [98.0] * 30
    opens = [97.0] * 30

    df = pd.DataFrame({"timestamp": dates, "open": opens, "high": highs, "low": lows, "close": closes})

    window = 3
    sh, sl = detect_causal_pivots(df, window=window)

    # The pivot occurred at index 10. With window=3, it can ONLY be confirmed at index 10 + 3 = 13!
    # Indices 0 to 12 must NOT be confirmed as a pivot high at that time
    for i in range(13):
        assert pd.isna(sh.iloc[i])

    # Index 13 should confirm the pivot
    assert sh.iloc[13] == 120.0


def test_metrics_calculation():
    initial_capital = 10000.0
    t1 = datetime(2023, 1, 1)
    t2 = datetime(2023, 1, 2)
    t3 = datetime(2023, 1, 3)

    trades = [
        TradeRecord(1, "XAUUSD", "long", t1, t2, 1900.0, 1920.0, 1.0, 19.0, 20.0, 1.0, 1.0, 0.0, "tp", 5),
        TradeRecord(2, "XAUUSD", "long", t2, t3, 1920.0, 1910.0, 1.0, -11.0, -10.0, -0.5, 1.0, 0.0, "sl", 3),
    ]

    eq_curve = [
        EquityPoint(t1, 10000.0, 10000.0, 0.0, 0.0, 0.0),
        EquityPoint(t2, 10019.0, 10019.0, 0.0, 0.0, 0.0019),
        EquityPoint(t3, 10008.0, 10008.0, 11.0, 0.1098, -0.0011),
    ]

    metrics = calculate_comprehensive_metrics(initial_capital, trades, eq_curve)
    assert metrics["final_equity"] == 10008.0
    assert metrics["total_trades"] == 2
    assert metrics["winning_trades"] == 1
    assert metrics["losing_trades"] == 1
    assert metrics["win_rate"] == 50.0
    assert metrics["profit_factor"] == pytest.approx(19.0 / 11.0, abs=1e-2)
