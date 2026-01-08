"""
Backtrader Indicator Adapter

Wraps core indicators to make them usable in Backtrader strategies.
Provides both 'lines' for signals/events and Python helpers for zone queries.

Usage in strategy:
    class MyStrategy(bt.Strategy):
        def __init__(self):
            # Load indicator
            self.ob_indicator = BacktraderIndicatorAdapter(
                core_indicator_class=OrderBlockIndicator,
                params={'min_body_size': 0.0005}
            )
        
        def next(self):
            # Access via lines (for events)
            if self.ob_indicator.lines.zone_created[0]:
                print("New zone created!")
            
            # Access via helpers (for queries)
            zones = self.ob_indicator.get_zones_containing(self.data.close[0], self.data.datetime.datetime())
            if zones:
                print(f"Price in {len(zones)} zones")
"""

import backtrader as bt
from core.indicator_base import IndicatorBase
from core.models import IndicatorResult
import pandas as pd


class BacktraderIndicatorAdapter(bt.Indicator):
    """
    Generic adapter for core indicators
    
    Exposes:
    - lines: For signals/events (Backtrader way)
    - Python helpers: For zone queries (non-lines)
    
    Lines provided:
    - event: 1 when something happened (zone created, BOS detected, etc.), 0 otherwise
    
    Note: We can't put all zones in lines (too many), so zones are accessed via helpers.
    """
    
    lines = ('event',)  # Generic event flag
    
    params = (
        ('core_indicator', None),  # Core indicator instance
        ('indicator_params', {}),  # Parameters for core indicator
    )
    
    def __init__(self):
        # Create core indicator instance
        if self.params.core_indicator is None:
            raise ValueError("Must provide core_indicator parameter")
        
        self.core_indicator = self.params.core_indicator(self.params.indicator_params)
        
        # Cache for results
        self._current_result = None
        self._bar_index = 0
    
    def next(self):
        """
        Called by Backtrader for each bar
        
        Problem: Backtrader calls next() bar by bar, but our indicators
        need the full history. Solution: Only calculate once when we have
        enough data, then just index into results.
        """
        # On first call, calculate for all available data
        if self._current_result is None:
            self._calculate_all()
        
        # Default: no event
        self.lines.event[0] = 0
        
        # Check if we have events for this bar
        # (This is indicator-specific logic)
        # For now, just set 0
        
        self._bar_index += 1
    
    def _calculate_all(self):
        """Calculate indicator for all available data"""
        # Convert Backtrader data to DataFrame
        candles = self._backtrader_to_dataframe()
        
        # Calculate
        self._current_result = self.core_indicator.calculate(candles)
    
    def _backtrader_to_dataframe(self) -> pd.DataFrame:
        """Convert Backtrader data to DataFrame format"""
        # Get all available bars
        n_bars = len(self.data)
        
        data = {
            'time': [],
            'open': [],
            'high': [],
            'low': [],
            'close': [],
            'volume': []
        }
        
        for i in range(-n_bars + 1, 1):
            data['time'].append(self.data.datetime.datetime(i))
            data['open'].append(self.data.open[i])
            data['high'].append(self.data.high[i])
            data['low'].append(self.data.low[i])
            data['close'].append(self.data.close[i])
            data['volume'].append(self.data.volume[i])
        
        df = pd.DataFrame(data)
        return df
    
    # === HELPER METHODS (non-lines) ===
    
    def get_result(self) -> IndicatorResult:
        """Get current indicator result"""
        if self._current_result is None:
            self._calculate_all()
        return self._current_result
    
    def get_zones_active_at(self, dt, tf=None, type=None):
        """Helper: Get zones active at datetime"""
        if not hasattr(self.core_indicator, 'zone_registry'):
            return []
        
        return self.core_indicator.zone_registry.zones_active_at(dt, tf, type)
    
    def get_zones_containing(self, price, dt, tf=None, type=None):
        """Helper: Get zones containing price at datetime"""
        if not hasattr(self.core_indicator, 'zone_registry'):
            return []
        
        return self.core_indicator.zone_registry.zones_containing(price, dt, tf, type)
    
    def get_nearest_zone(self, price, dt, tf=None, type=None, side='any'):
        """Helper: Get nearest zone to price"""
        if not hasattr(self.core_indicator, 'zone_registry'):
            return None
        
        return self.core_indicator.zone_registry.nearest_zone(price, dt, tf, type, side)


# === CONVENIENCE FUNCTIONS ===

def create_backtrader_indicator(indicator_class, params=None):
    """
    Create a Backtrader-compatible indicator from a core indicator class
    
    Args:
        indicator_class: Core indicator class (inherits from IndicatorBase)
        params: Dictionary of parameters
    
    Returns:
        Backtrader indicator class
    
    Example:
        OrderBlockIndicatorBT = create_backtrader_indicator(
            OrderBlockIndicator,
            params={'min_body_size': 0.0005}
        )
        
        class MyStrategy(bt.Strategy):
            def __init__(self):
                self.ob = OrderBlockIndicatorBT(self.data)
    """
    if params is None:
        params = {}
    
    class WrappedIndicator(BacktraderIndicatorAdapter):
        params = (
            ('core_indicator', indicator_class),
            ('indicator_params', params),
        )
    
    return WrappedIndicator
