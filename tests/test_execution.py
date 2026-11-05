"""Unit tests for Broker Execution abstraction."""
from src.config import BotConfig
from src.execution.alpaca import AlpacaBroker


def test_simulated_broker_execution():
    # Broker with no keys operates in safe simulated mode
    config = BotConfig(initial_capital=100.0)
    broker = AlpacaBroker(config=config)

    assert broker.is_connected is False
    equity = broker.get_portfolio_equity()
    assert equity == 100.0

    positions = broker.get_open_positions()
    assert positions == {}

    # Dollar order in simulation mode
    result = broker.place_dollar_order(ticker="QQQ", dollar_amount=49.0, side="buy")
    assert result["status"] == "SIMULATED"
    assert result["ticker"] == "QQQ"
    assert result["notional"] == "$49.00"
    assert result["side"] == "BUY"

