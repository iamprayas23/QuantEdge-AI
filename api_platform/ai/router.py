"""Grounded AI Router"""
from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException, Body
from sqlalchemy.orm import Session
from pydantic import BaseModel, Field

from infrastructure.database.connection import get_db
from infrastructure.database.models import User, Workspace, BacktestRun, StrategyVersion, Strategy
from api_platform.auth.dependencies import get_current_user, get_current_workspace
from api_platform.billing.service import record_usage
from core.ai.schemas import StrategySpecOutput, BacktestCritiqueOutput
from core.ai.hypothesis_assistant import parse_hypothesis_to_spec
from core.ai.backtest_critique import critique_backtest_run

router = APIRouter(prefix="/ai", tags=["Grounded AI"])


class HypothesisRequest(BaseModel):
    prompt: str = Field(..., min_length=5, description="Plain English trading strategy hypothesis")


@router.post("/hypothesis-to-spec", response_model=StrategySpecOutput)
def hypothesis_to_spec(
    payload: HypothesisRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    workspace: Workspace = Depends(get_current_workspace),
):
    spec = parse_hypothesis_to_spec(payload.prompt)

    # Meter AI usage
    record_usage(
        db=db,
        workspace_id=workspace.id,
        user_id=current_user.id,
        event_type="ai_strategy_translation",
        units=len(payload.prompt.split()) * 4.0,  # approximate token estimation
        unit_type="tokens",
        cost_cents=0.5,
        metadata={"strategy_type": spec.strategy_type},
    )

    return spec


@router.post("/critique-backtest/{run_id}", response_model=BacktestCritiqueOutput)
def critique_backtest(
    run_id: UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    workspace: Workspace = Depends(get_current_workspace),
):
    run = (
        db.query(BacktestRun)
        .filter(BacktestRun.id == run_id, BacktestRun.workspace_id == workspace.id)
        .first()
    )
    if not run:
        raise HTTPException(status_code=404, detail="Backtest run not found")

    if run.status != "COMPLETED":
        raise HTTPException(
            status_code=400,
            detail=f"Cannot critique backtest in '{run.status}' state. Backtest must be COMPLETED.",
        )

    version = db.query(StrategyVersion).filter(StrategyVersion.id == run.strategy_version_id).first()
    params = version.parameters if version else {}

    metrics = {
        "initial_capital": run.initial_capital,
        "final_equity": run.final_equity,
        "total_return": run.total_return,
        "cagr": run.cagr,
        "sharpe_ratio": run.sharpe_ratio,
        "sortino_ratio": run.sortino_ratio,
        "calmar_ratio": run.calmar_ratio,
        "max_drawdown": run.max_drawdown,
        "win_rate": run.win_rate,
        "profit_factor": run.profit_factor,
        "total_trades": run.total_trades,
        "winning_trades": run.winning_trades,
        "losing_trades": run.losing_trades,
    }

    critique = critique_backtest_run(
        run_id=str(run.id),
        metrics=metrics,
        parameters=params,
    )

    # Meter AI usage
    record_usage(
        db=db,
        workspace_id=workspace.id,
        user_id=current_user.id,
        event_type="ai_backtest_critique",
        units=450.0,
        unit_type="tokens",
        cost_cents=1.0,
        metadata={"run_id": str(run.id)},
    )

    return critique
