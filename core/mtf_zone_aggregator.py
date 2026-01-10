# core/mtf_zone_aggregator.py
from __future__ import annotations
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple, Any


@dataclass
class AggregatedZone:
    low: float
    high: float
    score: float
    contributors: List[Any] = field(default_factory=list)   # ZoneObject ou dict
    tf_counts: Dict[str, int] = field(default_factory=dict)
    directions: Dict[str, int] = field(default_factory=dict)  # bullish/bearish counts
    metadata: Dict[str, Any] = field(default_factory=dict)

    def contains(self, price: float) -> bool:
        return self.low <= price <= self.high


class MTFZoneAggregator:
    """
    Fusionne des zones par recouvrement de prix et calcule un score (multi-TF).
    Conçu pour être "stateless" : on lui donne des zones actives, il renvoie une vue agrégée.
    """

    def __init__(
        self,
        overlap_min_ratio: float = 0.2,
        merge_gap: float = 0.0,
        tf_weights: Optional[Dict[str, float]] = None,
        direction_key: str = "direction",
        state_active_value: str = "active",
        state_key: str = "state",
        source_tf_key: str = "source_tf",
    ):
        self.overlap_min_ratio = overlap_min_ratio
        self.merge_gap = merge_gap
        self.tf_weights = tf_weights or {}
        self.direction_key = direction_key
        self.state_active_value = state_active_value
        self.state_key = state_key
        self.source_tf_key = source_tf_key

    def _zone_fields(self, z: Any) -> Tuple[float, float, str, str]:
        # Support ZoneObject (attrs) ou dict
        low = getattr(z, "low", None) if not isinstance(z, dict) else z.get("low")
        high = getattr(z, "high", None) if not isinstance(z, dict) else z.get("high")
        tf = getattr(z, self.source_tf_key, None) if not isinstance(z, dict) else z.get(self.source_tf_key)
        state = getattr(z, self.state_key, None) if not isinstance(z, dict) else z.get(self.state_key)
        return float(low), float(high), str(tf), str(state)

    def _zone_direction(self, z: Any) -> Optional[str]:
        meta = getattr(z, "metadata", None) if not isinstance(z, dict) else z.get("metadata")
        if isinstance(meta, dict) and self.direction_key in meta:
            return str(meta[self.direction_key])
        # fallback direct field
        if isinstance(z, dict) and self.direction_key in z:
            return str(z[self.direction_key])
        return None

    @staticmethod
    def _overlap_ratio(a_low: float, a_high: float, b_low: float, b_high: float) -> float:
        inter = min(a_high, b_high) - max(a_low, b_low)
        if inter <= 0:
            return 0.0
        a_len = max(a_high - a_low, 1e-12)
        b_len = max(b_high - b_low, 1e-12)
        return inter / min(a_len, b_len)

    def aggregate(self, zones: List[Any]) -> List[AggregatedZone]:
        # garder uniquement zones actives si possible
        active = []
        for z in zones:
            low, high, tf, state = self._zone_fields(z)
            if state == "invalidated":
                continue
            active.append((low, high, tf, z))

        if not active:
            return []

        active.sort(key=lambda x: (x[0], x[1]))  # sort by low then high

        clusters: List[List[Tuple[float, float, str, Any]]] = []
        for low, high, tf, z in active:
            placed = False
            for cluster in clusters:
                c_low = min(x[0] for x in cluster)
                c_high = max(x[1] for x in cluster)

                # merge if overlap OR small gap
                gap = max(0.0, low - c_high, c_low - high)
                ratio = self._overlap_ratio(low, high, c_low, c_high)
                if ratio >= self.overlap_min_ratio or gap <= self.merge_gap:
                    cluster.append((low, high, tf, z))
                    placed = True
                    break
            if not placed:
                clusters.append([(low, high, tf, z)])

        aggregated: List[AggregatedZone] = []
        for cluster in clusters:
            low = min(x[0] for x in cluster)
            high = max(x[1] for x in cluster)

            tf_counts: Dict[str, int] = {}
            directions: Dict[str, int] = {}
            score = 0.0
            contributors = []

            for z_low, z_high, tf, z in cluster:
                contributors.append(z)
                tf_counts[tf] = tf_counts.get(tf, 0) + 1
                w = float(self.tf_weights.get(tf, 1.0))
                score += w

                d = self._zone_direction(z)
                if d:
                    directions[d] = directions.get(d, 0) + 1

            aggregated.append(
                AggregatedZone(
                    low=low,
                    high=high,
                    score=score,
                    contributors=contributors,
                    tf_counts=tf_counts,
                    directions=directions,
                    metadata={"n_sources": len(cluster)},
                )
            )

        # zones les plus fortes d’abord
        aggregated.sort(key=lambda z: (z.score, z.high - z.low), reverse=True)
        return aggregated

    def zones_at_price(self, aggregated_zones: List[AggregatedZone], price: float) -> List[AggregatedZone]:
        return [z for z in aggregated_zones if z.contains(price)]
