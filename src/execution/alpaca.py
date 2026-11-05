"""
Alpaca Broker Integration.
Supports fractional dollar-based order routing, account equity inspection,
and position status querying for live/paper accounts.
"""

from typing import Dict, Optional
from src.config import BotConfig


class AlpacaBroker:
    """Wrapper around Alpaca Trading API."""

    def __init__(self, config: Optional[BotConfig] = None):
        self.config = config or BotConfig()
        self._client = None
        self._init_client()

    def _init_client(self):
        """Initialize TradingClient if credentials exist."""
        if self.config.alpaca_api_key and self.config.alpaca_secret_key:
            try:
                from alpaca.trading.client import TradingClient
                self._client = TradingClient(
                    api_key=self.config.alpaca_api_key,
                    secret_key=self.config.alpaca_secret_key,
                    paper=self.config.alpaca_paper
                )
            except ImportError:
                self._client = None

    @property
    def is_connected(self) -> bool:
        """Check if active connection to broker client exists."""
        return self._client is not None

    def get_portfolio_equity(self) -> float:
        """Retrieve total portfolio liquidation value."""
        if not self.is_connected:
            # Fallback to configured initial capital if paper keys are unpopulated
            return self.config.initial_capital

        account = self._client.get_account()
        return float(account.portfolio_value)

    def get_open_positions(self) -> Dict[str, float]:
        """Return dict of {ticker: current_qty}."""
        if not self.is_connected:
            return {}

        positions = self._client.get_all_positions()
        return {p.symbol: float(p.qty) for p in positions}

    def place_dollar_order(self, ticker: str, dollar_amount: float, side: str = "buy") -> Dict[str, str]:
        """
        Submit a fractional dollar-based market order (notional order).
        """
        if not self.is_connected:
            return {
                "status": "SIMULATED",
                "ticker": ticker,
                "notional": f"${dollar_amount:.2f}",
                "side": side.upper(),
                "note": "Alpaca API credentials not configured; simulated order executed."
            }

        from alpaca.trading.requests import MarketOrderRequest
        from alpaca.trading.enums import OrderSide, TimeInForce

        order_side = OrderSide.BUY if side.lower() == "buy" else OrderSide.SELL

        order_data = MarketOrderRequest(
            symbol=ticker,
            notional=round(dollar_amount, 2),
            side=order_side,
            time_in_force=TimeInForce.DAY
        )

        order = self._client.submit_order(order_data=order_data)
        return {
            "status": "SUBMITTED",
            "id": str(order.id),
            "ticker": order.symbol,
            "notional": f"${dollar_amount:.2f}",
            "side": side.upper()
        }

