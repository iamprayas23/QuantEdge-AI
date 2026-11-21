"""Backtesting Router"""
from typing import List
from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from infrastructure.database.connection import get_db
from infrastructure.database.models import User, Workspace, StrategyVersion, Strategy
from api_platform.auth.dependencies import get_current_user, get_current_workspace
from api_platform.backtests import schemas, service

router = APIRouter(prefix="/backtests", tags=["Backtests"])


@router.post("/run", response_model=schemas.BacktestJobResponse)
def launch_run(
    payload: schemas.BacktestLaunchRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    workspace: Workspace = Depends(get_current_workspace),
):
    try:
        run = service.launch_backtest(
            db=db,
            user_id=current_user.id,
            workspace_id=workspace.id,
            req=payload,
        )
        return {
            "job_id": run.id,
            "status": run.status,
            "message": "Backtest submitted to queue successfully",
        }
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/", response_model=List[schemas.BacktestRunResponse])
def list_runs(
    db: Session = Depends(get_db),
    workspace: Workspace = Depends(get_current_workspace),
):
    return service.list_backtest_runs(db, workspace.id)


@router.get("/{run_id}/status")
def get_run_status(
    run_id: UUID,
    db: Session = Depends(get_db),
    workspace: Workspace = Depends(get_current_workspace),
):
    run = service.get_backtest_run(db, run_id, workspace.id)
    if not run:
        raise HTTPException(status_code=404, detail="Backtest run not found")
    return {
        "id": run.id,
        "status": run.status,
        "error_message": run.error_message,
        "completed_at": run.completed_at,
    }


@router.get("/{run_id}/tearsheet", response_model=schemas.BacktestTearsheetResponse)
def get_tearsheet(
    run_id: UUID,
    db: Session = Depends(get_db),
    workspace: Workspace = Depends(get_current_workspace),
):
    run = service.get_backtest_run(db, run_id, workspace.id)
    if not run:
        raise HTTPException(status_code=404, detail="Backtest run not found")

    version = db.query(StrategyVersion).filter(StrategyVersion.id == run.strategy_version_id).first()
    strategy = db.query(Strategy).filter(Strategy.id == version.strategy_id).first() if version else None

    trades = service.get_backtest_trades(db, run.id)
    equity = service.get_backtest_equity_curve(db, run.id)

    metrics = {
        "initial_capital": run.initial_capital,
        "final_equity": run.final_equity or run.initial_capital,
        "total_return": run.total_return or 0.0,
        "cagr": run.cagr or 0.0,
        "sharpe_ratio": run.sharpe_ratio or 0.0,
        "sortino_ratio": run.sortino_ratio or 0.0,
        "calmar_ratio": run.calmar_ratio or 0.0,
        "max_drawdown": run.max_drawdown or 0.0,
        "win_rate": run.win_rate or 0.0,
        "profit_factor": run.profit_factor or 0.0,
        "total_trades": run.total_trades or 0,
        "winning_trades": run.winning_trades or 0,
        "losing_trades": run.losing_trades or 0,
    }

    trade_items = [
        schemas.BacktestTradeItem(
            trade_number=t.trade_number,
            symbol=t.symbol,
            side=t.side,
            entry_ts=t.entry_ts,
            exit_ts=t.exit_ts,
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
        for t in trades[:100]  # top 100 recent
    ]

    equity_items = [
        schemas.EquityPointItem(
            ts=pt.ts,
            equity=pt.equity,
            cash=pt.cash,
            drawdown=pt.drawdown,
            drawdown_pct=pt.drawdown_pct,
            returns=pt.returns,
        )
        for pt in equity
    ]

    return schemas.BacktestTearsheetResponse(
        run=run,
        strategy_name=strategy.name if strategy else "Unknown Strategy",
        strategy_type=strategy.strategy_type if strategy else "rsi",
        parameters=version.parameters if version else {},
        metrics=metrics,
        recent_trades=trade_items,
        equity_curve=equity_items,
    )


@router.get("/{run_id}/trades", response_model=List[schemas.BacktestTradeItem])
def get_trades(
    run_id: UUID,
    db: Session = Depends(get_db),
    workspace: Workspace = Depends(get_current_workspace),
):
    run = service.get_backtest_run(db, run_id, workspace.id)
    if not run:
        raise HTTPException(status_code=404, detail="Backtest run not found")
    trades = service.get_backtest_trades(db, run.id)
    return [
        schemas.BacktestTradeItem(
            trade_number=t.trade_number,
            symbol=t.symbol,
            side=t.side,
            entry_ts=t.entry_ts,
            exit_ts=t.exit_ts,
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
        for t in trades
    ]


@router.get("/{run_id}/equity", response_model=List[schemas.EquityPointItem])
def get_equity(
    run_id: UUID,
    db: Session = Depends(get_db),
    workspace: Workspace = Depends(get_current_workspace),
):
    run = service.get_backtest_run(db, run_id, workspace.id)
    if not run:
        raise HTTPException(status_code=404, detail="Backtest run not found")
    points = service.get_backtest_equity_curve(db, run.id)
    return [
        schemas.EquityPointItem(
            ts=pt.ts,
            equity=pt.equity,
            cash=pt.cash,
            drawdown=pt.drawdown,
            drawdown_pct=pt.drawdown_pct,
            returns=pt.returns,
        )
        for pt in points
    ]
