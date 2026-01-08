"""
Calcul des indicateurs pour la visualisation
Méthodes simples et robustes sans dépendances externes complexes
"""

import pandas as pd
import numpy as np
from typing import Literal


class IndicatorCalculator:
    """Calculateur d'indicateurs techniques"""
    
    @staticmethod
    def compute_rsi(close: pd.Series, period: int = 14) -> pd.Series:
        """
        Calcule le RSI (Relative Strength Index)
        
        Méthode Wilder avec EMA smoothing
        
        Args:
            close: Série des prix de clôture
            period: Période RSI (défaut 14)
        
        Returns:
            Série RSI (0-100)
        """
        # Calcul des variations
        delta = close.diff()
        
        # Séparation gains/pertes
        gain = delta.clip(lower=0.0)
        loss = (-delta).clip(lower=0.0)
        
        # Wilder smoothing via EMA avec alpha = 1/period
        avg_gain = gain.ewm(alpha=1/period, adjust=False, min_periods=period).mean()
        avg_loss = loss.ewm(alpha=1/period, adjust=False, min_periods=period).mean()
        
        # Calcul RS et RSI
        rs = avg_gain / avg_loss.replace(0, np.nan)
        rsi = 100 - (100 / (1 + rs))
        
        # Remplissage NaN initiaux
        rsi = rsi.fillna(method='bfill')
        
        return rsi
    
    @staticmethod
    def compute_bollinger_bands(
        close: pd.Series,
        period: int = 20,
        std_dev: float = 2.0,
        ma_type: Literal["SMA", "EMA"] = "SMA"
    ) -> pd.DataFrame:
        """
        Calcule les Bandes de Bollinger
        
        Args:
            close: Série des prix de clôture
            period: Période de la moyenne mobile
            std_dev: Nombre d'écarts-types
            ma_type: Type de moyenne ("SMA" ou "EMA")
        
        Returns:
            DataFrame avec colonnes: middle, upper, lower
        """
        # Calcul de la moyenne mobile centrale
        if ma_type == "SMA":
            middle = close.rolling(window=period).mean()
        elif ma_type == "EMA":
            middle = close.ewm(span=period, adjust=False).mean()
        else:
            raise ValueError(f"ma_type non supporté: {ma_type}")
        
        # Calcul de l'écart-type
        std = close.rolling(window=period).std()
        
        # Bandes supérieure et inférieure
        upper = middle + (std_dev * std)
        lower = middle - (std_dev * std)
        
        # Création du DataFrame
        bb = pd.DataFrame({
            'middle': middle,
            'upper': upper,
            'lower': lower
        }, index=close.index)
        
        return bb
    
    @staticmethod
    def add_rsi_to_dataframe(
        df: pd.DataFrame,
        period: int = 14,
        column: str = 'close'
    ) -> pd.DataFrame:
        """
        Ajoute la colonne RSI à un DataFrame OHLCV
        
        Args:
            df: DataFrame avec prix
            period: Période RSI
            column: Colonne à utiliser pour le calcul (défaut 'close')
        
        Returns:
            DataFrame avec colonne 'rsi' ajoutée
        """
        df = df.copy()
        df['rsi'] = IndicatorCalculator.compute_rsi(df[column], period)
        return df
    
    @staticmethod
    def add_bollinger_to_dataframe(
        df: pd.DataFrame,
        period: int = 20,
        std_dev: float = 2.0,
        ma_type: Literal["SMA", "EMA"] = "SMA",
        column: str = 'close'
    ) -> pd.DataFrame:
        """
        Ajoute les colonnes Bollinger Bands à un DataFrame OHLCV
        
        Args:
            df: DataFrame avec prix
            period: Période moyenne mobile
            std_dev: Nombre d'écarts-types
            ma_type: Type de moyenne
            column: Colonne à utiliser
        
        Returns:
            DataFrame avec colonnes 'bb_middle', 'bb_upper', 'bb_lower'
        """
        df = df.copy()
        
        bb = IndicatorCalculator.compute_bollinger_bands(
            df[column],
            period=period,
            std_dev=std_dev,
            ma_type=ma_type
        )
        
        df['bb_middle'] = bb['middle']
        df['bb_upper'] = bb['upper']
        df['bb_lower'] = bb['lower']
        
        return df
    
    @staticmethod
    def compute_all_indicators(
        df: pd.DataFrame,
        rsi_period: int = 14,
        bb_period: int = 20,
        bb_std: float = 2.0,
        bb_ma_type: Literal["SMA", "EMA"] = "SMA"
    ) -> pd.DataFrame:
        """
        Calcule tous les indicateurs en une seule passe
        
        Args:
            df: DataFrame OHLCV
            rsi_period: Période RSI
            bb_period: Période Bollinger
            bb_std: Écarts-types Bollinger
            bb_ma_type: Type de moyenne Bollinger
        
        Returns:
            DataFrame avec tous les indicateurs
        """
        df = df.copy()
        
        # RSI
        df = IndicatorCalculator.add_rsi_to_dataframe(df, period=rsi_period)
        
        # Bollinger Bands
        df = IndicatorCalculator.add_bollinger_to_dataframe(
            df,
            period=bb_period,
            std_dev=bb_std,
            ma_type=bb_ma_type
        )
        
        return df


# Fonctions utilitaires rapides
def quick_rsi(close: pd.Series, period: int = 14) -> pd.Series:
    """Calcul RSI rapide"""
    return IndicatorCalculator.compute_rsi(close, period)


def quick_bollinger(
    close: pd.Series,
    period: int = 20,
    std_dev: float = 2.0
) -> pd.DataFrame:
    """Calcul Bollinger rapide"""
    return IndicatorCalculator.compute_bollinger_bands(close, period, std_dev)
