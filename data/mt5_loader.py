"""
MT5 Historical Data Loader

Loads multi-timeframe historical data from MetaTrader 5.
Used by chart_viewer to fetch candles for main TF and all indicator TFs.

IMPORTANT: This is for HISTORICAL data only, not real-time streaming.
"""

import MetaTrader5 as mt5
import pandas as pd
from datetime import datetime, timedelta
from typing import Dict, List, Optional
from pathlib import Path
import math


# Timeframe mapping
TIMEFRAME_MAP = {
    'M1': (mt5.TIMEFRAME_M1, 1),
    'M3': (mt5.TIMEFRAME_M3, 3),
    'M5': (mt5.TIMEFRAME_M5, 5),
    'M15': (mt5.TIMEFRAME_M15, 15),
    'M30': (mt5.TIMEFRAME_M30, 30),
    'H1': (mt5.TIMEFRAME_H1, 60),
    'H4': (mt5.TIMEFRAME_H4, 240),
    'D1': (mt5.TIMEFRAME_D1, 1440),
}


def get_data_filename(symbol: str, timeframe: str) -> str:
    """
    Génère le nom de fichier standardisé
    
    Args:
        symbol: Symbole (ex: NAS100, EURUSD)
        timeframe: Timeframe MT5 (ex: M3, M5, H1)
    
    Returns:
        str: Nom fichier (ex: NAS100_M3.csv)
    """
    return f"{symbol}_{timeframe}.csv"


class MT5Loader:
    """
    Loads historical candles from MT5 for multiple timeframes
    
    Usage:
        loader = MT5Loader()
        candles_by_tf = loader.load_multi_tf(
            symbol='EURUSD',
            main_tf='M5',
            n_bars_main=2000,
            required_tfs=['M5', 'H1', 'H4']
        )
    """
    
    def __init__(self):
        self.initialized = False
    
    def initialize(self) -> bool:
        """
        Initialize MT5 connection
        
        Returns:
            True if successful
        """
        if self.initialized:
            return True
        
        if not mt5.initialize():
            print(f"❌ MT5 initialize failed: {mt5.last_error()}")
            return False
        
        self.initialized = True
        print("✅ MT5 initialized")
        return True
    
    def shutdown(self):
        """Shutdown MT5 connection"""
        if self.initialized:
            mt5.shutdown()
            self.initialized = False
            print("✅ MT5 shutdown")
    
    def download_historical(
        self,
        symbol: str,
        timeframe_str: str,
        months: int = 6
    ) -> pd.DataFrame:
        """
        Télécharge données historiques MT5
        
        Args:
            symbol: Symbole (ex: NAS100, EURUSD)
            timeframe_str: Timeframe MT5 (ex: M3, M5, H1)
            months: Nombre de mois d'historique
            
        Returns:
            DataFrame avec colonnes: datetime, open, high, low, close, volume
            
        Raises:
            ValueError: Timeframe invalide ou symbole introuvable
            ConnectionError: Erreur MT5
        """
        if timeframe_str not in TIMEFRAME_MAP:
            raise ValueError(
                f"Timeframe '{timeframe_str}' invalide. "
                f"Valides: {list(TIMEFRAME_MAP.keys())}"
            )
        
        timeframe = TIMEFRAME_MAP[timeframe_str][0]
        
        # Vérifier symbole
        symbol_info = mt5.symbol_info(symbol)
        if symbol_info is None:
            raise ValueError(f"Symbole '{symbol}' introuvable")
        
        # Période
        to_date = datetime.now()
        from_date = to_date - timedelta(days=months * 30)
        
        print(f"📥 Téléchargement: {symbol} {timeframe_str}")
        print(f"   Période: {from_date.strftime('%Y-%m-%d')} → {to_date.strftime('%Y-%m-%d')}")
        
        # Télécharger
        rates = mt5.copy_rates_range(symbol, timeframe, from_date, to_date)
        
        if rates is None or len(rates) == 0:
            raise ConnectionError(f"Aucune donnée reçue: {mt5.last_error()}")
        
        print(f"   ✅ {len(rates):,} chandelles")
        
        # Convertir en DataFrame
        df = pd.DataFrame(rates)
        df['datetime'] = pd.to_datetime(df['time'], unit='s')
        df = df[['datetime', 'open', 'high', 'low', 'close', 'tick_volume']]
        df.columns = ['datetime', 'open', 'high', 'low', 'close', 'volume']
        df = df.sort_values('datetime').reset_index(drop=True)
        
        return df
    
    def load_multi_tf(
        self,
        symbol: str,
        main_tf: str,
        n_bars_main: int,
        required_tfs: List[str]
    ) -> Dict[str, pd.DataFrame]:
        """
        Load candles for multiple timeframes
        
        Automatically calculates required bars for each TF to cover the same
        time period as main_tf.
        
        Args:
            symbol: Trading symbol (e.g., 'EURUSD', 'NAS100')
            main_tf: Main timeframe (e.g., 'M5')
            n_bars_main: Number of bars for main timeframe
            required_tfs: List of all required timeframes (including main)
        
        Returns:
            Dict mapping timeframe -> DataFrame
            
        Example:
            candles_by_tf = loader.load_multi_tf(
                symbol='EURUSD',
                main_tf='M5',
                n_bars_main=2000,
                required_tfs=['M5', 'H1', 'H4']
            )
            # Returns: {'M5': df_m5, 'H1': df_h1, 'H4': df_h4}
        """
        if not self.initialize():
            raise ConnectionError("Failed to initialize MT5")
        
        print(f"\n📥 Loading MT5 data for {symbol}")
        print(f"   Main TF: {main_tf} ({n_bars_main} bars)")
        
        # Verify symbol exists
        symbol_info = mt5.symbol_info(symbol)
        if symbol_info is None:
            raise ValueError(
                f"Symbol {symbol} not found in MT5.\n"
                f"Check symbol name or broker availability."
            )
        
        # Get main TF minutes
        if main_tf not in TIMEFRAME_MAP:
            raise ValueError(f"Unknown timeframe: {main_tf}")
        
        main_tf_minutes = TIMEFRAME_MAP[main_tf][1]
        
        # Calculate bars needed for each TF
        bars_by_tf = {}
        for tf in required_tfs:
            if tf not in TIMEFRAME_MAP:
                raise ValueError(f"Unknown timeframe: {tf}")
            
            tf_minutes = TIMEFRAME_MAP[tf][1]
            
            if tf == main_tf:
                bars_by_tf[tf] = n_bars_main
            else:
                # Calculate: (n_bars_main * main_tf_minutes) / tf_minutes
                total_minutes = n_bars_main * main_tf_minutes
                n_bars_tf = math.ceil(total_minutes / tf_minutes)
                bars_by_tf[tf] = n_bars_tf
            
            print(f"   {tf}: {bars_by_tf[tf]} bars")
        
        # Load candles for each TF
        candles_by_tf = {}
        to_date = datetime.now()
        
        for tf, n_bars in bars_by_tf.items():
            mt5_tf = TIMEFRAME_MAP[tf][0]
            
            print(f"   Loading {tf}...", end=" ")
            
            # Try copy_rates_from (gets N most recent bars)
            rates = mt5.copy_rates_from(symbol, mt5_tf, to_date, n_bars)
            
            if rates is None or len(rates) == 0:
                print(f"❌ Failed")
                raise ValueError(
                    f"No data for {symbol} {tf}.\n"
                    f"MT5 error: {mt5.last_error()}"
                )
            
            # Convert to DataFrame
            df = pd.DataFrame(rates)
            df['time'] = pd.to_datetime(df['time'], unit='s')
            df = df[['time', 'open', 'high', 'low', 'close', 'tick_volume']]
            df.rename(columns={'tick_volume': 'volume'}, inplace=True)
            df.sort_values('time', inplace=True)
            df.reset_index(drop=True, inplace=True)
            
            candles_by_tf[tf] = df
            
            print(f"✅ {len(df)} bars ({df['time'].iloc[0]} → {df['time'].iloc[-1]})")
        
        print(f"✅ Loaded {len(candles_by_tf)} timeframes\n")
        
        return candles_by_tf
    
    def __enter__(self):
        """Context manager support"""
        self.initialize()
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager support"""
        self.shutdown()


# Convenience function
def load_candles_from_config(config: dict) -> Dict[str, pd.DataFrame]:
    """
    Load candles based on YAML config
    
    Args:
        config: Dict from YAML with keys:
            - data.symbol
            - data.main_timeframe
            - data.n_bars
            - indicators (list, each with 'timeframe')
    
    Returns:
        Dict mapping timeframe -> DataFrame
    
    Example:
        config = yaml.safe_load(open('config.yaml'))
        candles_by_tf = load_candles_from_config(config)
    """
    # Extract config
    symbol = config['data']['symbol']
    main_tf = config['data']['main_timeframe']
    n_bars = config['data']['n_bars']
    
    # Collect all required timeframes
    required_tfs = {main_tf}
    for ind in config.get('indicators', []):
        tf = ind.get('timeframe', main_tf)
        required_tfs.add(tf)
    
    # Load data
    with MT5Loader() as loader:
        candles_by_tf = loader.load_multi_tf(
            symbol=symbol,
            main_tf=main_tf,
            n_bars_main=n_bars,
            required_tfs=list(required_tfs)
        )
    
    return candles_by_tf


def ensure_data_file(config: dict) -> str:
    """
    Garantit qu'un fichier de données existe et est à jour
    
    Logique:
    - use_specific_csv_file = True  → Utilise config['data']['file'] TEL QUEL
                                       (ne télécharge JAMAIS, n'update JAMAIS)
    - use_specific_csv_file = False → Construit nom depuis symbol+timeframe
                                       Télécharge depuis MT5 si manquant ou périmé
    
    Args:
        config: Config YAML complète
        
    Returns:
        str: Chemin du fichier de données prêt à l'emploi
        
    Raises:
        FileNotFoundError: Si use_specific=True et fichier absent
        ConnectionError: Si impossible de télécharger depuis MT5
    """
    use_specific = config['data'].get('use_specific_csv_file', False)
    
    if use_specific:
        # MODE SPÉCIFIQUE: utiliser tel quel
        filepath = Path(config['data']['file'])
        
        if not filepath.exists():
            raise FileNotFoundError(
                f"Fichier spécifique introuvable: {filepath}\n"
                f"use_specific_csv_file=True nécessite un fichier existant."
            )
        
        print(f"✅ Fichier spécifique: {filepath}")
        return str(filepath)
    
    else:
        # MODE AUTO: générer depuis MT5
        symbol = config['data']['symbol']
        timeframe = config['data']['timeframe']
        months = config['data'].get('months', 6)
        
        filename = get_data_filename(symbol, timeframe)
        filepath = Path('data') / filename
        
        # Vérifier si téléchargement nécessaire
        needs_download = False
        
        if not filepath.exists():
            print(f"⚠️  Fichier manquant: {filepath}")
            needs_download = True
        else:
            # Vérifier âge
            refresh_days = config['execution'].get('refresh_data_days', 30)
            file_age = datetime.now() - datetime.fromtimestamp(filepath.stat().st_mtime)
            
            if file_age.days > refresh_days:
                print(f"⚠️  Données périmées: {file_age.days}j (seuil: {refresh_days}j)")
                needs_download = True
            else:
                print(f"✅ Données OK: {filepath} ({file_age.days}j)")
        
        if needs_download:
            auto_download = config['execution'].get('auto_download', True)
            
            if not auto_download:
                raise FileNotFoundError(
                    f"Fichier manquant/périmé: {filepath}\n"
                    f"auto_download=False → téléchargez manuellement avec:\n"
                    f"  python download_mt5_data.py --symbol {symbol} --timeframe {timeframe}"
                )
            
            print(f"\n📥 Téléchargement automatique MT5...")
            
            # Créer loader et télécharger
            loader = MT5Loader()
            if not loader.initialize():
                raise ConnectionError(
                    "Impossible de se connecter à MT5.\n"
                    "Vérifiez que MT5 est ouvert et connecté."
                )
            
            try:
                df = loader.download_historical(symbol, timeframe, months)
            finally:
                loader.shutdown()
            
            # Sauvegarder
            filepath.parent.mkdir(exist_ok=True)
            df.to_csv(filepath, index=False)
            
            size_mb = filepath.stat().st_size / 1024 / 1024
            print(f"✅ Sauvegardé: {filepath} ({size_mb:.2f} MB)\n")
        
        return str(filepath)
