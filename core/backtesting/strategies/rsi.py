"""RSI Mean-Reversion Strategy

Zero-lookahead execution with explicit cost modeling, SL/TP bounds,
and parameter flexibility.
"""
from typing import Dict, Any, Optional
import pandas as pd
from core.backtesting.strategies.base import BaseStrategy
from core.backtesting.signals import compute_rsi, compute_atr
from core.execution.cost_model import CostModel
from core.portfolio.state import PortfolioState, TradeRecord
from core.risk.position_sizer import calculate_position_size


class RSIStrategy(BaseStrategy):
    def __init__(self, params: Optional[Dict[str, Any]] = None):
        default_params = {
            "rsi_period": 14,
            "oversold": 30.0,
            "overbought": 70.0,
            "risk_per_trade_pct": 0.01,
            "risk_reward_ratio": 2.0,
            "atr_period": 14,
            "sl_atr_mult": 1.5,
            "max_bars_held": 48,
        }
        if params:
            default_params.update(params)
        super().__init__(name="rsi_mean_reversion", params=default_params)

    def run(
        self,
        df: pd.DataFrame,
        cost_model: CostModel,
        initial_capital: float = 10000.0,
        risk_per_trade_pct: float = 0.01,
        symbol: str = "XAUUSD",
    ) -> PortfolioState:
        rsi_period = int(self.params.get("rsi_period", 14))
        oversold = float(self.params.get("oversold", 30.0))
        overbought = float(self.params.get("overbought", 70.0))
        rr = float(self.params.get("risk_reward_ratio", 2.0))
        atr_period = int(self.params.get("atr_period", 14))
        sl_atr_mult = float(self.params.get("sl_atr_mult", 1.5))
        max_bars_held = int(self.params.get("max_bars_held", 48))
        effective_risk_pct = float(self.params.get("risk_per_trade_pct", risk_per_trade_pct))

        # Indicator calculations
        df = df.copy()
        df["rsi"] = compute_rsi(df["close"], period=rsi_period)
        df["atr"] = compute_atr(df, period=atr_period)

        state = PortfolioState(
            initial_capital=initial_capital,
            cash=initial_capital,
            equity=initial_capital,
            peak_equity=initial_capital,
        )

        n = len(df)
        trade_id = 0

        for i in range(max(rsi_period, atr_period) + 1, n):
            current_bar = df.iloc[i]
            prev_bar = df.iloc[i - 1]
            ts = current_bar["timestamp"]
            open_p = current_bar["open"]
            high_p = current_bar["high"]
            low_p = current_bar["low"]
            close_p = current_bar["close"]

            # Manage open position
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

                # Check SL and TP using intra-bar extremes
                if side == "long":
                    if low_p <= sl:
                        raw_exit_p = sl
                        exit_reason = "stop_loss"
                        exit_triggered = True
                    elif high_p >= tp:
                        raw_exit_p = tp
                        exit_reason = "take_profit"
                        exit_triggered = True
                    elif prev_bar["rsi"] >= overbought:
                        raw_exit_p = open_p
                        exit_reason = "signal_exit"
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
                    elif prev_bar["rsi"] <= oversold:
                        raw_exit_p = open_p
                        exit_reason = "signal_exit"
                        exit_triggered = True
                    elif pos["bars_held"] >= max_bars_held:
                        raw_exit_p = close_p
                        exit_reason = "time_exit"
                        exit_triggered = True

                # Force exit on final bar
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

            # Check new entry signal evaluated on closed bar (i - 1)
            if state.open_position is None and i < n - 1:
                sig_bar = df.iloc[i - 1]
                prev_rsi = sig_bar["rsi"]
                atr_val = sig_bar["atr"]

                # Entry signals:
                # Long: RSI < oversold on bar i-1 -> enter on bar i open
                # Short: RSI > overbought on bar i-1 -> enter on bar i open
                if prev_rsi < oversold:
                    raw_entry = open_p
                    sl_dist = atr_val * sl_atr_mult
                    sl = raw_entry - sl_dist
                    tp = raw_entry + (sl_dist * rr)

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

                elif prev_rsi > overbought:
                    raw_entry = open_p
                    sl_dist = atr_val * sl_atr_mult
                    sl = raw_entry + sl_dist
                    tp = raw_entry - (sl_dist * rr)

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
