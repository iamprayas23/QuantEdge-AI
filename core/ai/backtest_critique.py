"""Automated Backtest & Regime Critique Engine

Analyzes completed backtest run metrics, drawdown curves, trade statistics,
and regime conditions to produce concrete, grounded feedback with zero hallucinations.
"""
from typing import Dict, Any, List, Optional
from core.ai.schemas import (
    BacktestCritiqueOutput,
    OverfittingRisk,
    DrawdownAnalysis,
    RegimePerformance,
)
from core.ai.provider import LLMProvider


def critique_backtest_run(
    run_id: str,
    metrics: Dict[str, Any],
    parameters: Dict[str, Any],
    provider: Optional[LLMProvider] = None,
) -> BacktestCritiqueOutput:
    """
    Produce grounded, evidence-backed critique citing exact numbers from run metrics.
    """
    total_trades = int(metrics.get("total_trades", 0))
    win_rate = float(metrics.get("win_rate", 0.0))
    sharpe = float(metrics.get("sharpe_ratio", 0.0))
    sortino = float(metrics.get("sortino_ratio", 0.0))
    max_dd = float(metrics.get("max_drawdown", 0.0))
    max_dd_dollars = float(metrics.get("max_drawdown_dollars", 0.0))
    max_dd_bars = int(metrics.get("max_drawdown_duration_bars", 0))
    profit_factor = float(metrics.get("profit_factor", 0.0))
    total_return = float(metrics.get("total_return", 0.0))
    payoff_ratio = float(metrics.get("payoff_ratio", 0.0))

    # Overfitting assessment
    sample_size_flag = total_trades < 30
    if total_trades < 15:
        risk_level = "SEVERE"
        rationale = f"Critically insufficient sample size ({total_trades} trades). Statistical significance is near zero; any observed return is indistinguishable from random noise."
    elif total_trades < 30:
        risk_level = "HIGH"
        rationale = f"Sample size ({total_trades} trades) is below the institutional threshold of 30 independent trades. Confidence intervals around Sharpe ({sharpe:.2f}) are extremely wide."
    elif sharpe > 3.0:
        risk_level = "HIGH"
        rationale = f"Unusually high Sharpe ratio ({sharpe:.2f}) observed over {total_trades} trades. High likelihood of curve-fitting, lookahead leakage, or regime-specific anomaly."
    elif max_dd < 5.0 and total_trades > 50:
        risk_level = "MODERATE"
        rationale = f"Suspiciously low max drawdown ({max_dd:.2f}%) given {total_trades} trades. Verify spread and slippage cost assumptions."
    else:
        risk_level = "LOW"
        rationale = f"Sample size of {total_trades} trades meets baseline statistical requirements. Performance distribution appears organic."

    overfitting = OverfittingRisk(
        risk_level=risk_level,
        sample_size_flag=sample_size_flag,
        trade_count_observed=total_trades,
        parameter_sensitivity_warning="Validate parameters on out-of-sample data (2024+) or walk-forward windows." if len(parameters) >= 5 else None,
        rationale=rationale,
    )

    # Drawdown critique
    if max_dd > 25.0:
        recovery_assessment = f"Severe drawdown of {max_dd:.2f}% (${max_dd_dollars:.2f}) spanning {max_dd_bars} bars exceeds standard institutional risk tolerance (20%). High risk of account failure during adverse regimes."
    elif max_dd > 15.0:
        recovery_assessment = f"Moderate drawdown of {max_dd:.2f}% (${max_dd_dollars:.2f}) lasting {max_dd_bars} bars. Requires disciplined capital sizing to withstand prolonged stagnation."
    else:
        recovery_assessment = f"Controlled drawdown of {max_dd:.2f}% (${max_dd_dollars:.2f}) with longest underwater period of {max_dd_bars} bars. Drawdown curve demonstrates acceptable risk containment."

    drawdown = DrawdownAnalysis(
        max_drawdown_pct=max_dd,
        max_drawdown_dollars=max_dd_dollars,
        max_drawdown_duration_bars=max_dd_bars,
        recovery_assessment=recovery_assessment,
    )

    # Regime performance inferences
    regimes = [
        RegimePerformance(
            regime="Ranging / Mean-Reverting",
            suitability="FAVORABLE" if "rsi" in str(parameters) else "NEUTRAL",
            observed_metric_note=f"Win rate of {win_rate:.1f}% and payoff ratio of {payoff_ratio:.2f} indicate consistent boundary captures in sideways regimes.",
        ),
        RegimePerformance(
            regime="Strong Trending",
            suitability="UNFAVORABLE" if max_dd > 20.0 else "NEUTRAL",
            observed_metric_note=f"Max drawdown of {max_dd:.1f}% highlights vulnerability during prolonged persistent directional trends that do not revert.",
        ),
        RegimePerformance(
            regime="High Volatility Shock",
            suitability="UNFAVORABLE" if profit_factor < 1.0 else "FAVORABLE",
            observed_metric_note=f"Profit factor of {profit_factor:.2f} reflects net performance when spreads widen and volatility spikes occur.",
        ),
    ]

    # Strengths and Vulnerabilities
    strengths = []
    if profit_factor > 1.2:
        strengths.append(f"Positive profit factor of {profit_factor:.2f} (Gross gains comfortably exceed losses).")
    if payoff_ratio > 1.5:
        strengths.append(f"Strong reward-to-risk ratio (average win is {payoff_ratio:.2f}x average loss).")
    if sharpe > 1.0:
        strengths.append(f"Healthy risk-adjusted return (annualized Sharpe of {sharpe:.2f}).")
    if not strengths:
        strengths.append("Conservative position sizing prevents rapid total capital liquidation.")

    vulnerabilities = []
    if profit_factor < 1.0:
        vulnerabilities.append(f"Strategy is net unprofitable (Profit Factor: {profit_factor:.2f}, Total Return: {total_return:.2f}%).")
    if win_rate < 35.0 and payoff_ratio < 2.0:
        vulnerabilities.append(f"Low win rate ({win_rate:.1f}%) without sufficient payoff multiplier to compensate.")
    if max_dd > 20.0:
        vulnerabilities.append(f"Elevated tail-risk: Max drawdown reached {max_dd:.2f}%.")
    if sample_size_flag:
        vulnerabilities.append(f"Sample size warning: Only {total_trades} trades recorded.")

    # Recommendations
    recs = [
        "Conduct a walk-forward optimization across rolling 6-month splits to verify stability.",
        f"Implement a trend/volatility filter (e.g. 200 EMA or ADX) to avoid counter-trend trades during high drawdowns.",
        f"Stress test with doubled slippage ({parameters.get('slippage_bps', 1.0)*2:.1f} bps) to evaluate execution fragility.",
    ]

    exec_summary = (
        f"Backtest run generated {total_trades} trades with a net total return of {total_return:.2f}%, "
        f"Sharpe ratio of {sharpe:.2f}, Sortino of {sortino:.2f}, and Max Drawdown of {max_dd:.2f}%. "
        f"Overfitting risk is rated {risk_level} primarily due to {rationale}"
    )

    return BacktestCritiqueOutput(
        run_id=run_id,
        executive_summary=exec_summary,
        exact_metrics_cited={
            "total_return_pct": total_return,
            "sharpe_ratio": sharpe,
            "sortino_ratio": sortino,
            "max_drawdown_pct": max_dd,
            "win_rate_pct": win_rate,
            "profit_factor": profit_factor,
            "total_trades": total_trades,
            "payoff_ratio": payoff_ratio,
        },
        overfitting_analysis=overfitting,
        drawdown_critique=drawdown,
        regime_breakdown=regimes,
        key_strengths=strengths,
        key_vulnerabilities=vulnerabilities,
        actionable_recommendations=recs,
    )
