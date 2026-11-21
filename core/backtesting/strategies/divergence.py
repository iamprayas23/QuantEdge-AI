"""Divergence Quantitative Strategy (Zero Lookahead)

Identifies Regular Bullish and Bearish Divergence between Price action and RSI
using causal swing detection. Entry options: 'neckline_breakout' or 'early_candlestick'.
"""
from typing import Dict, Any, Optional, List
import pandas as pd
from core.backtesting.strategies.base import BaseStrategy
from core.backtesting.signals import (
    compute_rsi,
    compute_atr,
    detect_causal_pivots,
    is_bullish_engulfing,
    is_bearish_engulfing,
    is_bullish_marubozu,
    is_bearish_marubozu,
)
from core.execution.cost_model import CostModel
from core.portfolio.state import PortfolioState, TradeRecord
from core.risk.position_sizer import calculate_position_size


class DivergenceStrategy(BaseStrategy):
    def __init__(self, params: Optional[Dict[str, Any]] = None):
        default_params = {
            "rsi_period": 14,
            "swing_window": 5,
            "entry_mode": "early_candlestick",  # 'neckline_breakout' or 'early_candlestick'
            "risk_per_trade_pct": 0.01,
            "risk_reward_ratio": 2.0,
            "atr_period": 14,
            "sl_buffer_atr": 0.2,
            "oversold_threshold": 35.0,
            "overbought_threshold": 65.0,
            "max_bars_held": 72,
        }
        if params:
            default_params.update(params)
        super().__init__(name="divergence_strategy", params=default_params)

    def run(
        self,
        df: pd.DataFrame,
        cost_model: CostModel,
        initial_capital: float = 10000.0,
        risk_per_trade_pct: float = 0.01,
        symbol: str = "XAUUSD",
    ) -> PortfolioState:
        rsi_period = int(self.params.get("rsi_period", 14))
        swing_window = int(self.params.get("swing_window", 5))
        entry_mode = str(self.params.get("entry_mode", "early_candlestick"))
        rr = float(self.params.get("risk_reward_ratio", 2.0))
        atr_period = int(self.params.get("atr_period", 14))
        sl_buffer_atr = float(self.params.get("sl_buffer_atr", 0.2))
        oversold = float(self.params.get("oversold_threshold", 35.0))
        overbought = float(self.params.get("overbought_threshold", 65.0))
        max_bars_held = int(self.params.get("max_bars_held", 72))
        effective_risk_pct = float(self.params.get("risk_per_trade_pct", risk_per_trade_pct))

        df = df.copy()
        df["rsi"] = compute_rsi(df["close"], period=rsi_period)
        df["atr"] = compute_atr(df, period=atr_period)

        # Causal pivot series
        swing_highs, swing_lows = detect_causal_pivots(df, window=swing_window)
        df["swing_high"] = swing_highs
        df["swing_low"] = swing_lows

        state = PortfolioState(
            initial_capital=initial_capital,
            cash=initial_capital,
            equity=initial_capital,
            peak_equity=initial_capital,
        )

        n = len(df)
        trade_id = 0

        # Track confirmed causal pivots: list of dict(bar_idx, price, rsi)
        confirmed_lows: List[dict] = []
        confirmed_highs: List[dict] = []

        start_bar = max(rsi_period, swing_window * 3)

        for i in range(start_bar, n):
            current_bar = df.iloc[i]
            ts = current_bar["timestamp"]
            open_p = current_bar["open"]
            high_p = current_bar["high"]
            low_p = current_bar["low"]
            close_p = current_bar["close"]
            atr_val = current_bar["atr"]

            # Check if previous bar (i-1) confirmed a causal pivot (which was at i-1 - swing_window)
            prev_idx = i - 1
            if not pd.isna(df["swing_low"].iloc[prev_idx]):
                pivot_idx = prev_idx - swing_window
                confirmed_lows.append({
                    "bar_idx": pivot_idx,
                    "price": df["low"].iloc[pivot_idx],
                    "rsi": df["rsi"].iloc[pivot_idx],
                })
                # keep last 10
                if len(confirmed_lows) > 10:
                    confirmed_lows.pop(0)

            if not pd.isna(df["swing_high"].iloc[prev_idx]):
                pivot_idx = prev_idx - swing_window
                confirmed_highs.append({
                    "bar_idx": pivot_idx,
                    "price": df["high"].iloc[pivot_idx],
                    "rsi": df["rsi"].iloc[pivot_idx],
                })
                if len(confirmed_highs) > 10:
                    confirmed_highs.pop(0)

            # 1. Manage open position
            if state.open_position is not None:
                pos = state.open_position
                pos["bars_held"] += 1
                side = pos["side"]
                entry_p = pos["entry_price"]
                sl = pos["sl"]
                tp = pos["tp"]
                size = pos["size"]
                entry_ts = pos["entry_time"]
                entry_comm = pos["entry_commission"]
                entry_slip = pos["entry_slippage"]

                exit_triggered = False
                raw_exit_p = close_p
                exit_reason = ""

                if side == "long":
                    if low_p <= sl:
                        raw_exit_p = sl
                        exit_reason = "stop_loss"
                        exit_triggered = True
                    elif high_p >= tp:
                        raw_exit_p = tp
                        exit_reason = "take_profit"
                        exit_triggered = True
                    elif pos["bars_held"] >= max_bars_held:
                        raw_exit_p = close_p
                        exit_reason = "time_exit"
                        exit_triggered = True
                else:  # short
                    if high_p >= sl:
                        raw_exit_p = sl
                        exit_reason = "stop_loss"
                        exit_triggered = True
                    elif low_p <= tp:
                        raw_exit_p = tp
                        exit_reason = "take_profit"
                        exit_triggered = True
                    elif pos["bars_held"] >= max_bars_held:
                        raw_exit_p = close_p
                        exit_reason = "time_exit"
                        exit_triggered = True

                if not exit_triggered and i == n - 1:
                    raw_exit_p = close_p
                    exit_reason = "end_of_data"
                    exit_triggered = True

                if exit_triggered:
                    exec_exit_p = cost_model.calculate_exit_price(raw_exit_p, side)
                    exit_comm = cost_model.calculate_commission(exec_exit_p, size)
                    exit_slip = abs(exec_exit_p - raw_exit_p) * size * cost_model.point_value

                    if side == "long":
                        gross_pnl = (exec_exit_p - entry_p) * size * cost_model.point_value
                    else:
                        gross_pnl = (entry_p - exec_exit_p) * size * cost_model.point_value

                    total_comm = entry_comm + exit_comm
                    total_slip = entry_slip + exit_slip
                    net_pnl = gross_pnl - total_comm

                    state.cash += net_pnl
                    ret_pct = (net_pnl / (entry_p * size)) * 100.0 if (entry_p * size) > 0 else 0.0

                    trade_id += 1
                    state.trades.append(
                        TradeRecord(
                            trade_id=trade_id,
                            symbol=symbol,
                            side=side,
                            entry_time=entry_ts,
                            exit_time=ts,
                            entry_price=round(entry_p, 4),
                            exit_price=round(exec_exit_p, 4),
                            size=round(size, 4),
                            pnl=round(net_pnl, 2),
                            gross_pnl=round(gross_pnl, 2),
                            return_pct=round(ret_pct, 4),
                            commission=round(total_comm, 2),
                            slippage=round(total_slip, 2),
                            exit_reason=exit_reason,
                            bars_held=pos["bars_held"],
                        )
                    )
                    state.open_position = None

            # 2. Check Divergence Signals evaluated on closed bar (i - 1)
            if state.open_position is None and i < n - 1:
                sig_idx = i - 1
                entered = False

                # Bullish Divergence check
                if len(confirmed_lows) >= 2:
                    L1 = confirmed_lows[-2]
                    L2 = confirmed_lows[-1]
                    # Valid divergence within recent window: L2 must be relatively recent
                    if (sig_idx - L2["bar_idx"] <= 20) and (L2["bar_idx"] > L1["bar_idx"]):
                        # Lower price low, higher RSI low, and L1 was in oversold territory
                        if (L2["price"] < L1["price"]) and (L2["rsi"] > L1["rsi"]) and (L1["rsi"] < oversold):
                            signal_confirmed = False
                            if entry_mode == "neckline_breakout":
                                neckline = df["high"].iloc[L1["bar_idx"]:L2["bar_idx"] + 1].max()
                                if df["close"].iloc[sig_idx] > neckline:
                                    signal_confirmed = True
                            else:  # early_candlestick
                                if is_bullish_marubozu(df, sig_idx) or is_bullish_engulfing(df, sig_idx):
                                    signal_confirmed = True

                            if signal_confirmed:
                                raw_entry = open_p
                                sl = L2["price"] - (atr_val * sl_buffer_atr)
                                risk_dist = raw_entry - sl
                                if risk_dist > 0.05:
                                    tp = raw_entry + (risk_dist * rr)
                                    exec_entry = cost_model.calculate_entry_price(raw_entry, "long")
                                    size = calculate_position_size(
                                        capital=state.cash,
                                        risk_per_trade_pct=effective_risk_pct,
                                        entry_price=exec_entry,
                                        stop_loss_price=sl,
                                        point_value=cost_model.point_value,
                                    )
                                    if size > 0:
                                        comm = cost_model.calculate_commission(exec_entry, size)
                                        slip = abs(exec_entry - raw_entry) * size * cost_model.point_value
                                        state.open_position = {
                                            "side": "long",
                                            "entry_price": exec_entry,
                                            "raw_entry_price": raw_entry,
                                            "entry_time": ts,
                                            "sl": sl,
                                            "tp": tp,
                                            "size": size,
                                            "bars_held": 0,
                                            "entry_commission": comm,
                                            "entry_slippage": slip,
                                        }
                                        entered = True

                # Bearish Divergence check
                if not entered and len(confirmed_highs) >= 2:
                    H1 = confirmed_highs[-2]
                    H2 = confirmed_highs[-1]
                    if (sig_idx - H2["bar_idx"] <= 20) and (H2["bar_idx"] > H1["bar_idx"]):
                        # Higher price high, lower RSI high, and H1 was in overbought territory
                        if (H2["price"] > H1["price"]) and (H2["rsi"] < H1["rsi"]) and (H1["rsi"] > overbought):
                            signal_confirmed = False
                            if entry_mode == "neckline_breakout":
                                neckline = df["low"].iloc[H1["bar_idx"]:H2["bar_idx"] + 1].min()
                                if df["close"].iloc[sig_idx] < neckline:
                                    signal_confirmed = True
                            else:  # early_candlestick
                                if is_bearish_marubozu(df, sig_idx) or is_bearish_engulfing(df, sig_idx):
                                    signal_confirmed = True

                            if signal_confirmed:
                                raw_entry = open_p
                                sl = H2["price"] + (atr_val * sl_buffer_atr)
                                risk_dist = sl - raw_entry
                                if risk_dist > 0.05:
                                    tp = raw_entry - (risk_dist * rr)
                                    exec_entry = cost_model.calculate_entry_price(raw_entry, "short")
                                    size = calculate_position_size(
                                        capital=state.cash,
                                        risk_per_trade_pct=effective_risk_pct,
                                        entry_price=exec_entry,
                                        stop_loss_price=sl,
                                        point_value=cost_model.point_value,
                                    )
                                    if size > 0:
                                        comm = cost_model.calculate_commission(exec_entry, size)
                                        slip = abs(exec_entry - raw_entry) * size * cost_model.point_value
                                        state.open_position = {
                                            "side": "short",
                                            "entry_price": exec_entry,
                                            "raw_entry_price": raw_entry,
                                            "entry_time": ts,
                                            "sl": sl,
                                            "tp": tp,
                                            "size": size,
                                            "bars_held": 0,
                                            "entry_commission": comm,
                                            "entry_slippage": slip,
                                        }

            # Update mark-to-market equity curve
            unrealized = 0.0
            if state.open_position is not None:
                op = state.open_position
                if op["side"] == "long":
                    unrealized = (close_p - op["entry_price"]) * op["size"] * cost_model.point_value
                else:
                    unrealized = (op["entry_price"] - close_p) * op["size"] * cost_model.point_value

            state.record_equity(ts, unrealized_pnl=unrealized)

        return state
