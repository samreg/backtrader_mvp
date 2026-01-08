"""
Core data models for indicators and visualization

Defines standard object types that indicators can produce:
- GraphicPrimitive: Base class for all visual elements
- PointPrimitive, TextPrimitive, LinePrimitive, RectanglePrimitive, CurvePrimitive: Specific primitives
- ZoneObject: For order blocks, liquidity zones, imbalances (LEGACY - will migrate to RectanglePrimitive)
- SegmentObject: For BOS/CHOCH, trend lines (LEGACY - will migrate to LinePrimitive)
- IndicatorResult: Standard output format for all indicators
"""

from dataclasses import dataclass, field
from datetime import datetime
from typing import Dict, List, Optional, Any
import pandas as pd


# ============================================================================
# GRAPHIC PRIMITIVES - Generic visual elements
# ============================================================================

@dataclass
class GraphicPrimitive:
    """
    Base class for all graphic primitives.
    
    All graphic elements that can be rendered on a chart inherit from this.
    This provides a common interface for the chart viewer.
    """
    id: str
    layer: int = 0  # Z-order for stacking (higher = on top)
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class PointPrimitive(GraphicPrimitive):
    """
    Point/Marker primitive.
    
    Represents a single point on the chart (e.g., entry/exit signals).
    
    Attributes:
        time_index: Candle index (0-based)
        price: Y coordinate (price level)
        color: Hex color (e.g., '#26a69a')
        shape: Visual shape ('circle', 'square', 'triangle', 'cross', 'arrow_up', 'arrow_down')
        size: Size in pixels
    """
    time_index: int = 0
    price: float = 0.0
    color: str = '#000000'
    shape: str = 'circle'
    size: int = 5


@dataclass
class TextPrimitive(GraphicPrimitive):
    """
    Text label primitive.
    
    Displays text at a specific chart location.
    
    Attributes:
        time_index: Candle index (0-based)
        price: Y coordinate (price level)
        text: Text content
        color: Text color
        font_size: Font size in pixels
        background_color: Optional background box color
        alignment: Text alignment ('left', 'center', 'right')
    """
    time_index: int = 0
    price: float = 0.0
    text: str = ''
    color: str = '#000000'
    font_size: int = 12
    background_color: Optional[str] = None
    alignment: str = 'center'


@dataclass
class LinePrimitive(GraphicPrimitive):
    """
    Line/Segment primitive.
    
    Draws a line between two points. Can be horizontal, vertical, or diagonal.
    
    Attributes:
        time_start_index: Start candle index
        time_end_index: End candle index
        price_start: Start price
        price_end: End price (same as start for horizontal lines)
        color: Line color
        width: Line width in pixels
        style: Line style ('solid', 'dashed', 'dotted')
        label: Optional text label at line midpoint
    """
    time_start_index: int = 0
    time_end_index: int = 0
    price_start: float = 0.0
    price_end: float = 0.0
    color: str = '#000000'
    width: int = 1
    style: str = 'solid'
    label: Optional[str] = None


@dataclass
class RectanglePrimitive(GraphicPrimitive):
    """
    Rectangle/Zone primitive.
    
    Draws a filled rectangle (e.g., for Order Blocks, supply/demand zones).
    
    Attributes:
        time_start_index: Start candle index
        time_end_index: End candle index (None = extends to chart end)
        price_low: Bottom price
        price_high: Top price
        color: Fill color (hex)
        alpha: Transparency (0.0-1.0)
        border_color: Optional border color (defaults to fill color)
        border_width: Border width in pixels
        label: Optional text label inside rectangle
    """
    time_start_index: int = 0
    time_end_index: Optional[int] = None
    price_low: float = 0.0
    price_high: float = 0.0
    color: str = '#000000'
    alpha: float = 0.3
    border_color: Optional[str] = None
    border_width: int = 1
    label: Optional[str] = None


@dataclass
class CurvePrimitive(GraphicPrimitive):
    """
    Curve primitive (series of connected points).
    
    Draws a continuous line through multiple points (e.g., moving averages).
    
    Attributes:
        time_indices: List of candle indices
        prices: List of prices (same length as time_indices)
        color: Line color
        width: Line width in pixels
        style: Line style ('solid', 'dashed', 'dotted')
    """
    time_indices: List[int] = field(default_factory=list)
    prices: List[float] = field(default_factory=list)
    color: str = '#000000'
    width: int = 1
    style: str = 'solid'


# ============================================================================
# LEGACY OBJECTS - Will be phased out in favor of primitives
# ============================================================================

@dataclass
class ZoneObject:
    """
    Represents a price zone (order block, liquidity, imbalance, etc.)
    
    Zones remain in their native timeframe with absolute timestamps.
    No projection to main timeframe - use helpers to query zones.
    
    Attributes:
        id: Unique identifier for this zone
        t_start: Start timestamp (absolute)
        t_end: End timestamp (absolute, None = extends to present)
        low: Bottom price of zone
        high: Top price of zone
        type: Zone type ("order_block", "liquidity", "imbalance", "supply", "demand")
        state: Current state ("active", "invalidated")
        source_tf: Source timeframe (e.g., "H1", "M5")
        symbol: Trading symbol
        entry_candle_index: Index de la bougie d'entrée (création du bloc)
        exit_candle_index: Index de la bougie de sortie (invalidation), None si actif
        mitigation_count: Nombre de fois que le prix a touché la zone
        mitigation_score: Score de mitigation (0.0 = jamais touché, 1.0+ = très mitigé)
        last_mitigation_index: Index de la dernière bougie qui a touché la zone
        metadata: Additional data (strength, volume, etc.)
    """
    id: str
    t_start: datetime
    t_end: Optional[datetime]
    low: float
    high: float
    type: str
    state: str = "active"
    source_tf: str = ""
    symbol: str = ""
    entry_candle_index: Optional[int] = None
    exit_candle_index: Optional[int] = None
    mitigation_count: int = 0                    # NOUVEAU: Nombre de touches
    mitigation_score: float = 0.0                # NOUVEAU: Score de mitigation
    last_mitigation_index: Optional[int] = None  # NOUVEAU: Dernière touche
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def is_active_at(self, dt: datetime) -> bool:
        """Check if zone is active at given datetime"""
        if self.state != "active":
            return False
        if dt < self.t_start:
            return False
        if self.t_end is not None and dt > self.t_end:
            return False
        return True
    
    def contains_price(self, price: float) -> bool:
        """Check if price is within zone bounds"""
        return self.low <= price <= self.high
    
    def distance_to_price(self, price: float) -> float:
        """Calculate distance from price to nearest edge of zone"""
        if self.contains_price(price):
            return 0.0
        elif price < self.low:
            return self.low - price
        else:
            return price - self.high


@dataclass
class SegmentObject:
    """
    Represents a line segment (BOS, CHOCH, trend line, etc.)
    
    Segments remain in their native timeframe with absolute timestamps.
    
    Attributes:
        id: Unique identifier
        t_start: Start timestamp (absolute)
        t_end: End timestamp (absolute)
        y_start: Start price
        y_end: End price
        type: Segment type ("BOS", "CHOCH", "trendline")
        state: Current state ("active", "broken", "complete")
        source_tf: Source timeframe
        label: Display label
        metadata: Additional data
    """
    id: str
    t_start: datetime
    t_end: datetime
    y_start: float
    y_end: float
    type: str
    state: str = "active"
    source_tf: str = ""
    label: str = ""
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class IndicatorResult:
    """
    Standard output format for all indicators
    
    Indicators return this object containing:
    - series: Time series data aligned with candles (for oscillators like RSI, MACD)
    - objects: LEGACY - Graphical objects (zones, segments) - use primitives instead
    - primitives: NEW - Generic graphic primitives (points, lines, rectangles, etc.)
    - meta: Metadata (debug info, statistics, etc.)
    
    Example (NEW way with primitives):
        result = IndicatorResult(
            series={'ema': pd.Series([...])},
            primitives=[
                RectanglePrimitive(id='ob_1', ...),
                LinePrimitive(id='bos_1', ...)
            ],
            meta={'zones_created': 5, 'calculation_time': 0.05}
        )
    
    Example (LEGACY way - still supported):
        result = IndicatorResult(
            series={'ema': pd.Series([...])},
            objects=[ZoneObject(...), SegmentObject(...)],
            meta={'zones_created': 5}
        )
    """
    series: Dict[str, pd.Series] = field(default_factory=dict)
    objects: List[Any] = field(default_factory=list)  # LEGACY: ZoneObject | SegmentObject
    primitives: List[GraphicPrimitive] = field(default_factory=list)  # NEW: Generic primitives
    meta: Dict[str, Any] = field(default_factory=dict)
    
    def add_series(self, name: str, data: pd.Series):
        """Add a time series"""
        self.series[name] = data
    
    def add_object(self, obj):
        """LEGACY: Add a zone or segment object"""
        self.objects.append(obj)
    
    def add_primitive(self, primitive: GraphicPrimitive):
        """NEW: Add a graphic primitive"""
        self.primitives.append(primitive)
    
    def add_meta(self, key: str, value: Any):
        """Add metadata"""
        self.meta[key] = value


# Type aliases for clarity
Zone = ZoneObject
Segment = SegmentObject
Result = IndicatorResult
