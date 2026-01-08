"""
Configuration centralisée pour le module de visualisation
Totalement découplé de Backtrader
"""

from dataclasses import dataclass
from typing import Literal


@dataclass
class VisualizationConfig:
    """Configuration principale de la visualisation"""
    
    # Display
    timezone: str = "Europe/Paris"
    title: str = "Trading Visualization"
    
    # Chart proportions
    main_chart_height: float = 0.75  # 75% pour chart principal
    rsi_chart_height: float = 0.25   # 25% pour RSI
    
    # Colors
    bullish_color: str = "#00aa00"
    bearish_color: str = "#aa0000"
    neutral_color: str = "#888888"
    
    # Indicators enabled
    show_rsi: bool = True
    show_bollinger: bool = True
    show_volume: bool = False  # Non demandé dans specs


@dataclass
class RSIConfig:
    """Configuration RSI"""
    period: int = 14
    color: str = "#9C27B0"  # Violet
    width: int = 3
    
    # Niveaux de référence
    overbought: float = 70.0
    oversold: float = 30.0
    midline: float = 50.0
    
    # Couleurs des niveaux
    overbought_color: str = "#F44336"  # Rouge
    oversold_color: str = "#4CAF50"    # Vert
    midline_color: str = "#9E9E9E"     # Gris


@dataclass
class BollingerConfig:
    """Configuration Bollinger Bands"""
    period: int = 20
    std_dev: float = 2.0
    ma_type: Literal["SMA", "EMA"] = "SMA"
    
    # Couleurs
    middle_color: str = "#4ECDC4"  # Cyan
    bands_color: str = "#FF6B6B"   # Rouge clair
    
    # Styles
    middle_width: int = 2
    bands_width: int = 1


@dataclass
class TradeRenderConfig:
    """Configuration pour le rendu des trades (Étape 2)"""
    
    # Couleurs des rectangles
    sl_color: str = "rgba(255, 0, 0, 0.3)"      # Rouge transparent
    tp1_color: str = "rgba(0, 255, 0, 0.2)"     # Vert transparent
    tp2_color: str = "rgba(0, 255, 0, 0.3)"     # Vert plus opaque
    be_color: str = "rgba(128, 128, 128, 0.2)"  # Gris transparent
    
    # Bordures
    sl_border: str = "#FF0000"
    tp_border: str = "#00FF00"
    be_border: str = "#808080"
    
    # Opacités (0.0 à 1.0)
    sl_opacity: float = 0.3
    tp1_opacity: float = 0.2
    tp2_opacity: float = 0.3
    be_opacity: float = 0.2


@dataclass
class HeatmapConfig:
    """Configuration pour les heatmaps temporelles (Étape 2)"""
    
    # Métrique principale
    metric: Literal["total_pnl", "avg_pnl", "expectancy", "winrate"] = "total_pnl"
    
    # Timestamp de référence
    time_reference: Literal["entry", "exit"] = "entry"
    
    # Filtres
    min_trades_per_cell: int = 3  # Cellules avec < 3 trades grisées
    
    # Timezone pour analyse temporelle
    analysis_timezone: str = "Europe/Paris"


# Configurations par défaut prêtes à l'emploi
DEFAULT_VIZ_CONFIG = VisualizationConfig()
DEFAULT_RSI_CONFIG = RSIConfig()
DEFAULT_BOLLINGER_CONFIG = BollingerConfig()
DEFAULT_TRADE_RENDER_CONFIG = TradeRenderConfig()
DEFAULT_HEATMAP_CONFIG = HeatmapConfig()
