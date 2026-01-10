# core/mtf_zone_aggregator.py
from __future__ import annotations
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Any
from core.models import ZoneObject


@dataclass
class AggregatedZone:
    low: float
    high: float
    score: float
    tf_counts: Dict[str, int] = field(default_factory=dict)
    contributors: List[ZoneObject] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)

    def contains(self, price: float) -> bool:
        return self.low <= price <= self.high


class MTFZoneAggregator:
    """
    Agrège des zones par recouvrement de prix et calcule un score pondéré par TF.
    Stateless: on lui donne des zones actives -> il renvoie une vue agrégée.
    """

    def __init__(
        self,
        overlap_min_ratio: float = 0.2,
        merge_gap: float = 0.0,
        tf_weights: Optional[Dict[str, float]] = None,
    ):
        self.overlap_min_ratio = float(overlap_min_ratio)
        self.merge_gap = float(merge_gap)
        self.tf_weights = tf_weights or {}

    @staticmethod
    def _overlap_ratio(a_low: float, a_high: float, b_low: float, b_high: float) -> float:
        inter = min(a_high, b_high) - max(a_low, b_low)
        if inter <= 0:
            return 0.0
        a_len = max(a_high - a_low, 1e-12)
        b_len = max(b_high - b_low, 1e-12)
        return inter / min(a_len, b_len)

    def aggregate(self, zones: List[ZoneObject]) -> List[AggregatedZone]:
        # garder uniquement actives
        active = [z for z in zones if z.state == "active"]
        if not active:
            return []

        # tri par low/high
        active.sort(key=lambda z: (z.low, z.high))

        clusters: List[List[ZoneObject]] = []

        for z in active:
            placed = False
            for c in clusters:
                c_low = min(x.low for x in c)
                c_high = max(x.high for x in c)

                gap = 0.0
                if z.low > c_high:
                    gap = z.low - c_high
                elif c_low > z.high:
                    gap = c_low - z.high

                ratio = self._overlap_ratio(z.low, z.high, c_low, c_high)
                if ratio >= self.overlap_min_ratio or gap <= self.merge_gap:
                    c.append(z)
                    placed = True
                    break

            if not placed:
                clusters.append([z])

        out: List[AggregatedZone] = []
        for c in clusters:
            low = min(x.low for x in c)
            high = max(x.high for x in c)

            tf_counts: Dict[str, int] = {}
            score = 0.0
            for x in c:
                tf = x.source_tf or "UNKNOWN"
                tf_counts[tf] = tf_counts.get(tf, 0) + 1
                score += float(self.tf_weights.get(tf, 1.0))

            out.append(
                AggregatedZone(
                    low=low,
                    high=high,
                    score=score,
                    tf_counts=tf_counts,
                    contributors=c,
                    metadata={"n_sources": len(c)},
                )
            )

        out.sort(key=lambda z: (z.score, z.high - z.low), reverse=True)
        return out
