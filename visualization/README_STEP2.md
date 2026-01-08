# 📦 Étape 2 : Rectangles de Trades

Module de visualisation des trades sous forme de rectangles colorés sur Lightweight Charts.

## ✨ Fonctionnalités

✅ **Rectangles Stop Loss** (rouge)  
✅ **Rectangles TP1** (vert clair)  
✅ **Rectangles TP2** (vert foncé, recouvre TP1)  
✅ **Rectangles Break-Even** (gris, si BE sans TP)  
✅ **Gestion multi-trades** (plusieurs trades simultanés)  
✅ **Calcul automatique** des prix SL/TP depuis événements  

## 🎯 Spécifications (Cahier des Charges)

### A) Rectangle Stop Loss (ROUGE)

**Toujours affiché** pour chaque trade

- **time_start** = temps de l'ENTRY
- **time_end** = temps de sortie finale (SL/TP2/BE_HIT/CLOSE_INVALID)
- **Bornes prix** :
  - LONG : `[sl_price, entry_price]`
  - SHORT : `[entry_price, sl_price]`
- **Couleur** : Rouge transparent (`rgba(255, 0, 0, 0.3)`)

### B) Rectangle TP1 (VERT CLAIR)

**Affiché si événement TP1 existe**

- **time_start** = temps de l'ENTRY
- **time_end** = temps du TP1
- **Bornes prix** :
  - LONG : `[entry_price, tp1_price]`
  - SHORT : `[tp1_price, entry_price]`
- **Couleur** : Vert transparent (`rgba(0, 255, 0, 0.2)`)

### C) Rectangle TP2 (VERT FONCÉ)

**Affiché si événement TP2 existe**

Recouvre aussi la zone TP1 (opacité supérieure)

- **time_start** = temps de l'ENTRY
- **time_end** = temps du TP2
- **Bornes prix** :
  - LONG : `[entry_price, tp2_price]`
  - SHORT : `[tp2_price, entry_price]`
- **Couleur** : Vert plus opaque (`rgba(0, 255, 0, 0.35)`)

### D) Rectangle Break-Even (GRIS)

**Affiché uniquement si BE_HIT sans TP1/TP2**

Même taille verticale que le Stop Loss

- **time_start** = temps de l'ENTRY
- **time_end** = temps du BE_HIT
- **Bornes prix** : identiques au rectangle SL
- **Couleur** : Gris transparent (`rgba(128, 128, 128, 0.25)`)

## 🚀 Usage

### Méthode 1 : Script de démonstration

```bash
# Visualisation complète (backtest réel)
python demo_trades_visualization.py full

# Test avec 1 trade synthétique
python demo_trades_visualization.py single
```

### Méthode 2 : API complète

```python
from visualization import (
    DataLoader,
    IndicatorCalculator,
    ChartBuilder,
    TradesRenderer,
    TradeRenderConfig
)

# 1. Chargement données
df = DataLoader.load_ohlcv('data/candles.csv')
trades = DataLoader.load_trades('output/trades.csv')

# 2. Indicateurs
df = IndicatorCalculator.compute_all_indicators(df)

# 3. Graphique de base
builder = ChartBuilder()
builder.create_charts()
builder.load_candles(df)
builder.load_rsi(df)
builder.load_bollinger(df)

# 4. Ajout des rectangles de trades
config = TradeRenderConfig(
    sl_color="rgba(255, 0, 0, 0.3)",
    tp1_color="rgba(0, 255, 0, 0.2)",
    tp2_color="rgba(0, 255, 0, 0.35)",
    be_color="rgba(128, 128, 128, 0.25)"
)

renderer = TradesRenderer(builder.chart, config=config)
renderer.load_trades_from_events(trades)

# 5. Affichage
builder.show()
```

### Méthode 3 : Fonction rapide

```python
from visualization import quick_add_trades

# Après avoir créé le chart
quick_add_trades(chart, 'output/trades.csv')
```

## 📁 Format des Données Trades

### Fichier CSV/JSON requis

```csv
trade_id,time,event_type,price,direction,size,pnl
1,2024-01-01 10:00:00,ENTRY,16000.0,LONG,1.0,
1,2024-01-01 10:15:00,TP1,16100.0,LONG,0.5,50.0
1,2024-01-01 10:30:00,TP2,16200.0,LONG,0.5,100.0
2,2024-01-01 11:00:00,ENTRY,16050.0,SHORT,1.0,
2,2024-01-01 11:10:00,SL,16100.0,SHORT,1.0,-50.0
```

### Colonnes requises

| Colonne | Type | Description |
|---------|------|-------------|
| `trade_id` | int | Identifiant unique du trade |
| `time` | datetime | Timestamp de l'événement |
| `event_type` | str | Type : ENTRY, TP1, TP2, SL, BE_MOVE, SL_BE, BE_HIT, CLOSE_INVALID |
| `price` | float | Prix de l'événement |
| `direction` | str | LONG ou SHORT |
| `size` | float | Taille (optionnel) |
| `pnl` | float | Profit/Perte (optionnel) |

### Types d'événements supportés

- **ENTRY** : Entrée en position (obligatoire)
- **TP1** : Take Profit partiel (50%)
- **TP2** : Take Profit final (50% restant)
- **SL** : Stop Loss déclenché
- **BE_MOVE** : Déplacement du SL au break-even
- **SL_BE** ou **BE_HIT** : SL break-even touché
- **CLOSE_INVALID** : Fermeture forcée (fin de backtest, etc.)

## ⚙️ Configuration

### Configuration des couleurs

```python
from visualization import TradeRenderConfig

config = TradeRenderConfig(
    # Stop Loss
    sl_color="rgba(255, 0, 0, 0.3)",
    sl_border="#FF0000",
    sl_opacity=0.3,
    
    # TP1
    tp1_color="rgba(0, 255, 0, 0.2)",
    tp1_opacity=0.2,
    
    # TP2
    tp2_color="rgba(0, 255, 0, 0.35)",
    tp2_opacity=0.35,
    
    # Break-Even
    be_color="rgba(128, 128, 128, 0.25)",
    be_border="#808080",
    be_opacity=0.25,
    
    # Bordures communes TP
    tp_border="#00FF00"
)
```

## 📊 Logique de Rendu

### Ordre de superposition (z-index)

1. **TP2** (fond, vert foncé)
2. **TP1** (au-dessus du TP2, vert clair)
3. **SL** (au-dessus, rouge)
4. **BE** (au-dessus, gris)

Cela permet de voir toutes les zones simultanément sans masquage.

### Calcul automatique des prix

Si les événements SL/TP ne contiennent pas le prix exact :

- **SL** : Estimé à -2% (LONG) ou +2% (SHORT) de l'entry
- **TP1** : Récupéré depuis l'événement TP1
- **TP2** : Récupéré depuis l'événement TP2

### Gestion des cas particuliers

| Cas | Rectangles affichés |
|-----|---------------------|
| TP1 + TP2 atteints | SL (rouge) + TP1 (vert clair) + TP2 (vert foncé) |
| Seul TP1 atteint | SL (rouge) + TP1 (vert clair) |
| SL touché direct | SL (rouge) uniquement |
| BE sans TP | SL (rouge) + BE (gris) |
| TP1 + BE | SL (rouge) + TP1 (vert clair) (pas de BE car TP existe) |

## 🐛 Debug

### Vérifier les événements chargés

```python
from visualization import DataLoader

trades = DataLoader.load_trades('output/trades.csv')
print(trades['event_type'].value_counts())
print(f"Trades uniques: {trades['trade_id'].nunique()}")
```

### Inspecter les rectangles générés

```python
renderer = TradesRenderer(chart)
renderer.load_trades_from_events(trades)

# Statistiques
print(f"Total rectangles: {len(renderer.rectangles)}")

for rect in renderer.rectangles[:5]:  # Premiers 5
    print(f"Trade {rect.trade_id} - {rect.rect_type}")
    print(f"  Temps: {rect.time_start} → {rect.time_end}")
    print(f"  Prix: {rect.price_low} → {rect.price_high}")
```

## 📈 Exemple Complet

```python
from visualization import (
    DataLoader,
    IndicatorCalculator,
    ChartBuilder,
    TradesRenderer,
    VisualizationConfig,
    TradeRenderConfig
)

# Configuration
viz_config = VisualizationConfig(
    title="Backtest Results - RSI Strategy",
    show_rsi=True,
    show_bollinger=True
)

trade_config = TradeRenderConfig(
    sl_color="rgba(255, 0, 0, 0.4)",    # Rouge plus visible
    tp2_color="rgba(0, 255, 0, 0.4)"    # Vert plus visible
)

# Chargement
df = DataLoader.load_ohlcv('data/NAS100_3min.csv')
trades = DataLoader.load_trades('output/trades_backtest.csv')

# Indicateurs
df = IndicatorCalculator.compute_all_indicators(df)

# Construction
builder = ChartBuilder(viz_config=viz_config)
builder.create_charts()
builder.load_candles(df)
builder.load_rsi(df)
builder.load_bollinger(df)

# Trades
renderer = TradesRenderer(builder.chart, config=trade_config)
renderer.load_trades_from_events(trades)

# Statistiques
print(f"📊 Trades: {trades['trade_id'].nunique()}")
print(f"📦 Rectangles: {len(renderer.rectangles)}")

# Affichage
builder.show()
```

## 🔄 Intégration avec Backtest

### Export depuis Backtrader

Ton système exporte déjà les trades au bon format :

```python
# Dans strategy_rsi_amplitude.py
self._export_trade_event("ENTRY", price, size)
self._export_trade_event("TP1", price, size, pnl)
self._export_trade_event("TP2", price, size, pnl)
self._export_trade_event("SL", price, size, pnl)
```

Le fichier `output/trades_backtest.csv` est directement utilisable !

### Workflow complet

```bash
# 1. Génération des données
python generate_data.py

# 2. Backtest
python main_rsi_amplitude.py

# 3. Visualisation
python demo_trades_visualization.py full
```

## 🎯 Prochaines Améliorations

### Tooltips interactifs (à venir)

Au survol d'un rectangle :
- Trade ID
- Direction (LONG/SHORT)
- Entry price / time
- Exit price / time
- PnL
- R (risk/reward)
- Legs exécutés

### Remplissage complet (limitation Lightweight)

Actuellement : bordures des rectangles (top + bottom)

Alternative possible :
- Overlay HTML/SVG personnalisé
- Extension Lightweight Charts custom
- Utilisation d'annotations natives (si disponible)

## 📚 Références

- **Cahier des charges** : `SPEC_ETAPE2.md`
- **Config** : `visualization/config.py`
- **Renderer** : `visualization/trades_renderer.py`
- **Démo** : `demo_trades_visualization.py`

---

**Version** : 1.1.0 - Étape 2 implémentée  
**Statut** : ✅ Fonctionnel (bordures), 🔄 En amélioration (remplissage)
