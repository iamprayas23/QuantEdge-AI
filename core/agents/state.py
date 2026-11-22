"""Multi-Agent Shared State & Typed Context Contract

Defines the shared state structure passed across committee agent nodes.
Maintains pure zero-lookahead grounding and strict Pydantic validation.
"""
from datetime import datetime
from typing import Dict, Any, List, Optional
from pydantic import BaseModel, Field

from core.ai.schemas import (
    AnalystSignal,
    RiskAssessment,
    PortfolioProposal,
    CommitteeReviewOutput,
)


class AgentState(BaseModel):
    """
    Shared context container passed across the quantitative committee.
    Contains grounded market observations, backtest metrics, and agent outputs.
    """
    symbol: str = Field(default="XAUUSD", description="Market asset ticker")
    timeframe: str = Field(default="1H", description="Timeframe of evaluation")
    as_of_ts: str = Field(default_factory=lambda: datetime.utcnow().isoformat() + "Z")

    strategy_version_id: Optional[str] = Field(None, description="Linked strategy version UUID if provided")
    backtest_run_id: Optional[str] = Field(None, description="Linked backtest run UUID if provided")

    # Grounded Market Data Summary
    market_data_summary: Dict[str, Any] = Field(
        default_factory=dict,
        description="Deterministic features computed from closed candles (close, RSI, ATR, EMAs, etc.)"
    )

    # Historical Backtest Metrics (if evaluating a strategy run)
    backtest_metrics: Optional[Dict[str, Any]] = Field(
        default=None,
        description="Realized backtest statistics (Sharpe, max DD, win rate, total trades)"
    )

    # Market Regime Data
    regime_data: Optional[Dict[str, Any]] = Field(
        default=None,
        description="Regime classification (vol_regime, trend_regime, realized_vol)"
    )

    # Agent Outputs
    analyst_signals: Dict[str, AnalystSignal] = Field(
        default_factory=dict,
        description="Outputs from analyst nodes (technicals, regime)"
    )
    risk_assessment: Optional[RiskAssessment] = Field(
        default=None,
        description="Independent risk management evaluation and capital limits"
    )
    portfolio_proposal: Optional[PortfolioProposal] = Field(
        default=None,
        description="CIO synthesis and actionable strategy recommendations"
    )

    executive_summary: Optional[str] = Field(
        default=None,
        description="Committee consensus overview"
    )
    human_confirmation_required: bool = Field(
        default=True,
        description="Always enforces human review before applying strategy changes"
    )

    def to_review_output(self, report_id: str) -> CommitteeReviewOutput:
        """Export state into the API-facing CommitteeReviewOutput model."""
        if not self.risk_assessment:
            raise ValueError("State missing risk_assessment")
        if not self.portfolio_proposal:
            raise ValueError("State missing portfolio_proposal")

        return CommitteeReviewOutput(
            id=report_id,
            symbol=self.symbol,
            timeframe=self.timeframe,
            as_of_ts=self.as_of_ts,
            strategy_version_id=self.strategy_version_id,
            backtest_run_id=self.backtest_run_id,
            analyst_signals=self.analyst_signals,
            risk_assessment=self.risk_assessment,
            portfolio_proposal=self.portfolio_proposal,
            executive_summary=self.executive_summary or "Multi-agent committee review complete.",
            human_confirmation_required=True,
        )
