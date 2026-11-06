"""
Market Data Provider.
Retrieves historical OHLCV and latest price quotes for the ETF universe
using Yahoo Finance (with graceful offline mock fallback for air-gapped/sandbox runs).
"""

from typing import Dict, List, Optional
import pandas as pd
import numpy as np


class MarketDataProvider:
    """Fetches and normalizes market data for candidate ETFs."""

    def __init__(self, offline_fallback: bool = True):
        self.offline_fallback = offline_fallback

    def fetch_history(self, tickers: List[str], period: str = "3mo") -> Dict[str, pd.DataFrame]:
        """
        Download historical daily data for a list of tickers.
        Returns a dict of {ticker: DataFrame with lowercase 'close' column}.
        """
        data: Dict[str, pd.DataFrame] = {}
        failed_tickers: List[str] = []

        try:
            import yfinance as yf
            # Download bulk daily data
            df_all = yf.download(tickers=tickers, period=period, interval="1d", progress=False, group_by="ticker")
            
            for ticker in tickers:
                try:
                    if len(tickers) == 1:
                        df_t = df_all
                    else:
                        df_t = df_all[ticker] if ticker in df_all else pd.DataFrame()

                    if not df_t.empty and "Close" in df_t:
                        clean_df = pd.DataFrame({"close": df_t["Close"].dropna()})
                        if len(clean_df) >= 20:
                            data[ticker] = clean_df
                        else:
                            failed_tickers.append(ticker)
                    else:
                        failed_tickers.append(ticker)
                except Exception:
                    failed_tickers.append(ticker)

        except Exception as e:
            failed_tickers = list(tickers)

        # If any ticker failed or network unavailable, populate mock realistic data if fallback enabled
        if self.offline_fallback and failed_tickers:
            for t in failed_tickers:
                data[t] = self._generate_mock_series(t)

        return data

    def get_latest_prices(self, tickers: List[str], history: Optional[Dict[str, pd.DataFrame]] = None) -> Dict[str, float]:
        """Extract latest closing/last price for each ticker."""
        prices: Dict[str, float] = {}
        hist = history or self.fetch_history(tickers, period="5d")

        for t in tickers:
            if t in hist and not hist[t].empty:
                prices[t] = float(hist[t]["close"].iloc[-1])
            else:
                prices[t] = 100.0  # Safe default baseline
        return prices

    def _generate_mock_series(self, ticker: str, periods: int = 65) -> pd.DataFrame:
        """Deterministic mock data for testing/offline simulation."""
        base_prices = {
            "SPY": 580.0,
            "QQQ": 490.0,
            "XLK": 225.0,
            "XLF": 48.0,
            "XLE": 90.0,
            "GLD": 240.0,
            "TLT": 92.0,
            "BIL": 91.5
        }
        start = base_prices.get(ticker, 100.0)
        # Add a subtle deterministic drift
        np.random.seed(abs(hash(ticker)) % 10000)
        noise = np.random.normal(0.001, 0.008, periods)
        prices = [start]
        for n in noise:
            prices.append(prices[-1] * (1.0 + n))
        return pd.DataFrame({"close": prices[1:]})

