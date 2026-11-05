"""Abstract Base Strategy Interface."""
from abc import ABC, abstractmethod
from typing import Dict, List
import pandas as pd


class BaseStrategy(ABC):
    """Abstract interface that all trading strategies must implement."""

    @abstractmethod
    def generate_signals(self, price_history: Dict[str, pd.DataFrame]) -> List[str]:
        """
        Evaluate historical market data and return an ordered list of target ETF tickers
        to hold for the upcoming period.
        """
        pass

