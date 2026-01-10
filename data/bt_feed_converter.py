import backtrader as bt
import pandas as pd


class PandasDataFeed(bt.feeds.PandasData):
    """
    Wrapper générique pour convertir un DataFrame en DataFeed Backtrader.
    Le DataFrame doit contenir : datetime, open, high, low, close, volume.
    """
    params = (
        ('datetime', 'datetime'),
        ('open', 'open'),
        ('high', 'high'),
        ('low', 'low'),
        ('close', 'close'),
        ('volume', 'volume'),
        ('openinterest', -1),
    )


def dataframe_to_btfeed(df: pd.DataFrame, name: str = "feed"):
    """
    Convertit un DataFrame OHLCV en Backtrader DataFeed.

    Args:
        df (pd.DataFrame): DataFrame contenant datetime + OHLCV
        name (str): nom du feed pour le moteur Backtrader

    Returns:
        PandasDataFeed: un feed utilisable via cerebro.adddata()
    """
    if not isinstance(df, pd.DataFrame):
        raise TypeError("df must be a pandas DataFrame")

    # Assurer que datetime est en index
    if "datetime" in df.columns:
        df = df.set_index("datetime")

    # Assurer le bon format
    df.index = pd.to_datetime(df.index)

    # Backtrader exige un index ordonné
    df = df.sort_index()

    feed = PandasDataFeed(dataname=df)
    feed._name = name  # utile pour le debug / log

    return feed
