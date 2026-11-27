"""Dynamic Portfolio Risk, Volatility Targeting & Drawdown Monitor

Provides:
- Volatility-targeted position sizing (targeting constant annual portfolio volatility)
- Multi-asset/strategy correlation monitoring and concentration risk flags
- Underwater duration and recovery trajectory tracking
- Real-time risk state snapshot (distance to limits, exposure caps, regime multipliers)
"""
from datetime import datetime, timezone
from typing import Dict, Any, List, Optional, Literal
import numpy as np
import pandas as pd
from pydantic import BaseModel, Field

from core.portfolio.state import EquityPoint, TradeRecord


class VolatilityTargetConfig(BaseModel):
    target_annual_vol_pct: float = Field(default=15.0, ge=5.0, le=40.0, description="Target annualized portfolio volatility (e.g. 15%)")
    min_multiplier: float = Field(default=0.25, ge=0.1, le=1.0, description="Minimum size scaling under extreme volatility")
    max_multiplier: float = Field(default=2.0, ge=1.0, le=4.0, description="Maximum leverage scaling under quiet volatility")
    lookback_bars: int = Field(default=24, ge=10, le=100, description="Rolling bars for realized volatility computation")


class UnderwaterTracker(BaseModel):
    current_drawdown_pct: float
    current_underwater_bars: int
    max_historical_drawdown_pct: float
    max_historical_underwater_bars: int
    is_at_high_water_mark: bool
    estimated_bars_to_recovery: Optional[int] = None
    recovery_status: Literal["PEAK", "SHALLOW_DIP", "DEEP_DRAWDOWN", "CRITICAL_RECESSION"]


class PortfolioRiskSnapshot(BaseModel):
    as_of_ts: str
    current_equity: float
    high_water_mark: float
    current_drawdown_pct: float
    daily_drawdown_pct: float
    distance_to_daily_limit_pct: float
    distance_to_max_limit_pct: float
    realized_vol_pct: float
    vol_target_multiplier: float
    suggested_risk_pct: float
    underwater_state: UnderwaterTracker
    concentration_risk_level: Literal["LOW", "MEDIUM", "HIGH"]
    correlation_notes: str
    recommended_action: Literal["NORMAL", "TRIM_EXPOSURE", "HALT"]
    summary: str


def compute_volatility_targeting_multiplier(
    current_realized_vol: float,
    config: Optional[VolatilityTargetConfig] = None,
) -> float:
    """
    Computes inverse volatility scaling multiplier:
    multiplier = clamp(target_vol / realized_vol, min_multiplier, max_multiplier)
    """
    cfg = config or VolatilityTargetConfig()
    if current_realized_vol <= 0.0:
        return 1.0

    raw_mult = cfg.target_annual_vol_pct / current_realized_vol
    clamped = float(np.clip(raw_mult, cfg.min_multiplier, cfg.max_multiplier))
    return round(clamped, 2)


def track_underwater_state(equity_series: List[EquityPoint]) -> UnderwaterTracker:
    """
    Computes active underwater metrics and longest drawdown duration from equity points.
    """
    if not equity_series:
        return UnderwaterTracker(
            current_drawdown_pct=0.0,
            current_underwater_bars=0,
            max_historical_drawdown_pct=0.0,
            max_historical_underwater_bars=0,
            is_at_high_water_mark=True,
            estimated_bars_to_recovery=0,
            recovery_status="PEAK",
        )

    equities = np.array([pt.equity for pt in equity_series])
    hwm_series = np.maximum.accumulate(equities)
    dd_series = (hwm_series - equities) / np.maximum(hwm_series, 1e-6) * 100.0

    current_dd = float(dd_series[-1])
    max_dd = float(np.max(dd_series))

    # Calculate underwater durations
    underwater_bars = 0
    max_underwater_bars = 0
    curr_underwater_count = 0

    for dd in dd_series:
        if dd > 0.05:  # more than 0.05% below HWM
            curr_underwater_count += 1
            max_underwater_bars = max(max_underwater_bars, curr_underwater_count)
        else:
            curr_underwater_count = 0

    current_underwater_bars = curr_underwater_count
    is_at_peak = current_dd <= 0.05

    # Status classification
    if is_at_peak:
        status = "PEAK"
    elif current_dd <= 5.0:
        status = "SHALLOW_DIP"
    elif current_dd <= 15.0:
        status = "DEEP_DRAWDOWN"
    else:
        status = "CRITICAL_RECESSION"

    # Estimate recovery bars based on historical recovery speed
    est_recovery = None
    if not is_at_peak and max_underwater_bars > 0:
        recovery_factor = current_dd / max(max_dd, 1e-6)
        est_recovery = max(5, int(max_underwater_bars * recovery_factor * 0.75))

    return UnderwaterTracker(
        current_drawdown_pct=round(current_dd, 2),
        current_underwater_bars=current_underwater_bars,
        max_historical_drawdown_pct=round(max_dd, 2),
        max_historical_underwater_bars=max_underwater_bars,
        is_at_high_water_mark=is_at_peak,
        estimated_bars_to_recovery=est_recovery,
        recovery_status=status,
    )


def compute_portfolio_correlation_matrix(returns_dict: Dict[str, pd.Series]) -> Dict[str, Any]:
    """
    Computes correlation across strategy/symbol returns and assesses concentration risk.
    """
    if len(returns_dict) < 2:
        return {
            "matrix": {},
            "avg_correlation": 1.0,
            "concentration_level": "LOW",
            "notes": "Single strategy/asset active. No cross-asset correlation available.",
        }

    df_ret = pd.DataFrame(returns_dict).dropna()
    if len(df_ret) < 5:
        return {
            "matrix": {},
            "avg_correlation": 0.0,
            "concentration_level": "LOW",
            "notes": "Insufficient sample returns for correlation matrix.",
        }

    corr_df = df_ret.corr()
    matrix = {col: {idx: round(float(val), 2) for idx, val in corr_df[col].items()} for col in corr_df.columns}

    # Average pairwise correlation off-diagonal
    n = len(corr_df)
    upper_tri = [corr_df.iloc[i, j] for i in range(n) for j in range(i + 1, n)]
    avg_corr = float(np.mean(upper_tri)) if upper_tri else 0.0

    if avg_corr >= 0.75:
        conc = "HIGH"
        notes = f"High positive correlation ({avg_corr:.2f}) across active positions. Strong concentration risk during market selloffs."
    elif avg_corr >= 0.40:
        conc = "MEDIUM"
        notes = f"Moderate diversification ({avg_corr:.2f} average correlation). Partial tail-risk co-movement."
    else:
        conc = "LOW"
        notes = f"Healthy portfolio diversification ({avg_corr:.2f} average correlation). Uncorrelated alpha streams."

    return {
        "matrix": matrix,
        "avg_correlation": round(avg_corr, 2),
        "concentration_level": conc,
        "notes": notes,
    }


def generate_portfolio_risk_snapshot(
    current_equity: float,
    daily_start_equity: float,
    equity_series: List[EquityPoint],
    current_realized_vol: float = 14.5,
    daily_limit_pct: float = 3.0,
    max_limit_pct: float = 15.0,
    base_risk_per_trade_pct: float = 0.01,
    vol_target_cfg: Optional[VolatilityTargetConfig] = None,
    correlation_data: Optional[Dict[str, Any]] = None,
) -> PortfolioRiskSnapshot:
    """
    Assembles a real-time institutional risk snapshot.
    """
    hwm = max(current_equity, max([pt.equity for pt in equity_series]) if equity_series else current_equity)
    underwater = track_underwater_state(equity_series)

    # Current daily drawdown
    daily_dd_pct = max(0.0, (daily_start_equity - current_equity) / max(daily_start_equity, 1e-6) * 100.0)
    current_dd_pct = underwater.current_drawdown_pct

    # Distances to limits
    dist_daily = round(max(0.0, daily_limit_pct - daily_dd_pct), 2)
    dist_max = round(max(0.0, max_limit_pct - current_dd_pct), 2)

    # Volatility multiplier
    vol_mult = compute_volatility_targeting_multiplier(current_realized_vol, vol_target_cfg)
    suggested_risk = round(base_risk_per_trade_pct * vol_mult, 4)

    # Concentration
    corr_info = correlation_data or {"concentration_level": "LOW", "notes": "Standalone portfolio risk monitoring."}
    conc_level = corr_info.get("concentration_level", "LOW")

    # Recommended action
    if dist_daily <= 0.0 or dist_max <= 0.0:
        rec_action = "HALT"
        summary = f"RISK HALT: Loss limit breached (Daily DD: {daily_dd_pct:.1f}%, Max DD: {current_dd_pct:.1f}%). New risk is prohibited."
    elif dist_daily < 1.0 or dist_max < 3.0 or underwater.recovery_status == "DEEP_DRAWDOWN":
        rec_action = "TRIM_EXPOSURE"
        summary = f"RISK WARNING: Approaching drawdown ceiling (Daily Buffer: {dist_daily:.1f}%, Max Buffer: {dist_max:.1f}%). Sizing clamped by 50%."
        suggested_risk = round(suggested_risk * 0.5, 4)
    else:
        rec_action = "NORMAL"
        summary = f"Risk parameters healthy. Daily loss buffer: {dist_daily:.1f}%, Max drawdown buffer: {dist_max:.1f}%. Volatility scaling: {vol_mult:.2f}x."

    return PortfolioRiskSnapshot(
        as_of_ts=datetime.now(timezone.utc).isoformat(),
        current_equity=round(current_equity, 2),
        high_water_mark=round(hwm, 2),
        current_drawdown_pct=round(current_dd_pct, 2),
        daily_drawdown_pct=round(daily_dd_pct, 2),
        distance_to_daily_limit_pct=dist_daily,
        distance_to_max_limit_pct=dist_max,
        realized_vol_pct=round(current_realized_vol, 2),
        vol_target_multiplier=vol_mult,
        suggested_risk_pct=suggested_risk,
        underwater_state=underwater,
        concentration_risk_level=conc_level,
        correlation_notes=corr_info.get("notes", ""),
        recommended_action=rec_action,
        summary=summary,
    )
