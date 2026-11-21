"""Backtesting Service Layer & Execution Engine Integration"""
import time
import os
from pathlib import Path
from typing import List, Optional, Dict, Any
from uuid import UUID
from datetime import datetime
from sqlalchemy.orm import Session
from sqlalchemy import desc

from infrastructure.database.connection import SessionLocal
from infrastructure.database.models import (
    BacktestRun,
    BacktestTrade,
    EquityPointModel,
    StrategyVersion,
    Strategy,
    OHLCVBar,
)
from api_platform.billing.service import record_usage
from api_platform.worker import dispatch_job
from core.execution.cost_model import CostModel
from core.backtesting.engine import BacktestEngine
from core.backtesting.data_loader import load_and_normalize_ohlcv
from api_platform.backtests.schemas import BacktestLaunchRequest
import pandas as pd


def launch_backtest(
    db: Session,
    user_id: UUID,
    workspace_id: UUID,
    req: BacktestLaunchRequest,
) -> BacktestRun:
    version = (
        db.query(StrategyVersion)
        .join(Strategy)
        .filter(
            StrategyVersion.id == req.strategy_version_id,
            Strategy.workspace_id == workspace_id,
        )
        .first()
    )
    if not version:
        raise ValueError("Strategy version not found in this workspace")

    run = BacktestRun(
        strategy_version_id=req.strategy_version_id,
        workspace_id=workspace_id,
        user_id=user_id,
        status="PENDING",
        config_hash=version.code_hash,
        symbol=req.symbol,
        timeframe=req.timeframe,
        initial_capital=req.initial_capital,
        slippage_bps=req.slippage_bps,
        commission_per_trade=req.commission_per_trade,
        spread_pips=req.spread_pips,
    )
    db.add(run)
    db.commit()
    db.refresh(run)

    # Dispatch execution job
    dispatch_job(execute_backtest_job, run.id, req.model_dump())

    return run


def execute_backtest_job(run_id: UUID, req_params: Dict[str, Any]):
    """
    Background worker task to execute backtest and persist results.
    """
    db = SessionLocal()
    start_time = time.time()
    try:
        run = db.query(BacktestRun).filter(BacktestRun.id == run_id).first()
        if not run:
            return

        run.status = "RUNNING"
        db.commit()

        version = db.query(StrategyVersion).filter(StrategyVersion.id == run.strategy_version_id).first()
        strategy = db.query(Strategy).filter(Strategy.id == version.strategy_id).first()

        # Load data: first check database ohlcv_bars, fallback to CSV file
        df = None
        db_bars = (
            db.query(OHLCVBar)
            .filter(OHLCVBar.symbol == run.symbol, OHLCVBar.timeframe == run.timeframe)
            .order_by(OHLCVBar.ts_utc.asc())
            .all()
        )
        if len(db_bars) >= 50:
            data_records = [
                {
                    "timestamp": b.ts_utc,
                    "open": b.open,
                    "high": b.high,
                    "low": b.low,
                    "close": b.close,
                    "volume": b.volume,
                }
                for b in db_bars
            ]
            df = pd.DataFrame(data_records)
        else:
            # Fallback to local CSV
            csv_path = Path("data/XAUUSD_1H_merged.csv")
            if csv_path.exists():
                df = load_and_normalize_ohlcv(csv_path)

        if df is None or len(df) < 50:
            run.status = "FAILED"
            run.error_message = f"Insufficient market data found for {run.symbol} ({run.timeframe})"
            db.commit()
            return

        # Setup cost model & engine
        cost_model = CostModel(
            slippage_bps=run.slippage_bps,
            commission_per_trade=run.commission_per_trade,
            spread_pips=run.spread_pips,
        )

        engine = BacktestEngine(
            cost_model=cost_model,
            initial_capital=run.initial_capital,
            risk_per_trade_pct=req_params.get("risk_per_trade_pct", 0.01),
            symbol=run.symbol,
            timeframe=run.timeframe,
        )

        result = engine.run(
            strategy_type=strategy.strategy_type,
            data=df,
            params=version.parameters,
            start_date=req_params.get("start_date"),
            end_date=req_params.get("end_date"),
        )

        metrics = result.metrics

        # Persist trades
        for t in result.trades:
            trade_model = BacktestTrade(
                backtest_run_id=run.id,
                trade_number=t.trade_id,
                symbol=t.symbol,
                side=t.side,
                entry_ts=t.entry_time,
                exit_ts=t.exit_time,
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
            db.add(trade_model)

        # Downsample equity points if dataset is huge (> 1000 points) for fast frontend rendering
        eq_series = result.equity_series
        step = max(1, len(eq_series) // 500)
        sampled_eq = [eq_series[i] for i in range(0, len(eq_series), step)]
        if eq_series and (sampled_eq[-1].timestamp != eq_series[-1].timestamp):
            sampled_eq.append(eq_series[-1])

        for pt in sampled_eq:
            eq_model = EquityPointModel(
                backtest_run_id=run.id,
                ts=pt.timestamp,
                equity=pt.equity,
                cash=pt.cash,
                drawdown=pt.drawdown,
                drawdown_pct=pt.drawdown_pct,
                returns=pt.returns,
            )
            db.add(eq_model)

        # Update run record
        run.status = "COMPLETED"
        run.final_equity = metrics.get("final_equity")
        run.total_return = metrics.get("total_return")
        run.cagr = metrics.get("cagr")
        run.sharpe_ratio = metrics.get("sharpe_ratio")
        run.sortino_ratio = metrics.get("sortino_ratio")
        run.calmar_ratio = metrics.get("calmar_ratio")
        run.max_drawdown = metrics.get("max_drawdown")
        run.win_rate = metrics.get("win_rate")
        run.profit_factor = metrics.get("profit_factor")
        run.total_trades = metrics.get("total_trades")
        run.winning_trades = metrics.get("winning_trades")
        run.losing_trades = metrics.get("losing_trades")
        run.completed_at = datetime.utcnow()

        db.commit()

        # Record billing compute duration
        duration_sec = time.time() - start_time
        record_usage(
            db=db,
            workspace_id=run.workspace_id,
            user_id=run.user_id,
            event_type="backtest_execution",
            units=round(duration_sec, 2),
            unit_type="seconds",
            cost_cents=round(duration_sec * 0.05, 4),  # $0.05 per compute sec
            metadata={"run_id": str(run.id), "trades_count": len(result.trades)},
        )

    except Exception as e:
        db.rollback()
        run = db.query(BacktestRun).filter(BacktestRun.id == run_id).first()
        if run:
            run.status = "FAILED"
            run.error_message = str(e)
            db.commit()
    finally:
        db.close()


def list_backtest_runs(db: Session, workspace_id: UUID) -> List[BacktestRun]:
    return (
        db.query(BacktestRun)
        .filter(BacktestRun.workspace_id == workspace_id)
        .order_by(desc(BacktestRun.created_at))
        .all()
    )


def get_backtest_run(db: Session, run_id: UUID, workspace_id: UUID) -> Optional[BacktestRun]:
    return (
        db.query(BacktestRun)
        .filter(BacktestRun.id == run_id, BacktestRun.workspace_id == workspace_id)
        .first()
    )


def get_backtest_trades(db: Session, run_id: UUID) -> List[BacktestTrade]:
    return (
        db.query(BacktestTrade)
        .filter(BacktestTrade.backtest_run_id == run_id)
        .order_by(BacktestTrade.trade_number.asc())
        .all()
    )


def get_backtest_equity_curve(db: Session, run_id: UUID) -> List[EquityPointModel]:
    return (
        db.query(EquityPointModel)
        .filter(EquityPointModel.backtest_run_id == run_id)
        .order_by(EquityPointModel.ts.asc())
        .all()
    )
