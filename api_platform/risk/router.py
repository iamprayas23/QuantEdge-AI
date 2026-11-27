"""Risk Router (Pillars 2 & 4: Execution Guardrails, Rule Profiles & Dynamic Risk Monitor)"""
from uuid import UUID
from typing import List, Dict, Any, Optional
from datetime import datetime, timezone
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from pydantic import BaseModel, Field

from infrastructure.database.connection import get_db
from infrastructure.database.models import (
    User,
    Workspace,
    RiskRuleProfileModel,
    BacktestRun,
    BacktestTrade,
    EquityPointModel,
    OHLCVBar,
)
from api_platform.auth.dependencies import get_current_user, get_current_workspace
from api_platform.billing.service import record_usage
from core.risk.guardrails import (
    RiskRuleProfile,
    GuardrailEvaluationResult,
    GuardrailAuditReport,
    evaluate_proposed_trade,
    audit_trade_log_against_guardrails,
)
from core.risk.portfolio_risk import (
    PortfolioRiskSnapshot,
    VolatilityTargetConfig,
    generate_portfolio_risk_snapshot,
)
from core.portfolio.state import TradeRecord, EquityPoint

router = APIRouter(prefix="/risk", tags=["Risk Guardrails & Portfolio Monitor"])


# --- Schemas ---
class CreateRiskProfileRequest(BaseModel):
    name: str = Field(default="Conservative Institutional Rulebook")
    max_risk_per_trade_pct: float = Field(default=0.01)
    daily_loss_limit_pct: float = Field(default=0.03)
    daily_loss_limit_abs: Optional[float] = None
    max_drawdown_pct: float = Field(default=0.15)
    drawdown_mode: str = Field(default="trailing")
    max_consecutive_losses: int = Field(default=3)
    cooldown_bars: int = Field(default=12)
    max_trades_per_day: int = Field(default=5)
    max_gross_exposure_pct: float = Field(default=1.0)


class EvaluateOrderRequest(BaseModel):
    profile_id: Optional[UUID] = None
    symbol: str = "XAUUSD"
    proposed_risk_pct: float = Field(default=0.01)
    proposed_size: float = Field(default=1.0)
    current_equity: float = Field(default=10000.0)
    high_water_mark: float = Field(default=10000.0)
    daily_start_equity: float = Field(default=10000.0)
    today_trades_count: int = Field(default=0)
    consecutive_losses: int = Field(default=0)
    cooldown_remaining: int = Field(default=0)


class AuditBacktestRequest(BaseModel):
    backtest_run_id: UUID
    profile_id: Optional[UUID] = None


# --- Endpoints: Profiles ---
@router.get("/guardrails/profiles")
def list_profiles(
    db: Session = Depends(get_db),
    workspace: Workspace = Depends(get_current_workspace),
):
    """List risk discipline rule profiles for the workspace."""
    profiles = db.query(RiskRuleProfileModel).filter(RiskRuleProfileModel.workspace_id == workspace.id).all()
    if not profiles:
        # Create default profile if empty
        default_prof = RiskRuleProfileModel(
            workspace_id=workspace.id,
            user_id=workspace.owner_id,
            name="Standard Institutional Discipline",
            max_risk_per_trade_pct=0.01,
            daily_loss_limit_pct=0.03,
            max_drawdown_pct=0.15,
            drawdown_mode="trailing",
            max_consecutive_losses=3,
            cooldown_bars=12,
            max_trades_per_day=5,
            max_gross_exposure_pct=1.0,
        )
        db.add(default_prof)
        db.commit()
        db.refresh(default_prof)
        profiles = [default_prof]

    return [
        {
            "id": str(p.id),
            "name": p.name,
            "max_risk_per_trade_pct": p.max_risk_per_trade_pct,
            "daily_loss_limit_pct": p.daily_loss_limit_pct,
            "daily_loss_limit_abs": p.daily_loss_limit_abs,
            "max_drawdown_pct": p.max_drawdown_pct,
            "drawdown_mode": p.drawdown_mode,
            "max_consecutive_losses": p.max_consecutive_losses,
            "cooldown_bars": p.cooldown_bars,
            "max_trades_per_day": p.max_trades_per_day,
            "max_gross_exposure_pct": p.max_gross_exposure_pct,
            "created_at": p.created_at.isoformat(),
        }
        for p in profiles
    ]


@router.post("/guardrails/profiles")
def create_profile(
    payload: CreateRiskProfileRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    workspace: Workspace = Depends(get_current_workspace),
):
    """Save an institutional risk & discipline rule profile."""
    prof = RiskRuleProfileModel(
        workspace_id=workspace.id,
        user_id=current_user.id,
        name=payload.name,
        max_risk_per_trade_pct=payload.max_risk_per_trade_pct,
        daily_loss_limit_pct=payload.daily_loss_limit_pct,
        daily_loss_limit_abs=payload.daily_loss_limit_abs,
        max_drawdown_pct=payload.max_drawdown_pct,
        drawdown_mode=payload.drawdown_mode,
        max_consecutive_losses=payload.max_consecutive_losses,
        cooldown_bars=payload.cooldown_bars,
        max_trades_per_day=payload.max_trades_per_day,
        max_gross_exposure_pct=payload.max_gross_exposure_pct,
    )
    db.add(prof)
    db.commit()
    db.refresh(prof)
    return {"id": str(prof.id), "status": "created"}


# --- Endpoints: Guardrail Evaluation ---
@router.post("/guardrails/evaluate", response_model=GuardrailEvaluationResult)
def evaluate_trade(
    payload: EvaluateOrderRequest,
    db: Session = Depends(get_db),
    workspace: Workspace = Depends(get_current_workspace),
):
    """
    Evaluates an order against active rule profile guardrails before execution.
    """
    profile = None
    if payload.profile_id:
        p_row = db.query(RiskRuleProfileModel).filter(
            RiskRuleProfileModel.id == payload.profile_id,
            RiskRuleProfileModel.workspace_id == workspace.id
        ).first()
        if p_row:
            profile = RiskRuleProfile(
                profile_id=str(p_row.id),
                name=p_row.name,
                max_risk_per_trade_pct=p_row.max_risk_per_trade_pct,
                daily_loss_limit_pct=p_row.daily_loss_limit_pct,
                daily_loss_limit_abs=p_row.daily_loss_limit_abs,
                max_drawdown_pct=p_row.max_drawdown_pct,
                drawdown_mode=p_row.drawdown_mode,
                max_consecutive_losses=p_row.max_consecutive_losses,
                cooldown_bars=p_row.cooldown_bars,
                max_trades_per_day=p_row.max_trades_per_day,
                max_gross_exposure_pct=p_row.max_gross_exposure_pct,
            )

    if not profile:
        profile = RiskRuleProfile()

    return evaluate_proposed_trade(
        profile=profile,
        current_equity=payload.current_equity,
        current_cash=payload.current_equity,
        high_water_mark=payload.high_water_mark,
        daily_start_equity=payload.daily_start_equity,
        today_trades_count=payload.today_trades_count,
        consecutive_losses_count=payload.consecutive_losses,
        cooldown_remaining=payload.cooldown_remaining,
        proposed_risk_pct=payload.proposed_risk_pct,
        proposed_size=payload.proposed_size,
        current_ts=datetime.now(timezone.utc),
    )


@router.post("/guardrails/audit-backtest", response_model=GuardrailAuditReport)
def audit_backtest(
    payload: AuditBacktestRequest,
    db: Session = Depends(get_db),
    workspace: Workspace = Depends(get_current_workspace),
):
    """
    Audits a historical backtest run against risk discipline guardrails,
    revealing exact rule breaches and counterfactual alpha preserved.
    """
    run = db.query(BacktestRun).filter(
        BacktestRun.id == payload.backtest_run_id,
        BacktestRun.workspace_id == workspace.id
    ).first()
    if not run:
        raise HTTPException(status_code=404, detail="Backtest run not found")

    # Fetch trades & equity curve
    db_trades = db.query(BacktestTrade).filter(BacktestTrade.backtest_run_id == run.id).order_by(BacktestTrade.trade_number).all()
    db_points = db.query(EquityPointModel).filter(EquityPointModel.backtest_run_id == run.id).order_by(EquityPointModel.ts).all()

    trades = [
        TradeRecord(
            trade_number=t.trade_number,
            symbol=t.symbol,
            side=t.side,
            entry_time=t.entry_ts,
            exit_time=t.exit_ts,
            entry_price=t.entry_price,
            exit_price=t.exit_price,
            size=t.size,
            pnl=t.pnl,
            gross_pnl=t.gross_pnl,
            return_pct=t.return_pct,
            commission=t.commission,
            slippage=t.slippage,
            exit_reason=t.exit_reason,
            bars_held=t.bars_held,
        )
        for t in db_trades
    ]

    equity_series = [
        EquityPoint(
            timestamp=pt.ts,
            equity=pt.equity,
            cash=pt.cash,
            drawdown=pt.drawdown,
            drawdown_pct=pt.drawdown_pct,
            returns=pt.returns,
        )
        for pt in db_points
    ]

    profile = RiskRuleProfile()
    if payload.profile_id:
        p_row = db.query(RiskRuleProfileModel).filter(RiskRuleProfileModel.id == payload.profile_id).first()
        if p_row:
            profile = RiskRuleProfile(
                profile_id=str(p_row.id),
                name=p_row.name,
                max_risk_per_trade_pct=p_row.max_risk_per_trade_pct,
                daily_loss_limit_pct=p_row.daily_loss_limit_pct,
                daily_loss_limit_abs=p_row.daily_loss_limit_abs,
                max_drawdown_pct=p_row.max_drawdown_pct,
                drawdown_mode=p_row.drawdown_mode,
                max_consecutive_losses=p_row.max_consecutive_losses,
                cooldown_bars=p_row.cooldown_bars,
                max_trades_per_day=p_row.max_trades_per_day,
                max_gross_exposure_pct=p_row.max_gross_exposure_pct,
            )

    return audit_trade_log_against_guardrails(
        profile=profile,
        trades=trades,
        equity_series=equity_series,
        initial_capital=run.initial_capital,
    )


# --- Endpoints: Portfolio Monitor ---
@router.get("/portfolio-monitor", response_model=PortfolioRiskSnapshot)
def get_portfolio_risk_monitor(
    symbol: str = "XAUUSD",
    timeframe: str = "1H",
    target_vol_pct: float = 15.0,
    db: Session = Depends(get_db),
    workspace: Workspace = Depends(get_current_workspace),
):
    """
    Live institutional portfolio risk monitor snapshot:
    drawdown, recovery duration, distance to limits, and volatility targeting.
    """
    # Fetch recent equity curve from latest completed backtest or baseline
    latest_run = (
        db.query(BacktestRun)
        .filter(BacktestRun.workspace_id == workspace.id, BacktestRun.status == "COMPLETED")
        .order_by(BacktestRun.completed_at.desc())
        .first()
    )

    equity_points: List[EquityPoint] = []
    current_equity = 10000.0
    daily_start = 10000.0

    if latest_run:
        pts = db.query(EquityPointModel).filter(EquityPointModel.backtest_run_id == latest_run.id).order_by(EquityPointModel.ts).all()
        if pts:
            equity_points = [
                EquityPoint(
                    timestamp=p.ts,
                    equity=p.equity,
                    cash=p.cash,
                    drawdown=p.drawdown,
                    drawdown_pct=p.drawdown_pct,
                    returns=p.returns,
                )
                for p in pts
            ]
            current_equity = equity_points[-1].equity
            daily_start = equity_points[max(0, len(equity_points) - 24)].equity

    snapshot = generate_portfolio_risk_snapshot(
        current_equity=current_equity,
        daily_start_equity=daily_start,
        equity_series=equity_points,
        current_realized_vol=14.5,
        daily_limit_pct=3.0,
        max_limit_pct=15.0,
        base_risk_per_trade_pct=0.01,
        vol_target_cfg=VolatilityTargetConfig(target_annual_vol_pct=target_vol_pct),
    )
    return snapshot
