import yaml
import pandas as pd

from data.mt5_loader import load_candles_from_config
from visualization.indicators.tracker_mtf_order_blocks import Indicator as MTFTracker


def main(cfg_path="../config_mtf_ob_tracker.yaml"):
    cfg = yaml.safe_load(open(cfg_path, "r", encoding="utf-8"))

    candles_by_tf = load_candles_from_config(cfg)
    main_tf = cfg["data"]["main_timeframe"]

    ind_cfg = cfg["indicators"][0]
    params = ind_cfg.get("params", {})
    ind = MTFTracker(params)
    ind.name = ind_cfg.get("name", "tracker_mtf_ob")
    ind.timeframe = main_tf

    res = ind.calculate_multi(candles_by_tf=candles_by_tf, main_tf=main_tf)

    zones = [o for o in res.objects if getattr(o, "type", "") == "order_block_mtf"]
    print(f"Aggregated zones: {len(zones)}")

    # tri par score desc
    zones.sort(key=lambda z: float(z.metadata.get("score", 0.0)), reverse=True)

    for z in zones[:20]:
        score = z.metadata.get("score")
        tf_counts = z.metadata.get("tf_counts")
        mit_sum = z.metadata.get("mitigation_count_active_sum")
        active_n = z.metadata.get("contributors_active")
        inval_n = z.metadata.get("contributors_invalidated")
        print(
            f"[{z.state}] score={score} mit_active_sum={mit_sum} "
            f"active={active_n} invalid={inval_n} "
            f"low={z.low:.5f} high={z.high:.5f} "
            f"start={z.t_start} end={z.t_end} tf_counts={tf_counts}"
        )


if __name__ == "__main__":
    main()
