"""QuantEdge Full Test Suite Runner (Zero External Test Dependencies)"""
import os
import sys
import time
import unittest
from datetime import datetime, timedelta
import pandas as pd
import numpy as np

# Set environment for tests
os.environ["DATABASE_URL"] = "sqlite:///./test_quantedge_suite.db"
os.environ["USE_IN_MEMORY_QUEUE"] = "true"
sys.path.insert(0, os.path.abspath("."))

from infrastructure.database.models import Base
from infrastructure.database.connection import engine, SessionLocal
from core.execution.cost_model import CostModel
from core.risk.position_sizer import calculate_position_size
from core.portfolio.state import TradeRecord, EquityPoint
from core.backtesting.metrics import calculate_comprehensive_metrics
from core.backtesting.signals import compute_rsi, compute_atr, detect_causal_pivots
from core.backtesting.engine import BacktestEngine
from core.ai.schemas import StrategySpecOutput, BacktestCritiqueOutput
from core.ai.hypothesis_assistant import parse_hypothesis_to_spec
from core.ai.backtest_critique import critique_backtest_run

# API layer functions
import api_platform.auth.schemas as auth_schemas
import api_platform.auth.service as auth_service
import api_platform.strategies.schemas as strat_schemas
import api_platform.strategies.service as strat_service
import api_platform.backtests.schemas as bt_schemas
import api_platform.backtests.service as bt_service
import api_platform.billing.service as bill_service
import api_platform.ai.router as ai_router


class TestBacktestMath(unittest.TestCase):
    def test_cost_model_adjustments(self):
        cm = CostModel(slippage_bps=2.0, commission_per_trade=1.5, spread_pips=0.4, point_value=1.0)
        raw_price = 2000.0

        long_entry = cm.calculate_entry_price(raw_price, "long")
        self.assertAlmostEqual(long_entry, 2000.6, places=3)

        short_entry = cm.calculate_entry_price(raw_price, "short")
        self.assertAlmostEqual(short_entry, 1999.4, places=3)

        long_exit = cm.calculate_exit_price(raw_price, "long")
        self.assertAlmostEqual(long_exit, 1999.4, places=3)

        comm = cm.calculate_commission(price=2000.0, size=2.0)
        self.assertEqual(comm, 1.5)

    def test_position_sizing(self):
        capital = 10000.0
        risk_pct = 0.01
        entry = 2000.0
        sl = 1990.0
        size = calculate_position_size(capital, risk_pct, entry, sl, point_value=1.0)
        self.assertEqual(size, 10.0)

    def test_zero_lookahead_causal_pivots(self):
        dates = [datetime(2023, 1, 1) + timedelta(hours=i) for i in range(30)]
        highs = [100.0] * 30
        highs[10] = 120.0
        lows = [95.0] * 30
        closes = [98.0] * 30
        opens = [97.0] * 30

        df = pd.DataFrame({"timestamp": dates, "open": opens, "high": highs, "low": lows, "close": closes})

        window = 3
        sh, sl = detect_causal_pivots(df, window=window)

        for i in range(13):
            self.assertTrue(pd.isna(sh.iloc[i]))
        self.assertEqual(sh.iloc[13], 120.0)

    def test_metrics_calculation(self):
        initial_capital = 10000.0
        t1 = datetime(2023, 1, 1)
        t2 = datetime(2023, 1, 2)
        t3 = datetime(2023, 1, 3)

        trades = [
            TradeRecord(1, "XAUUSD", "long", t1, t2, 1900.0, 1920.0, 1.0, 19.0, 20.0, 1.0, 1.0, 0.0, "tp", 5),
            TradeRecord(2, "XAUUSD", "long", t2, t3, 1920.0, 1910.0, 1.0, -11.0, -10.0, -0.5, 1.0, 0.0, "sl", 3),
        ]

        eq_curve = [
            EquityPoint(t1, 10000.0, 10000.0, 0.0, 0.0, 0.0),
            EquityPoint(t2, 10019.0, 10019.0, 0.0, 0.0, 0.0019),
            EquityPoint(t3, 10008.0, 10008.0, 11.0, 0.1098, -0.0011),
        ]

        metrics = calculate_comprehensive_metrics(initial_capital, trades, eq_curve)
        self.assertEqual(metrics["final_equity"], 10008.0)
        self.assertEqual(metrics["total_trades"], 2)
        self.assertEqual(metrics["winning_trades"], 1)
        self.assertEqual(metrics["losing_trades"], 1)
        self.assertEqual(metrics["win_rate"], 50.0)
        self.assertAlmostEqual(metrics["profit_factor"], 19.0 / 11.0, places=2)


class TestPydanticAISchemas(unittest.TestCase):
    def test_hypothesis_parsing_rsi(self):
        prompt = "Trade XAUUSD on 1H with RSI period 14, enter long below 28, risk 1% per trade, 2.5 risk reward"
        spec = parse_hypothesis_to_spec(prompt)

        self.assertEqual(spec.strategy_type, "rsi")
        self.assertEqual(spec.symbol, "XAUUSD")
        self.assertEqual(spec.timeframe, "1H")
        self.assertEqual(spec.parameters["rsi_period"], 14)
        self.assertEqual(spec.parameters["oversold"], 28.0)
        self.assertEqual(spec.parameters["risk_reward_ratio"], 2.5)
        self.assertEqual(spec.parameters["risk_per_trade_pct"], 0.01)
        self.assertTrue(spec.human_confirmation_required)

    def test_hypothesis_parsing_divergence(self):
        prompt = "Trade divergence on gold with 5 swing window and neckline breakout, 2% risk"
        spec = parse_hypothesis_to_spec(prompt)

        self.assertEqual(spec.strategy_type, "divergence")
        self.assertEqual(spec.parameters["swing_window"], 5)
        self.assertEqual(spec.parameters["entry_mode"], "neckline_breakout")
        self.assertEqual(spec.parameters["risk_per_trade_pct"], 0.02)

    def test_grounded_backtest_critique(self):
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

        critique = critique_backtest_run(
            run_id="test-run-123",
            metrics=metrics,
            parameters=params,
        )

        self.assertEqual(critique.exact_metrics_cited["total_return_pct"], 15.0)
        self.assertEqual(critique.exact_metrics_cited["sharpe_ratio"], 1.45)
        self.assertEqual(critique.exact_metrics_cited["max_drawdown_pct"], 12.0)
        self.assertEqual(critique.exact_metrics_cited["total_trades"], 64)
        self.assertEqual(critique.overfitting_analysis.trade_count_observed, 64)
        self.assertFalse(critique.overfitting_analysis.sample_size_flag)
        self.assertEqual(critique.drawdown_critique.max_drawdown_pct, 12.0)


class TestAPIPlatformServices(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        Base.metadata.drop_all(bind=engine)
        Base.metadata.create_all(bind=engine)
        cls.db = SessionLocal()

    @classmethod
    def tearDownClass(cls):
        cls.db.close()
        Base.metadata.drop_all(bind=engine)
        if os.path.exists("./test_quantedge_suite.db"):
            try:
                os.remove("./test_quantedge_suite.db")
            except Exception:
                pass

    def test_full_service_and_data_workflow(self):
        db = self.db

        # 1. Register User & Create Workspace
        user, workspace = auth_service.create_user_with_workspace(
            db, email="trader_pro@fund.com", password="SecretPassword123!", workspace_name="Apex Alpha Lab"
        )
        self.assertIsNotNone(user.id)
        self.assertIsNotNone(workspace.id)

        # 2. Authenticate
        authed = auth_service.authenticate_user(db, "trader_pro@fund.com", "SecretPassword123!")
        self.assertIsNotNone(authed)
        self.assertEqual(authed.id, user.id)

        # 3. Create Strategy with initial v1
        strat = strat_service.create_strategy(
            db=db,
            workspace_id=workspace.id,
            user_id=user.id,
            name="XAUUSD Trend Reversion",
            description="Institutional RSI Mean Reversion Strategy",
            strategy_type="rsi",
            initial_parameters={
                "rsi_period": 14,
                "oversold": 30.0,
                "overbought": 70.0,
                "risk_per_trade_pct": 0.01,
                "risk_reward_ratio": 2.0,
            },
        )
        self.assertEqual(strat.name, "XAUUSD Trend Reversion")
        versions = strat_service.list_strategy_versions(db, strat.id)
        self.assertEqual(len(versions), 1)
        v1 = versions[0]
        self.assertEqual(v1.version_number, 1)
        self.assertIsNotNone(v1.code_hash)

        # 4. Bump to immutable v2
        v2 = strat_service.create_strategy_version(
            db=db,
            strategy_id=strat.id,
            parameters={
                "rsi_period": 21,
                "oversold": 28.0,
                "overbought": 72.0,
                "risk_per_trade_pct": 0.015,
                "risk_reward_ratio": 2.5,
            },
        )
        self.assertEqual(v2.version_number, 2)
        self.assertNotEqual(v2.code_hash, v1.code_hash)

        # 5. Launch and execute deterministic backtest
        req = bt_schemas.BacktestLaunchRequest(
            strategy_version_id=v1.id,
            symbol="XAUUSD",
            timeframe="1H",
            initial_capital=10000.0,
            slippage_bps=1.0,
            commission_per_trade=1.0,
            spread_pips=0.2,
            risk_per_trade_pct=0.01,
        )
        run = bt_service.launch_backtest(
            db=db,
            user_id=user.id,
            workspace_id=workspace.id,
            req=req,
        )
        self.assertIsNotNone(run.id)

        # Wait for async background completion
        completed = False
        for _ in range(25):
            db.refresh(run)
            if run.status == "COMPLETED":
                completed = True
                break
            elif run.status == "FAILED":
                self.fail(f"Backtest run failed: {run.error_message}")
            time.sleep(0.5)

        self.assertTrue(completed, "Backtest run did not finish in time")

        # 6. Verify trade logs and equity curve
        trades = bt_service.get_backtest_trades(db, run.id)
        equity_curve = bt_service.get_backtest_equity_curve(db, run.id)

        self.assertGreater(len(trades), 0)
        self.assertGreater(len(equity_curve), 0)
        self.assertIsNotNone(run.sharpe_ratio)
        self.assertIsNotNone(run.max_drawdown)
        self.assertIsNotNone(run.profit_factor)

        # 7. AI Hypothesis parse
        spec = parse_hypothesis_to_spec("Trade gold 1H when RSI crosses below 25, 2.5 RR, 1% risk")
        self.assertEqual(spec.strategy_type, "rsi")
        self.assertEqual(spec.parameters["oversold"], 25.0)

        # 8. AI Critique evaluation
        critique = critique_backtest_run(
            run_id=str(run.id),
            metrics={
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
            },
            parameters=v1.parameters,
        )
        self.assertEqual(critique.run_id, str(run.id))
        self.assertIsNotNone(critique.executive_summary)
        self.assertIsNotNone(critique.overfitting_analysis)

        # 9. Verify Billing Metering
        usage_summary = bill_service.get_workspace_usage_summary(db, workspace.id)
        self.assertGreaterEqual(usage_summary["total_records"], 1)
        self.assertGreater(usage_summary["total_compute_seconds"], 0.0)


if __name__ == "__main__":
    unittest.main(verbosity=2)
