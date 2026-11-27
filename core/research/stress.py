"""Deterministic Stress-Testing & Shock Scenarios Engine

Simulates adverse institutional execution conditions:
- 2x to 3x slippage and bid-ask spread expansion
- Commission fee hikes
- Flash volatility spikes and black swan adverse gap openings
- Tail risk and drawdown expansion tolerance
"""
from typing import List, Dict, Any, Optional, Literal
import pandas as pd
import numpy as np
from pydantic import BaseModel, Field

from core.execution.cost_model import CostModel
from core.backtesting.engine import BacktestEngine, BacktestResult
from core.backtesting.data_loader import load_and_normalize_ohlcv


class StressScenario(BaseModel):
    name: str
    description: str
    slippage_mult: float = 1.0
    spread_mult: float = 1.0
    commission_mult: float = 1.0
    gap_shock_pct: float = 0.0


class StressTestReport(BaseModel):
    scenario_name: str
    description: str
    base_sharpe: float
    stressed_sharpe: float
    base_max_dd: float
    stressed_max_dd: float
    base_final_equity: float
    stressed_final_equity: float
    drawdown_expansion_pct: float
    equity_erosion_pct: float
    status: Literal["PASS", "DEGRADED", "FAILED"]
    critical_findings: List[str]


def get_default_stress_scenarios() -> List[StressScenario]:
    """Pre-configured institutional shock battery."""
    return [
        StressScenario(
            name="Slippage Shock (2.5x)",
            description="Simulates fast-moving liquidity voids where fills slip by 2.5x standard assumption.",
            slippage_mult=2.5,
            spread_mult=1.0,
            commission_mult=1.0,
        ),
        StressScenario(
            name="Spread Widening (3.0x)",
            description="Simulates off-hours or rollover spread widening where bid-ask spreads blow out by 3x.",
            slippage_mult=1.0,
            spread_mult=3.0,
            commission_mult=1.0,
        ),
        StressScenario(
            name="Execution Crisis (Combined 3x)",
            description="Combined liquidity collapse: 3x slippage, 3x spread, and 1.5x commission surcharges.",
            slippage_mult=3.0,
            spread_mult=3.0,
            commission_mult=1.5,
        ),
        StressScenario(
            name="Adverse Opening Gap Shock (-1.5%)",
            description="Simulates weekend/macro gaps opening 1.5% against active positions before stops execute.",
            slippage_mult=2.0,
            spread_mult=2.0,
            commission_mult=1.0,
            gap_shock_pct=-0.015,
        ),
    ]


def run_stress_battery(
    strategy_type: str,
    data: Any,
    params: Optional[Dict[str, Any]] = None,
    base_cost_model: Optional[CostModel] = None,
    initial_capital: float = 10000.0,
    symbol: str = "XAUUSD",
    timeframe: str = "1H",
    custom_scenarios: Optional[List[StressScenario]] = None,
) -> List[StressTestReport]:
    """
    Runs a battery of stress-testing scenarios against a strategy.
    """
    df = load_and_normalize_ohlcv(data)
    bcm = base_cost_model or CostModel()
    scenarios = custom_scenarios or get_default_stress_scenarios()

    # 1. Base Run
    base_engine = BacktestEngine(cost_model=bcm, initial_capital=initial_capital, symbol=symbol, timeframe=timeframe)
    base_res = base_engine.run(strategy_type=strategy_type, data=df, params=params)

    base_sharpe = float(base_res.metrics.get("sharpe_ratio", 0.0))
    base_dd = float(base_res.metrics.get("max_drawdown", 0.0))
    base_eq = float(base_res.metrics.get("final_equity", initial_capital))

    reports: List[StressTestReport] = []

    for sc in scenarios:
        # Create stressed cost model
        stressed_cm = CostModel(
            slippage_bps=bcm.slippage_bps * sc.slippage_mult,
            commission_per_trade=bcm.commission_per_trade * sc.commission_mult,
            spread_pips=bcm.spread_pips * sc.spread_mult,
            point_value=bcm.point_value,
        )

        stressed_df = df.copy()
        if sc.gap_shock_pct != 0.0:
            # Apply occasional adverse gap shock on random bars
            shock_indices = np.linspace(10, len(stressed_df) - 5, num=min(5, len(stressed_df) // 50), dtype=int)
            for idx in shock_indices:
                stressed_df.loc[idx, "low"] = stressed_df.loc[idx, "low"] * (1.0 + sc.gap_shock_pct)
                stressed_df.loc[idx, "close"] = stressed_df.loc[idx, "close"] * (1.0 + sc.gap_shock_pct * 0.7)

        stressed_engine = BacktestEngine(
            cost_model=stressed_cm, initial_capital=initial_capital, symbol=symbol, timeframe=timeframe
        )
        stressed_res = stressed_engine.run(strategy_type=strategy_type, data=stressed_df, params=params)

        str_sharpe = float(stressed_res.metrics.get("sharpe_ratio", 0.0))
        str_dd = float(stressed_res.metrics.get("max_drawdown", 0.0))
        str_eq = float(stressed_res.metrics.get("final_equity", initial_capital))

        dd_expansion = round(str_dd - base_dd, 2)
        eq_erosion = round(((base_eq - str_eq) / max(base_eq, 1e-6)) * 100.0, 2)

        findings: List[str] = []
        if str_sharpe < 0.0:
            findings.append("Strategy became completely unprofitable under this stress condition.")
        if dd_expansion > 10.0:
            findings.append(f"Severe drawdown blowout (+{dd_expansion:.1f}% expansion to {str_dd:.1f}%).")
        if eq_erosion > 20.0:
            findings.append(f"Excessive capital erosion ({eq_erosion:.1f}% loss relative to base case).")

        # Status determination
        if str_sharpe >= 0.8 and dd_expansion <= 5.0 and eq_erosion <= 10.0:
            status = "PASS"
            if not findings:
                findings.append("Robust resilience. Strategy withstands execution friction with negligible degradation.")
        elif str_sharpe >= 0.2 and dd_expansion <= 15.0 and str_eq >= initial_capital * 0.90:
            status = "DEGRADED"
            findings.append("Tolerable performance decay. Recommend wider take-profit buffers to offset friction.")
        else:
            status = "FAILED"
            if not findings:
                findings.append("Strategy broke under stress. Friction erodes positive edge.")

        reports.append(
            StressTestReport(
                scenario_name=sc.name,
                description=sc.description,
                base_sharpe=round(base_sharpe, 2),
                stressed_sharpe=round(str_sharpe, 2),
                base_max_dd=round(base_dd, 2),
                stressed_max_dd=round(str_dd, 2),
                base_final_equity=round(base_eq, 2),
                stressed_final_equity=round(str_eq, 2),
                drawdown_expansion_pct=dd_expansion,
                equity_erosion_pct=eq_erosion,
                status=status,
                critical_findings=findings,
            )
        )

    return reports
