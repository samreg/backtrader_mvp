"""
Bollinger Bands Indicator

Calcule les bandes de Bollinger (SMA ± N × std)
Retourne 3 séries: upper, middle, lower
"""

from core.indicator_base import IndicatorBase
from core.models import IndicatorResult
import pandas as pd


class Indicator(IndicatorBase):
    """
    Bollinger Bands indicator
    
    Params:
        period: SMA period (default: 20)
        std_dev: Standard deviation multiplier (default: 1.5)
    """
    
    def __init__(self, params: dict):
        super().__init__(params)
        self.period = params.get('period', 20)
        self.std_dev = params.get('std_dev', 1.5)
    
    def calculate(self, candles: pd.DataFrame) -> IndicatorResult:
        """
        Calculate Bollinger Bands
        
        Returns:
            IndicatorResult with series: bb_upper, bb_middle, bb_lower
        """
        result = IndicatorResult()
        
        # Calculate SMA
        sma = candles['close'].rolling(window=self.period).mean()
        
        # Calculate standard deviation
        std = candles['close'].rolling(window=self.period).std()
        
        # Calculate bands
        upper = sma + (self.std_dev * std)
        middle = sma
        lower = sma - (self.std_dev * std)
        
        # Add as series (not primitives - continuous lines)
        result.add_series('bb_upper', upper)
        result.add_series('bb_middle', middle)
        result.add_series('bb_lower', lower)
        
        # Store params in metadata
        result.meta['period'] = self.period
        result.meta['std_dev'] = self.std_dev
        
        return result
