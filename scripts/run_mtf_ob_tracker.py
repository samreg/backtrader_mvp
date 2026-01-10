# scripts/run_mtf_ob_tracker.py
import yaml
import pandas as pd

from data.mt5_loader import MT5Loader
from visualization.indicators.order_blocks import Indicator as OBIndicator  # ton module OB :contentReference[oaicite:4]{index=4}
from core.mtf_zone_aggregator import MTFZoneAggregator
from core.order_block_tracker import OrderBlockTracker


def _prepare_candles_for_indicator(df: pd.DataFrame) -> pd.DataFrame:
    """
    Ton OrderBlocks utilise get_time_column(candles). Selon l'implémentation, il peut chercher
    'time' ou 'datetime'. Pour être robuste, on fournit une colonne 'datetime' et une colonne 'time'.
    """
    out = df.copy()
    # si l'index est datetime, remettre en colonne
    if isinstance(out.index, pd.DatetimeIndex):
        out = out.reset_index().rename(columns={"index": "datetime"})
    if "datetime" not in out.columns and "time" in out.columns:
        out["datetime"] = out["time"]
    if "time" not in out.columns and "datetime" in out.columns:
        out["time"] = out["datetime"]
    return out


def main(config_path: str):
    cfg = yaml.safe_load(open(config_path, "r", encoding="utf-8"))

    symbol = cfg["data"]["symbol"]
    main_tf = cfg["data"]["main_timeframe"]
    n_bars = int(cfg["data"]["n_bars"])

    tfs = cfg["mtf_order_blocks"]["timeframes"]
    ob_params = dict(cfg["mtf_order_blocks"].get("params", {}))

    ag_cfg = cfg.get("aggregator", {})
    aggregator = MTFZoneAggregator(
        overlap_min_ratio=float(ag_cfg.get("overlap_min_ratio", 0.2)),
        merge_gap=float(ag_cfg.get("merge_gap", 0.0)),
        tf_weights=dict(ag_cfg.get("tf_weights", {})),
    )

    required = list({main_tf, *tfs})
    tracker = OrderBlockTracker(timeframes=tfs, aggregator=aggregator, keep_invalidated=False)

    with MT5Loader() as loader:
        candles_by_tf = loader.load_multi_tf(
            symbol=symbol,
            main_tf=main_tf,
            n_bars_main=n_bars,
            required_tfs=required
        )

    # calcule OB sur chaque TF demandée
    for tf in tfs:
        df = candles_by_tf[tf]
        df_for_ind = _prepare_candles_for_indicator(df)

        params = dict(ob_params)
        params["timeframe"] = tf  # pour ZoneObject.source_tf (IndicatorBase) :contentReference[oaicite:5]{index=5}
        ind = OBIndicator(params)

        res = ind.calculate(df_for_ind)
        tracker.update_from_indicator_result(tf, res)

        # stats
        n_z = len(tracker.get_active_zones([tf]))
        print(f"[{tf}] zones actives: {n_z}")

    aggregated = tracker.aggregate()
    print("\n=== Aggregated Zones (top 10) ===")
    for z in aggregated[:10]:
        print(f"low={z.low:.5f} high={z.high:.5f} score={z.score:.2f} tf_counts={z.tf_counts} dirs={z.directions}")

    # test “prix courant dans zone ?” (dernier close du main_tf)
    main_df = candles_by_tf[main_tf]
    last_close = float(main_df["close"].iloc[-1]) if "close" in main_df.columns else float(main_df.iloc[-1]["close"])
    hit = tracker.zones_at_price(last_close, refresh=False)

    print(f"\nLast close ({main_tf}) = {last_close:.5f}")
    print(f"Zones contenant le prix: {len(hit)}")
    for z in hit[:5]:
        print(f"  -> low={z.low:.5f} high={z.high:.5f} score={z.score:.2f} tf_counts={z.tf_counts}")


if __name__ == "__main__":
    import sys
    main(sys.argv[1] if len(sys.argv) > 1 else "config_mtf_ob_tracker.yaml")
