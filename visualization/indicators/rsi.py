"""
RSI (Relative Strength Index) Indicator

Calcule le RSI en utilisant EMA (comme Backtrader)
Retourne une série: rsi
"""

from core.indicator_base import IndicatorBase
from core.models import IndicatorResult
import pandas as pd


class Indicator(IndicatorBase):
    """
    RSI indicator
    
    Uses EMA (Exponential Weighted Moving Average) for smoothing,
    compatible with Backtrader's RSI calculation.
    
    Params:
        period: RSI period (default: 14)
    """
    
    def __init__(self, params: dict):
        super().__init__(params)
        self.period = params.get('period', 14)
    
    def calculate(self, candles: pd.DataFrame) -> IndicatorResult:
        """
        Calculate RSI using EMA smoothing
        
        Returns:
            IndicatorResult with series: rsi
        """
        result = IndicatorResult()
        
        # Calculate price changes
        delta = candles['close'].diff()
        
        # Separate gains and losses
        gain = delta.where(delta > 0, 0)
        loss = -delta.where(delta < 0, 0)
        
        # IMPORTANT: Use EWM (Exponential Weighted Moving) like Backtrader
        # NOT rolling().mean() (Simple Moving Average)
        avg_gain = gain.ewm(alpha=1/self.period, adjust=False).mean()
        avg_loss = loss.ewm(alpha=1/self.period, adjust=False).mean()
        
        # Calculate RS and RSI
        rs = avg_gain / avg_loss
        rsi = 100 - (100 / (1 + rs))
        
        # Add as series
        result.add_series('rsi', rsi)
        
        # Store params in metadata
        result.meta['period'] = self.period
        
        return result
