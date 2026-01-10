# core/order_block_tracker.py
from __future__ import annotations
from typing import Any, Dict, List, Optional
from core.mtf_zone_aggregator import MTFZoneAggregator, AggregatedZone


class OrderBlockTracker:
    """
    Stocke et maintient les OrderBlocks (ZoneObject) par timeframe.
    - State = mémoire (zones actives/invalidées)
    - N'agrège pas : il délègue à MTFZoneAggregator pour la vue consolidée.
    """

    def __init__(
        self,
        timeframes: List[str],
        aggregator: Optional[MTFZoneAggregator] = None,
        keep_invalidated: bool = False,
        max_zones_per_tf: int = 200,
    ):
        self.timeframes = list(timeframes)
        self.keep_invalidated = keep_invalidated
        self.max_zones_per_tf = max_zones_per_tf

        self.zones_by_tf: Dict[str, Dict[str, Any]] = {tf: {} for tf in self.timeframes}
        self.aggregator = aggregator or MTFZoneAggregator()

        # cache
        self._last_aggregated: List[AggregatedZone] = []

    def update_from_indicator_result(self, tf: str, indicator_result: Any) -> None:
        """
        indicator_result est l'objet renvoyé par order_blocks.Indicator.calculate()
        On récupère les ZoneObject via result.objects (ou attribut équivalent).
        """
        zones = None
        for attr in ("objects", "objs", "zones"):
            if hasattr(indicator_result, attr):
                zones = getattr(indicator_result, attr)
                break
        if zones is None:
            # fallback: certains frameworks stockent via get_objects()
            if hasattr(indicator_result, "get_objects"):
                zones = indicator_result.get_objects()
            else:
                zones = []

        self.update(tf, zones)

    def update(self, tf: str, zones: List[Any]) -> None:
        if tf not in self.zones_by_tf:
            self.zones_by_tf[tf] = {}

        bucket = self.zones_by_tf[tf]

        for z in zones:
            zid = getattr(z, "id", None) if not isinstance(z, dict) else z.get("id")
            if zid is None:
                # générer un id stable minimal (pas idéal, mais évite crash)
                zid = str(id(z))

            bucket[zid] = z

        # purge invalidated si demandé
        if not self.keep_invalidated:
            to_del = []
            for zid, z in bucket.items():
                state = getattr(z, "state", None) if not isinstance(z, dict) else z.get("state")
                if state == "invalidated":
                    to_del.append(zid)
            for zid in to_del:
                del bucket[zid]

        # limite mémoire (garde les plus récents si possible)
        if len(bucket) > self.max_zones_per_tf:
            # heuristique: si ZoneObject a t_start, trier par t_start
            items = list(bucket.items())
            def key(item):
                z = item[1]
                t = getattr(z, "t_start", None) if not isinstance(z, dict) else z.get("t_start")
                return t
            items.sort(key=key, reverse=True)
            bucket.clear()
            for zid, z in items[: self.max_zones_per_tf]:
                bucket[zid] = z

    def get_active_zones(self, tfs: Optional[List[str]] = None) -> List[Any]:
        res = []
        for tf in (tfs or self.zones_by_tf.keys()):
            for z in self.zones_by_tf.get(tf, {}).values():
                state = getattr(z, "state", None) if not isinstance(z, dict) else z.get("state")
                if state != "invalidated":
                    res.append(z)
        return res

    def aggregate(self) -> List[AggregatedZone]:
        active = self.get_active_zones()
        self._last_aggregated = self.aggregator.aggregate(active)
        return self._last_aggregated

    def get_aggregated(self) -> List[AggregatedZone]:
        return self._last_aggregated

    def zones_at_price(self, price: float, refresh: bool = True) -> List[AggregatedZone]:
        if refresh or not self._last_aggregated:
            self.aggregate()
        return self.aggregator.zones_at_price(self._last_aggregated, price)
