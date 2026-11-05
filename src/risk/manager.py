"""
Risk Management Engine.
Enforces position sizing, fractional share calculation, stop loss computation,
and capital preservation for micro and standard portfolios.
"""

from typing import Dict, List, Optional
from pydantic import BaseModel, Field
from src.config import BotConfig


class PositionAllocation(BaseModel):
    ticker: str
    target_dollars: float = Field(..., gt=0.0)
    target_shares: float = Field(..., gt=0.0)
    current_price: float = Field(..., gt=0.0)
    stop_loss_price: float = Field(..., gt=0.0)
    take_profit_price: Optional[float] = None


class RiskManager:
    """Manages portfolio risk, capital distribution, and position constraints."""

    def __init__(self, config: Optional[BotConfig] = None, cash_buffer_pct: float = 0.02):
        self.config = config or BotConfig()
        self.cash_buffer_pct = cash_buffer_pct  # Reserve 2% cash for slippage / fees

    def calculate_allocations(
        self,
        total_equity: float,
        selected_tickers: List[str],
        current_prices: Dict[str, float]
    ) -> List[PositionAllocation]:
        """
        Calculate equal-weighted fractional allocations for selected momentum leaders.
        Respects cash buffer, max positions, and computes strict stop-loss bounds.
        """
        if total_equity <= 0:
            raise ValueError(f"Total equity must be positive, got {total_equity}")

        if not selected_tickers:
            return []

        # Cap selected tickers to configured max_positions
        active_tickers = selected_tickers[: self.config.max_positions]
        if not active_tickers:
            return []

        # Available capital after preserving cash buffer
        investable_capital = total_equity * (1.0 - self.cash_buffer_pct)
        dollar_per_position = investable_capital / len(active_tickers)

        allocations: List[PositionAllocation] = []

        for ticker in active_tickers:
            price = current_prices.get(ticker)
            if not price or price <= 0:
                raise ValueError(f"Valid positive price required for ticker {ticker}, got {price}")

            # Fractional shares calculated to 4 decimal places
            shares = round(dollar_per_position / price, 4)
            stop_price = round(price * (1.0 - self.config.stop_loss_pct), 2)
            take_profit = round(price * (1.0 + self.config.take_profit_pct), 2)

            allocations.append(
                PositionAllocation(
                    ticker=ticker,
                    target_dollars=round(dollar_per_position, 2),
                    target_shares=shares,
                    current_price=price,
                    stop_loss_price=stop_price,
                    take_profit_price=take_profit
                )
            )

        return allocations

    def should_exit_position(
        self,
        entry_price: float,
        current_price: float,
        highest_price: Optional[float] = None
    ) -> tuple[bool, str]:
        """
        Evaluate if an open position hits stop-loss or take-profit rules.
        Supports trailing stop from highest price reached.
        """
        high = highest_price or entry_price
        trailing_stop = high * (1.0 - self.config.stop_loss_pct)

        if current_price <= trailing_stop:
            return True, f"STOP_LOSS_HIT (Price {current_price:.2f} <= Stop {trailing_stop:.2f})"

        take_profit = entry_price * (1.0 + self.config.take_profit_pct)
        if current_price >= take_profit:
            return True, f"TAKE_PROFIT_HIT (Price {current_price:.2f} >= Target {take_profit:.2f})"

        return False, "HOLD"

