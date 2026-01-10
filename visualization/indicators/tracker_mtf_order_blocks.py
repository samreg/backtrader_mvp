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
    def _is_visible_for_render(z: ZoneObject) -> bool:
        # On veut voir les zones actives ET invalidées (historique)
        return z.state in ("active", "invalidated")

    @staticmethod
    def _as_time_df(df: pd.DataFrame) -> pd.DataFrame:
        """
        Garantit une colonne 'time' en pandas datetime, quel que soit le format d'entrée:
        - DatetimeIndex (format MT5 loader aligné)
        - colonne 'datetime'
        - colonne 'time'
        """
        out = df.copy()

        # 1) si index datetime -> le mettre en colonne 'time'
        if isinstance(out.index, pd.DatetimeIndex):
            out = out.reset_index().rename(columns={"index": "time"})

        # 2) sinon si 'time' absent mais 'datetime' présent -> renommer/copier
        if "time" not in out.columns and "datetime" in out.columns:
            out["time"] = out["datetime"]

        # 3) si toujours pas de 'time', erreur explicite
        if "time" not in out.columns:
            raise KeyError(
                "tracker_mtf_order_blocks: impossible de construire la colonne 'time'. "
                f"Colonnes disponibles: {out.columns.tolist()} | index={type(df.index)}"
            )

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

        # --- construire deux vues: trading (actives) vs rendu (actives + invalidées) ---
        all_contributors = []
        for tf in self.timeframes:
            all_contributors.extend(self.tracker.zones_by_tf.get(tf, {}).values())

        contributors_render = [z for z in all_contributors if self._is_visible_for_render(z)]
        contributors_active = [z for z in contributors_render if z.state == "active"]
        # 2) agrégation
        agg_render = self.aggregator.aggregate(contributors_render) #historique des zones
        agg_active = self.aggregator.aggregate(contributors_active)  # si tu veux t'en servir plus tard







        # 3) produire des zones “agrégées” + rectangles
        rectangles = 0
        for i, az in enumerate(agg_render):
            if rectangles >= self.max_rectangles:
                break

            contributors = az.contributors
            active_contrib = [z for z in contributors if z.state == "active"]
            invalid_contrib = [z for z in contributors if z.state == "invalidated"]

            t_start = min(z.t_start for z in contributors)

            # règle: zone agrégée valide tant qu'il reste au moins un contributeur actif
            if len(active_contrib) > 0:
                agg_state = "active"
                t_end = None
                end_idx = None
            else:
                agg_state = "invalidated"
                # fin = dernière invalidation (max t_end) puisque plus aucun actif
                t_end = max(z.t_end for z in invalid_contrib if z.t_end is not None)
                end_idx = self._project_time_to_index(main_index, pd.to_datetime(t_end))

            # mitigation

            mitigation_sum_active = sum(getattr(z, "mitigation_count", 0) for z in active_contrib)
            mitigation_score_sum_active = sum(getattr(z, "mitigation_score", 0.0) for z in active_contrib)

            # projection sur main timeframe (indices)
            start_idx = self._project_time_to_index(main_index, pd.to_datetime(t_start))
            end_idx = self._project_time_to_index(main_index, pd.to_datetime(t_end)) if t_end else None

            bull = az.directions.get("bullish", 0) + az.directions.get("bull", 0)
            bear = az.directions.get("bearish", 0) + az.directions.get("bear", 0)

            if bull > bear:
                dom_dir = "bullish"
            elif bear > bull:
                dom_dir = "bearish"
            else:
                dom_dir = "mixed"

            if dom_dir == "bullish":
                color = "#00b894"  # vert
                label_dir = "OB Bull"
            elif dom_dir == "bearish":
                color = "#d63031"  # rouge
                label_dir = "OB Bear"
            else:
                color = "#6c5ce7"  # violet (mix)
                label_dir = "OB Mix"

            # ZoneObject agrégée (legacy)
            zone_id = f"ob_mtf_{i}"
            zobj = ZoneObject(
                id=zone_id,
                t_start=pd.to_datetime(t_start),
                t_end=pd.to_datetime(t_end) if t_end else None,
                low=float(az.low),
                high=float(az.high),
                type="order_block_mtf",
                state=agg_state,
                source_tf="MTF",
                metadata={
                    "score": az.score,
                    "tf_counts": az.tf_counts,
                    "n_sources": az.metadata.get("n_sources"),
                    "direction": dom_dir,
                    "direction_counts": az.directions,
                    "mitigation_count_active_sum": mitigation_sum_active,
                    "mitigation_score_active_sum": mitigation_score_sum_active,
                    "contributors_active": len(active_contrib),
                    "contributors_invalidated": len(invalid_contrib),
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
                color=color,
                alpha=float(alpha),
                border_color=color,
                border_width=1,
                label=(f"OB-MTF s={az.score:.1f} mit={mitigation_sum_active}" if agg_state == "active" else f"OB-MTF (X) s={az.score:.1f}"),

                metadata={
                    "tf_counts": az.tf_counts,
                    "score": az.score,
                    "direction": dom_dir,
                    "state": agg_state,
                    "mitigation_count_active_sum": mitigation_sum_active,
                },
            )
            result.add_primitive(rect)

            rectangles += 1

        result.add_meta("aggregated_zones", len(agg))
        result.add_meta("rectangles", rectangles)
        return result
