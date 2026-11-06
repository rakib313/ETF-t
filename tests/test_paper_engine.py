"""Unit tests for SQLite Persistent Paper Trading Engine."""
import tempfile
from pathlib import Path
import pytest
from src.config import BotConfig
from src.engine.paper_engine import PaperTradingEngine


@pytest.fixture
def temp_engine():
    with tempfile.TemporaryDirectory() as tmpdir:
        db_path = Path(tmpdir) / "test_ledger.db"
        config = BotConfig(initial_capital=100.0, max_positions=2, stop_loss_pct=0.05)
        engine = PaperTradingEngine(db_path=db_path, config=config)
        yield engine


def test_initial_state(temp_engine):
    state = temp_engine.get_account_state()
    assert state["total_equity"] == 100.0
    assert state["cash"] == 100.0
    assert state["market_value"] == 0.0
    assert state["positions_count"] == 0
    assert state["realized_pnl"] == 0.0


def test_market_buy_and_sell_lifecycle(temp_engine):
    # Buy $49 of QQQ
    buy_result = temp_engine.execute_market_buy(ticker="QQQ", dollar_amount=49.0, reason="TEST_BUY")
    assert buy_result is not None
    assert buy_result["ticker"] == "QQQ"
    assert buy_result["shares"] > 0

    state_after_buy = temp_engine.get_account_state()
    assert state_after_buy["cash"] == 51.0
    assert state_after_buy["positions_count"] == 1
    assert state_after_buy["positions"][0]["ticker"] == "QQQ"

    # Sell QQQ
    sell_result = temp_engine.execute_market_sell(ticker="QQQ", reason="TEST_SELL")
    assert sell_result is not None
    assert sell_result["ticker"] == "QQQ"
    assert sell_result["shares"] == buy_result["shares"]

    state_after_sell = temp_engine.get_account_state()
    assert state_after_sell["positions_count"] == 0
    assert state_after_sell["cash"] > 0


def test_order_audit_trail_and_logging(temp_engine):
    temp_engine.execute_market_buy(ticker="SPY", dollar_amount=20.0, reason="TEST_AUDIT")
    orders = temp_engine.get_recent_orders(limit=10)
    assert len(orders) >= 1
    assert orders[0]["ticker"] == "SPY"
    assert orders[0]["side"] == "BUY"
    assert orders[0]["slippage_cost"] >= 0

    logs = temp_engine.get_recent_logs(limit=10)
    assert len(logs) >= 1

