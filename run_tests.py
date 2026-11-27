"""QuantEdge Full Test Suite Runner (Zero External Test Dependencies)"""
import os
import sys
import time
import unittest
from datetime import datetime, timezone, timedelta
import pandas as pd
import numpy as np

# Set environment for tests
os.environ["DATABASE_URL"] = "sqlite:///./test_quantedge_suite.db"
os.environ["USE_IN_MEMORY_QUEUE"] = "true"
sys.path.insert(0, os.path.abspath("."))

from infrastructure.database.models import (
    Base,
    CommitteeReport,
    MarketCatalyst,
    RiskRuleProfileModel,
    WalkForwardRun,
    CashflowPlanModel,
)
from infrastructure.database.connection import engine, SessionLocal
from core.execution.cost_model import CostModel
from core.risk.position_sizer import calculate_position_size
from core.portfolio.state import TradeRecord, EquityPoint
from core.backtesting.metrics import calculate_comprehensive_metrics
from core.backtesting.signals import compute_rsi, compute_atr, detect_causal_pivots
from core.backtesting.engine import BacktestEngine
from core.ai.schemas import (
    StrategySpecOutput,
    BacktestCritiqueOutput,
    AnalystSignal,
    RiskAssessment,
    PortfolioProposal,
    CommitteeReviewOutput,
)
from core.ai.hypothesis_assistant import parse_hypothesis_to_spec
from core.ai.backtest_critique import critique_backtest_run
from core.agents import (
    AgentState,
    CommitteeOrchestrator,
    TechnicalsAgent,
    RegimeAgent,
    RiskAgent,
    PortfolioManagerAgent,
)
from core.research.catalysts import (
    MarketCatalystEvent,
    get_default_catalysts,
    align_catalysts_with_bars,
    compute_catalyst_regime_impact,
)
from core.ai.catalyst_brief import CatalystBriefOutput, generate_catalyst_regime_brief
from core.risk.guardrails import (
    RiskRuleProfile,
    RuleBreach,
    GuardrailEvaluationResult,
    GuardrailAuditReport,
    evaluate_proposed_trade,
    audit_trade_log_against_guardrails,
)
from core.research.walk_forward import (
    WalkForwardConfig,
    WalkForwardAnalysisResult,
    run_walk_forward_analysis,
)
from core.research.stress import (
    StressScenario,
    StressTestReport,
    run_stress_battery,
)
from core.risk.portfolio_risk import (
    VolatilityTargetConfig,
    UnderwaterTracker,
    PortfolioRiskSnapshot,
    compute_volatility_targeting_multiplier,
    track_underwater_state,
    generate_portfolio_risk_snapshot,
)
from core.finance.planner import (
    CashFlowItem,
    DebtItem,
    FinancialGoal,
    TaxDragConfig,
    FinancialPlanOutput,
    calculate_cash_flow_and_runway,
    simulate_debt_payoff,
    simulate_compound_tax_drag,
    generate_comprehensive_financial_plan,
)

# API layer functions
import api_platform.auth.schemas as auth_schemas
import api_platform.auth.service as auth_service
import api_platform.strategies.schemas as strat_schemas
import api_platform.strategies.service as strat_service
import api_platform.backtests.schemas as bt_schemas
import api_platform.backtests.service as bt_service
import api_platform.billing.service as bill_service
import api_platform.ai.router as ai_router
import api_platform.research.router as research_router
import api_platform.risk.router as risk_router
import api_platform.finance.router as finance_router
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


class TestMultiAgentCommittee(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        Base.metadata.create_all(bind=engine)
        cls.db = SessionLocal()

    @classmethod
    def tearDownClass(cls):
        cls.db.close()

    def test_technicals_agent_deterministic_signal(self):
        agent = TechnicalsAgent()
        market_summary_bull = {
            "last_close": 2050.0,
            "ema50": 2020.0,
            "ema200": 2000.0,
            "rsi14": 58.0,
            "atr14": 12.5,
        }
        res_bull = agent.evaluate("XAUUSD", market_summary_bull)
        self.assertIsInstance(res_bull, AnalystSignal)
        self.assertEqual(res_bull.signal, "BULLISH")
        self.assertGreaterEqual(res_bull.confidence, 0.5)
        self.assertEqual(res_bull.metrics_grounding["last_close"], 2050.0)

        market_summary_bear = {
            "last_close": 1950.0,
            "ema50": 1980.0,
            "ema200": 2000.0,
            "rsi14": 75.0,
            "atr14": 15.0,
        }
        res_bear = agent.evaluate("XAUUSD", market_summary_bear)
        self.assertEqual(res_bear.signal, "BEARISH")
        self.assertIn("bearish", res_bear.rationale.lower())

    def test_regime_agent_deterministic_signal(self):
        agent = RegimeAgent()
        regime_data_bull = {
            "vol_regime": "medium_vol",
            "trend_regime": "trending_bull",
            "realized_vol_pct": 14.5,
        }
        res_bull = agent.evaluate("XAUUSD", regime_data_bull)
        self.assertIsInstance(res_bull, AnalystSignal)
        self.assertEqual(res_bull.signal, "BULLISH")
        self.assertEqual(res_bull.metrics_grounding["vol_regime"], "medium_vol")

        regime_data_ranging = {
            "vol_regime": "low_vol",
            "trend_regime": "ranging",
            "realized_vol_pct": 8.5,
        }
        res_ranging = agent.evaluate("XAUUSD", regime_data_ranging)
        self.assertEqual(res_ranging.signal, "NEUTRAL")

    def test_risk_agent_guardrails_and_limits(self):
        agent = RiskAgent()
        market_summary = {"last_close": 2000.0}
        regime_data = {"vol_regime": "high_vol", "realized_vol_pct": 24.0}

        # Severe drawdown scenario (> 25%)
        backtest_severe = {
            "max_drawdown": 28.5,
            "total_trades": 18,
            "profit_factor": 1.2,
        }
        risk_out = agent.evaluate("XAUUSD", market_summary, regime_data, backtest_severe)
        self.assertIsInstance(risk_out, RiskAssessment)
        self.assertEqual(risk_out.allowed_action, "RESTRICT")
        self.assertLessEqual(risk_out.max_risk_per_trade_pct, 0.005)
        self.assertTrue(any("Sample size warning" in w for w in risk_out.risk_warnings))
        self.assertTrue(any("Severe historical drawdown" in w for w in risk_out.risk_warnings))

        # Safe scenario
        backtest_safe = {
            "max_drawdown": 8.5,
            "total_trades": 55,
            "profit_factor": 1.75,
        }
        regime_safe = {"vol_regime": "medium_vol", "realized_vol_pct": 12.0}
        risk_safe = agent.evaluate("XAUUSD", market_summary, regime_safe, backtest_safe)
        self.assertEqual(risk_safe.allowed_action, "PERMIT")
        self.assertEqual(risk_safe.max_risk_per_trade_pct, 0.01)

    def test_portfolio_manager_synthesis(self):
        agent = PortfolioManagerAgent()
        tech = AnalystSignal(
            agent_name="technicals",
            signal="BULLISH",
            confidence=0.8,
            rationale="Strong trend",
            metrics_grounding={"last_close": 2050.0},
        )
        reg = AnalystSignal(
            agent_name="regime",
            signal="BULLISH",
            confidence=0.75,
            rationale="Trending bull",
            metrics_grounding={"vol_regime": "medium_vol"},
        )
        risk = RiskAssessment(
            max_risk_per_trade_pct=0.01,
            max_drawdown_limit_pct=20.0,
            allowed_action="PERMIT",
            volatility_assessment="Medium Vol",
            risk_warnings=[],
            rationale="Risk parameters validated",
        )

        proposal = agent.evaluate("XAUUSD", tech, reg, risk)
        self.assertIsInstance(proposal, PortfolioProposal)
        self.assertEqual(proposal.target_action, "BUY")
        self.assertEqual(proposal.target_allocation_pct, 100.0)
        self.assertTrue(proposal.human_confirmation_required)

        # Test Halt condition overrides analyst bullishness
        risk_halt = RiskAssessment(
            max_risk_per_trade_pct=0.0,
            max_drawdown_limit_pct=20.0,
            allowed_action="HALT",
            volatility_assessment="Extreme Vol",
            risk_warnings=["Severe loss"],
            rationale="Halt trading",
        )
        proposal_halt = agent.evaluate("XAUUSD", tech, reg, risk_halt)
        self.assertEqual(proposal_halt.target_action, "HOLD")
        self.assertEqual(proposal_halt.target_allocation_pct, 0.0)

    def test_orchestrator_end_to_end(self):
        dates = pd.date_range("2024-01-01", periods=60, freq="h")
        df = pd.DataFrame({
            "timestamp": dates,
            "open": [2000.0 + i for i in range(60)],
            "high": [2005.0 + i for i in range(60)],
            "low": [1995.0 + i for i in range(60)],
            "close": [2002.0 + i for i in range(60)],
            "volume": [1000.0] * 60,
        })

        orchestrator = CommitteeOrchestrator()
        review = orchestrator.run(
            symbol="XAUUSD",
            timeframe="1H",
            ohlcv_df=df,
            backtest_metrics={"max_drawdown": 10.0, "total_trades": 45, "profit_factor": 1.6},
            strategy_params={"rsi_period": 14, "oversold": 30.0},
        )

        self.assertIsInstance(review, CommitteeReviewOutput)
        self.assertIn("technicals", review.analyst_signals)
        self.assertIn("regime", review.analyst_signals)
        self.assertIsNotNone(review.risk_assessment)
        self.assertIsNotNone(review.portfolio_proposal)
        self.assertTrue(review.human_confirmation_required)
        self.assertGreater(len(review.executive_summary), 20)

    def test_committee_api_endpoint_and_db_persistence(self):
        # 1. Setup user & workspace
        email = f"committee_quant_{int(time.time())}@quantedge.io"
        u, ws = auth_service.create_user_with_workspace(
            self.db, email=email, password="Password123!", workspace_name="Committee Lab"
        )

        # 2. Invoke Committee Review endpoint handler
        req = ai_router.CommitteeReviewRequest(
            symbol="XAUUSD",
            timeframe="1H",
            limit_bars=60,
        )
        review_out = ai_router.convene_committee_review(
            payload=req,
            db=self.db,
            current_user=u,
            workspace=ws,
        )

        self.assertIsInstance(review_out, CommitteeReviewOutput)
        self.assertEqual(review_out.symbol, "XAUUSD")
        self.assertTrue(review_out.human_confirmation_required)

        # 3. Verify Database Persistence of CommitteeReport
        reports = ai_router.list_committee_reports(limit=10, db=self.db, workspace=ws)
        self.assertGreaterEqual(len(reports), 1)
        latest_summary = reports[0]
        self.assertEqual(latest_summary.symbol, "XAUUSD")

        # 4. Fetch full report by ID
        from uuid import UUID
        report_detail = ai_router.get_committee_report(
            report_id=UUID(latest_summary.id),
            db=self.db,
            workspace=ws,
        )
        self.assertIn("analyst_signals", report_detail)
        self.assertIn("portfolio_proposal", report_detail)

        # 5. Verify usage was recorded
        usage = bill_service.get_workspace_usage_summary(self.db, ws.id)
        self.assertGreaterEqual(usage["total_records"], 1)


class TestFinanceAndTradingPillars(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        Base.metadata.create_all(bind=engine)
        cls.db = SessionLocal()

    @classmethod
    def tearDownClass(cls):
        cls.db.close()

    def test_pillar1_catalyst_alignment_and_impact(self):
        dates = pd.date_range("2023-01-01", periods=100, freq="h", tz="UTC")
        df = pd.DataFrame({
            "timestamp": dates,
            "open": [2000.0 + i * 0.1 for i in range(100)],
            "high": [2005.0 + i * 0.1 for i in range(100)],
            "low": [1995.0 + i * 0.1 for i in range(100)],
            "close": [2002.0 + i * 0.1 for i in range(100)],
            "volume": [1000.0] * 100,
        })

        catalysts = get_default_catalysts(symbol="XAUUSD")
        self.assertGreater(len(catalysts), 0)

        aligned = align_catalysts_with_bars(df, catalysts, window_hours=12.0)
        self.assertIn("nearest_catalyst_title", aligned.columns)
        self.assertIn("in_catalyst_window", aligned.columns)

        impact = compute_catalyst_regime_impact(aligned)
        self.assertIn("range_multiplier", impact)
        self.assertIn("vol_spike_ratio", impact)

        brief = generate_catalyst_regime_brief(df, catalysts, symbol="XAUUSD")
        self.assertIsInstance(brief, CatalystBriefOutput)
        self.assertIn("XAUUSD", brief.symbol)
        self.assertGreater(len(brief.executive_brief), 20)

    def test_pillar2_guardrail_rule_evaluations(self):
        profile = RiskRuleProfile(
            max_risk_per_trade_pct=0.01,
            daily_loss_limit_pct=0.03,
            max_drawdown_pct=0.15,
            drawdown_mode="trailing",
            max_consecutive_losses=3,
            cooldown_bars=6,
            max_trades_per_day=4,
        )

        now = datetime.now(timezone.utc)

        # 1. Normal allowed trade
        res_ok = evaluate_proposed_trade(
            profile=profile,
            current_equity=10000.0,
            current_cash=10000.0,
            high_water_mark=10000.0,
            daily_start_equity=10000.0,
            today_trades_count=1,
            consecutive_losses_count=0,
            cooldown_remaining=0,
            proposed_risk_pct=0.01,
            proposed_size=2.0,
            current_ts=now,
        )
        self.assertTrue(res_ok.allowed)
        self.assertEqual(res_ok.adjusted_size, 2.0)
        self.assertEqual(len(res_ok.breached_rules), 0)

        # 2. Daily loss limit breach (down 4% today)
        res_daily_loss = evaluate_proposed_trade(
            profile=profile,
            current_equity=9600.0,
            current_cash=9600.0,
            high_water_mark=10000.0,
            daily_start_equity=10000.0,
            today_trades_count=2,
            consecutive_losses_count=1,
            cooldown_remaining=0,
            proposed_risk_pct=0.01,
            proposed_size=2.0,
            current_ts=now,
        )
        self.assertFalse(res_daily_loss.allowed)
        self.assertEqual(res_daily_loss.adjusted_size, 0.0)
        self.assertTrue(any(b.rule_name == "daily_loss_limit_pct" for b in res_daily_loss.breached_rules))

        # 3. Consecutive losses cooldown
        res_cooldown = evaluate_proposed_trade(
            profile=profile,
            current_equity=9800.0,
            current_cash=9800.0,
            high_water_mark=10000.0,
            daily_start_equity=9900.0,
            today_trades_count=2,
            consecutive_losses_count=3,
            cooldown_remaining=4,
            proposed_risk_pct=0.01,
            proposed_size=2.0,
            current_ts=now,
        )
        self.assertFalse(res_cooldown.allowed)
        self.assertTrue(any(b.rule_name == "consecutive_losses_cooldown" for b in res_cooldown.breached_rules))

        # 4. Oversized risk (clamp size)
        res_oversize = evaluate_proposed_trade(
            profile=profile,
            current_equity=10000.0,
            current_cash=10000.0,
            high_water_mark=10000.0,
            daily_start_equity=10000.0,
            today_trades_count=1,
            consecutive_losses_count=0,
            cooldown_remaining=0,
            proposed_risk_pct=0.02,  # exceeds 0.01 limit
            proposed_size=4.0,
            current_ts=now,
        )
        self.assertTrue(res_oversize.allowed)
        self.assertAlmostEqual(res_oversize.adjusted_size, 2.0, places=2)
        self.assertTrue(any(b.rule_name == "max_risk_per_trade_pct" for b in res_oversize.breached_rules))

    def test_pillar2_guardrail_audit_against_trade_log(self):
        profile = RiskRuleProfile(
            daily_loss_limit_pct=0.02,
            max_drawdown_pct=0.10,
            max_consecutive_losses=2,
        )
        t1 = datetime(2023, 1, 1, 10, 0, tzinfo=timezone.utc)
        t2 = datetime(2023, 1, 1, 14, 0, tzinfo=timezone.utc)
        t3 = datetime(2023, 1, 1, 16, 0, tzinfo=timezone.utc)
        t4 = datetime(2023, 1, 2, 10, 0, tzinfo=timezone.utc)

        trades = [
            TradeRecord(1, "XAUUSD", "long", t1, t1, 1900.0, 1870.0, 1.0, -250.0, -250.0, -2.5, 0.0, 0.0, "sl", 2),
            TradeRecord(2, "XAUUSD", "long", t2, t2, 1870.0, 1850.0, 1.0, -200.0, -200.0, -2.0, 0.0, 0.0, "sl", 2),
            TradeRecord(3, "XAUUSD", "long", t3, t3, 1850.0, 1820.0, 1.0, -300.0, -300.0, -3.0, 0.0, 0.0, "sl", 2),
            TradeRecord(4, "XAUUSD", "long", t4, t4, 1820.0, 1860.0, 1.0, 400.0, 400.0, 4.0, 0.0, 0.0, "tp", 5),
        ]

        audit = audit_trade_log_against_guardrails(profile, trades, [], initial_capital=10000.0)
        self.assertIsInstance(audit, GuardrailAuditReport)
        self.assertGreater(audit.breach_count, 0)
        self.assertGreater(audit.capital_lost_to_breaches, 0.0)
        self.assertGreater(audit.counterfactual_final_equity, audit.actual_final_equity)

    def test_pillar3_walk_forward_and_stress(self):
        dates = pd.date_range("2023-01-01", periods=450, freq="h")
        df = pd.DataFrame({
            "timestamp": dates,
            "open": [2000.0 + np.sin(i / 10.0) * 20.0 for i in range(450)],
            "high": [2005.0 + np.sin(i / 10.0) * 20.0 for i in range(450)],
            "low": [1995.0 + np.sin(i / 10.0) * 20.0 for i in range(450)],
            "close": [2002.0 + np.sin(i / 10.0) * 20.0 for i in range(450)],
            "volume": [1000.0] * 450,
        })

        cfg = WalkForwardConfig(train_bars=250, test_bars=80, step_bars=80, mode="rolling")
        wf_res = run_walk_forward_analysis("rsi", df, config=cfg)
        self.assertIsInstance(wf_res, WalkForwardAnalysisResult)
        self.assertGreater(wf_res.num_windows, 0)
        self.assertIn(wf_res.robustness_verdict, ["ROBUST", "BORDERLINE", "OVERFIT"])

        # Stress testing
        stress_reports = run_stress_battery("rsi", df, params={"rsi_period": 14})
        self.assertGreaterEqual(len(stress_reports), 3)
        for r in stress_reports:
            self.assertIn(r.status, ["PASS", "DEGRADED", "FAILED"])

    def test_pillar4_dynamic_portfolio_risk(self):
        # 1. Vol targeting scale
        mult_calm = compute_volatility_targeting_multiplier(7.5, VolatilityTargetConfig(target_annual_vol_pct=15.0))
        self.assertEqual(mult_calm, 2.0)

        mult_spike = compute_volatility_targeting_multiplier(30.0, VolatilityTargetConfig(target_annual_vol_pct=15.0))
        self.assertEqual(mult_spike, 0.5)

        # 2. Underwater tracker
        t0 = datetime(2023, 1, 1, tzinfo=timezone.utc)
        pts = [
            EquityPoint(t0, 10000.0, 10000.0, 0.0, 0.0, 0.0),
            EquityPoint(t0, 9500.0, 9500.0, 500.0, 5.0, -0.05),
            EquityPoint(t0, 9200.0, 9200.0, 800.0, 8.0, -0.03),
        ]
        underwater = track_underwater_state(pts)
        self.assertAlmostEqual(underwater.current_drawdown_pct, 8.0, places=1)
        self.assertFalse(underwater.is_at_high_water_mark)

        # 3. Snapshot
        snap = generate_portfolio_risk_snapshot(
            current_equity=9200.0,
            daily_start_equity=9500.0,
            equity_series=pts,
            current_realized_vol=18.0,
            daily_limit_pct=3.0,
            max_limit_pct=15.0,
        )
        self.assertIsInstance(snap, PortfolioRiskSnapshot)
        self.assertIn(snap.recommended_action, ["NORMAL", "TRIM_EXPOSURE", "HALT"])

    def test_pillar5_personal_cash_flow_planner(self):
        flows = [
            CashFlowItem(name="Salary", amount=8000.0, flow_type="income", frequency="monthly", is_fixed=True),
            CashFlowItem(name="Rent", amount=2500.0, flow_type="expense", frequency="monthly", is_fixed=True),
            CashFlowItem(name="Living", amount=1500.0, flow_type="expense", frequency="monthly", is_fixed=True),
        ]
        cf = calculate_cash_flow_and_runway(flows, liquid_reserves=24000.0)
        self.assertEqual(cf["net_cashflow"], 4000.0)
        self.assertEqual(cf["savings_rate_pct"], 50.0)
        self.assertEqual(cf["runway"].runway_months, 6.0)
        self.assertEqual(cf["runway"].health_status, "ROBUST")

        # Debt elimination comparison
        debts = [
            DebtItem(name="Card", balance=3000.0, interest_rate_pct=20.0, minimum_payment=100.0),
            DebtItem(name="Loan", balance=10000.0, interest_rate_pct=6.0, minimum_payment=150.0),
        ]
        debt_sims = simulate_debt_payoff(debts, extra_monthly_payment=500.0)
        self.assertEqual(len(debt_sims), 2)
        # Avalanche interest should be <= Snowball interest
        self.assertLessEqual(debt_sims[0].total_interest_paid, debt_sims[1].total_interest_paid + 1.0)

        # Compound tax drag simulation
        proj = simulate_compound_tax_drag(initial_capital=10000.0, monthly_contribution=1000.0, years=5)
        self.assertEqual(len(proj), 5)
        self.assertGreater(proj[-1].cumulative_drag_dollars, 0.0)

        # Full plan
        plan = generate_comprehensive_financial_plan(flows, liquid_reserves=24000.0, debts=debts)
        self.assertIsInstance(plan, FinancialPlanOutput)
        self.assertIn("not provide certified financial", str(plan.disclaimer))

    def test_pillars_api_endpoints(self):
        email = f"pillar_tester_{int(time.time())}@quantedge.io"
        u, ws = auth_service.create_user_with_workspace(
            self.db, email=email, password="Password123!", workspace_name="Pillar Lab"
        )

        # 1. Research Catalysts
        cats = research_router.list_catalysts(symbol="XAUUSD", limit=10, db=self.db, workspace=ws)
        self.assertGreater(len(cats), 0)

        # 2. Risk Profiles & Evaluate
        profs = risk_router.list_profiles(db=self.db, workspace=ws)
        self.assertGreater(len(profs), 0)

        eval_order = risk_router.evaluate_trade(
            payload=risk_router.EvaluateOrderRequest(proposed_risk_pct=0.01, proposed_size=1.0),
            db=self.db,
            workspace=ws,
        )
        self.assertIsInstance(eval_order, GuardrailEvaluationResult)

        # 3. Portfolio Risk Monitor
        monitor = risk_router.get_portfolio_risk_monitor(target_vol_pct=15.0, db=self.db, workspace=ws)
        self.assertIsInstance(monitor, PortfolioRiskSnapshot)

        # 4. Finance Plan
        fplan = finance_router.calculate_plan(
            payload=finance_router.PlanRequest(liquid_reserves=20000.0),
            db=self.db,
            current_user=u,
            workspace=ws,
        )
        self.assertIsInstance(fplan, FinancialPlanOutput)
        self.assertIn(fplan.emergency_runway.health_status, ["ADEQUATE", "ROBUST"])


if __name__ == "__main__":
    unittest.main(verbosity=2)
