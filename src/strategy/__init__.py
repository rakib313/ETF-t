"""Trading Strategy module."""
from .base import BaseStrategy
from .momentum import ETFMomentumStrategy

__all__ = ["BaseStrategy", "ETFMomentumStrategy"]

