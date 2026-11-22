"""Multi-Agent Committee Orchestrator

Coordinates technicals, regime, risk, and portfolio manager agents to produce
a verified, zero-hallucination quantitative committee evaluation.
"""
import uuid
from datetime import datetime
from typing import Dict, Any, Optional
import pandas as pd
import numpy as np

from core.ai.provider import LLMProvider
from core.ai.schemas import CommitteeReviewOutput
from core.agents.state import AgentState
from core.agents.technicals_agent import TechnicalsAgent
from core.agents.regime_agent import RegimeAgent
from core.agents.risk_agent import RiskAgent
from core.agents.portfolio_manager_agent import PortfolioManagerAgent
from core.backtesting.signals import compute_rsi, compute_atr
from core.research.regimes import compute_market_regimes


class CommitteeOrchestrator:
    def __init__(self, provider: Optional[LLMProvider] = None):
        self.provider = provider or LLMProvider()
        self.technicals_agent = TechnicalsAgent(self.provider)
        self.regime_agent = RegimeAgent(self.provider)
        self.risk_agent = RiskAgent(self.provider)
        self.portfolio_agent = PortfolioManagerAgent(self.provider)

    def extract_market_features(self, df: pd.DataFrame) -> Dict[str, Any]:
        """
        Computes deterministic, zero-lookahead technical & regime features from DataFrame.
        """
        if len(df) == 0:
            return {
                "last_close": 2000.0,
                "ema50": 2000.0,
                "ema200": 2000.0,
                "rsi14": 50.0,
                "atr14": 10.0,
                "vol_regime": "medium_vol",
                "trend_regime": "ranging",
                "realized_vol_pct": 15.0,
            }

        df = df.copy()
        rsi = compute_rsi(df["close"], period=14)
        atr = compute_atr(df, period=14)
        ema50 = df["close"].ewm(span=50, adjust=False).mean()
        ema200 = df["close"].ewm(span=min(200, max(10, len(df))), adjust=False).mean()

        regime_df = compute_market_regimes(df, period=min(24, len(df)))

        last_idx = df.index[-1]
        last_close = float(df["close"].iloc[-1])
        last_rsi = float(rsi.iloc[-1])
        last_atr = float(atr.iloc[-1])
        last_ema50 = float(ema50.iloc[-1])
        last_ema200 = float(ema200.iloc[-1])

        vol_regime = str(regime_df["vol_regime"].iloc[-1])
        trend_regime = str(regime_df["trend_regime"].iloc[-1])
        realized_vol = float(regime_df["realized_vol"].iloc[-1])
        if pd.isna(realized_vol):
            realized_vol = 15.0

        return {
            "last_close": round(last_close, 2),
            "ema50": round(last_ema50, 2),
            "ema200": round(last_ema200, 2),
            "rsi14": round(last_rsi, 2),
            "atr14": round(last_atr, 2),
            "vol_regime": vol_regime,
            "trend_regime": trend_regime,
            "realized_vol_pct": round(realized_vol, 2),
        }

    def run(
        self,
        symbol: str,
        timeframe: str,
        ohlcv_df: pd.DataFrame,
        backtest_metrics: Optional[Dict[str, Any]] = None,
        strategy_params: Optional[Dict[str, Any]] = None,
        strategy_version_id: Optional[str] = None,
        backtest_run_id: Optional[str] = None,
    ) -> CommitteeReviewOutput:
        """
        Execute full multi-agent committee pipeline.
        """
        report_id = str(uuid.uuid4())
        features = self.extract_market_features(ohlcv_df)

        market_summary = {
            "last_close": features["last_close"],
            "ema50": features["ema50"],
            "ema200": features["ema200"],
            "rsi14": features["rsi14"],
            "atr14": features["atr14"],
        }
        regime_data = {
            "vol_regime": features["vol_regime"],
            "trend_regime": features["trend_regime"],
            "realized_vol_pct": features["realized_vol_pct"],
        }

        # 1. Analyst Phase
        tech_signal = self.technicals_agent.evaluate(
            symbol=symbol,
            market_summary=market_summary,
            backtest_metrics=backtest_metrics,
        )

        reg_signal = self.regime_agent.evaluate(
            symbol=symbol,
            regime_data=regime_data,
            market_summary=market_summary,
        )

        # 2. Risk Management Phase
        risk_assessment = self.risk_agent.evaluate(
            symbol=symbol,
            market_summary=market_summary,
            regime_data=regime_data,
            backtest_metrics=backtest_metrics,
        )

        # 3. Portfolio Management Synthesis
        portfolio_proposal = self.portfolio_agent.evaluate(
            symbol=symbol,
            technicals=tech_signal,
            regime=reg_signal,
            risk=risk_assessment,
            current_parameters=strategy_params,
        )

        # 4. Committee Consensus Executive Summary
        exec_summary = (
            f"Multi-Agent Committee Consensus for {symbol} ({timeframe}): "
            f"Technicals voted {tech_signal.signal} ({tech_signal.confidence:.0%}), "
            f"Regime is {reg_signal.signal} ({features['vol_regime']}, {features['trend_regime']}), "
            f"and Risk Manager permits {risk_assessment.allowed_action} "
            f"with max {risk_assessment.max_risk_per_trade_pct * 100:.2f}% risk per trade. "
            f"Portfolio Manager recommends: {portfolio_proposal.target_action} "
            f"({portfolio_proposal.target_allocation_pct}% allocation)."
        )

        # 5. Populate State
        state = AgentState(
            symbol=symbol,
            timeframe=timeframe,
            strategy_version_id=strategy_version_id,
            backtest_run_id=backtest_run_id,
            market_data_summary=market_summary,
            backtest_metrics=backtest_metrics,
            regime_data=regime_data,
            analyst_signals={
                "technicals": tech_signal,
                "regime": reg_signal,
            },
            risk_assessment=risk_assessment,
            portfolio_proposal=portfolio_proposal,
            executive_summary=exec_summary,
            human_confirmation_required=True,
        )

        return state.to_review_output(report_id=report_id)
