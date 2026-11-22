"""Regime & Volatility Analyst Agent

Evaluates rolling realized volatility regimes and directional trend structure
using core/research/regimes.py metrics.
"""
from typing import Dict, Any, Optional
from core.ai.schemas import AnalystSignal
from core.ai.provider import LLMProvider


class RegimeAgent:
    def __init__(self, provider: Optional[LLMProvider] = None):
        self.provider = provider or LLMProvider()

    def evaluate(
        self,
        symbol: str,
        regime_data: Dict[str, Any],
        market_summary: Optional[Dict[str, Any]] = None,
    ) -> AnalystSignal:
        """
        Evaluate market regime (volatility and trend) using deterministic metrics.
        """
        vol_regime = regime_data.get("vol_regime", "medium_vol")
        trend_regime = regime_data.get("trend_regime", "ranging")
        realized_vol = float(regime_data.get("realized_vol_pct", 15.0))

        # Grounded heuristic evaluation
        if trend_regime == "trending_bull":
            signal = "BULLISH"
            confidence = 0.75
            rationale = (
                f"Market regime is bullish trending with {vol_regime.replace('_', ' ')} "
                f"(realized volatility: {realized_vol:.1f}%). Trend continuity is favorable."
            )
        elif trend_regime == "trending_bear":
            signal = "BEARISH"
            confidence = 0.75
            rationale = (
                f"Market regime is bearish trending with {vol_regime.replace('_', ' ')} "
                f"(realized volatility: {realized_vol:.1f}%). Downward momentum dominates."
            )
        else:
            signal = "NEUTRAL"
            confidence = 0.65
            rationale = (
                f"Market regime is mean-reverting/ranging with {vol_regime.replace('_', ' ')} "
                f"(realized volatility: {realized_vol:.1f}%). Suitable for oscillator boundaries."
            )

        grounding = {
            "vol_regime": vol_regime,
            "trend_regime": trend_regime,
            "realized_vol_pct": round(realized_vol, 2),
        }

        # Optional LLM enrichment
        system_prompt = (
            "You are a quantitative macro and regime analyst. Given volatility and trend classification, "
            "return JSON with 'signal' (BULLISH/BEARISH/NEUTRAL), 'confidence' (0.0 to 1.0), and 'rationale'."
        )
        user_prompt = (
            f"Asset: {symbol}\n"
            f"Regime: Volatility={vol_regime}, Trend={trend_regime}, Realized Vol={realized_vol:.1f}%."
        )

        llm_res = self.provider.generate_json(user_prompt, system_prompt)
        if llm_res and isinstance(llm_res, dict):
            llm_sig = str(llm_res.get("signal", "")).upper()
            if llm_sig in ("BULLISH", "BEARISH", "NEUTRAL"):
                signal = llm_sig
                if "confidence" in llm_res and isinstance(llm_res["confidence"], (int, float)):
                    confidence = float(min(1.0, max(0.0, llm_res["confidence"])))
                if "rationale" in llm_res and isinstance(llm_res["rationale"], str):
                    rationale = llm_res["rationale"]

        return AnalystSignal(
            agent_name="regime",
            signal=signal,
            confidence=confidence,
            rationale=rationale,
            metrics_grounding=grounding,
            suggested_adjustments={
                "vol_regime": vol_regime,
                "recommended_buffer_atr": 0.3 if vol_regime == "high_vol" else 0.15,
            },
        )
