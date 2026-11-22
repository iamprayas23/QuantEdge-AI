#!/usr/bin/env python3
"""Divergence Neckline Breakout Backtest Runner (Causal Zero-Lookahead Engine)"""
from core.execution.cost_model import CostModel
from core.backtesting.engine import BacktestEngine


def main():
    print("========== Initializing QuantEdge Divergence (Neckline Breakout) Backtest ==========")
    cost_model = CostModel(
        slippage_bps=1.0,
        commission_per_trade=1.0,
        spread_pips=0.2,
    )

    engine = BacktestEngine(
        cost_model=cost_model,
        initial_capital=10000.0,
        risk_per_trade_pct=0.01,
        symbol="XAUUSD",
        timeframe="1H",
    )

    result = engine.run(
        strategy_type="divergence",
        data="data/XAUUSD_1H_merged.csv",
        params={
            "rsi_period": 14,
            "swing_window": 5,
            "entry_mode": "neckline_breakout",
            "risk_per_trade_pct": 0.01,
            "risk_reward_ratio": 2.0,
            "atr_period": 14,
            "sl_buffer_atr": 0.2,
            "oversold_threshold": 35.0,
            "overbought_threshold": 65.0,
            "max_bars_held": 72,
        },
    )

    m = result.metrics
    print("\n========== Divergence Neckline Breakout Results ==========")
    print(f"Initial Capital : ${m['initial_capital']:,.2f}")
    print(f"Final Equity    : ${m['final_equity']:,.2f}")
    print(f"Total Return    : {m['total_return']:+.2f}%")
    print(f"Annualized CAGR : {m['cagr']:+.2f}%")
    print(f"Sharpe Ratio    : {m['sharpe_ratio']:.2f}")
    print(f"Sortino Ratio   : {m['sortino_ratio']:.2f}")
    print(f"Calmar Ratio    : {m['calmar_ratio']:.2f}")
    print(f"Max Drawdown    : -{m['max_drawdown']:.2f}% (${m['max_drawdown_dollars']:,.2f})")
    print(f"Max DD Duration : {m['max_drawdown_duration_bars']} bars")
    print(f"Total Trades    : {m['total_trades']} ({m['winning_trades']}W / {m['losing_trades']}L)")
    print(f"Win Rate        : {m['win_rate']:.2f}%")
    print(f"Profit Factor   : {m['profit_factor']:.2f}")
    print(f"Avg Win / Loss  : ${m['avg_win']:.2f} / ${m['avg_loss']:.2f} (Payoff: {m['payoff_ratio']:.2f})")
    print(f"Total Costs     : ${m['total_commission'] + m['total_slippage']:,.2f} (Comm: ${m['total_commission']:,.2f}, Slip: ${m['total_slippage']:,.2f})")


if __name__ == "__main__":
    main()
