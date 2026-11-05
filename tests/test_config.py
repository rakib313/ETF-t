"""Unit tests for configuration validation."""
from src.config import BotConfig, get_config


def test_default_config():
    config = get_config()
    assert config.initial_capital == 100.0
    assert config.max_positions == 2
    assert config.stop_loss_pct == 0.05
    assert "SPY" in config.etf_universe
    assert config.allow_fractional is True


def test_custom_config_override():
    config = BotConfig(initial_capital=250.0, max_positions=3, stop_loss_pct=0.08)
    assert config.initial_capital == 250.0
    assert config.max_positions == 3
    assert config.stop_loss_pct == 0.08

