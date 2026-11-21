"""Quantitative Performance Metrics & Tearsheet Analytics

Deterministic calculations for Sharpe, Sortino, Calmar, Drawdown, Profit Factor,
Win Rate, and trade statistics.
"""
from typing import List, Dict, Any
import numpy as np
import pandas as pd
from core.portfolio.state import TradeRecord, EquityPoint


def calculate_comprehensive_metrics(
    initial_capital: float,
    trades: List[TradeRecord],
    equity_curve: List[EquityPoint],
    periods_per_year: int = 252 * 24,  # Default for 1H data (forex/crypto)
) -> Dict[str, Any]:
    """
    Compute full institutional-grade tearsheet metrics from equity points and trade logs.
    """
    if not equity_curve:
        return {
            "initial_capital": initial_capital,
            "final_equity": initial_capital,
            "total_return": 0.0,
            "cagr": 0.0,
            "sharpe_ratio": 0.0,
            "sortino_ratio": 0.0,
            "calmar_ratio": 0.0,
            "max_drawdown": 0.0,
            "max_drawdown_dollars": 0.0,
            "max_drawdown_duration_bars": 0,
            "win_rate": 0.0,
            "profit_factor": 0.0,
            "total_trades": 0,
            "winning_trades": 0,
            "losing_trades": 0,
            "avg_trade_pnl": 0.0,
            "avg_win": 0.0,
            "avg_loss": 0.0,
            "payoff_ratio": 0.0,
            "total_commission": 0.0,
            "total_slippage": 0.0,
            "avg_bars_held": 0.0,
        }

    final_equity = equity_curve[-1].equity
    total_return = ((final_equity - initial_capital) / initial_capital) * 100.0

    # Periodic returns series
    equities = np.array([pt.equity for pt in equity_curve])
    returns = np.diff(equities) / equities[:-1] if len(equities) > 1 else np.array([0.0])

    # Annualized Return (CAGR)
    num_bars = len(equity_curve)
    years = num_bars / periods_per_year if periods_per_year > 0 else 1.0
    if years > 0 and final_equity > 0 and initial_capital > 0:
        cagr = ((final_equity / initial_capital) ** (1.0 / max(years, 0.001)) - 1.0) * 100.0
    else:
        cagr = total_return

    # Sharpe Ratio
    std_ret = np.std(returns)
    mean_ret = np.mean(returns)
    if std_ret > 1e-9:
        sharpe = (mean_ret / std_ret) * np.sqrt(periods_per_year)
    else:
        sharpe = 0.0

    # Sortino Ratio (downside deviations only)
    downside_returns = returns[returns < 0]
    downside_std = np.std(downside_returns) if len(downside_returns) > 0 else 0.0
    if downside_std > 1e-9:
        sortino = (mean_ret / downside_std) * np.sqrt(periods_per_year)
    else:
        sortino = sharpe if sharpe > 0 else 0.0

    # Max Drawdown and Duration
    peak = equities[0]
    max_dd_dollars = 0.0
    max_dd_pct = 0.0
    current_dd_bars = 0
    max_dd_bars = 0

    for eq in equities:
        if eq >= peak:
            peak = eq
            current_dd_bars = 0
        else:
            current_dd_bars += 1
            dd_dol = peak - eq
            dd_pct = (dd_dol / peak) * 100.0 if peak > 0 else 0.0
            if dd_dol > max_dd_dollars:
                max_dd_dollars = dd_dol
            if dd_pct > max_dd_pct:
                max_dd_pct = dd_pct
            if current_dd_bars > max_dd_bars:
                max_dd_bars = current_dd_bars

    # Calmar Ratio
    calmar = (cagr / max_dd_pct) if max_dd_pct > 1e-4 else 0.0

    # Trade statistics
    total_trades = len(trades)
    winning_trades = [t for t in trades if t.pnl > 0]
    losing_trades = [t for t in trades if t.pnl < 0]

    win_count = len(winning_trades)
    loss_count = len(losing_trades)
    win_rate = (win_count / total_trades * 100.0) if total_trades > 0 else 0.0

    gross_profit = sum(t.pnl for t in winning_trades)
    gross_loss = abs(sum(t.pnl for t in losing_trades))

    if gross_loss > 1e-6:
        profit_factor = gross_profit / gross_loss
    else:
        profit_factor = float("inf") if gross_profit > 0 else 0.0

    avg_win = (gross_profit / win_count) if win_count > 0 else 0.0
    avg_loss = (gross_loss / loss_count) if loss_count > 0 else 0.0
    payoff_ratio = (avg_win / avg_loss) if avg_loss > 1e-6 else 0.0

    total_commission = sum(t.commission for t in trades)
    total_slippage = sum(t.slippage for t in trades)
    avg_bars_held = (sum(t.bars_held for t in trades) / total_trades) if total_trades > 0 else 0.0
    avg_trade_pnl = (sum(t.pnl for t in trades) / total_trades) if total_trades > 0 else 0.0

    return {
        "initial_capital": float(round(initial_capital, 2)),
        "final_equity": float(round(final_equity, 2)),
        "total_return": float(round(total_return, 2)),
        "cagr": float(round(cagr, 2)),
        "sharpe_ratio": float(round(float(sharpe), 4)),
        "sortino_ratio": float(round(float(sortino), 4)),
        "calmar_ratio": float(round(float(calmar), 4)),
        "max_drawdown": float(round(float(max_dd_pct), 4)),
        "max_drawdown_dollars": float(round(float(max_dd_dollars), 2)),
        "max_drawdown_duration_bars": int(max_dd_bars),
        "win_rate": float(round(float(win_rate), 2)),
        "profit_factor": float(round(float(profit_factor), 4)) if profit_factor != float("inf") else 999.0,
        "total_trades": int(total_trades),
        "winning_trades": int(win_count),
        "losing_trades": int(loss_count),
        "avg_trade_pnl": float(round(float(avg_trade_pnl), 2)),
        "avg_win": float(round(float(avg_win), 2)),
        "avg_loss": float(round(float(avg_loss), 2)),
        "payoff_ratio": float(round(float(payoff_ratio), 4)),
        "total_commission": float(round(float(total_commission), 2)),
        "total_slippage": float(round(float(total_slippage), 2)),
        "avg_bars_held": float(round(float(avg_bars_held), 1)),
    }
