"""
Zone Aggregator Indicator

Aggregates zones from multiple sources (HTF indicators) and provides
a boolean series: "is price in any zone at each bar?"

This demonstrates Approach A: querying zones from HTF without projection.

Usage in YAML:
    indicators:
      - name: zone_aggregator
        module: zone_aggregator.py
        timeframe: M5  # Main TF
        panel: bottom_1
        params:
          sources:
            - indicator: order_blocks_h1
              type: order_block
            - indicator: order_blocks_h4
              type: order_block
"""

from core.indicator_base import IndicatorBase
from core.models import IndicatorResult
import pandas as pd


class Indicator(IndicatorBase):
    """
    Zone Aggregator
    
    Queries zones from multiple source indicators and produces a boolean series
    indicating if price is within ANY zone at each bar.
    
    This demonstrates the Approach A helper usage:
    - Sources remain in their native TF
    - We query "zones active at time t"
    - We check "does price fall within any zone"
    
    Params:
        sources: List of dicts with:
            - indicator: Name of source indicator
            - type: Zone type to query (optional)
    
    Note:
        This indicator needs access to other indicators' zone registries.
        In practice, this is handled by chart_viewer passing indicator instances.
    """
    
    def __init__(self, params: dict):
        super().__init__(params)
        self.sources = params.get('sources', [])
        
        # Will be set by chart_viewer
        self.source_indicators = {}
    
    def set_source_indicators(self, indicators: dict):
        """
        Set source indicator instances
        
        Called by chart_viewer to inject indicator references.
        
        Args:
            indicators: Dict mapping indicator name -> indicator instance
        """
        self.source_indicators = indicators
    
    def calculate(self, candles: pd.DataFrame) -> IndicatorResult:
        """
        Aggregate zones and produce boolean series
        
        For each bar in main TF candles:
        1. Get timestamp and close price
        2. Query all source indicators for zones active at that time
        3. Check if price is within any zone
        4. Set boolean value
        
        Args:
            candles: DataFrame with OHLCV data (main TF)
        
        Returns:
            IndicatorResult with 'price_in_zone' boolean series
        """
        self.validate_candles(candles)
        
        result = IndicatorResult()
        
        time_col = self.get_time_column(candles)
        
        # Boolean series: price in any zone?
        price_in_zone = pd.Series(False, index=candles.index)
        
        # Count zones found
        total_zones_checked = 0
        zones_hit = 0
        
        # For each bar
        for i in range(len(candles)):
            dt = time_col.iloc[i]
            price = candles.iloc[i]['close']
            
            in_any_zone = False
            
            # Query each source
            for source_config in self.sources:
                indicator_name = source_config['indicator']
                zone_type = source_config.get('type', None)
                
                # Get indicator instance
                if indicator_name not in self.source_indicators:
                    continue  # Source not available
                
                indicator = self.source_indicators[indicator_name]
                
                # Check if indicator has zone_registry
                if not hasattr(indicator, 'zone_registry'):
                    continue
                
                # Query zones active at this time
                active_zones = indicator.zone_registry.zones_active_at(
                    dt=dt,
                    type=zone_type
                )
                
                total_zones_checked += len(active_zones)
                
                # Check if price is in any zone
                for zone in active_zones:
                    if zone.contains_price(price):
                        in_any_zone = True
                        zones_hit += 1
                        break
                
                if in_any_zone:
                    break
            
            price_in_zone.iloc[i] = in_any_zone
        
        # Add series to result
        result.add_series('price_in_zone', price_in_zone)
        
        # Add metadata
        result.add_meta('total_zones_checked', total_zones_checked)
        result.add_meta('bars_in_zone', price_in_zone.sum())
        result.add_meta('bars_outside_zone', (~price_in_zone).sum())
        result.add_meta('zone_hit_rate', zones_hit / len(candles) if len(candles) > 0 else 0)
        
        return result
