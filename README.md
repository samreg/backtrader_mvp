# MVP Backtrader - Trading System

## Description

MVP de backtest basé sur Backtrader avec gestion complète de trades :
- **Take Profit partiels** (TP1 + TP2)
- **Break-even** après TP1
- **Stop Loss** dynamique
- **Exit Rule** simple (sortie conditionnelle)
- **Gestion du risque** : 1% du capital par trade
- **Export CSV** des trades
- **Visualisation** Backtrader standard

## Structure du projet

```
backtrader_mvp/
├── main.py              # Point d'entrée principal
├── config.yaml          # Configuration complète
├── strategy.py          # Stratégie avec TP partiels et BE
├── sizing.py            # Calcul de taille de position
├── costs.py             # Modèle de coûts
├── requirements.txt     # Dépendances Python
├── data/                # Dossier pour les données CSV
│   └── NAS100_3min.csv (généré automatiquement si absent)
└── output/              # Dossier pour les exports
    └── trades.csv       # Log des trades
```

## Installation

### 1. Créer un environnement virtuel (recommandé)

```bash
python -m venv venv
source venv/bin/activate  # Linux/Mac
# ou
venv\Scripts\activate  # Windows
```

### 2. Installer les dépendances

```bash
pip install -r requirements.txt
```

## Configuration

Éditer le fichier `config.yaml` pour ajuster :

### Capital et risque
- `capital`: Capital initial (défaut: 10000)
- `risk_per_trade`: Risque par trade en % (défaut: 0.01 = 1%)

### Take Profit et Stop Loss
- `tp1_distance`: Distance TP1 en points (défaut: 20)
- `tp2_distance`: Distance TP2 en points (défaut: 40)
- `sl_distance`: Distance SL en points (défaut: 10)
- `tp1_ratio`: Part de la position fermée au TP1 (défaut: 0.5 = 50%)
- `tp2_ratio`: Part restante au TP2 (défaut: 0.5 = 50%)

### Break-even
- `enable_breakeven`: Activer le BE (défaut: true)
- `breakeven_after_tp1`: Déclencher après TP1 (défaut: true)
- `breakeven_offset`: Offset du BE (défaut: 0 = prix d'entrée)

### Exit Rule
- `enable_exit_rule`: Activer la sortie conditionnelle (défaut: true)
- `exit_rule_type`: Type de règle (défaut: "rsi_extreme")
- `exit_rule_rsi_threshold`: Seuil RSI pour sortie (défaut: 70)

### Coûts
- `cost_rate`: Taux de commission par exécution (défaut: 0.0002 = 0.02%)

### Données
- `data_file`: Chemin vers le fichier CSV (défaut: "data/NAS100_3min.csv")

## Format des données

Le fichier CSV doit contenir au minimum les colonnes OHLCV. Les formats suivants sont supportés :

### Format 1 (standard)
```csv
datetime,open,high,low,close,volume
2024-01-01 00:00:00,16000,16010,15990,16005,250
2024-01-01 00:03:00,16005,16020,16000,16015,320
```

### Format 2 (MT5/broker export)
```csv
time,open,high,low,close,volume,spread,real_volume
2024-01-01 00:00:00,16000,16010,15990,16005,250,2,1000
2024-01-01 00:03:00,16005,16020,16000,16015,320,2,1200
```

**Colonnes acceptées pour le timestamp** : `datetime`, `time`, `timestamp`, `date`  
**Colonnes requises** : `open`, `high`, `low`, `close`, `volume`  
**Colonnes ignorées** : `spread`, `real_volume`, et autres colonnes supplémentaires

**Note** : 
- Les noms de colonnes sont insensibles à la casse (TIME, time, Time fonctionnent)
- Si le fichier n'existe pas, des données d'exemple seront générées automatiquement
- Les lignes avec valeurs manquantes sont automatiquement supprimées

## Utilisation

### Lancer le backtest

```bash
python main.py
```

### Sortie attendue

Le script va :
1. Charger la configuration
2. Charger les données (ou en générer)
3. Initialiser Backtrader
4. Exécuter le backtest
5. Afficher les statistiques
6. Exporter les trades dans `output/trades.csv`
7. Générer une visualisation graphique

### Exemple de sortie

```
============================================================
MVP BACKTRADER - BACKTEST
============================================================

[1] Loading configuration...
Capital: $10000
Risk per trade: 1.0%
Commission: 0.02%

[2] Loading data...
Data loaded: 175200 rows from 2024-01-01 to 2024-12-31

[3] Initializing Backtrader Cerebro...
[4] Running backtest...
------------------------------------------------------------
Starting Portfolio Value: $10000.00

2024-01-15T09:15:00 - LONG SIGNAL - Entry order placed
2024-01-15T09:18:00 - BUY EXECUTED - Price: 16050.00
2024-01-15T09:45:00 - TP1 HIT - Partial exit
2024-01-15T09:45:00 - BREAK-EVEN activated at 16050.00
2024-01-15T10:20:00 - TP2 HIT - Position closed
...

Final Portfolio Value: $10500.00
Total Return: $500.00 (5.00%)

============================================================
BACKTEST STATISTICS
============================================================

--- Trade Analysis ---
Total trades: 25
Won: 15
Lost: 10
Win rate: 60.00%
Average win: $50.00
Average loss: $-25.00

--- Drawdown ---
Max drawdown: $250.00 (2.50%)

--- Returns ---
Total return: 5.00%

[5] Exporting trades...
Trades exported to: output/trades.csv
Total events logged: 75

Trade Events Summary:
ENTRY          25
TP1            15
TP2            10
SL              8
BE_MOVE        15
CLOSE_INVALID   2

Total PnL from events: 500.00

[6] Generating plot...
Plot generated successfully

============================================================
BACKTEST COMPLETED
============================================================
```

## Fichier de sortie : trades.csv

Le fichier `output/trades.csv` contient tous les événements du backtest :

```csv
datetime,trade_id,event_type,direction,price,size,pnl
2024-01-15 09:18:00,1,ENTRY,LONG,16050.00,10.0,0.0
2024-01-15 09:45:00,1,TP1,LONG,16070.00,5.0,100.0
2024-01-15 09:45:00,1,BE_MOVE,LONG,16050.00,0.0,0.0
2024-01-15 10:20:00,1,TP2,LONG,16090.00,5.0,200.0
...
```

### Types d'événements
- `ENTRY`: Entrée en position
- `TP1`: Premier take profit touché
- `TP2`: Deuxième take profit touché
- `SL`: Stop loss touché
- `BE_MOVE`: Déplacement du SL au break-even
- `CLOSE_INVALID`: Sortie via exit rule

## Stratégie implémentée (exemple)

La stratégie par défaut utilise :
- **Bollinger Bands** (période 20, écart-type 2)
- **RSI** (période 14)

### Signal LONG
- Prix franchit la bande inférieure puis rebondit
- RSI < 40 (confirmation)

### Signal SHORT
- Prix franchit la bande supérieure puis retombe
- RSI > 60 (confirmation)

### Exit Rule
- LONG : sortie si RSI > 70
- SHORT : sortie si RSI < 30

**Note** : Vous pouvez modifier la logique dans `strategy.py` → méthode `_generate_signal()`

## Personnalisation

### Modifier la stratégie

Éditer `strategy.py` et modifier :
- `_generate_signal()` : logique d'entrée
- `_check_exit_rule()` : logique de sortie conditionnelle

### Ajouter des indicateurs

Dans `__init__()` de la stratégie :
```python
self.ma_fast = bt.indicators.SMA(self.data.close, period=10)
self.ma_slow = bt.indicators.SMA(self.data.close, period=50)
```

### Modifier le sizing

Éditer `sizing.py` pour implémenter d'autres méthodes (Kelly, Fixed Fractional, etc.)

## Limitations du MVP

Conformément au cahier des charges :
- ✅ Un seul trade à la fois
- ✅ Exécution standard Backtrader (bar-by-bar)
- ✅ Pas de gestion intrabar complexe
- ✅ Pas de moteur d'exécution custom
- ✅ Visualisation Backtrader standard (pas de lightweight-charts)

## Prochaines étapes (post-MVP)

1. Intégration lightweight-charts pour visualisation avancée
2. Gestion multi-trades simultanés
3. Gestion intrabar précise avec priorités SL/TP
4. Système d'exit rules modulaire
5. Plus d'analyseurs et métriques

## Support

Pour toute question ou amélioration, référez-vous au cahier des charges original.

## Licence

Ce projet est un MVP éducatif pour le backtesting de stratégies de trading.
