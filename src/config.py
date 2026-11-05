"""
ETF Trading Bot Configuration Module.
Strict validation of trading parameters, risk constraints, and broker credentials.
"""

from typing import List
from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class BotConfig(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore"
    )

    # Broker Credentials
    alpaca_api_key: str = Field(default="", description="Alpaca API Key ID")
    alpaca_secret_key: str = Field(default="", description="Alpaca Secret Key")
    alpaca_paper: bool = Field(default=True, description="Whether to use paper trading endpoints")

    # Universe & Portfolio Settings
    etf_universe: List[str] = Field(
        default=["SPY", "QQQ", "XLK", "XLF", "XLE", "GLD", "TLT"],
        description="Core liquid ETF universe for momentum ranking"
    )
    cash_proxy: str = Field(
        default="BIL",
        description="Ultra-short term Treasury ETF proxy when defensive"
    )
    rebalance_frequency: str = Field(
        default="weekly",
        description="Rebalance frequency (daily, weekly, monthly)"
    )

    # Risk Controls (Calibrated for initial $100 starting capital)
    initial_capital: float = Field(default=100.0, ge=10.0, description="Baseline working capital")
    max_portfolio_risk_pct: float = Field(default=0.02, gt=0.0, le=0.10, description="Max 2% capital risk per trade")
    max_positions: int = Field(default=2, ge=1, le=10, description="Max concurrent ETF positions (e.g. top 2 momentum leaders)")
    stop_loss_pct: float = Field(default=0.05, gt=0.0, le=0.20, description="Hard trailing or initial stop-loss percentage (5%)")
    take_profit_pct: float = Field(default=0.10, gt=0.0, description="Target take-profit percentage (10%)")
    allow_fractional: bool = Field(default=True, description="Enable fractional share execution")


def get_config() -> BotConfig:
    """Retrieve validated configuration instance."""
    return BotConfig()

