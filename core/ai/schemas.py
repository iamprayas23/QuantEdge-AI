"""Pydantic Schemas for Grounded AI Layer & Multi-Agent Committee

Enforces strict typed contracts, zero hallucinations, explicit risk disclosures,
concrete numerical grounding, and human-in-the-loop confirmation.
"""
from datetime import datetime
from typing import Dict, Any, List, Optional, Literal
from pydantic import BaseModel, Field


# =========================================================================
# 1. Strategy-to-Spec Assistant Schemas
# =========================================================================

class ParameterSpec(BaseModel):
    name: str = Field(..., description="Parameter key name (e.g., rsi_period)")
    value: Any = Field(..., description="Validated parameter value")
    type: Literal["int", "float", "string", "bool"] = Field(..., description="Data type")
    description: str = Field(..., description="Human-readable explanation of this parameter")
    bounds_applied: Optional[str] = Field(None, description="Any clamping or validation bounds enforced")


class ValidationFinding(BaseModel):
    severity: Literal["INFO", "WARNING", "ERROR"] = Field(..., description="Finding severity")
    message: str = Field(..., description="Specific finding or ambiguity in the user prompt")
    recommendation: str = Field(..., description="Actionable suggestion or correction")


class StrategySpecOutput(BaseModel):
    hypothesis_summary: str = Field(..., description="Summarized quantitative trading hypothesis")
    strategy_type: Literal["rsi", "divergence"] = Field(..., description="Target strategy archetype")
    symbol: str = Field(default="XAUUSD", description="Target asset symbol")
    timeframe: str = Field(default="1H", description="Target timeframe")
    parameters: Dict[str, Any] = Field(..., description="Machine-executable parameter dictionary")
    parameter_breakdown: List[ParameterSpec] = Field(default_factory=list, description="Detailed parameter list")
    validation_findings: List[ValidationFinding] = Field(default_factory=list, description="Validation issues or warnings")
    human_confirmation_required: bool = Field(default=True, description="Always requires human confirmation before live run")
    disclaimer: str = Field(
        default="AI-generated specifications are hypotheses for research only. Past performance does not guarantee future results.",
        description="Standard quantitative compliance disclosure"
    )


# =========================================================================
# 2. Automated Backtest & Regime Critique Schemas
# =========================================================================

class OverfittingRisk(BaseModel):
    risk_level: Literal["LOW", "MODERATE", "HIGH", "SEVERE"] = Field(..., description="Overfitting risk classification")
    sample_size_flag: bool = Field(..., description="True if trade count is too low (< 30 trades)")
    trade_count_observed: int = Field(..., description="Actual trade count cited from the backtest run")
    parameter_sensitivity_warning: Optional[str] = Field(None, description="Warning regarding narrow parameter tuning")
    rationale: str = Field(..., description="Concrete explanation citing specific metrics")


class RegimePerformance(BaseModel):
    regime: str = Field(..., description="Market regime (e.g., Trending Bull, Trending Bear, Ranging, High Volatility)")
    suitability: Literal["FAVORABLE", "NEUTRAL", "UNFAVORABLE"] = Field(..., description="Strategy suitability in this regime")
    observed_metric_note: str = Field(..., description="Grounded observation based on historical metrics")


class DrawdownAnalysis(BaseModel):
    max_drawdown_pct: float = Field(..., description="Exact max drawdown percentage from the run")
    max_drawdown_dollars: float = Field(..., description="Exact max drawdown in currency from the run")
    max_drawdown_duration_bars: int = Field(..., description="Longest underwater period in bars")
    recovery_assessment: str = Field(..., description="Assessment of recovery speed and pain tolerance")


class BacktestCritiqueOutput(BaseModel):
    run_id: str = Field(..., description="ID of the evaluated backtest run")
    executive_summary: str = Field(..., description="High-level grounded evaluation citing exact Sharpe, Return, and DD")
    exact_metrics_cited: Dict[str, Any] = Field(..., description="Verifiable metrics copied directly from run records")
    overfitting_analysis: OverfittingRisk = Field(..., description="Overfitting and degrees-of-freedom audit")
    drawdown_critique: DrawdownAnalysis = Field(..., description="In-depth underwater and tail-risk analysis")
    regime_breakdown: List[RegimePerformance] = Field(default_factory=list, description="Performance across regimes")
    key_strengths: List[str] = Field(default_factory=list, description="Evidence-backed strengths")
    key_vulnerabilities: List[str] = Field(default_factory=list, description="Evidence-backed failure modes")
    actionable_recommendations: List[str] = Field(default_factory=list, description="Concrete next steps for research")
    disclaimer: str = Field(
        default="Grounded critique is algorithmic and factual. It does not provide financial or investment advice.",
        description="Compliance notice"
    )


# =========================================================================
# 3. Multi-Agent Committee & Specialized Role Contracts
# =========================================================================

class AnalystSignal(BaseModel):
    agent_name: str = Field(..., description="Name of the analyst agent (e.g. 'technicals', 'regime')")
    signal: Literal["BULLISH", "BEARISH", "NEUTRAL"] = Field(..., description="Directional stance")
    confidence: float = Field(..., ge=0.0, le=1.0, description="Confidence score between 0.0 and 1.0")
    rationale: str = Field(..., description="Grounded qualitative and quantitative explanation")
    metrics_grounding: Dict[str, Any] = Field(default_factory=dict, description="Verifiable metrics cited directly from market data or backtest")
    suggested_adjustments: Optional[Dict[str, Any]] = Field(default=None, description="Optional parameter adjustment proposals")


class RiskAssessment(BaseModel):
    max_risk_per_trade_pct: float = Field(..., description="Maximum prudent risk per trade percentage")
    max_drawdown_limit_pct: float = Field(default=20.0, description="Drawdown risk threshold")
    allowed_action: Literal["PERMIT", "RESTRICT", "HALT"] = Field(..., description="Risk manager authorization gate")
    volatility_assessment: str = Field(..., description="Current volatility regime impact")
    risk_warnings: List[str] = Field(default_factory=list, description="Identified tail-risk or sample-size warnings")
    rationale: str = Field(..., description="Risk manager rationale citing exact numbers")


class PortfolioProposal(BaseModel):
    target_action: Literal["BUY", "SELL", "HOLD"] = Field(..., description="Recommended portfolio decision")
    recommended_parameters: Dict[str, Any] = Field(default_factory=dict, description="Synthesized strategy parameters")
    target_allocation_pct: float = Field(default=100.0, ge=0.0, le=100.0, description="Capital allocation percentage")
    risk_per_trade_pct: float = Field(default=0.01, ge=0.0, le=0.05, description="Recommended risk per trade")
    stop_loss_atr_mult: float = Field(default=1.5, description="Recommended SL ATR multiple")
    take_profit_atr_mult: float = Field(default=3.0, description="Recommended TP ATR multiple")
    execution_urgency: Literal["PATIENT", "NORMAL", "IMMEDIATE"] = Field(default="NORMAL", description="Execution stance")
    reasoning: str = Field(..., description="CIO synthesis and resolution of conflicting analyst votes")
    human_confirmation_required: bool = Field(default=True, description="Strict human-in-the-loop requirement before applying changes")


class CommitteeReviewOutput(BaseModel):
    id: str = Field(..., description="Unique ID for this committee report")
    symbol: str = Field(default="XAUUSD", description="Asset symbol evaluated")
    timeframe: str = Field(default="1H", description="Timeframe evaluated")
    as_of_ts: str = Field(..., description="Timestamp of evaluation")
    strategy_version_id: Optional[str] = Field(None, description="Linked strategy version ID if provided")
    backtest_run_id: Optional[str] = Field(None, description="Linked backtest run ID if provided")
    analyst_signals: Dict[str, AnalystSignal] = Field(..., description="Individual analyst outputs")
    risk_assessment: RiskAssessment = Field(..., description="Independent risk manager audit")
    portfolio_proposal: PortfolioProposal = Field(..., description="Final CIO portfolio manager decision")
    executive_summary: str = Field(..., description="High-level committee consensus summary")
    human_confirmation_required: bool = Field(default=True, description="Enforced human sign-off flag")
    disclaimer: str = Field(
        default="Multi-agent committee outputs are algorithmic research aids. They do not constitute financial advice or automated execution.",
        description="Quantitative compliance disclosure"
    )
