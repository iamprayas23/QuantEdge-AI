"""Portfolio Manager Agent (Chief Investment Officer / Synthesis)

Reconciles analyst signals (Technicals, Regime) with Risk Management constraints
to formulate an actionable strategy proposal with human-in-the-loop confirmation.
"""
from typing import Dict, Any, Optional
from core.ai.schemas import AnalystSignal, RiskAssessment, PortfolioProposal
from core.ai.provider import LLMProvider


class PortfolioManagerAgent:
    def __init__(self, provider: Optional[LLMProvider] = None):
        self.provider = provider or LLMProvider()

    def evaluate(
        self,
        symbol: str,
        technicals: AnalystSignal,
        regime: AnalystSignal,
        risk: RiskAssessment,
        current_parameters: Optional[Dict[str, Any]] = None,
    ) -> PortfolioProposal:
        """
        Synthesize all inputs into a final, actionable portfolio decision.
        """
        params = current_parameters.copy() if current_parameters else {}

        # Default recommended parameters
        recommended_params = {
            "rsi_period": params.get("rsi_period", 14),
            "oversold": params.get("oversold", 30.0),
            "overbought": params.get("overbought", 70.0),
            "risk_per_trade_pct": risk.max_risk_per_trade_pct,
            "risk_reward_ratio": params.get("risk_reward_ratio", 2.0),
            "sl_atr_mult": params.get("sl_atr_mult", 1.5),
            "max_bars_held": params.get("max_bars_held", 48),
        }

        # Rule synthesis
        if risk.allowed_action == "HALT":
            target_action = "HOLD"
            allocation_pct = 0.0
            urgency = "PATIENT"
            reasoning = (
                f"Risk Manager issued a HALT condition for {symbol}. Capital preservation active: "
                f"no new entries permitted. Warnings: {'; '.join(risk.risk_warnings)}."
            )
        elif technicals.signal == "BULLISH" and regime.signal in ("BULLISH", "NEUTRAL"):
            target_action = "BUY"
            allocation_pct = 100.0 if risk.allowed_action == "PERMIT" else 50.0
            urgency = "NORMAL"
            reasoning = (
                f"Confluence detected: Technicals are BULLISH (confidence: {technicals.confidence:.2f}) "
                f"and Regime is {regime.signal}. Risk Manager allows {risk.allowed_action} "
                f"with max {risk.max_risk_per_trade_pct * 100:.2f}% risk per trade."
            )
        elif technicals.signal == "BEARISH" and regime.signal in ("BEARISH", "NEUTRAL"):
            target_action = "SELL"
            allocation_pct = 100.0 if risk.allowed_action == "PERMIT" else 50.0
            urgency = "NORMAL"
            reasoning = (
                f"Bearish alignment: Technicals are BEARISH (confidence: {technicals.confidence:.2f}) "
                f"and Regime is {regime.signal}. Target action is SELL or short hedged."
            )
        else:
            # Conflicting signals
            target_action = "HOLD"
            allocation_pct = 0.0
            urgency = "PATIENT"
            reasoning = (
                f"Divergent signals between Technicals ({technicals.signal}) and Regime ({regime.signal}). "
                f"Prudent stance is HOLD pending directional clarification."
            )

        # ATR stop adjustments
        sl_mult = 1.5
        if "high_vol" in str(regime.metrics_grounding.get("vol_regime", "")):
            sl_mult = 2.0
            recommended_params["sl_atr_mult"] = 2.0

        tp_mult = sl_mult * float(recommended_params.get("risk_reward_ratio", 2.0))

        # Optional LLM refinement
        system_prompt = (
            "You are a Chief Investment Officer (CIO) leading a quantitative committee. "
            "Synthesize technicals, regime, and risk reports into a JSON decision with keys: "
            "'target_action' (BUY/SELL/HOLD), 'target_allocation_pct' (0-100), "
            "'execution_urgency' (PATIENT/NORMAL/IMMEDIATE), and 'reasoning'."
        )
        user_prompt = (
            f"Asset: {symbol}\n"
            f"Technicals: {technicals.signal} (Conf: {technicals.confidence:.2f}) - {technicals.rationale}\n"
            f"Regime: {regime.signal} (Conf: {regime.confidence:.2f}) - {regime.rationale}\n"
            f"Risk: {risk.allowed_action} (Max Risk: {risk.max_risk_per_trade_pct * 100:.2f}%) - {risk.rationale}\n"
            f"Initial CIO view: Action={target_action}, Allocation={allocation_pct}%."
        )

        llm_res = self.provider.generate_json(user_prompt, system_prompt)
        if llm_res and isinstance(llm_res, dict):
            act = str(llm_res.get("target_action", "")).upper()
            if act in ("BUY", "SELL", "HOLD") and risk.allowed_action != "HALT":
                target_action = act
            if "target_allocation_pct" in llm_res and isinstance(llm_res["target_allocation_pct"], (int, float)):
                allocation_pct = float(min(100.0, max(0.0, llm_res["target_allocation_pct"])))
            if "execution_urgency" in llm_res and str(llm_res["execution_urgency"]).upper() in ("PATIENT", "NORMAL", "IMMEDIATE"):
                urgency = str(llm_res["execution_urgency"]).upper()
            if "reasoning" in llm_res and isinstance(llm_res["reasoning"], str):
                reasoning = llm_res["reasoning"]

        return PortfolioProposal(
            target_action=target_action,
            recommended_parameters=recommended_params,
            target_allocation_pct=round(allocation_pct, 1),
            risk_per_trade_pct=risk.max_risk_per_trade_pct,
            stop_loss_atr_mult=round(sl_mult, 2),
            take_profit_atr_mult=round(tp_mult, 2),
            execution_urgency=urgency,
            reasoning=reasoning,
            human_confirmation_required=True,
        )
