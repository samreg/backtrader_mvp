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

        #------------------------------
        print(f"\n📊 TIMEFRAME ALIGNMENT CHECK:")
        print(f"Main TF ({main_tf}): {len(main_candles)} candles")
        print(f"  → First: {main_index[0]}")
        print(f"  → Last:  {main_index[-1]}")

        for tf in self.timeframes:
            if tf in candles_by_tf:
                tf_df = candles_by_tf[tf]
                tf_index = pd.to_datetime(tf_df.index)
                print(f"\n{tf}: {len(tf_df)} candles")
                print(f"  → First: {tf_index[0]}")
                print(f"  → Last:  {tf_index[-1]}")

                # Check overlap
                if tf_index[0] > main_index[0]:
                    delta = (tf_index[0] - main_index[0]).total_seconds() / 60
                    print(f"  ⚠️ STARTS {delta:.0f} minutes AFTER main TF!")
                if tf_index[-1] < main_index[-1]:
                    delta = (main_index[-1] - tf_index[-1]).total_seconds() / 60
                    print(f"  ⚠️ ENDS {delta:.0f} minutes BEFORE main TF!")

        print("\n" + "=" * 60 + "\n")
        #------------------------------

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
            bucket = self.tracker.zones_by_tf.get(tf, {})
            all_contributors.extend(bucket.values())

            n_total = len(bucket)
            n_active = sum(z.state == "active" for z in bucket.values())
            n_invalid = sum(z.state == "invalidated" for z in bucket.values())
            print(f"[{tf}] tracker bucket total={n_total} active={n_active} invalidated={n_invalid}")

        contributors_active = [z for z in all_contributors if z.state == "active"]
        contributors_invalidated = [z for z in all_contributors if z.state == "invalidated"]

        # 2) agrégation SÉPARÉE pour éviter la fusion actives/invalidées
        agg_active = self.aggregator.aggregate(contributors_active)
        agg_invalidated = self.aggregator.aggregate(contributors_invalidated)

        # Combiner pour le rendu
        agg_render = agg_active + agg_invalidated

        print(f"   Aggregated: {len(agg_active)} active, {len(agg_invalidated)} invalidated")

        # ============================================================================
        # NOUVELLE LOGIQUE DE RENDU : 3 COUCHES
        # ============================================================================

        # Compteur de primitives
        prim_count = 0

        # ----------------------------------------------------------------------------
        # ----------------------------------------------------------------------------
        # COUCHE 1 : RENDRE TOUS LES OB INDIVIDUELS (M5, M10, ...)
        # ----------------------------------------------------------------------------
        for z in all_contributors:
            if prim_count >= self.max_rectangles:
                break

            # TOUJOURS projeter via timestamp (pas via entry_candle_index)
            # car entry_candle_index est l'index dans le TF source (M5/M10), pas dans main_tf (M3)
            start_idx = self._project_time_to_index(main_index, z.t_start)
            end_idx = self._project_time_to_index(main_index, z.t_end) if z.t_end else None

            # DEBUG
            print(
                f"🔹 Rendering {z.id}: t_start={z.t_start}, projected_idx={start_idx} (was source_idx={z.entry_candle_index})")

            # Direction
            direction = z.metadata.get('direction', 'unknown')

            # Couleur et alpha selon état et direction
            if z.state == 'invalidated':
                color = '#9E9E9E'  # Gris
                alpha = 0.12
                state_mark = ' (X)'
            elif direction == 'bullish':
                color = '#00b894'  # Vert
                alpha = 0.22
                state_mark = ''
            elif direction == 'bearish':
                color = '#d63031'  # Rouge
                alpha = 0.22
                state_mark = ''
            else:
                color = '#6c5ce7'  # Violet
                alpha = 0.18
                state_mark = ''

            # Label compact : TF + mitigation
            tf_short = z.source_tf if z.source_tf else '??'
            label = f"{tf_short} {direction[:4].upper()}{state_mark} m={z.mitigation_count}"

            # Primitive OB individuel
            rect = RectanglePrimitive(
                id=f"rect_ob_{z.id}",
                time_start_index=int(start_idx),
                time_end_index=int(end_idx) if end_idx is not None else None,
                price_low=float(z.low),
                price_high=float(z.high),
                color=color,
                alpha=float(alpha),
                border_color=color,
                border_width=1,
                label=label,
                layer=0,  # Couche base
                metadata={
                    'type': 'individual_ob',
                    'zone_id': z.id,
                    'tf': z.source_tf,
                    'direction': direction,
                    'state': z.state,
                    'mitigation_count': z.mitigation_count,
                },
            )
            print(f"🟦 tracker COUCHE 1: Creating primitive {rect.id}, label='{rect.label}'")

            result.add_primitive(rect)
            prim_count += 1

            # Ajouter le ZoneObject (legacy)
            result.add_object(z)

        # ----------------------------------------------------------------------------
        # COUCHE 2 : RENDRE LES ZONES AGRÉGÉES (OVERLAY GRIS)
        # ----------------------------------------------------------------------------
        for i, az in enumerate(agg_render):
            if prim_count >= self.max_rectangles:
                break

            contributors = az.contributors
            active_contrib = [z for z in contributors if z.state == "active"]
            invalid_contrib = [z for z in contributors if z.state == "invalidated"]

            # Ne rendre que les agrégats avec ≥2 contributeurs
            if len(contributors) < 2:
                continue

            # État de l'agrégat
            if len(active_contrib) >= 1:
                agg_state = "active"
                t_end = None
                end_idx = None
            else:
                agg_state = "invalidated"
                # Ne pas afficher les agrégats invalidés (tous contributeurs morts)
                continue

            # Timestamps
            t_start = min(z.t_start for z in contributors)
            start_idx = self._project_time_to_index(main_index, pd.to_datetime(t_start))

            # Mitigation totale (sum des actifs)
            mitigation_sum_active = sum(getattr(z, "mitigation_count", 0) for z in active_contrib)
            mitigation_score_sum_active = sum(getattr(z, "mitigation_score", 0.0) for z in active_contrib)

            # Direction dominante
            bull = az.directions.get("bullish", 0) + az.directions.get("bull", 0)
            bear = az.directions.get("bearish", 0) + az.directions.get("bear", 0)

            if bull > bear:
                dom_dir = "BULL"
            elif bear > bull:
                dom_dir = "BEAR"
            else:
                dom_dir = "MIX"

            # Couleur agrégat : GRIS semi-transparent (overlay)
            agg_color = '#A0A0A0'
            agg_alpha = 0.08  # Très transparent

            # Label agrégat
            n_active = len(active_contrib)
            n_invalid = len(invalid_contrib)
            label_agg = f"AGG#{i} x{n_active}"
            if n_invalid > 0:
                label_agg += f" ({n_invalid}X)"
            label_agg += f"                                      AGG {dom_dir} m={mitigation_sum_active}"

            # ZoneObject agrégé (legacy)
            zone_id = f"ob_mtf_agg_{i}"
            zobj = ZoneObject(
                id=zone_id,
                t_start=pd.to_datetime(t_start),
                t_end=None,  # Agrégat actif n'a pas de fin
                low=float(az.low),
                high=float(az.high),
                type="order_block_aggregated",
                state=agg_state,
                source_tf="MTF",
                entry_candle_index=int(start_idx),
                exit_candle_index=None,
                mitigation_count=mitigation_sum_active,
                mitigation_score=mitigation_score_sum_active,
                metadata={
                    "score": az.score,
                    "tf_counts": az.tf_counts,
                    "n_contributors_active": n_active,
                    "n_contributors_invalidated": n_invalid,
                    "direction": dom_dir,
                    "contributors_ids": [c.id for c in contributors],
                },
            )
            result.add_object(zobj)

            # Primitive agrégat (overlay gris)
            rect_agg = RectanglePrimitive(
                id=f"rect_{zone_id}",
                time_start_index=int(start_idx),
                time_end_index=None,
                price_low=float(az.low),
                price_high=float(az.high),
                color=agg_color,
                alpha=float(agg_alpha),
                border_color='#FFFFFF',
                border_width=3,  # Bordure plus épaisse
                label=label_agg,
                layer=1,  # Couche supérieure (overlay)
                metadata={
                    'type': 'aggregated_zone',
                    'zone_id': zone_id,
                    'tf_counts': az.tf_counts,
                    'score': az.score,
                    'direction': dom_dir,
                    'state': agg_state,
                    'n_contributors_active': n_active,
                    'n_contributors_invalidated': n_invalid,
                    'contributors_ids': [c.id for c in contributors],
                },
            )
            print(f"🟩 tracker COUCHE 2: Creating primitive {rect_agg.id}, label='{rect_agg.label}'")

            result.add_primitive(rect_agg)

            # DEBUG détaillé pour rectangles gris
            if z.state == 'invalidated':
                print(f"  🔴 INVALIDATED OB: {z.id}")
                print(f"     start_idx={start_idx}, end_idx={end_idx}")
                print(f"     t_start={z.t_start}, t_end={z.t_end}")
                print(f"     price=[{z.low:.2f}, {z.high:.2f}]")
                print(f"     label='{label}'")

            prim_count += 1

        # Metadata
        result.add_meta("total_individual_obs", len(all_contributors))
        result.add_meta("active_individual_obs", len(contributors_active))
        result.add_meta("invalidated_individual_obs", len(contributors_invalidated))
        result.add_meta("aggregated_zones", len([z for z in agg_render if len(z.contributors) >= 2]))
        result.add_meta("total_primitives", prim_count)

        return result
