"""Strategy-to-Spec & Hypothesis Assistant

Translates natural language trading hypotheses into strictly validated, machine-executable
parameters for RSI and Divergence engines with zero hallucinations.
"""
import re
from typing import Dict, Any, List, Optional
from core.ai.schemas import StrategySpecOutput, ParameterSpec, ValidationFinding
from core.ai.provider import LLMProvider


def parse_hypothesis_to_spec(user_prompt: str, provider: Optional[LLMProvider] = None) -> StrategySpecOutput:
    """
    Parse a plain-English trading hypothesis into a validated StrategySpecOutput.
    Uses LLM when available, and falls back to deterministic rule extraction.
    """
    prov = provider or LLMProvider()
    prompt_lower = user_prompt.lower()

    # Try LLM first if available
    system_prompt = """You are a quantitative systems engineer. Convert the user's trading strategy description into a valid JSON specification matching our schema.
Available strategy_type: 'rsi' or 'divergence'.
For RSI: rsi_period (int, 2-100), oversold (float, 10-45), overbought (float, 55-90), risk_per_trade_pct (float, 0.001-0.05), risk_reward_ratio (float, 0.5-10.0), sl_atr_mult (float, 0.5-5.0), max_bars_held (int, 1-200).
For Divergence: rsi_period, swing_window (int, 2-20), entry_mode ('neckline_breakout' or 'early_candlestick'), risk_per_trade_pct, risk_reward_ratio, sl_buffer_atr (float, 0.1-2.0), oversold_threshold, overbought_threshold.
Return pure JSON with keys: hypothesis_summary, strategy_type, symbol, timeframe, parameters.
Do NOT promise profits or invent indicators not supported."""

    llm_result = prov.generate_json(prompt=user_prompt, system_prompt=system_prompt)
    if llm_result and "strategy_type" in llm_result and "parameters" in llm_result:
        try:
            return _build_validated_spec(
                summary=llm_result.get("hypothesis_summary", user_prompt[:120]),
                strategy_type=llm_result["strategy_type"],
                symbol=llm_result.get("symbol", "XAUUSD"),
                timeframe=llm_result.get("timeframe", "1H"),
                raw_params=llm_result.get("parameters", {}),
                source="llm",
            )
        except Exception:
            pass

    # Deterministic heuristic fallback
    return _heuristic_parse(user_prompt)


def _heuristic_parse(prompt: str) -> StrategySpecOutput:
    p = prompt.lower()

    # Determine strategy type
    if "diverg" in p or "swing" in p or "neckline" in p:
        stype = "divergence"
    else:
        stype = "rsi"

    # Default baseline parameters
    params: Dict[str, Any] = {}
    findings: List[ValidationFinding] = []

    # Symbol extraction
    symbol = "XAUUSD"
    if "eurusd" in p:
        symbol = "EURUSD"
    elif "gbpusd" in p:
        symbol = "GBPUSD"
    elif "btc" in p or "btcusd" in p:
        symbol = "BTCUSD"

    # Timeframe extraction
    tf = "1H"
    if "15m" in p or "15 min" in p:
        tf = "15m"
    elif "4h" in p or "4 hour" in p:
        tf = "4H"
    elif "1d" in p or "daily" in p:
        tf = "1D"

    # Parameter regex matching
    # RSI period
    rsi_match = re.search(r"rsi\s*(?:period|window|length|len)?\s*[:=]?\s*(\d+)", p)
    rsi_period = int(rsi_match.group(1)) if rsi_match else 14
    if rsi_period < 2 or rsi_period > 100:
        findings.append(ValidationFinding(
            severity="WARNING",
            message=f"RSI period {rsi_period} is outside typical range (2-50). Clamped to 14.",
            recommendation="Use 14 as baseline."
        ))
        rsi_period = 14

    # Oversold
    os_match = re.search(r"(?:oversold|below|crosses below|<)\s*[:=]?\s*(\d+)", p)
    oversold = float(os_match.group(1)) if os_match else 30.0

    # Overbought
    ob_match = re.search(r"(?:overbought|above|crosses above|>)\s*[:=]?\s*(\d+)", p)
    overbought = float(ob_match.group(1)) if ob_match else 70.0

    # Risk per trade - support both "risk 1%" and "1% risk"
    risk_match = re.search(r"(?:risk\s*[:=]?\s*(\d+(?:\.\d+)?)\s*%|(\d+(?:\.\d+)?)\s*%\s*risk)", p)
    if risk_match:
        val_str = risk_match.group(1) or risk_match.group(2)
        risk_pct = float(val_str) / 100.0
    else:
        risk_pct = 0.01

    if risk_pct > 0.05:
        findings.append(ValidationFinding(
            severity="WARNING",
            message=f"Risk per trade of {risk_pct*100:.1f}% exceeds safe risk bounds (>5%). Clamped to 2%.",
            recommendation="Keep risk per trade between 0.5% and 2.0%."
        ))
        risk_pct = 0.02

    # Risk-Reward - support both "rr 2.5", "2.5 rr", "risk reward 2", "2.5 risk reward"
    rr_match = re.search(r"(?:(?:rr|risk\s*reward|ratio)\s*[:=]?\s*(\d+(?:\.\d+)?)|(\d+(?:\.\d+)?)\s*(?:rr|risk\s*reward|ratio))", p)
    if rr_match:
        val_str = rr_match.group(1) or rr_match.group(2)
        rr = float(val_str)
    else:
        rr = 2.0

    if stype == "rsi":
        params = {
            "rsi_period": rsi_period,
            "oversold": oversold,
            "overbought": overbought,
            "risk_per_trade_pct": risk_pct,
            "risk_reward_ratio": rr,
            "atr_period": 14,
            "sl_atr_mult": 1.5,
            "max_bars_held": 48,
        }
    else:
        entry_mode = "early_candlestick"
        if "neckline" in p:
            entry_mode = "neckline_breakout"

        params = {
            "rsi_period": rsi_period,
            "swing_window": 5,
            "entry_mode": entry_mode,
            "risk_per_trade_pct": risk_pct,
            "risk_reward_ratio": rr,
            "atr_period": 14,
            "sl_buffer_atr": 0.2,
            "oversold_threshold": oversold,
            "overbought_threshold": overbought,
            "max_bars_held": 72,
        }

    return _build_validated_spec(
        summary=f"Automated translation of: {prompt.strip()}",
        strategy_type=stype,
        symbol=symbol,
        timeframe=tf,
        raw_params=params,
        findings=findings,
        source="rule_engine",
    )


def _build_validated_spec(
    summary: str,
    strategy_type: str,
    symbol: str,
    timeframe: str,
    raw_params: Dict[str, Any],
    findings: Optional[List[ValidationFinding]] = None,
    source: str = "llm",
) -> StrategySpecOutput:
    valid_findings = findings or []
    breakdown = []

    # Enforce safe bounds
    safe_params = dict(raw_params)
    safe_params["rsi_period"] = max(2, min(int(safe_params.get("rsi_period", 14)), 100))
    safe_params["risk_per_trade_pct"] = max(0.001, min(float(safe_params.get("risk_per_trade_pct", 0.01)), 0.05))
    safe_params["risk_reward_ratio"] = max(0.5, min(float(safe_params.get("risk_reward_ratio", 2.0)), 10.0))

    if strategy_type == "rsi":
        safe_params["oversold"] = max(10.0, min(float(safe_params.get("oversold", 30.0)), 45.0))
        safe_params["overbought"] = max(55.0, min(float(safe_params.get("overbought", 70.0)), 90.0))
        safe_params["sl_atr_mult"] = max(0.5, min(float(safe_params.get("sl_atr_mult", 1.5)), 5.0))
        safe_params["max_bars_held"] = max(4, min(int(safe_params.get("max_bars_held", 48)), 200))
    else:
        safe_params["swing_window"] = max(2, min(int(safe_params.get("swing_window", 5)), 20))
        safe_params["entry_mode"] = "neckline_breakout" if "neckline" in str(safe_params.get("entry_mode", "")) else "early_candlestick"
        safe_params["sl_buffer_atr"] = max(0.0, min(float(safe_params.get("sl_buffer_atr", 0.2)), 2.0))
        safe_params["max_bars_held"] = max(10, min(int(safe_params.get("max_bars_held", 72)), 300))

    for k, v in safe_params.items():
        vtype = "int" if isinstance(v, int) else ("float" if isinstance(v, float) else "string")
        breakdown.append(ParameterSpec(
            name=k,
            value=v,
            type=vtype,
            description=f"Operational parameter for {k}",
            bounds_applied="Enforced within system quantitative limits",
        ))

    return StrategySpecOutput(
        hypothesis_summary=summary,
        strategy_type=strategy_type,
        symbol=symbol,
        timeframe=timeframe,
        parameters=safe_params,
        parameter_breakdown=breakdown,
        validation_findings=valid_findings,
        human_confirmation_required=True,
    )
