import backtrader as bt
from data.mt5_loader import MT5Loader
from data.bt_feed_converter import dataframe_to_btfeed


class MTFAlignmentProbe(bt.Strategy):
    def __init__(self):
        for i, d in enumerate(self.datas):
            print(f"Data{i} name={d._name}")

    def next(self):
        # Print 1 ligne de debug par bougie principale seulement (évite spam)
        dt0 = bt.num2date(self.datas[0].datetime[0])
        dt1 = bt.num2date(self.datas[1].datetime[0])
        dt2 = bt.num2date(self.datas[2].datetime[0])
        print(f"DT main={dt0} | tf1={dt1} | tf2={dt2}")


def run():
    symbol = "EURUSD"
    main_tf = "M3"
    n_bars_main = 2000
    required_tfs = ["M5", "M15"]  # tu peux même oublier M3 maintenant si tu appliques le patch D

    loader = MT5Loader()
    candles_by_tf = loader.load_multi_tf(
        symbol=symbol,
        main_tf=main_tf,
        n_bars_main=n_bars_main,
        required_tfs=required_tfs
    )

    # --- Vérifications structurelles ---
    assert main_tf in candles_by_tf, f"Main TF {main_tf} absent du retour: {list(candles_by_tf.keys())}"

    for tf, df in candles_by_tf.items():
        assert df.index.dtype.kind == "M", f"{tf} n'a pas un index datetime (dtype={df.index.dtype})"
        assert len(df) > 50, f"{tf} trop court: {len(df)} lignes"
        print(f"{tf}: {df.index.min()} → {df.index.max()} ({len(df)} bars)")

    # --- Vérification alignement ---
    common_start = max(df.index.min() for df in candles_by_tf.values())
    common_end = min(df.index.max() for df in candles_by_tf.values())
    for tf, df in candles_by_tf.items():
        assert df.index.min() == common_start, f"{tf} start non aligné: {df.index.min()} vs {common_start}"
        assert df.index.max() == common_end, f"{tf} end non aligné: {df.index.max()} vs {common_end}"

    print(f"OK alignement: {common_start} → {common_end}")

    # --- Conversion en feeds et test Backtrader ---
    feeds = {tf: dataframe_to_btfeed(df, name=f"{symbol}_{tf}") for tf, df in candles_by_tf.items()}

    cerebro = bt.Cerebro()
    cerebro.adddata(feeds[main_tf])
    # ajouter les autres TF dans un ordre stable
    for tf in sorted([k for k in feeds.keys() if k != main_tf]):
        cerebro.adddata(feeds[tf])

    cerebro.addstrategy(MTFAlignmentProbe)
    cerebro.run()


if __name__ == "__main__":
    run()
