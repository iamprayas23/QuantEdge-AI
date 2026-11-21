"""Risk Management & Position Sizing

Deterministic position sizing models based on fixed risk percentage or fixed units.
"""
from typing import Optional


def calculate_position_size(
    capital: float,
    risk_per_trade_pct: float,
    entry_price: float,
    stop_loss_price: float,
    point_value: float = 1.0,
    max_capital_pct: Optional[float] = None,
    min_size: float = 0.01,
    max_size: Optional[float] = None,
) -> float:
    """
    Calculate position size based on capital at risk and stop loss distance.
    Risk amount = capital * risk_per_trade_pct
    Risk per unit = abs(entry_price - stop_loss_price) * point_value
    Position size = risk_amount / risk_per_unit
    """
    sl_distance = abs(entry_price - stop_loss_price)
    if sl_distance <= 1e-6:
        return 0.0

    risk_amount = capital * risk_per_trade_pct
    unit_risk = sl_distance * point_value
    size = risk_amount / unit_risk

    # Cap notional value to max_capital_pct if specified
    if max_capital_pct is not None:
        max_notional_units = (capital * max_capital_pct) / (entry_price * point_value)
        if size > max_notional_units:
            size = max_notional_units

    if max_size is not None and size > max_size:
        size = max_size

    if size < min_size:
        return 0.0

    return round(size, 4)
