# 📊 Module de Visualisation Trading

Module **totalement découplé de Backtrader** pour visualiser des données de trading avec Lightweight Charts.

**Note** : Pour les backtests complets avec trading windows, voir `config_bollinger_breakout_windows.yaml` à la racine du projet.

## ✨ Fonctionnalités - Étape 1 (COMPLÉTÉE)

✅ **Lightweight Charts** avec chandeliers OHLC  
✅ **RSI en sous-graphe** (remplace le volume)  
✅ **Bollinger Bands** en overlay  
✅ **Configuration flexible** (couleurs, périodes, etc.)  
✅ **Format de données standardisé** (CSV/JSON)  

## 🚀 Installation

```bash
pip install lightweight-charts pandas numpy
```

## 📖 Usage Rapide

### Méthode 1 : Fonction tout-en-un

```python
from visualization import quick_visualize

# Visualisation en 1 ligne !
quick_visualize('data/NAS100_3min.csv')
```

### Méthode 2 : Script de démonstration

```bash
# Démo basique
python demo_visualization.py basic

# Démo personnalisée
python demo_visualization.py custom

# RSI seul
python demo_visualization.py rsi
```

### Méthode 3 : API complète

```python
from visualization import (
    DataLoader,
    IndicatorCalculator,
    ChartBuilder,
    VisualizationConfig
)

# 1. Charger données
df = DataLoader.load_ohlcv('data/candles.csv')

# 2. Calculer indicateurs
df = IndicatorCalculator.compute_all_indicators(
    df,
    rsi_period=14,
    bb_period=20,
    bb_std=2.0
)

# 3. Configuration
config = VisualizationConfig(
    title="Mon Graphique",
    show_rsi=True,
    show_bollinger=True
)

# 4. Construction
builder = ChartBuilder(viz_config=config)
builder.create_charts()
builder.load_candles(df)
builder.load_rsi(df)
builder.load_bollinger(df)

# 5. Affichage
builder.show()
```

## 📁 Format des Données

### OHLCV (candles.csv ou candles.json)

```csv
time,open,high,low,close,volume
2024-01-01 00:00:00,16000.0,16050.0,15980.0,16020.0,1000
2024-01-01 00:03:00,16020.0,16070.0,16010.0,16060.0,1200
...
```

**Colonnes requises** : `time`, `open`, `high`, `low`, `close`  
**Colonne optionnelle** : `volume` (non affichée)

### Indicateurs (optionnel - si pré-calculés)

**RSI (rsi.json)** :
```json
[
  {"time": "2024-01-01 00:00:00", "value": 45.2},
  {"time": "2024-01-01 00:03:00", "value": 48.7}
]
```

**Bollinger (bb.json)** :
```json
[
  {"time": "2024-01-01 00:00:00", "upper": 16100, "middle": 16000, "lower": 15900}
]
```

## ⚙️ Configuration

### Configuration principale

```python
from visualization import VisualizationConfig

config = VisualizationConfig(
    timezone="Europe/Paris",
    title="Trading Chart",
    main_chart_height=0.75,  # 75% principal
    rsi_chart_height=0.25,   # 25% RSI
    show_rsi=True,
    show_bollinger=True
)
```

### Configuration RSI

```python
from visualization import RSIConfig

rsi_config = RSIConfig(
    period=14,
    color="#9C27B0",  # Violet
    width=3,
    overbought=70.0,
    oversold=30.0,
    midline=50.0
)
```

### Configuration Bollinger

```python
from visualization import BollingerConfig

bb_config = BollingerConfig(
    period=20,
    std_dev=2.0,
    ma_type="SMA",  # ou "EMA"
    middle_color="#4ECDC4",
    bands_color="#FF6B6B"
)
```

## 📊 Indicateurs Disponibles

### RSI (Relative Strength Index)

```python
from visualization import IndicatorCalculator

# Calcul seul
rsi = IndicatorCalculator.compute_rsi(df['close'], period=14)

# Ajout au DataFrame
df = IndicatorCalculator.add_rsi_to_dataframe(df, period=14)
```

### Bollinger Bands

```python
# Calcul seul
bb = IndicatorCalculator.compute_bollinger_bands(
    df['close'],
    period=20,
    std_dev=2.0,
    ma_type="SMA"
)

# Ajout au DataFrame
df = IndicatorCalculator.add_bollinger_to_dataframe(
    df,
    period=20,
    std_dev=2.0
)
```

### Tous les indicateurs

```python
# Calcul en une passe
df = IndicatorCalculator.compute_all_indicators(
    df,
    rsi_period=14,
    bb_period=20,
    bb_std=2.0
)
```

## 🎨 Personnalisation

### Couleurs personnalisées

```python
viz_config = VisualizationConfig(
    bullish_color="#00FF00",
    bearish_color="#FF0000",
    neutral_color="#888888"
)
```

### RSI personnalisé

```python
rsi_config = RSIConfig(
    period=21,               # RSI(21)
    color="#FF00FF",         # Magenta
    overbought=80,           # Seuil 80
    oversold=20,             # Seuil 20
    overbought_color="#FF0000",
    oversold_color="#00FF00"
)
```

### Bollinger personnalisé

```python
bb_config = BollingerConfig(
    period=50,               # BB(50)
    std_dev=1.5,            # 1.5σ
    ma_type="EMA",          # EMA au lieu de SMA
    middle_color="#FFFF00",
    bands_color="#00FFFF"
)
```

## 📈 Prochaines Étapes

### Étape 2 : Rectangles de Trades (EN COURS)
- ⏳ Rendu des trades sous forme de rectangles
- ⏳ SL/TP/BE colorés
- ⏳ Tooltips interactifs
- ⏳ Support multi-trades

### Étape 3 : Heatmaps Temporelles
- ⏳ Analyse jour × heure
- ⏳ Métriques de rentabilité
- ⏳ Identification des patterns temporels
- ⏳ Export CSV/JSON

### Étape 4 : Connecteur MT5
- ⏳ Récupération données OHLC
- ⏳ Export format standard
- ⏳ Streaming live (optionnel)

## 🐛 Troubleshooting

### Erreur "lightweight-charts not found"

```bash
pip install lightweight-charts
```

### Erreur "Fichier introuvable"

Vérifiez que votre fichier CSV existe et contient les colonnes requises :
```python
import pandas as pd
df = pd.read_csv('data/candles.csv')
print(df.columns)  # Doit contenir: time, open, high, low, close
```

### Graphique ne s'affiche pas

Vérifiez que vous appelez `show()` :
```python
builder.show(block=True)  # block=True pour bloquer l'exécution
```

## 📚 Architecture du Module

```
visualization/
├── __init__.py           # API publique
├── config.py             # Configuration (dataclasses)
├── data_loader.py        # Chargement CSV/JSON
├── indicators.py         # Calcul RSI, Bollinger
├── chart_builder.py      # Construction Lightweight Charts
└── trades_renderer.py    # Rectangles trades (Étape 2)
```

## 🔗 Intégration avec Backtest

Le module est **totalement découplé** mais peut facilement s'intégrer :

```python
# Après backtest
import pandas as pd
from visualization import quick_visualize

# Export des données
ohlcv.to_csv('output/candles.csv')

# Visualisation
quick_visualize('output/candles.csv')
```

## 🎯 Objectifs de Design

✅ **Découplage total** de Backtrader  
✅ **Formats standardisés** (CSV/JSON)  
✅ **API simple** (quick_visualize en 1 ligne)  
✅ **API avancée** (configuration complète)  
✅ **Extensible** (facile d'ajouter indicateurs)  
✅ **Performant** (Lightweight Charts natif)  

---

**Version** : 1.0.0 - Étape 1 complétée  
**Auteur** : Système de trading automatisé  
**Licence** : Usage personnel
