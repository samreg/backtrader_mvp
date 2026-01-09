"""
Primitive Serializer

Converts core primitives to JavaScript structures for Lightweight Charts
"""

import pandas as pd
from core.models import IndicatorResult, PointPrimitive, RectanglePrimitive, LinePrimitive, TextPrimitive
from typing import List, Dict, Any


class PrimitiveSerializer:
    """
    Converts primitives from IndicatorResult to JS data structures
    
    Usage:
        serializer = PrimitiveSerializer(candles_data)
        
        # Convert series
        bb_upper = serializer.series_to_js(result, 'bb_upper')
        
        # Convert primitives
        markers = serializer.points_to_markers(result)
        rectangles = serializer.rectangles_to_js(result)
    """
    
    def __init__(self, candles_data: List[Dict[str, Any]]):
        """
        Initialize serializer
        
        Args:
            candles_data: List of candle dicts with 'time' field
                         [{time: timestamp, open, high, low, close}, ...]
        """
        self.candles_data = candles_data
    
    def series_to_js(self, result: IndicatorResult, series_name: str) -> List[Dict[str, Any]]:
        """
        Convert pandas Series to Lightweight Charts line data
        
        Args:
            result: IndicatorResult containing the series
            series_name: Name of series to convert (e.g. 'bb_upper', 'rsi')
        
        Returns:
            List of {time, value} dicts
        """
        if series_name not in result.series:
            return []
        
        series = result.series[series_name]
        js_data = []
        
        for i, val in enumerate(series):
            if pd.notna(val) and i < len(self.candles_data):
                js_data.append({
                    'time': self.candles_data[i]['time'],
                    'value': float(val)
                })
        
        return js_data
    
    def points_to_markers(self, result: IndicatorResult) -> List[Dict[str, Any]]:
        """
        Convert PointPrimitive to Lightweight Charts markers
        
        Args:
            result: IndicatorResult containing PointPrimitive objects
        
        Returns:
            List of marker dicts for Lightweight Charts
        """
        markers = []
        
        for prim in result.primitives:
            if not isinstance(prim, PointPrimitive):
                continue
            
            # Skip if index out of bounds
            if prim.time_index >= len(self.candles_data):
                continue
            
            # Determine position based on shape
            if 'up' in prim.shape.lower():
                position = 'belowBar'
            elif 'down' in prim.shape.lower():
                position = 'aboveBar'
            else:
                position = 'inBar'
            
            marker = {
                'time': self.candles_data[prim.time_index]['time'],
                'position': position,
                'color': prim.color,
                'shape': self._convert_shape(prim.shape),
                'text': prim.metadata.get('label', ''),
                'id': prim.id
            }
            
            markers.append(marker)
        
        return markers
    
    def rectangles_to_js(self, result: IndicatorResult) -> List[Dict[str, Any]]:
        """
        Convert RectanglePrimitive to canvas rectangles data
        
        Args:
            result: IndicatorResult containing RectanglePrimitive objects
        
        Returns:
            List of rectangle dicts matching existing JS structure
        """
        rectangles = []
        
        for prim in result.primitives:
            if not isinstance(prim, RectanglePrimitive):
                continue
            
            # Skip if indices out of bounds
            if prim.time_start_index >= len(self.candles_data):
                continue

            # Build rectangle dict
            # CORRECTION: Utiliser les timestamps originaux des metadata (pas ceux des bougies)
            rect = {
                'type': prim.metadata.get('box_type', 'UNKNOWN'),
                'trade_id': prim.metadata.get('trade_id'),
                'time1': prim.metadata.get('original_start_time', self.candles_data[prim.time_start_index]['time']),
                'time2': prim.metadata.get('original_end_time'),
                'price1': prim.price_low,
                'price2': prim.price_high,
                'fillColor': prim.color,
                'borderColor': prim.border_color or prim.color,
                'metadata': prim.metadata
            }

            # Fallback si pas de original_end_time dans metadata
            if rect['time2'] is None and prim.time_end_index is not None and prim.time_end_index < len(
                    self.candles_data):
                rect['time2'] = self.candles_data[prim.time_end_index]['time']
            
            rectangles.append(rect)
        
        return rectangles
    
    def _convert_shape(self, shape: str) -> str:
        """
        Convert primitive shape to Lightweight Charts shape
        
        Args:
            shape: Primitive shape name (e.g. 'arrow_up', 'circle')
        
        Returns:
            Lightweight Charts shape name
        """
        mapping = {
            'arrow_up': 'arrowUp',
            'arrow_down': 'arrowDown',
            'circle': 'circle',
            'square': 'square'
        }
        return mapping.get(shape.lower(), 'circle')
