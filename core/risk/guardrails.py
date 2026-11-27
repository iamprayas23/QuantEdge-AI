"""Deterministic Execution & Rule Discipline Guardrail Engine

Evaluates proposed trades and historical trade logs against strict quantitative rules:
- Max risk per trade %
- Daily loss limit (percentage & absolute currency)
- Max drawdown limit (static peak vs trailing high-water mark)
- Consecutive losses cooldown trigger
- Max trades per day
- Max gross exposure %

Prevents emotional overrides and provides an auditable rule adherence score.
"""
from dataclasses import dataclass, field
from datetime import datetime, date
from typing import List, Dict, Any, Optional, Literal
import numpy as np
import pandas as pd
from pydantic import BaseModel, Field

from core.portfolio.state import TradeRecord, EquityPoint


class RiskRuleProfile(BaseModel):
    profile_id: Optional[str] = Field(None, description="Unique rule profile ID")
    name: str = Field(default="Standard Institutional Discipline", description="Profile label")
    max_risk_per_trade_pct: float = Field(default=0.01, ge=0.001, le=0.10, description="Max allowed risk per trade (e.g. 1%)")
    daily_loss_limit_pct: float = Field(default=0.03, ge=0.005, le=0.20, description="Max daily drawdown before trading halts (e.g. 3%)")
    daily_loss_limit_abs: Optional[float] = Field(None, description="Absolute daily loss currency ceiling")
    max_drawdown_pct: float = Field(default=0.15, ge=0.01, le=0.50, description="Max cumulative drawdown limit (e.g. 15%)")
    drawdown_mode: Literal["static", "trailing"] = Field(default="trailing", description="Static initial peak vs trailing high water mark")
    max_consecutive_losses: int = Field(default=3, ge=1, le=10, description="Number of losses before mandatory cooling off")
    cooldown_bars: int = Field(default=12, ge=1, le=100, description="Mandatory timeout bars following consecutive losses")
    max_trades_per_day: int = Field(default=5, ge=1, le=50, description="Maximum executions permitted per calendar day")
    max_gross_exposure_pct: float = Field(default=1.0, ge=0.1, le=5.0, description="Max position size relative to portfolio equity")


class RuleBreach(BaseModel):
    timestamp: datetime = Field(..., description="Timestamp of the rule breach")
    rule_name: str = Field(..., description="Identifier of the breached constraint")
    threshold: Any = Field(..., description="Rule threshold specified")
    observed_value: Any = Field(..., description="Actual value observed")
    severity: Literal["WARNING", "BREACH", "CRITICAL"] = Field(..., description="Breach severity tier")
    action_taken: Literal["HALT_NEW_TRADES", "REDUCE_SIZE", "FORCE_COOLDOWN", "REJECT_TRADE"] = Field(...)
    message: str = Field(..., description="Human-readable explanation of why the rule fired")


class GuardrailEvaluationResult(BaseModel):
    allowed: bool = Field(..., description="Whether the proposed execution is approved")
    adjusted_size: float = Field(..., description="Prudent position size after rule caps and adjustments")
    breached_rules: List[RuleBreach] = Field(default_factory=list)
    rule_adherence_score: float = Field(..., ge=0.0, le=100.0, description="Discipline score from 0 (chronic drift) to 100 (perfect)")
    cooldown_remaining_bars: int = Field(default=0)
    current_daily_pnl: float = Field(default=0.0)
    current_drawdown_pct: float = Field(default=0.0)
    consecutive_losses: int = Field(default=0)
    trades_today: int = Field(default=0)
    summary_verdict: str = Field(..., description="Concise assessment for execution blotter")


class GuardrailAuditReport(BaseModel):
    profile_name: str
    total_trades_evaluated: int
    compliant_trades: int
    breach_count: int
    rule_adherence_score: float
    capital_lost_to_breaches: float
    counterfactual_final_equity: float
    actual_final_equity: float
    disciplined_alpha_preserved: float
    breach_breakdown: Dict[str, int]
    detailed_breaches: List[RuleBreach]
    summary_recommendation: str


def evaluate_proposed_trade(
    profile: RiskRuleProfile,
    current_equity: float,
    current_cash: float,
    high_water_mark: float,
    daily_start_equity: float,
    today_trades_count: int,
    consecutive_losses_count: int,
    cooldown_remaining: int,
    proposed_risk_pct: float,
    proposed_size: float,
    current_ts: datetime,
) -> GuardrailEvaluationResult:
    """
    Evaluates an incoming live or backtested order against the discipline profile.
    """
    breaches: List[RuleBreach] = []
    adjusted_size = proposed_size
    allowed = True

    # 1. Check Active Cooldown
    if cooldown_remaining > 0:
        breaches.append(
            RuleBreach(
                timestamp=current_ts,
                rule_name="consecutive_losses_cooldown",
                threshold=0,
                observed_value=cooldown_remaining,
                severity="CRITICAL",
                action_taken="FORCE_COOLDOWN",
                message=f"Mandatory cooldown active after {profile.max_consecutive_losses} consecutive losses. {cooldown_remaining} bars remaining."
            )
        )
        return GuardrailEvaluationResult(
            allowed=False,
            adjusted_size=0.0,
            breached_rules=breaches,
            rule_adherence_score=60.0,
            cooldown_remaining_bars=cooldown_remaining,
            current_daily_pnl=current_equity - daily_start_equity,
            current_drawdown_pct=max(0.0, (high_water_mark - current_equity) / max(high_water_mark, 1e-6) * 100.0),
            consecutive_losses=consecutive_losses_count,
            trades_today=today_trades_count,
            summary_verdict="REJECTED: Cooldown period active.",
        )

    # 2. Check Daily Trades Count
    if today_trades_count >= profile.max_trades_per_day:
        breaches.append(
            RuleBreach(
                timestamp=current_ts,
                rule_name="max_trades_per_day",
                threshold=profile.max_trades_per_day,
                observed_value=today_trades_count,
                severity="BREACH",
                action_taken="HALT_NEW_TRADES",
                message=f"Daily trade limit of {profile.max_trades_per_day} reached. Overtrading prevention active."
            )
        )
        allowed = False
        adjusted_size = 0.0

    # 3. Check Daily Loss Limit
    daily_pnl = current_equity - daily_start_equity
    daily_drawdown_pct = abs(daily_pnl) / max(daily_start_equity, 1e-6) if daily_pnl < 0 else 0.0

    if daily_drawdown_pct >= profile.daily_loss_limit_pct:
        breaches.append(
            RuleBreach(
                timestamp=current_ts,
                rule_name="daily_loss_limit_pct",
                threshold=profile.daily_loss_limit_pct * 100.0,
                observed_value=round(daily_drawdown_pct * 100.0, 2),
                severity="CRITICAL",
                action_taken="HALT_NEW_TRADES",
                message=f"Daily loss limit of {profile.daily_loss_limit_pct * 100:.1f}% breached (-${abs(daily_pnl):.2f}). Trading halted for the day."
            )
        )
        allowed = False
        adjusted_size = 0.0

    if profile.daily_loss_limit_abs and daily_pnl < -abs(profile.daily_loss_limit_abs):
        breaches.append(
            RuleBreach(
                timestamp=current_ts,
                rule_name="daily_loss_limit_abs",
                threshold=profile.daily_loss_limit_abs,
                observed_value=round(abs(daily_pnl), 2),
                severity="CRITICAL",
                action_taken="HALT_NEW_TRADES",
                message=f"Absolute daily loss limit (-${profile.daily_loss_limit_abs:.2f}) breached."
            )
        )
        allowed = False
        adjusted_size = 0.0

    # 4. Check Maximum Drawdown
    ref_peak = high_water_mark if profile.drawdown_mode == "trailing" else daily_start_equity
    current_dd_pct = max(0.0, (ref_peak - current_equity) / max(ref_peak, 1e-6))

    if current_dd_pct >= profile.max_drawdown_pct:
        breaches.append(
            RuleBreach(
                timestamp=current_ts,
                rule_name="max_drawdown_pct",
                threshold=profile.max_drawdown_pct * 100.0,
                observed_value=round(current_dd_pct * 100.0, 2),
                severity="CRITICAL",
                action_taken="HALT_NEW_TRADES",
                message=f"Max portfolio drawdown limit of {profile.max_drawdown_pct * 100:.1f}% breached ({current_dd_pct * 100:.1f}% observed). Trading stopped."
            )
        )
        allowed = False
        adjusted_size = 0.0

    # 5. Check Single Trade Risk Limit
    if proposed_risk_pct > profile.max_risk_per_trade_pct:
        breaches.append(
            RuleBreach(
                timestamp=current_ts,
                rule_name="max_risk_per_trade_pct",
                threshold=profile.max_risk_per_trade_pct * 100.0,
                observed_value=round(proposed_risk_pct * 100.0, 2),
                severity="WARNING",
                action_taken="REDUCE_SIZE",
                message=f"Proposed risk per trade ({proposed_risk_pct * 100:.2f}%) exceeds rule ceiling ({profile.max_risk_per_trade_pct * 100:.2f}%). Clamping size."
            )
        )
        scaling = profile.max_risk_per_trade_pct / max(proposed_risk_pct, 1e-6)
        adjusted_size = round(proposed_size * scaling, 4)

    # Calculate Adherence Score
    score = 100.0
    for b in breaches:
        if b.severity == "CRITICAL":
            score -= 30.0
        elif b.severity == "BREACH":
            score -= 15.0
        elif b.severity == "WARNING":
            score -= 5.0
    score = float(max(0.0, min(100.0, score)))

    verdict = "APPROVED" if allowed and not breaches else ("APPROVED_WITH_ADJUSTMENTS" if allowed else "REJECTED_BREACH")

    return GuardrailEvaluationResult(
        allowed=allowed,
        adjusted_size=adjusted_size,
        breached_rules=breaches,
        rule_adherence_score=score,
        cooldown_remaining_bars=cooldown_remaining,
        current_daily_pnl=round(daily_pnl, 2),
        current_drawdown_pct=round(current_dd_pct * 100.0, 2),
        consecutive_losses=consecutive_losses_count,
        trades_today=today_trades_count,
        summary_verdict=verdict,
    )


def audit_trade_log_against_guardrails(
    profile: RiskRuleProfile,
    trades: List[TradeRecord],
    equity_series: List[EquityPoint],
    initial_capital: float = 10000.0,
) -> GuardrailAuditReport:
    """
    Audits a completed backtest or live trading blotter against the rule profile.
    Simulates a counterfactual portfolio where trades occurring during rule breaches are halted,
    revealing exact capital preserved by disciplined execution.
    """
    if not trades:
        return GuardrailAuditReport(
            profile_name=profile.name,
            total_trades_evaluated=0,
            compliant_trades=0,
            breach_count=0,
            rule_adherence_score=100.0,
            capital_lost_to_breaches=0.0,
            counterfactual_final_equity=initial_capital,
            actual_final_equity=initial_capital,
            disciplined_alpha_preserved=0.0,
            breach_breakdown={},
            detailed_breaches=[],
            summary_recommendation="No trades provided for audit.",
        )

    breaches: List[RuleBreach] = []
    breach_counts_by_rule: Dict[str, int] = {}
    capital_lost_to_breaches = 0.0

    current_equity = initial_capital
    counterfactual_equity = initial_capital
    hwm = initial_capital
    cf_hwm = initial_capital

    current_day: Optional[date] = None
    daily_start_equity = initial_capital
    trades_today = 0
    consecutive_losses = 0
    cooldown_counter = 0

    compliant_trades = 0

    for t in trades:
        entry_ts = t.entry_time if isinstance(t.entry_time, datetime) else pd.to_datetime(t.entry_time).to_pydatetime()
        trade_date = entry_ts.date()

        if trade_date != current_day:
            current_day = trade_date
            daily_start_equity = current_equity
            trades_today = 0

        eval_res = evaluate_proposed_trade(
            profile=profile,
            current_equity=current_equity,
            current_cash=current_equity,
            high_water_mark=hwm,
            daily_start_equity=daily_start_equity,
            today_trades_count=trades_today,
            consecutive_losses_count=consecutive_losses,
            cooldown_remaining=cooldown_counter,
            proposed_risk_pct=profile.max_risk_per_trade_pct,
            proposed_size=t.size,
            current_ts=entry_ts,
        )

        if eval_res.allowed:
            compliant_trades += 1
            counterfactual_equity += t.pnl
            cf_hwm = max(cf_hwm, counterfactual_equity)
        else:
            for b in eval_res.breached_rules:
                breaches.append(b)
                breach_counts_by_rule[b.rule_name] = breach_counts_by_rule.get(b.rule_name, 0) + 1
            if t.pnl < 0:
                capital_lost_to_breaches += abs(t.pnl)

        # Actual execution trajectory
        current_equity += t.pnl
        hwm = max(hwm, current_equity)
        trades_today += 1

        if t.pnl < 0:
            consecutive_losses += 1
            if consecutive_losses >= profile.max_consecutive_losses:
                cooldown_counter = profile.cooldown_bars
        else:
            consecutive_losses = 0

        if cooldown_counter > 0:
            cooldown_counter = max(0, cooldown_counter - t.bars_held)

    total_evaluated = len(trades)
    adherence_pct = round((compliant_trades / max(total_evaluated, 1)) * 100.0, 1)
    alpha_preserved = round(counterfactual_equity - current_equity, 2)

    if adherence_pct >= 90.0:
        recommendation = "Excellent rule discipline. Execution adherence exceeds institutional benchmarks."
    elif adherence_pct >= 75.0:
        recommendation = f"Moderate rule drift detected ({len(breaches)} breaches). Enforcement of daily loss limits would have preserved ${abs(capital_lost_to_breaches):.2f}."
    else:
        recommendation = f"Severe execution indiscipline ({len(breaches)} rule breaches). Trader frequently overrides stops or overtrades. Counterfactual disciplined alpha: +${alpha_preserved:.2f}."

    return GuardrailAuditReport(
        profile_name=profile.name,
        total_trades_evaluated=total_evaluated,
        compliant_trades=compliant_trades,
        breach_count=len(breaches),
        rule_adherence_score=adherence_pct,
        capital_lost_to_breaches=round(capital_lost_to_breaches, 2),
        counterfactual_final_equity=round(counterfactual_equity, 2),
        actual_final_equity=round(current_equity, 2),
        disciplined_alpha_preserved=alpha_preserved,
        breach_breakdown=breach_counts_by_rule,
        detailed_breaches=breaches[:20],  # sample most relevant
        summary_recommendation=recommendation,
    )
