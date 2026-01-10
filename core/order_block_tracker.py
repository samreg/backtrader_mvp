# core/order_block_tracker.py
from __future__ import annotations
from typing import Dict, List, Optional
from core.models import ZoneObject
from core.mtf_zone_aggregator import MTFZoneAggregator, AggregatedZone


class OrderBlockTracker:
    """
    Stateful: maintient l'état des zones OB par timeframe.
    """

    def __init__(
        self,
        timeframes: List[str],
        aggregator: Optional[MTFZoneAggregator] = None,
        keep_invalidated: bool = False,
        max_zones_per_tf: int = 300,
    ):
        self.timeframes = list(timeframes)
        self.keep_invalidated = keep_invalidated
        self.max_zones_per_tf = int(max_zones_per_tf)
        self.zones_by_tf: Dict[str, Dict[str, ZoneObject]] = {tf: {} for tf in self.timeframes}
        self.aggregator = aggregator or MTFZoneAggregator()
        self._last_aggregated: List[AggregatedZone] = []

    def update(self, tf: str, zones: List[ZoneObject]) -> None:
        bucket = self.zones_by_tf.setdefault(tf, {})

        for z in zones:
            # s'assurer que source_tf est correct
            z.source_tf = tf
            bucket[z.id] = z

        if not self.keep_invalidated:
            for zid in [k for k, v in bucket.items() if v.state != "active"]:
                del bucket[zid]

        # limite mémoire : garder les plus récentes selon entry_candle_index si dispo
        if len(bucket) > self.max_zones_per_tf:
            items = list(bucket.items())

            def key(item):
                z = item[1]
                return z.entry_candle_index if z.entry_candle_index is not None else -1

            items.sort(key=key, reverse=True)
            bucket.clear()
            for zid, z in items[: self.max_zones_per_tf]:
                bucket[zid] = z

    def get_active_zones(self, tfs: Optional[List[str]] = None) -> List[ZoneObject]:
        res: List[ZoneObject] = []
        for tf in (tfs or list(self.zones_by_tf.keys())):
            for z in self.zones_by_tf.get(tf, {}).values():
                if z.state == "active":
                    res.append(z)
        return res

    def aggregate(self) -> List[AggregatedZone]:
        self._last_aggregated = self.aggregator.aggregate(self.get_active_zones())
        return self._last_aggregated

    def get_aggregated(self) -> List[AggregatedZone]:
        return self._last_aggregated

    def zones_at_price(self, price: float, refresh: bool = True) -> List[AggregatedZone]:
        if refresh or not self._last_aggregated:
            self.aggregate()
        return [z for z in self._last_aggregated if z.contains(price)]
