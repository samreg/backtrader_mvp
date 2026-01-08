"""
Chargement des données depuis CSV/JSON
Format standardisé pour la visualisation
"""

import pandas as pd
from pathlib import Path
from typing import Optional


class DataLoader:
    """Chargeur de données pour la visualisation"""
    
    @staticmethod
    def load_ohlcv(filepath: str | Path) -> pd.DataFrame:
        """
        Charge les données OHLCV depuis CSV ou JSON
        
        Format attendu:
        - time (datetime ou timestamp)
        - open, high, low, close (float)
        - volume (optionnel, float)
        
        Returns:
            DataFrame avec DatetimeIndex sur 'time'
        """
        filepath = Path(filepath)
        
        if not filepath.exists():
            raise FileNotFoundError(f"Fichier introuvable: {filepath}")
        
        # Détection du format
        if filepath.suffix == '.csv':
            df = pd.read_csv(filepath)
        elif filepath.suffix == '.json':
            df = pd.read_json(filepath)
        else:
            raise ValueError(f"Format non supporté: {filepath.suffix}")
        
        # Normalisation des colonnes (case-insensitive)
        df.columns = df.columns.str.lower()
        
        # Vérification des colonnes requises
        required = ['time', 'open', 'high', 'low', 'close']
        missing = [col for col in required if col not in df.columns]
        if missing:
            # Essai avec 'datetime' au lieu de 'time'
            if 'datetime' in df.columns:
                df = df.rename(columns={'datetime': 'time'})
            else:
                raise ValueError(f"Colonnes manquantes: {missing}")
        
        # Conversion time en datetime
        df['time'] = pd.to_datetime(df['time'])
        
        # Index sur time
        df = df.set_index('time')
        
        # Tri chronologique
        df = df.sort_index()
        
        # Validation des valeurs
        for col in ['open', 'high', 'low', 'close']:
            if not pd.api.types.is_numeric_dtype(df[col]):
                df[col] = pd.to_numeric(df[col], errors='coerce')
        
        # Suppression des NaN
        df = df.dropna(subset=['open', 'high', 'low', 'close'])
        
        print(f"✅ OHLCV chargé: {len(df)} bougies")
        print(f"   Période: {df.index[0]} → {df.index[-1]}")
        
        return df
    
    @staticmethod
    def load_trades(filepath: str | Path) -> pd.DataFrame:
        """
        Charge les événements de trades depuis CSV ou JSON
        
        Format attendu:
        - trade_id (int)
        - datetime ou time (datetime)
        - event_type (str): ENTRY, TP1, TP2, SL, BE_MOVE, SL_BE, etc.
        - price (float)
        - size (float, signé ou avec colonne direction)
        - direction (str): LONG, SHORT
        - pnl (float, optionnel)
        
        Returns:
            DataFrame avec événements triés par temps
        """
        filepath = Path(filepath)
        
        if not filepath.exists():
            raise FileNotFoundError(f"Fichier introuvable: {filepath}")
        
        # Chargement
        if filepath.suffix == '.csv':
            df = pd.read_csv(filepath)
        elif filepath.suffix == '.json':
            df = pd.read_json(filepath)
        else:
            raise ValueError(f"Format non supporté: {filepath.suffix}")
        
        # Normalisation colonnes
        df.columns = df.columns.str.lower()
        
        # Détection colonne temps
        time_col = None
        for col in ['datetime', 'time', 'timestamp']:
            if col in df.columns:
                time_col = col
                break
        
        if time_col is None:
            raise ValueError("Aucune colonne temporelle trouvée (datetime, time, timestamp)")
        
        # Renommage en 'time'
        if time_col != 'time':
            df = df.rename(columns={time_col: 'time'})
        
        # Conversion datetime
        df['time'] = pd.to_datetime(df['time'])
        
        # Vérification colonnes essentielles
        required = ['trade_id', 'event_type', 'price', 'direction']
        missing = [col for col in required if col not in df.columns]
        if missing:
            raise ValueError(f"Colonnes manquantes: {missing}")
        
        # Tri chronologique
        df = df.sort_values('time')
        
        print(f"✅ Trades chargés: {len(df)} événements")
        print(f"   Trades uniques: {df['trade_id'].nunique()}")
        print(f"   Types d'événements: {df['event_type'].unique().tolist()}")
        
        return df
    
    @staticmethod
    def load_indicators(
        filepath: str | Path,
        indicator_name: str,
        columns: Optional[list[str]] = None
    ) -> pd.DataFrame:
        """
        Charge des indicateurs pré-calculés depuis CSV/JSON
        
        Args:
            filepath: Chemin vers le fichier
            indicator_name: Nom de l'indicateur (ex: "RSI", "BB")
            columns: Colonnes attendues (ex: ['value'] pour RSI, ['upper', 'middle', 'lower'] pour BB)
        
        Returns:
            DataFrame avec DatetimeIndex sur 'time'
        """
        filepath = Path(filepath)
        
        if not filepath.exists():
            raise FileNotFoundError(f"Fichier introuvable: {filepath}")
        
        # Chargement
        if filepath.suffix == '.csv':
            df = pd.read_csv(filepath)
        elif filepath.suffix == '.json':
            df = pd.read_json(filepath)
        else:
            raise ValueError(f"Format non supporté: {filepath.suffix}")
        
        # Normalisation
        df.columns = df.columns.str.lower()
        
        # Vérification colonne temps
        if 'time' not in df.columns:
            raise ValueError(f"Colonne 'time' manquante pour {indicator_name}")
        
        # Conversion datetime
        df['time'] = pd.to_datetime(df['time'])
        df = df.set_index('time')
        df = df.sort_index()
        
        # Vérification colonnes spécifiques
        if columns:
            missing = [col for col in columns if col not in df.columns]
            if missing:
                raise ValueError(f"{indicator_name}: colonnes manquantes {missing}")
        
        print(f"✅ {indicator_name} chargé: {len(df)} valeurs")
        
        return df


# Fonctions utilitaires rapides
def quick_load_ohlcv(filepath: str | Path) -> pd.DataFrame:
    """Alias rapide pour charger OHLCV"""
    return DataLoader.load_ohlcv(filepath)


def quick_load_trades(filepath: str | Path) -> pd.DataFrame:
    """Alias rapide pour charger trades"""
    return DataLoader.load_trades(filepath)
