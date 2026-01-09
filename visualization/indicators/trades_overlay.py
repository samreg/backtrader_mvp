"""
Trades Overlay Indicator

Lit trades_backtest.csv et boxes_log.csv
Génère primitives pour visualisation:
- PointPrimitive pour markers ENTRY/EXIT
- RectanglePrimitive pour boxes SL/TP
- Meta trades_navigation pour navigation
"""

from core.indicator_base import IndicatorBase
from core.models import IndicatorResult, PointPrimitive, RectanglePrimitive
import pandas as pd
from pathlib import Path
from typing import Dict, Optional


class Indicator(IndicatorBase):
    """
    Trades overlay indicator
    
    Params:
        trades_file: Path to trades_backtest.csv (default: output/trades_backtest.csv)
        boxes_file: Path to boxes_log.csv (default: output/boxes_log.csv)
    """
    
    def __init__(self, params: dict):
        super().__init__(params)
        self.trades_file = params.get('trades_file', 'output/trades_backtest.csv')
        self.boxes_file = params.get('boxes_file', 'output/boxes_log.csv')
    
    def calculate(self, candles: pd.DataFrame) -> IndicatorResult:
        """
        Calculate trades overlay primitives
        
        Returns:
            IndicatorResult with:
            - PointPrimitive for ENTRY markers
            - RectanglePrimitive for SL/TP boxes
            - meta['trades_navigation'] for trade navigation
        """
        result = IndicatorResult()
        
        # Check if trades file exists
        if not Path(self.trades_file).exists():
            print(f"⚠️  Trades file not found: {self.trades_file}")
            return result

        # Load trades
        trades = pd.read_csv(self.trades_file, parse_dates=['datetime'])
        # CORRECTION: Garder UTC naive (pas de conversion)
        
        # Build time → index mapping
        time_to_index = self._build_time_index_map(candles)
        
        # 1. Generate ENTRY markers (PointPrimitive)
        self._add_entry_markers(result, trades, time_to_index)
        
        # 2. Generate boxes (RectanglePrimitive)
        if Path(self.boxes_file).exists():
            self._add_boxes(result, time_to_index)
        else:
            print(f"⚠️  Boxes file not found: {self.boxes_file}")
        
        # 3. Build trades navigation data
        trades_nav = self._build_trades_navigation(trades, time_to_index)
        result.meta['trades_navigation'] = trades_nav
        
        return result
    
    def _build_time_index_map(self, candles: pd.DataFrame) -> Dict[pd.Timestamp, int]:
        """
        Build mapping: datetime → candle index
        
        Args:
            candles: DataFrame with 'time' or 'datetime' column
        
        Returns:
            Dict mapping timestamp to index
        """
        time_col = 'time' if 'time' in candles.columns else 'datetime'
        
        time_to_index = {}
        for idx, row in candles.iterrows():
            ts = pd.to_datetime(row[time_col])
            # Normalize timezone: remove tz info for comparison
            if ts.tz is not None:
                ts = ts.tz_localize(None)
            time_to_index[ts] = idx
        
        return time_to_index
    
    def _find_closest_index(self, dt: pd.Timestamp, time_to_index: Dict) -> Optional[int]:
        """
        Find closest candle index for given datetime
        
        Args:
            dt: Target datetime
            time_to_index: Time mapping dict
        
        Returns:
            Index or None if not found
        """
        dt = pd.to_datetime(dt)
        # Normalize timezone: remove tz info for comparison
        if dt.tz is not None:
            dt = dt.tz_localize(None)
        
        # Exact match
        if dt in time_to_index:
            return time_to_index[dt]
        
        # Find closest
        all_times = sorted(time_to_index.keys())
        
        # Binary search for closest
        for i, t in enumerate(all_times):
            if t >= dt:
                return time_to_index[t]
        
        # If after all times, return last
        if len(all_times) > 0:
            return time_to_index[all_times[-1]]
        
        return None
    
    def _add_entry_markers(
        self,
        result: IndicatorResult,
        trades: pd.DataFrame,
        time_to_index: Dict
    ):
        """
        Add PointPrimitive for ENTRY events
        
        Args:
            result: IndicatorResult to add primitives to
            trades: Trades DataFrame
            time_to_index: Time mapping
        """
        entries = trades[trades['event_type'] == 'ENTRY']
        
        for _, entry in entries.iterrows():
            idx = self._find_closest_index(entry['datetime'], time_to_index)
            
            if idx is None:
                continue
            
            # Determine color and shape based on direction
            if entry['direction'] == 'LONG':
                color = '#26a69a'
                shape = 'arrow_up'
            else:  # SHORT
                color = '#ef5350'
                shape = 'arrow_down'
            
            point = PointPrimitive(
                id=f"entry_{entry['trade_id']}",
                time_index=idx,
                price=float(entry['price']),
                color=color,
                shape=shape,
                size=8,
                metadata={
                    'trade_id': int(entry['trade_id']),
                    'type': 'ENTRY',
                    'direction': entry['direction'],
                    'label': f"#{entry['trade_id']}"
                }
            )
            
            result.add_primitive(point)
    
    def _add_boxes(
        self,
        result: IndicatorResult,
        time_to_index: Dict
    ):
        """
        Add RectanglePrimitive for SL/TP boxes
        
        Args:
            result: IndicatorResult to add primitives to
            time_to_index: Time mapping
        """
        boxes = pd.read_csv(self.boxes_file, parse_dates=['start_time', 'end_time'])
        # CORRECTION: Garder UTC naive (pas de conversion)
        
        for idx, box in boxes.iterrows():
            start_idx = self._find_closest_index(box['start_time'], time_to_index)
            
            if start_idx is None:
                continue
            
            # End index (can be None if box still active)
            end_idx = None
            if pd.notna(box['end_time']):
                end_idx = self._find_closest_index(box['end_time'], time_to_index)
            
            # Determine color based on type
            box_type = box['type']
            if box_type == 'SL':
                fill_color = 'rgba(239, 83, 80, 0.15)'
                border_color = '#ef5350'
            elif box_type == 'SL_INITIAL':
                fill_color = 'rgba(239, 83, 80, 0.08)'
                border_color = 'rgba(239, 83, 80, 0.5)'
            elif box_type == 'TP1':
                fill_color = 'rgba(38, 166, 154, 0.15)'
                border_color = '#26a69a'
            elif box_type == 'TP2':
                fill_color = 'rgba(77, 208, 225, 0.15)'
                border_color = '#4dd0e1'
            else:
                fill_color = 'rgba(255, 167, 38, 0.15)'
                border_color = '#FFA726'

            # Parse metadata if exists
            dt_start = pd.to_datetime(box['start_time'])
            dt_end = pd.to_datetime(box['end_time']) if pd.notna(box['end_time']) else None

            metadata = {
                'box_type': box_type,
                'trade_id': int(box['trade_id']),
                'original_start_time': int(dt_start.timestamp()),
                'original_end_time': int(dt_end.timestamp()) if dt_end is not None else None
            }
            
            if 'metadata' in box and pd.notna(box['metadata']):
                try:
                    # metadata is string representation of dict
                    import ast
                    meta_dict = ast.literal_eval(str(box['metadata']))
                    metadata.update(meta_dict)
                except:
                    pass
            
            rect = RectanglePrimitive(
                id=f"box_{box_type}_{box['trade_id']}_{start_idx}",
                time_start_index=start_idx,
                time_end_index=end_idx,
                price_low=float(box['price_low']),
                price_high=float(box['price_high']),
                color=fill_color,
                border_color=border_color,
                border_width=1,
                alpha=1.0,  # Alpha already in rgba color
                label=box_type,
                metadata=metadata
            )
            
            result.add_primitive(rect)
    
    def _build_trades_navigation(
        self,
        trades: pd.DataFrame,
        time_to_index: Dict
    ) -> list:
        """
        Build trades navigation data for UI
        
        Args:
            trades: Trades DataFrame
            time_to_index: Time mapping
        
        Returns:
            List of trade navigation dicts
        """
        trades_nav = []
        
        for trade_id in sorted(trades['trade_id'].unique()):
            trade_events = trades[trades['trade_id'] == trade_id]
            
            # Get ENTRY event
            entry_events = trade_events[trade_events['event_type'] == 'ENTRY']
            if len(entry_events) == 0:
                continue
            
            entry = entry_events.iloc[0]

            nav_entry = {
                'id': int(trade_id),
                'time': int(entry['datetime'].timestamp()),
                'direction': entry['direction'],
                'price': float(entry['price'])
            }
            
            trades_nav.append(nav_entry)
        
        return trades_nav
