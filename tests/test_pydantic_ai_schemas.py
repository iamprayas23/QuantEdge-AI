"""Unit Tests for Pydantic AI Schemas & Grounded Critique"""
import pytest
from core.ai.schemas import StrategySpecOutput, BacktestCritiqueOutput
from core.ai.hypothesis_assistant import parse_hypothesis_to_spec
from core.ai.backtest_critique import critique_backtest_run


def test_hypothesis_parsing_rsi():
    prompt = "Trade XAUUSD on 1H with RSI period 14, enter long below 28, risk 1% per trade, 2.5 risk reward"
    spec: StrategySpecOutput = parse_hypothesis_to_spec(prompt)

    assert spec.strategy_type == "rsi"
    assert spec.symbol == "XAUUSD"
    assert spec.timeframe == "1H"
    assert spec.parameters["rsi_period"] == 14
    assert spec.parameters["oversold"] == 28.0
    assert spec.parameters["risk_reward_ratio"] == 2.5
    assert spec.parameters["risk_per_trade_pct"] == 0.01
    assert spec.human_confirmation_required is True


def test_hypothesis_parsing_divergence():
    prompt = "Trade divergence on gold with 5 swing window and neckline breakout, 2% risk"
    spec: StrategySpecOutput = parse_hypothesis_to_spec(prompt)

    assert spec.strategy_type == "divergence"
    assert spec.parameters["swing_window"] == 5
    assert spec.parameters["entry_mode"] == "neckline_breakout"
    assert spec.parameters["risk_per_trade_pct"] == 0.02


def test_grounded_backtest_critique_exact_citation():
    metrics = {
        "initial_capital": 10000.0,
        "final_equity": 11500.0,
        "total_return": 15.0,
        "cagr": 12.3,
        "sharpe_ratio": 1.45,
        "sortino_ratio": 1.82,
        "calmar_ratio": 1.25,
        "max_drawdown": 12.0,
        "max_drawdown_dollars": 1250.0,
        "max_drawdown_duration_bars": 120,
        "win_rate": 55.0,
        "profit_factor": 1.65,
        "total_trades": 64,
        "winning_trades": 35,
        "losing_trades": 29,
        "payoff_ratio": 1.35,
    }
    params = {"rsi_period": 14, "oversold": 30.0}

    critique: BacktestCritiqueOutput = critique_backtest_run(
        run_id="test-run-123",
        metrics=metrics,
        parameters=params,
    )

    # Verify exact numbers cited
    assert critique.exact_metrics_cited["total_return_pct"] == 15.0
    assert critique.exact_metrics_cited["sharpe_ratio"] == 1.45
    assert critique.exact_metrics_cited["max_drawdown_pct"] == 12.0
    assert critique.exact_metrics_cited["total_trades"] == 64
    assert critique.overfitting_analysis.trade_count_observed == 64
    assert critique.overfitting_analysis.sample_size_flag is False
    assert critique.drawdown_critique.max_drawdown_pct == 12.0
    assert len(critique.actionable_recommendations) >= 2
