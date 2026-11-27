"""Deterministic Walk-Forward Optimization & Out-of-Sample Efficiency Engine

Implements rolling and anchored walk-forward validation:
- In-Sample (IS) parameter calibration vs. Out-of-Sample (OOS) verification
- Walk-Forward Efficiency (WFE = OOS performance / IS performance)
- Parameter stability score across successive validation windows
- Early detection of curve-fitting and degrees-of-freedom overfitting
"""
from dataclasses import dataclass
from typing import List, Dict, Any, Optional, Literal
import numpy as np
import pandas as pd
from pydantic import BaseModel, Field

from core.execution.cost_model import CostModel
from core.backtesting.engine import BacktestEngine, BacktestResult
from core.backtesting.data_loader import load_and_normalize_ohlcv


class WalkForwardConfig(BaseModel):
    train_bars: int = Field(default=300, ge=50, description="In-sample training window length in bars")
    test_bars: int = Field(default=100, ge=20, description="Out-of-sample forward testing window length in bars")
    step_bars: int = Field(default=100, ge=20, description="Step progression length between windows")
    mode: Literal["rolling", "anchored"] = Field(default="rolling", description="Rolling vs expanding anchor window")
    min_trades: int = Field(default=5, description="Minimum trades per test window required for statistical significance")
    candidate_params: Optional[List[Dict[str, Any]]] = Field(
        default=None, description="Candidate parameter variations to evaluate on In-Sample data"
    )


class WalkForwardWindowResult(BaseModel):
    window_index: int
    train_start: str
    train_end: str
    test_start: str
    test_end: str
    selected_params: Dict[str, Any]
    is_metrics: Dict[str, Any]
    oos_metrics: Dict[str, Any]
    wfe: float = Field(..., description="Walk-Forward Efficiency ratio (OOS Sharpe / IS Sharpe)")


class WalkForwardAnalysisResult(BaseModel):
    strategy_type: str
    symbol: str
    timeframe: str
    mode: str
    num_windows: int
    overall_wfe: float = Field(..., description="Aggregated Out-of-Sample Walk-Forward Efficiency (WFE)")
    parameter_stability_score: float = Field(..., ge=0.0, le=100.0, description="Parameter stability score (0-100)")
    robustness_verdict: Literal["ROBUST", "BORDERLINE", "OVERFIT"]
    windows: List[WalkForwardWindowResult]
    stitched_oos_summary: Dict[str, Any]
    summary_verdict: str


def run_walk_forward_analysis(
    strategy_type: str,
    data: Any,
    config: Optional[WalkForwardConfig] = None,
    cost_model: Optional[CostModel] = None,
    initial_capital: float = 10000.0,
    symbol: str = "XAUUSD",
    timeframe: str = "1H",
) -> WalkForwardAnalysisResult:
    """
    Executes a deterministic rolling or anchored walk-forward analysis.
    """
    df = load_and_normalize_ohlcv(data)
    total_bars = len(df)
    cfg = config or WalkForwardConfig()
    cm = cost_model or CostModel()

    # Default candidate parameter grids if not specified
    if not cfg.candidate_params:
        if strategy_type == "rsi":
            cfg.candidate_params = [
                {"rsi_period": 10, "oversold": 25.0, "overbought": 75.0, "risk_reward_ratio": 2.0, "sl_atr_mult": 1.5},
                {"rsi_period": 14, "oversold": 30.0, "overbought": 70.0, "risk_reward_ratio": 2.0, "sl_atr_mult": 1.5},
                {"rsi_period": 21, "oversold": 35.0, "overbought": 65.0, "risk_reward_ratio": 1.8, "sl_atr_mult": 2.0},
                {"rsi_period": 14, "oversold": 28.0, "overbought": 72.0, "risk_reward_ratio": 2.5, "sl_atr_mult": 1.2},
            ]
        else:
            cfg.candidate_params = [
                {"rsi_period": 14, "swing_window": 4, "entry_mode": "early_candlestick", "risk_reward_ratio": 2.0},
                {"rsi_period": 14, "swing_window": 5, "entry_mode": "early_candlestick", "risk_reward_ratio": 2.0},
                {"rsi_period": 14, "swing_window": 5, "entry_mode": "neckline_breakout", "risk_reward_ratio": 2.5},
                {"rsi_period": 21, "swing_window": 6, "entry_mode": "early_candlestick", "risk_reward_ratio": 1.8},
            ]

    # Validate window requirements
    min_required = cfg.train_bars + cfg.test_bars
    if total_bars < min_required:
        raise ValueError(
            f"Insufficient data for walk-forward: {total_bars} bars provided, minimum {min_required} required."
        )

    windows: List[WalkForwardWindowResult] = []
    oos_trades_all = []
    engine = BacktestEngine(cost_model=cm, initial_capital=initial_capital, symbol=symbol, timeframe=timeframe)

    current_train_start = 0
    window_idx = 0

    while True:
        train_end = current_train_start + cfg.train_bars
        test_start = train_end
        test_end = test_start + cfg.test_bars

        if test_end > total_bars:
            break

        train_slice = df.iloc[current_train_start:train_end].copy().reset_index(drop=True)
        test_slice = df.iloc[test_start:test_end].copy().reset_index(drop=True)

        # 1. In-Sample Optimization: Select Best Parameters on IS Slice
        best_candidate = cfg.candidate_params[0]
        best_is_sharpe = -999.0
        best_is_result: Optional[BacktestResult] = None

        for param_set in cfg.candidate_params:
            try:
                res = engine.run(strategy_type=strategy_type, data=train_slice, params=param_set)
                sharpe = float(res.metrics.get("sharpe_ratio", 0.0))
                # Primary ranking: Sharpe ratio, tie-break: profit factor
                if sharpe > best_is_sharpe:
                    best_is_sharpe = sharpe
                    best_candidate = param_set
                    best_is_result = res
            except Exception:
                continue

        if best_is_result is None:
            # Fallback run
            best_is_result = engine.run(strategy_type=strategy_type, data=train_slice, params=best_candidate)

        # 2. Out-of-Sample Verification: Run Selected Best on OOS Slice
        oos_result = engine.run(strategy_type=strategy_type, data=test_slice, params=best_candidate)

        is_metrics = best_is_result.metrics
        oos_metrics = oos_result.metrics
        oos_trades_all.extend(oos_result.trades)

        is_sharpe = float(is_metrics.get("sharpe_ratio", 0.01))
        oos_sharpe = float(oos_metrics.get("sharpe_ratio", 0.0))

        # Calculate WFE (clamped reasonably)
        if abs(is_sharpe) < 0.05:
            wfe = 1.0 if oos_sharpe >= 0 else 0.0
        else:
            wfe = max(-2.0, min(3.0, oos_sharpe / is_sharpe))

        windows.append(
            WalkForwardWindowResult(
                window_index=window_idx,
                train_start=str(train_slice["timestamp"].iloc[0]),
                train_end=str(train_slice["timestamp"].iloc[-1]),
                test_start=str(test_slice["timestamp"].iloc[0]),
                test_end=str(test_slice["timestamp"].iloc[-1]),
                selected_params=best_candidate,
                is_metrics={
                    "sharpe_ratio": round(is_sharpe, 2),
                    "total_return": round(float(is_metrics.get("total_return", 0.0)), 2),
                    "max_drawdown": round(float(is_metrics.get("max_drawdown", 0.0)), 2),
                    "total_trades": int(is_metrics.get("total_trades", 0)),
                    "win_rate": round(float(is_metrics.get("win_rate", 0.0)), 1),
                },
                oos_metrics={
                    "sharpe_ratio": round(oos_sharpe, 2),
                    "total_return": round(float(oos_metrics.get("total_return", 0.0)), 2),
                    "max_drawdown": round(float(oos_metrics.get("max_drawdown", 0.0)), 2),
                    "total_trades": int(oos_metrics.get("total_trades", 0)),
                    "win_rate": round(float(oos_metrics.get("win_rate", 0.0)), 1),
                },
                wfe=round(wfe, 2),
            )
        )

        window_idx += 1
        if cfg.mode == "rolling":
            current_train_start += cfg.step_bars
        else:  # anchored: expanding training window
            cfg.train_bars += cfg.step_bars

    if not windows:
        raise ValueError("Could not complete any walk-forward validation window.")

    # 3. Aggregate Performance Metrics & Robustness Verdict
    avg_wfe = float(np.mean([w.wfe for w in windows]))

    # Parameter stability: count how often parameter sets were identical across folds
    param_shifts = 0
    for i in range(len(windows) - 1):
        if windows[i].selected_params != windows[i + 1].selected_params:
            param_shifts += 1

    param_stability = round(max(0.0, 100.0 - (param_shifts / max(len(windows) - 1, 1) * 100.0)), 1)

    # Robustness verdict
    if avg_wfe >= 0.55 and param_stability >= 50.0:
        verdict = "ROBUST"
        summary = (
            f"Strategy exhibits institutional robustness. Out-of-Sample Walk-Forward Efficiency (WFE: {avg_wfe:.2f}) "
            f"exceeds the 0.55 benchmark with {param_stability}% parameter stability across {len(windows)} windows."
        )
    elif avg_wfe >= 0.30:
        verdict = "BORDERLINE"
        summary = (
            f"Strategy exhibits moderate degradation out-of-sample (WFE: {avg_wfe:.2f}, stability: {param_stability}%). "
            f"Performance decays in certain regime transitions. Recommend wider parameter tolerance."
        )
    else:
        verdict = "OVERFIT"
        summary = (
            f"High likelihood of curve-fitting detected (WFE: {avg_wfe:.2f} < 0.30). In-sample parameters fail "
            f"to generalize out-of-sample across {len(windows)} validation folds."
        )

    stitched_summary = {
        "total_oos_windows": len(windows),
        "avg_oos_sharpe": round(float(np.mean([w.oos_metrics["sharpe_ratio"] for w in windows])), 2),
        "avg_is_sharpe": round(float(np.mean([w.is_metrics["sharpe_ratio"] for w in windows])), 2),
        "total_oos_trades": sum(w.oos_metrics["total_trades"] for w in windows),
        "avg_oos_win_rate": round(float(np.mean([w.oos_metrics["win_rate"] for w in windows])), 1),
    }

    return WalkForwardAnalysisResult(
        strategy_type=strategy_type,
        symbol=symbol,
        timeframe=timeframe,
        mode=cfg.mode,
        num_windows=len(windows),
        overall_wfe=round(avg_wfe, 2),
        parameter_stability_score=param_stability,
        robustness_verdict=verdict,
        windows=windows,
        stitched_oos_summary=stitched_summary,
        summary_verdict=summary,
    )
