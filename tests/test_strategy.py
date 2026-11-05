"""Unit tests for Relative Strength Momentum Strategy."""
import pandas as pd
import numpy as np
from src.config import BotConfig
from src.strategy.momentum import ETFMomentumStrategy


def create_price_series(start_val: float, end_val: float, periods: int = 60) -> pd.DataFrame:
    values = np.linspace(start_val, end_val, periods)
    return pd.DataFrame({"close": values})


def test_momentum_ranking_selects_top_performers():
    config = BotConfig(max_positions=2, cash_proxy="BIL")
    strategy = ETFMomentumStrategy(config=config, lookback_days=20, trend_filter_days=50)

    # SPY in steady bull trend (100 -> 110, +10%)
    # QQQ strong momentum (100 -> 130, +30%)
    # XLK high momentum (100 -> 120, +20%)
    # XLE declining momentum (100 -> 90, -10%)
    data = {
        "SPY": create_price_series(100.0, 110.0),
        "QQQ": create_price_series(100.0, 130.0),
        "XLK": create_price_series(100.0, 120.0),
        "XLE": create_price_series(100.0, 90.0)
    }

    signals = strategy.generate_signals(data)
    # Top 2 with highest momentum: QQQ, then XLK
    assert signals == ["QQQ", "XLK"]


def test_bear_regime_rotates_to_cash():
    config = BotConfig(cash_proxy="BIL")
    strategy = ETFMomentumStrategy(config=config, lookback_days=20, trend_filter_days=30)

    # SPY crashes below SMA (e.g., drops sharply at end: 150 down to 100)
    values = np.concatenate([np.repeat(150.0, 40), np.repeat(100.0, 10)])
    spy_df = pd.DataFrame({"close": values})

    data = {
        "SPY": spy_df,
        "QQQ": create_price_series(100.0, 120.0),
    }

    signals = strategy.generate_signals(data)
    # Because SPY is in severe downtrend below SMA, strategy must protect capital in BIL
    assert signals == ["BIL"]

