"""Unit tests for Risk Management Engine ($100 budget & fractional sizing)."""
import pytest
from src.config import BotConfig
from src.risk.manager import RiskManager


def test_micro_allocation_100_dollars():
    config = BotConfig(initial_capital=100.0, max_positions=2, stop_loss_pct=0.05)
    risk_manager = RiskManager(config=config, cash_buffer_pct=0.02)

    # $100 equity, 2% cash buffer = $98 investable. Distributed over 2 tickers = $49 each.
    prices = {"QQQ": 480.0, "XLK": 220.0}
    allocations = risk_manager.calculate_allocations(
        total_equity=100.0,
        selected_tickers=["QQQ", "XLK"],
        current_prices=prices
    )

    assert len(allocations) == 2

    qqq = allocations[0]
    assert qqq.ticker == "QQQ"
    assert qqq.target_dollars == 49.0
    assert qqq.target_shares == round(49.0 / 480.0, 4)
    assert qqq.stop_loss_price == round(480.0 * 0.95, 2)

    xlk = allocations[1]
    assert xlk.ticker == "XLK"
    assert xlk.target_dollars == 49.0
    assert xlk.target_shares == round(49.0 / 220.0, 4)
    assert xlk.stop_loss_price == round(220.0 * 0.95, 2)


def test_stop_loss_and_take_profit_triggers():
    config = BotConfig(stop_loss_pct=0.05, take_profit_pct=0.10)
    risk_manager = RiskManager(config=config)

    # Normal hold
    should_exit, reason = risk_manager.should_exit_position(entry_price=100.0, current_price=102.0)
    assert should_exit is False
    assert reason == "HOLD"

    # Stop loss hit (-5%)
    should_exit, reason = risk_manager.should_exit_position(entry_price=100.0, current_price=94.5)
    assert should_exit is True
    assert "STOP_LOSS_HIT" in reason

    # Take profit hit (+10%)
    should_exit, reason = risk_manager.should_exit_position(entry_price=100.0, current_price=111.0)
    assert should_exit is True
    assert "TAKE_PROFIT_HIT" in reason


def test_zero_or_negative_equity():
    risk_manager = RiskManager()
    with pytest.raises(ValueError):
        risk_manager.calculate_allocations(total_equity=0.0, selected_tickers=["SPY"], current_prices={"SPY": 500.0})

