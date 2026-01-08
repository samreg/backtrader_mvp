"""
Base class for all indicators

All indicators must inherit from IndicatorBase and implement calculate().
This ensures a common interface for dynamic loading and execution.

How to add a new indicator:
1. Create a file in visualization/indicators/ (e.g., my_indicator.py)
2. Import IndicatorBase from core.indicator_base
3. Inherit from IndicatorBase
4. Implement __init__(self, params: dict)
5. Implement calculate(self, candles: pd.DataFrame) -> IndicatorResult
6. Add to config YAML

Example:
    class MyIndicator(IndicatorBase):
        def __init__(self, params: dict):
            super().__init__(params)
            self.period = params.get('period', 14)
        
        def calculate(self, candles: pd.DataFrame) -> IndicatorResult:
            result = IndicatorResult()
            # ... calculate indicator
            result.add_series('my_line', pd.Series(...))
            return result
"""

from abc import ABC, abstractmethod
from typing import Dict, Any
import pandas as pd
from core.models import IndicatorResult


class IndicatorBase(ABC):
    """
    Base class for all indicators
    
    Indicators are pure calculation engines:
    - No UI logic
    - No Backtrader logic
    - Just: candles in → IndicatorResult out
    
    Attributes:
        params: Dictionary of parameters from YAML
        name: Indicator name (set by loader)
        timeframe: Source timeframe (set by loader)
    """
    
    def __init__(self, params: Dict[str, Any]):
        """
        Initialize indicator with parameters
        
        Args:
            params: Dictionary of parameters from YAML config
        """
        self.params = params
        self.name = ""  # Set by loader
        self.timeframe = ""  # Set by loader
    
    @abstractmethod
    def calculate(self, candles: pd.DataFrame) -> IndicatorResult:
        """
        Calculate indicator values
        
        This is the main method that must be implemented by all indicators.
        
        Args:
            candles: DataFrame with columns: time, open, high, low, close, volume
                     Index should be DatetimeIndex or have 'time' column
        
        Returns:
            IndicatorResult with:
            - series: Dict of pd.Series aligned with candles
            - objects: List of ZoneObject/SegmentObject
            - meta: Dict of metadata
        
        Example:
            def calculate(self, candles):
                result = IndicatorResult()
                
                # Calculate series (e.g., EMA)
                ema = candles['close'].ewm(span=self.period).mean()
                result.add_series('ema', ema)
                
                # Or create zones
                zone = ZoneObject(
                    id=self.generate_zone_id(),
                    t_start=candles.iloc[i]['time'],
                    t_end=None,
                    low=low_price,
                    high=high_price,
                    type='order_block',
                    source_tf=self.timeframe
                )
                result.add_object(zone)
                
                return result
        """
        pass
    
    def validate_candles(self, candles: pd.DataFrame) -> bool:
        """
        Validate that candles DataFrame has required columns
        
        Args:
            candles: DataFrame to validate
        
        Returns:
            True if valid, raises ValueError otherwise
        """
        required_cols = ['open', 'high', 'low', 'close']  # Volume optionnel
        
        for col in required_cols:
            if col not in candles.columns:
                raise ValueError(f"Missing required column: {col}")
        
        # Check for time column or DatetimeIndex
        if 'time' not in candles.columns and not isinstance(candles.index, pd.DatetimeIndex):
            raise ValueError("Candles must have 'time' column or DatetimeIndex")
        
        return True
    
    def get_time_column(self, candles: pd.DataFrame) -> pd.Series:
        """
        Get time column from candles (handles both 'time' column and DatetimeIndex)
        
        Args:
            candles: DataFrame with time data
        
        Returns:
            Series of datetime values
        """
        if 'time' in candles.columns:
            return candles['time']
        elif isinstance(candles.index, pd.DatetimeIndex):
            return pd.Series(candles.index, index=candles.index)
        else:
            raise ValueError("No time column found")
    
    def __repr__(self) -> str:
        return f"{self.__class__.__name__}(name='{self.name}', tf='{self.timeframe}')"
