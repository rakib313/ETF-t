"""
ETF Relative Strength & Dual Momentum Strategy.
Ranks candidate sector & asset-class ETFs by cumulative return over a lookback window,
with an absolute regime filter (SPY vs SMA) that rotates to cash proxy during market downturns.
"""

from typing import Dict, List, Optional
import pandas as pd
from src.config import BotConfig
from .base import BaseStrategy


class ETFMomentumStrategy(BaseStrategy):
    """
    Momentum rotation strategy:
    1. Checks if benchmark (e.g. SPY) is trading above its trend filter (SMA 50).
    2. If benchmark is below SMA (bear regime), rotates 100% to cash proxy (e.g. BIL).
    3. If bull regime, ranks all candidate ETFs by lookback momentum score and selects top N.
    """

    def __init__(
        self,
        config: Optional[BotConfig] = None,
        lookback_days: int = 20,
        trend_filter_days: int = 50,
        benchmark: str = "SPY"
    ):
        self.config = config or BotConfig()
        self.lookback_days = lookback_days
        self.trend_filter_days = trend_filter_days
        self.benchmark = benchmark

    def is_market_bullish(self, spy_df: pd.DataFrame) -> bool:
        """Check if SPY close is above its Simple Moving Average."""
        if spy_df.empty or len(spy_df) < self.trend_filter_days:
            return True  # Fallback to neutral/bullish if insufficient history

        close_series = spy_df["close"]
        sma = close_series.rolling(window=self.trend_filter_days).mean().iloc[-1]
        latest_close = close_series.iloc[-1]
        return latest_close >= sma

    def calculate_momentum_score(self, df: pd.DataFrame) -> float:
        """
        Calculate momentum score (percentage return over lookback period).
        Returns -999.0 if data is insufficient.
        """
        if df.empty or len(df) <= self.lookback_days:
            return -999.0

        close = df["close"]
        current = close.iloc[-1]
        past = close.iloc[-self.lookback_days - 1]
        if past <= 0:
            return -999.0

        return (current - past) / past

    def generate_signals(self, price_history: Dict[str, pd.DataFrame]) -> List[str]:
        """
        Evaluate universe price history.
        Returns top ETF tickers or cash proxy.
        """
        # 1. Macro Regime Check
        if self.benchmark in price_history:
            if not self.is_market_bullish(price_history[self.benchmark]):
                # Market is in a severe correction/bear market: stay safe in cash proxy
                return [self.config.cash_proxy]

        # 2. Score each candidate ETF
        scores: Dict[str, float] = {}
        for ticker in self.config.etf_universe:
            if ticker in price_history:
                score = self.calculate_momentum_score(price_history[ticker])
                # Only consider ETFs with positive absolute momentum
                if score > 0:
                    scores[ticker] = score

        if not scores:
            # If no ETF has positive momentum, hold cash proxy
            return [self.config.cash_proxy]

        # 3. Sort by momentum descending
        ranked = sorted(scores.keys(), key=lambda t: scores[t], reverse=True)
        return ranked[: self.config.max_positions]

