"""
Package de stratégies de trading
"""

from .base_strategy import BaseStrategy
from .strategy_rsi_amplitude import RSIAmplitudeStrategy
from .strategy_macd_ema import MACDEMAStrategy
from .strategy_bollinger_breakout import BollingerBreakoutStrategy

__all__ = [
    'BaseStrategy',
    'RSIAmplitudeStrategy',
    'MACDEMAStrategy',
    'BollingerBreakoutStrategy',
]
