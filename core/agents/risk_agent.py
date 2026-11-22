"""Risk Manager Agent

Enforces capital preservation, position limits, drawdown constraints,
and degrees-of-freedom / sample-size guardrails inspired by ai-hedge-fund patterns.
"""
from typing import Dict, Any, List, Optional
from core.ai.schemas import RiskAssessment
from core.ai.provider import LLMProvider


class RiskAgent:
    def __init__(self, provider: Optional[LLMProvider] = None):
        self.provider = provider or LLMProvider()

    def evaluate(
        self,
        symbol: str,
        market_summary: Dict[str, Any],
        regime_data: Optional[Dict[str, Any]] = None,
        backtest_metrics: Optional[Dict[str, Any]] = None,
    ) -> RiskAssessment:
        """
        Evaluate risk profile and mandate strict risk limits before execution.
        """
        regime = regime_data or {}
        vol_regime = regime.get("vol_regime", "medium_vol")
        realized_vol = float(regime.get("realized_vol_pct", 15.0))

        risk_warnings: List[str] = []
        max_risk_pct = 0.01  # baseline 1.0%
        allowed_action = "PERMIT"
        max_drawdown_limit_pct = 20.0

        # Analyze backtest metrics if provided
        if backtest_metrics:
            mdd = float(backtest_metrics.get("max_drawdown", 0.0))
            trades = int(backtest_metrics.get("total_trades", 0))
            profit_factor = float(backtest_metrics.get("profit_factor", 1.0))

            if trades > 0 and trades < 30:
                risk_warnings.append(
                    f"Sample size warning: Only {trades} trades observed (< 30 min required for statistical power)."
                )
                max_risk_pct = min(max_risk_pct, 0.0075)

            if mdd >= 25.0:
                risk_warnings.append(
                    f"Severe historical drawdown of {mdd:.1f}% exceeds standard 20% limit."
                )
                allowed_action = "RESTRICT"
                max_risk_pct = 0.005  # de-risk to 0.5%
            elif mdd >= 18.0:
                risk_warnings.append(
                    f"Elevated historical drawdown ({mdd:.1f}%). Tightening risk per trade to 0.75%."
                )
                max_risk_pct = min(max_risk_pct, 0.0075)

            if profit_factor < 1.0 and trades >= 10:
                risk_warnings.append(
                    f"Unfavorable profit factor ({profit_factor:.2f} < 1.0). Strategy is unprofitable."
                )
                allowed_action = "HALT"
                max_risk_pct = 0.0

        # Adjust for market volatility
        if vol_regime == "high_vol":
            risk_warnings.append(
                f"Elevated realized volatility ({realized_vol:.1f}%). Widen stop-loss distance or reduce size."
            )
            max_risk_pct = min(max_risk_pct, 0.008)

        # Build grounded rationale
        if allowed_action == "HALT":
            rationale = (
                f"Trading halted for {symbol} due to severe risk triggers: "
                + "; ".join(risk_warnings)
            )
        elif allowed_action == "RESTRICT":
            rationale = (
                f"Capital allocation restricted for {symbol}. Risk per trade clamped to {max_risk_pct * 100:.2f}% "
                f"under {vol_regime.replace('_', ' ')} conditions. Warnings: {len(risk_warnings)}."
            )
        else:
            rationale = (
                f"Risk parameters validated for {symbol}. Permitted risk per trade: {max_risk_pct * 100:.2f}%. "
                f"Volatility is {vol_regime.replace('_', ' ')} ({realized_vol:.1f}%)."
            )

        # Optional LLM refinement
        system_prompt = (
            "You are a chief risk officer (CRO). Evaluate risk and return JSON with "
            "'allowed_action' (PERMIT/RESTRICT/HALT), 'max_risk_per_trade_pct' (float), "
            "and 'rationale'. Be conservative and adhere strictly to capital preservation."
        )
        user_prompt = (
            f"Asset: {symbol}, Volatility Regime: {vol_regime}, Realized Vol: {realized_vol:.1f}%\n"
            f"Warnings: {risk_warnings}\n"
            f"Initial permitted risk: {max_risk_pct}, Action: {allowed_action}"
        )

        llm_res = self.provider.generate_json(user_prompt, system_prompt)
        if llm_res and isinstance(llm_res, dict):
            act = str(llm_res.get("allowed_action", "")).upper()
            if act in ("PERMIT", "RESTRICT", "HALT"):
                # Safety constraint: never loosen risk beyond programmatic cap
                if act == "HALT" or (act == "RESTRICT" and allowed_action == "PERMIT"):
                    allowed_action = act
            if "rationale" in llm_res and isinstance(llm_res["rationale"], str):
                rationale = llm_res["rationale"]

        vol_assessment = f"{vol_regime.replace('_', ' ').capitalize()} ({realized_vol:.1f}% annualized)"

        return RiskAssessment(
            max_risk_per_trade_pct=round(max_risk_pct, 4),
            max_drawdown_limit_pct=max_drawdown_limit_pct,
            allowed_action=allowed_action,
            volatility_assessment=vol_assessment,
            risk_warnings=risk_warnings,
            rationale=rationale,
        )
