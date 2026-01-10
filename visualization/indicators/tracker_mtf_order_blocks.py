# visualization/indicators/tracker_mtf_order_blocks.py
from __future__ import annotations
from typing import Dict, Any, List
import pandas as pd

from core.indicator_base import IndicatorBase
from core.models import IndicatorResult, ZoneObject, RectanglePrimitive
from core.order_block_tracker import OrderBlockTracker
from core.mtf_zone_aggregator import MTFZoneAggregator

from visualization.indicators.order_blocks import Indicator as OrderBlocksIndicator


class Indicator(IndicatorBase):
    """
    Indicateur composite:
    - calcule OrderBlocks sur plusieurs TF
    - track + aggregate
    - renvoie zones consolidées (objets) + rectangles (primitives)
    """

    def __init__(self, params: Dict[str, Any]):
        super().__init__(params)
        self.timeframes: List[str] = list(params.get("timeframes", []))
        if not self.timeframes:
            raise ValueError("tracker_mtf_order_blocks: params.timeframes est requis")

        ag = params.get("aggregator", {})
        self.aggregator = MTFZoneAggregator(
            overlap_min_ratio=float(ag.get("overlap_min_ratio", 0.2)),
            merge_gap=float(ag.get("merge_gap", 0.0)),
            tf_weights=dict(ag.get("tf_weights", {})),
        )
        self.tracker = OrderBlockTracker(
            timeframes=self.timeframes,
            aggregator=self.aggregator,
            keep_invalidated=bool(params.get("keep_invalidated", False)),
            max_zones_per_tf=int(params.get("max_zones_per_tf", 300)),
        )

        # params pour l’indicateur order_blocks “source”
        self.ob_params = dict(params.get("order_blocks_params", {}))

        # rendu
        self.alpha_base = float(params.get("alpha_base", 0.18))
        self.alpha_per_score = float(params.get("alpha_per_score", 0.03))
        self.max_rectangles = int(params.get("max_rectangles", 120))

    def calculate(self, candles: pd.DataFrame) -> IndicatorResult:
        # On ne peut pas faire MTF avec seulement un DF
        raise ValueError(
            "tracker_mtf_order_blocks doit être exécuté via calculate_multi(candles_by_tf, main_tf)."
        )

    @staticmethod
    def _as_time_df(df: pd.DataFrame) -> pd.DataFrame:
        """
        OrderBlocks et IndicatorBase supportent 'time' colonne ou DatetimeIndex.
        Pour être robuste, on fournit une colonne 'time' si index datetime.
        """
        out = df.copy()
        if isinstance(out.index, pd.DatetimeIndex):
            out = out.reset_index().rename(columns={"index": "time"})
        elif "time" not in out.columns:
            # fallback: si index pas datetime mais on a 'datetime'
            if "datetime" in out.columns:
                out["time"] = out["datetime"]
        out["time"] = pd.to_datetime(out["time"])
        return out

    @staticmethod
    def _project_time_to_index(main_index: pd.DatetimeIndex, dt: pd.Timestamp) -> int:
        """
        Convertit un timestamp en index de bougie (projection sur la TF principale).
        """
        pos = int(main_index.searchsorted(dt, side="left"))
        if pos < 0:
            return 0
        if pos >= len(main_index):
            return len(main_index) - 1
        return pos

    def calculate_multi(self, candles_by_tf: Dict[str, pd.DataFrame], main_tf: str) -> IndicatorResult:
        result = IndicatorResult()

        if main_tf not in candles_by_tf:
            raise ValueError(f"Main TF {main_tf} absent de candles_by_tf")

        main_candles = candles_by_tf[main_tf]
        main_index = pd.to_datetime(main_candles.index)

        # 1) calcul OB sur chaque TF et update tracker
        for tf in self.timeframes:
            if tf not in candles_by_tf:
                continue

            tf_df = self._as_time_df(candles_by_tf[tf])
            ind = OrderBlocksIndicator({**self.ob_params})
            ind.timeframe = tf  # important pour ZoneObject.source_tf (IndicatorBase) :contentReference[oaicite:1]{index=1}
            ind.name = f"order_blocks_{tf}"
            tf_res = ind.calculate(tf_df)

            zones = [z for z in tf_res.objects if isinstance(z, ZoneObject)]
            self.tracker.update(tf, zones)

        # 2) agrégation
        agg = self.tracker.aggregate()

        # 3) produire des zones “agrégées” + rectangles
        rectangles = 0
        for i, az in enumerate(agg):
            if rectangles >= self.max_rectangles:
                break

            # t_start / t_end : on prend l’enveloppe temporelle des contributeurs
            t_start = min(z.t_start for z in az.contributors)
            t_end_candidates = [z.t_end for z in az.contributors if z.t_end is not None]
            t_end = max(t_end_candidates) if t_end_candidates else None

            # projection sur main timeframe (indices)
            start_idx = self._project_time_to_index(main_index, pd.to_datetime(t_start))
            end_idx = self._project_time_to_index(main_index, pd.to_datetime(t_end)) if t_end else None

            # ZoneObject agrégée (legacy)
            zone_id = f"ob_mtf_{i}"
            zobj = ZoneObject(
                id=zone_id,
                t_start=pd.to_datetime(t_start),
                t_end=pd.to_datetime(t_end) if t_end else None,
                low=float(az.low),
                high=float(az.high),
                type="order_block_mtf",
                state="active",
                source_tf="MTF",
                metadata={
                    "score": az.score,
                    "tf_counts": az.tf_counts,
                    "n_sources": az.metadata.get("n_sources"),
                },
            )
            result.add_object(zobj)

            # RectanglePrimitive (rendu)
            alpha = min(0.85, self.alpha_base + self.alpha_per_score * float(az.score))
            rect = RectanglePrimitive(
                id=f"rect_{zone_id}",
                time_start_index=int(start_idx),
                time_end_index=None if end_idx is None else int(end_idx),
                price_low=float(az.low),
                price_high=float(az.high),
                color="#6c5ce7",
                alpha=float(alpha),
                border_color="#6c5ce7",
                border_width=1,
                label=f"OB-MTF s={az.score:.1f}",
                metadata={"tf_counts": az.tf_counts, "score": az.score},
            )
            result.add_primitive(rect)

            rectangles += 1

        result.add_meta("aggregated_zones", len(agg))
        result.add_meta("rectangles", rectangles)
        return result
