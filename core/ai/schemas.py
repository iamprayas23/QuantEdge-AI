"""Pydantic Schemas for Grounded AI Layer

Enforces strict typed contracts, zero hallucinations, explicit risk disclosures,
and concrete numerical grounding.
"""
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
