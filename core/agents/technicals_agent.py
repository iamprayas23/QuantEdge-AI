"""Technicals Analyst Agent

Evaluates causal price action, moving averages (EMA 50/200), RSI momentum,
and ATR volatility to produce a grounded technical stance.
"""
from typing import Dict, Any, Optional
from core.ai.schemas import AnalystSignal
from core.ai.provider import LLMProvider


class TechnicalsAgent:
    def __init__(self, provider: Optional[LLMProvider] = None):
        self.provider = provider or LLMProvider()

    def evaluate(
        self,
        symbol: str,
        market_summary: Dict[str, Any],
        backtest_metrics: Optional[Dict[str, Any]] = None,
    ) -> AnalystSignal:
        """
        Evaluate technical conditions using deterministic indicators with optional LLM reasoning.
        Always grounds rationale in verifiable prices and indicator levels.
        """
        last_close = float(market_summary.get("last_close", 2000.0))
        ema50 = float(market_summary.get("ema50", last_close))
        ema200 = float(market_summary.get("ema200", last_close))
        rsi14 = float(market_summary.get("rsi14", 50.0))
        atr14 = float(market_summary.get("atr14", 10.0))

        # Deterministic Grounded Evaluation
        bullish_score = 0
        bearish_score = 0

        # Moving average alignment
        if last_close > ema50 > ema200:
            bullish_score += 2
        elif last_close < ema50 < ema200:
            bearish_score += 2
        elif last_close > ema50:
            bullish_score += 1
        elif last_close < ema50:
            bearish_score += 1

        # RSI momentum & mean-reversion
        if rsi14 < 30.0:
            bullish_score += 2  # Oversold mean reversion
        elif rsi14 > 70.0:
            bearish_score += 2  # Overbought pullback
        elif 50.0 <= rsi14 < 65.0:
            bullish_score += 1
        elif 35.0 < rsi14 < 50.0:
            bearish_score += 1

        total_score = bullish_score + bearish_score
        if total_score == 0:
            total_score = 1

        if bullish_score > bearish_score:
            signal = "BULLISH"
            confidence = round(min(0.85, 0.50 + (bullish_score / 6.0) * 0.35), 2)
            rationale = (
                f"{symbol} exhibits bullish structure. Price ({last_close:.2f}) trades above EMA50 ({ema50:.2f}) "
                f"and EMA200 ({ema200:.2f}) with RSI at {rsi14:.1f} and ATR of {atr14:.2f}."
            )
        elif bearish_score > bullish_score:
            signal = "BEARISH"
            confidence = round(min(0.85, 0.50 + (bearish_score / 6.0) * 0.35), 2)
            rationale = (
                f"{symbol} exhibits bearish pressure. Price ({last_close:.2f}) trades below EMA50 ({ema50:.2f}) "
                f"and EMA200 ({ema200:.2f}) with RSI at {rsi14:.1f} and ATR of {atr14:.2f}."
            )
        else:
            signal = "NEUTRAL"
            confidence = 0.50
            rationale = (
                f"{symbol} is in a neutral consolidation phase near EMA50 ({ema50:.2f}) "
                f"with balanced RSI at {rsi14:.1f}."
            )

        grounding = {
            "last_close": last_close,
            "ema50": round(ema50, 2),
            "ema200": round(ema200, 2),
            "rsi14": round(rsi14, 2),
            "atr14": round(atr14, 2),
        }

        # Attempt LLM enrichment if available
        system_prompt = (
            "You are a quantitative technicals analyst. Given verifiable market metrics, "
            "provide a concise JSON response with keys: 'signal' (BULLISH/BEARISH/NEUTRAL), "
            "'confidence' (0.0 to 1.0), and 'rationale'. Never hallucinate prices or indicators."
        )
        user_prompt = (
            f"Asset: {symbol}\n"
            f"Metrics: Last Close={last_close:.2f}, EMA50={ema50:.2f}, EMA200={ema200:.2f}, "
            f"RSI14={rsi14:.1f}, ATR14={atr14:.2f}."
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
            agent_name="technicals",
            signal=signal,
            confidence=confidence,
            rationale=rationale,
            metrics_grounding=grounding,
            suggested_adjustments={"rsi_period": 14, "sl_atr_mult": 1.5},
        )
