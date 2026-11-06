"""Unit tests for Market Data Provider."""
from src.data.provider import MarketDataProvider


def test_offline_fallback_market_data():
    provider = MarketDataProvider(offline_fallback=True)
    history = provider.fetch_history(["SPY", "QQQ"], period="3mo")

    assert "SPY" in history
    assert "QQQ" in history
    assert len(history["SPY"]) >= 20
    assert "close" in history["SPY"].columns

    prices = provider.get_latest_prices(["SPY", "QQQ"], history=history)
    assert prices["SPY"] > 0
    assert prices["QQQ"] > 0

