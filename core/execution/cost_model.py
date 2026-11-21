"""Cost Model & Execution Assumptions

Provides explicit modeling of slippage, commissions, and bid-ask spreads
to eliminate unrealistic backtesting fills.
"""
from dataclasses import dataclass


@dataclass
class CostModel:
    slippage_bps: float = 1.0          # Slippage in basis points (1 bps = 0.01% = 0.0001)
    commission_per_trade: float = 0.0   # Fixed dollar commission per order
    commission_bps: float = 0.0         # Commission in basis points of notional volume
    spread_pips: float = 0.0           # Half-spread or full spread in price points
    point_value: float = 1.0           # Point value / contract multiplier (e.g. 1.0 for gold spot)

    def calculate_entry_price(self, raw_price: float, side: str) -> float:
        """
        Adjust entry price for spread and slippage.
        Long pays higher (ask + slippage), Short sells lower (bid - slippage).
        """
        slippage_delta = raw_price * (self.slippage_bps / 10000.0)
        spread_delta = (self.spread_pips / 2.0)

        if side.lower() in ("long", "buy", "1"):
            return raw_price + spread_delta + slippage_delta
        else:
            return raw_price - spread_delta - slippage_delta

    def calculate_exit_price(self, raw_price: float, side: str) -> float:
        """
        Adjust exit price for spread and slippage.
        Closing a Long sells at bid - slippage.
        Closing a Short buys back at ask + slippage.
        """
        slippage_delta = raw_price * (self.slippage_bps / 10000.0)
        spread_delta = (self.spread_pips / 2.0)

        if side.lower() in ("long", "buy", "1"):
            # Exiting a long means selling
            return raw_price - spread_delta - slippage_delta
        else:
            # Exiting a short means buying
            return raw_price + spread_delta + slippage_delta

    def calculate_commission(self, price: float, size: float) -> float:
        """
        Calculate total commission for an executed order.
        """
        notional = price * size * self.point_value
        bps_cost = notional * (self.commission_bps / 10000.0)
        return self.commission_per_trade + bps_cost
