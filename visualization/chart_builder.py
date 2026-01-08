"""
Construction du graphique Lightweight Charts
Inspiré de ton code qui fonctionne + structure modulaire
"""

import pandas as pd
from lightweight_charts import Chart
from typing import Optional

from .config import (
    VisualizationConfig,
    RSIConfig,
    BollingerConfig,
    DEFAULT_VIZ_CONFIG,
    DEFAULT_RSI_CONFIG,
    DEFAULT_BOLLINGER_CONFIG
)


class ChartBuilder:
    """Constructeur de graphique Lightweight Charts"""
    
    def __init__(
        self,
        viz_config: VisualizationConfig = DEFAULT_VIZ_CONFIG,
        rsi_config: RSIConfig = DEFAULT_RSI_CONFIG,
        bollinger_config: BollingerConfig = DEFAULT_BOLLINGER_CONFIG
    ):
        self.viz_config = viz_config
        self.rsi_config = rsi_config
        self.bollinger_config = bollinger_config
        
        self.chart: Optional[Chart] = None
        self.rsi_chart: Optional[Chart] = None
        self.rsi_line = None
        
        # Lignes Bollinger
        self.bb_upper_line = None
        self.bb_middle_line = None
        self.bb_lower_line = None
    
    def create_charts(self, title: Optional[str] = None) -> None:
        """
        Crée le chart principal et le subchart RSI
        Méthode qui fonctionne (testée dans ton code)
        """
        chart_title = title or self.viz_config.title
        
        # Chart principal avec bonne proportion
        self.chart = Chart(
            inner_width=1,
            inner_height=self.viz_config.main_chart_height,
            title=chart_title
        )
        
        # Subchart RSI si activé
        if self.viz_config.show_rsi:
            self.rsi_chart = self.chart.create_subchart(
                width=1,
                height=self.viz_config.rsi_chart_height,
                sync=True  # ✅ Synchronisation importante
            )
            
            # Ligne RSI
            self.rsi_line = self.rsi_chart.create_line(
                name="RSI",
                color=self.rsi_config.color,
                width=self.rsi_config.width
            )
        
        print("✅ Charts créés (principal + RSI)" if self.viz_config.show_rsi else "✅ Chart principal créé")
    
    def load_candles(self, df: pd.DataFrame) -> None:
        """
        Charge les données OHLC dans le chart principal
        
        Args:
            df: DataFrame avec index DatetimeIndex et colonnes: open, high, low, close
        """
        if self.chart is None:
            raise RuntimeError("Appelez create_charts() d'abord")
        
        # Préparation format Lightweight
        candles = self._format_candles(df)
        
        # Chargement
        self.chart.set(candles)
        print(f"✅ {len(candles)} bougies chargées")
    
    def load_rsi(self, df: pd.DataFrame, column: str = 'rsi') -> None:
        """
        Charge les données RSI dans le subchart
        
        Args:
            df: DataFrame avec index DatetimeIndex et colonne RSI
            column: Nom de la colonne RSI (défaut 'rsi')
        """
        if not self.viz_config.show_rsi:
            print("⚠️ RSI désactivé dans la config")
            return
        
        if self.rsi_line is None:
            raise RuntimeError("RSI chart non créé")
        
        if column not in df.columns:
            raise ValueError(f"Colonne '{column}' introuvable dans le DataFrame")
        
        # Préparation format Lightweight
        rsi_df = pd.DataFrame({
            'time': df.index,
            'RSI': df[column].values
        })
        
        # Chargement
        self.rsi_line.set(rsi_df)
        print(f"✅ RSI chargé ({len(rsi_df)} valeurs)")
        
        # Ajout des lignes de référence
        self._add_rsi_reference_lines(rsi_df['time'])
    
    def load_bollinger(self, df: pd.DataFrame) -> None:
        """
        Charge les Bollinger Bands sur le chart principal
        
        Args:
            df: DataFrame avec colonnes: bb_middle, bb_upper, bb_lower
        """
        if not self.viz_config.show_bollinger:
            print("⚠️ Bollinger désactivé dans la config")
            return
        
        if self.chart is None:
            raise RuntimeError("Chart principal non créé")
        
        # Vérification colonnes
        required = ['bb_middle', 'bb_upper', 'bb_lower']
        missing = [col for col in required if col not in df.columns]
        if missing:
            raise ValueError(f"Colonnes Bollinger manquantes: {missing}")
        
        # Ligne du milieu
        self.bb_middle_line = self.chart.create_line(
            name="BB_Middle",
            color=self.bollinger_config.middle_color,
            width=self.bollinger_config.middle_width
        )
        bb_middle_df = pd.DataFrame({
            'time': df.index,
            'BB_Middle': df['bb_middle'].values
        })
        self.bb_middle_line.set(bb_middle_df)
        
        # Bande supérieure
        self.bb_upper_line = self.chart.create_line(
            name="BB_Upper",
            color=self.bollinger_config.bands_color,
            width=self.bollinger_config.bands_width
        )
        bb_upper_df = pd.DataFrame({
            'time': df.index,
            'BB_Upper': df['bb_upper'].values
        })
        self.bb_upper_line.set(bb_upper_df)
        
        # Bande inférieure
        self.bb_lower_line = self.chart.create_line(
            name="BB_Lower",
            color=self.bollinger_config.bands_color,
            width=self.bollinger_config.bands_width
        )
        bb_lower_df = pd.DataFrame({
            'time': df.index,
            'BB_Lower': df['bb_lower'].values
        })
        self.bb_lower_line.set(bb_lower_df)
        
        print("✅ Bollinger Bands chargées (upper, middle, lower)")
    
    def show(self, block: bool = True) -> None:
        """
        Affiche le graphique
        
        Args:
            block: Si True, bloque l'exécution jusqu'à fermeture
        """
        if self.chart is None:
            raise RuntimeError("Aucun chart créé")
        
        print(f"\n{'='*60}")
        print("📊 GRAPHIQUE PRÊT")
        print(f"{'='*60}")
        if self.viz_config.show_rsi:
            print("📈 Graphique principal (75%): OHLC + Bollinger")
            print("📉 Sous-graphique RSI (25%): RSI(14) + niveaux")
        else:
            print("📈 Graphique principal: OHLC + Bollinger")
        print(f"{'='*60}\n")
        
        self.chart.show(block=block)
    
    # ========== Méthodes privées ==========
    
    def _format_candles(self, df: pd.DataFrame) -> pd.DataFrame:
        """Format les bougies pour Lightweight Charts"""
        candles = df[['open', 'high', 'low', 'close']].copy()
        candles = candles.reset_index()
        candles = candles.rename(columns={candles.columns[0]: 'time'})
        return candles
    
    def _add_rsi_reference_lines(self, time_index: pd.Series) -> None:
        """Ajoute les lignes de référence sur le RSI (70, 50, 30)"""
        if self.rsi_chart is None:
            return
        
        try:
            # Ligne 70 (surachat)
            ref_70 = pd.DataFrame({
                'time': time_index,
                'Level_70': [self.rsi_config.overbought] * len(time_index)
            })
            line_70 = self.rsi_chart.create_line(
                name="Level_70",
                color=self.rsi_config.overbought_color,
                width=1,
                style="dashed"
            )
            line_70.set(ref_70)
            
            # Ligne 30 (survente)
            ref_30 = pd.DataFrame({
                'time': time_index,
                'Level_30': [self.rsi_config.oversold] * len(time_index)
            })
            line_30 = self.rsi_chart.create_line(
                name="Level_30",
                color=self.rsi_config.oversold_color,
                width=1,
                style="dashed"
            )
            line_30.set(ref_30)
            
            # Ligne 50 (milieu)
            ref_50 = pd.DataFrame({
                'time': time_index,
                'Level_50': [self.rsi_config.midline] * len(time_index)
            })
            line_50 = self.rsi_chart.create_line(
                name="Level_50",
                color=self.rsi_config.midline_color,
                width=1,
                style="dotted"
            )
            line_50.set(ref_50)
            
            print("✅ Lignes de référence RSI ajoutées (70, 50, 30)")
        
        except Exception as e:
            print(f"⚠️ Erreur lignes référence RSI: {e}")


# Fonction utilitaire pour usage rapide
def quick_chart(
    df: pd.DataFrame,
    title: str = "Trading Chart",
    show_rsi: bool = True,
    show_bollinger: bool = True
) -> ChartBuilder:
    """
    Crée et affiche rapidement un graphique complet
    
    Args:
        df: DataFrame avec OHLCV + indicateurs (rsi, bb_*)
        title: Titre du graphique
        show_rsi: Afficher RSI
        show_bollinger: Afficher Bollinger
    
    Returns:
        ChartBuilder instance (pour customisation)
    """
    # Config
    viz_config = VisualizationConfig(
        title=title,
        show_rsi=show_rsi,
        show_bollinger=show_bollinger
    )
    
    # Construction
    builder = ChartBuilder(viz_config=viz_config)
    builder.create_charts()
    builder.load_candles(df)
    
    if show_rsi and 'rsi' in df.columns:
        builder.load_rsi(df)
    
    if show_bollinger and 'bb_middle' in df.columns:
        builder.load_bollinger(df)
    
    return builder
