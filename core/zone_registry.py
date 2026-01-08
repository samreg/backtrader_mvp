"""
Zone Registry - Manages zones for indicators

Provides efficient storage and querying of zones.
Each indicator has its own registry.

Performance: Currently O(n) for queries, but interface allows
for future optimization (R-tree, spatial indexing, etc.)
"""

from typing import List, Optional, Literal
from datetime import datetime
from core.models import ZoneObject


class ZoneRegistry:
    """
    Registry for managing zones
    
    Each indicator that produces zones should maintain its own registry.
    Aggregators can query multiple registries.
    
    Usage:
        registry = ZoneRegistry()
        registry.add_zone(zone)
        active = registry.zones_active_at(datetime.now())
        containing = registry.zones_containing(price=1.0500, dt=datetime.now())
    """
    
    def __init__(self):
        self.zones: List[ZoneObject] = []
        self._id_counter = 0
    
    def generate_id(self, prefix: str = "zone") -> str:
        """Generate unique zone ID"""
        self._id_counter += 1
        return f"{prefix}_{self._id_counter}"
    
    def add_zone(self, zone: ZoneObject):
        """Add a zone to registry"""
        self.zones.append(zone)
    
    def update_zone_state(self, zone_id: str, new_state: str):
        """Update zone state (active, mitigated, expired)"""
        for zone in self.zones:
            if zone.id == zone_id:
                zone.state = new_state
                break
    
    def get_zone(self, zone_id: str) -> Optional[ZoneObject]:
        """Get zone by ID"""
        for zone in self.zones:
            if zone.id == zone_id:
                return zone
        return None
    
    def zones_active_at(
        self,
        dt: datetime,
        tf: Optional[str] = None,
        type: Optional[str] = None
    ) -> List[ZoneObject]:
        """
        Get zones active at given datetime
        
        Args:
            dt: Datetime to check
            tf: Filter by timeframe (e.g., "H1")
            type: Filter by type (e.g., "order_block")
        
        Returns:
            List of active zones
        """
        result = []
        for zone in self.zones:
            # Check if active at dt
            if not zone.is_active_at(dt):
                continue
            
            # Filter by timeframe
            if tf is not None and zone.source_tf != tf:
                continue
            
            # Filter by type
            if type is not None and zone.type != type:
                continue
            
            result.append(zone)
        
        return result
    
    def zones_containing(
        self,
        price: float,
        dt: datetime,
        tf: Optional[str] = None,
        type: Optional[str] = None
    ) -> List[ZoneObject]:
        """
        Get zones containing the given price at datetime
        
        Args:
            price: Price to check
            dt: Datetime to check
            tf: Filter by timeframe
            type: Filter by type
        
        Returns:
            List of zones containing price
        """
        active = self.zones_active_at(dt, tf, type)
        return [z for z in active if z.contains_price(price)]
    
    def nearest_zone(
        self,
        price: float,
        dt: datetime,
        tf: Optional[str] = None,
        type: Optional[str] = None,
        side: Literal["above", "below", "any"] = "any"
    ) -> Optional[ZoneObject]:
        """
        Find nearest zone to given price
        
        Args:
            price: Reference price
            dt: Datetime to check
            tf: Filter by timeframe
            type: Filter by type
            side: Look for zones "above", "below", or "any"
        
        Returns:
            Nearest zone or None
        """
        active = self.zones_active_at(dt, tf, type)
        
        if not active:
            return None
        
        # Filter by side
        if side == "above":
            candidates = [z for z in active if z.low > price]
        elif side == "below":
            candidates = [z for z in active if z.high < price]
        else:
            candidates = active
        
        if not candidates:
            return None
        
        # Find nearest
        return min(candidates, key=lambda z: z.distance_to_price(price))
    
    def get_all_zones(self, state: Optional[str] = None) -> List[ZoneObject]:
        """
        Get all zones, optionally filtered by state
        
        Args:
            state: Filter by state ("active", "mitigated", "expired", None=all)
        
        Returns:
            List of zones
        """
        if state is None:
            return self.zones.copy()
        return [z for z in self.zones if z.state == state]
    
    def clear(self):
        """Clear all zones"""
        self.zones.clear()
        self._id_counter = 0
    
    def __len__(self) -> int:
        """Number of zones in registry"""
        return len(self.zones)
    
    def __repr__(self) -> str:
        active = sum(1 for z in self.zones if z.state == "active")
        return f"ZoneRegistry(total={len(self.zones)}, active={active})"
