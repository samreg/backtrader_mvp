"""
EMA Indicator - Exponential Moving Average

Simple series indicator example.
Calculates EMA and returns it as a series aligned with candles.

Usage in YAML:
    indicators:
      - name: ema_50
        module: ema.py
        timeframe: M5
        panel: main
        params:
          period: 50
        style:
          color: '#2196F3'
          linewidth: 2
"""

from core.indicator_base import IndicatorBase
from core.models import IndicatorResult
import pandas as pd


class Indicator(IndicatorBase):
    """
    EMA (Exponential Moving Average) indicator
    
    Params:
        period: EMA period (default: 20)
        source: Column to use ('close', 'open', 'high', 'low', default: 'close')
    """
    
    def __init__(self, params: dict):
        super().__init__(params)
        self.period = params.get('period', 20)
        self.source = params.get('source', 'close')
    
    def calculate(self, candles: pd.DataFrame) -> IndicatorResult:
        """
        Calculate EMA
        
        Args:
            candles: DataFrame with OHLCV data
        
        Returns:
            IndicatorResult with 'ema' series
        """
        self.validate_candles(candles)
        
        result = IndicatorResult()
        
        # Calculate EMA
        ema = candles[self.source].ewm(span=self.period, adjust=False).mean()
        
        # Add to result
        result.add_series('ema', ema)
        
        # Add metadata
        result.add_meta('period', self.period)
        result.add_meta('source', self.source)
        
        return result
