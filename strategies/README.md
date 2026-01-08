# 📚 Stratégies de Trading

Ce dossier contient toutes les stratégies de trading disponibles.

## 🏗️ Architecture

```
strategies/
├── base_strategy.py              # Classe de base (commune)
├── strategy_rsi_amplitude.py     # RSI + Amplitude SL
├── strategy_macd_ema.py          # MACD + EMA Crossover
└── strategy_bollinger_breakout.py # Bollinger Bands Breakout
```

## 📋 Stratégies Disponibles

### 1. RSI + Amplitude (`RSIAmplitudeStrategy`)

**Concept**: Trade sur suracheté/survendu RSI avec SL basé sur l'amplitude des bougies

**Signaux**:
- **LONG**: RSI < seuil (30) → SL = low des N dernières bougies
- **SHORT**: RSI > seuil (70) → SL = high des N dernières bougies

**Paramètres**:
```yaml
strategy_name: "RSIAmplitudeStrategy"
strategy_params:
  rsi_period: 14
  rsi_long_threshold: 30
  rsi_short_threshold: 70
  sl_lookback: 3
```

---

### 2. MACD + EMA (`MACDEMAStrategy`)

**Concept**: Crossover MACD confirmé par position par rapport à l'EMA

**Signaux**:
- **LONG**: MACD cross au-dessus signal + prix > EMA
- **SHORT**: MACD cross en-dessous signal + prix < EMA

**Paramètres**:
```yaml
strategy_name: "MACDEMAStrategy"
strategy_params:
  macd_fast: 12
  macd_slow: 26
  macd_signal: 9
  ema_period: 50
  sl_atr_multiplier: 2.0
```

---

### 3. Bollinger Breakout (`BollingerBreakoutStrategy`)

**Concept**: Breakout des bandes de Bollinger avec confirmation de volume

**Signaux**:
- **LONG**: Prix casse bande haute + volume > moyenne
- **SHORT**: Prix casse bande basse + volume > moyenne

**Paramètres**:
```yaml
strategy_name: "BollingerBreakoutStrategy"
strategy_params:
  bb_period: 20
  bb_std: 2.0
  volume_ma_period: 20
  volume_threshold: 1.5
  sl_atr_multiplier: 2.5
```

---

## 🔧 Ajouter une Nouvelle Stratégie

### Étape 1: Créer le fichier

```python
# strategies/strategy_ma_cross.py
from strategies.base_strategy import BaseStrategy
import backtrader as bt

class MAC rossStrategy(BaseStrategy):
    """Moving Average Crossover"""
    
    params = (
        ('fast_period', 10),
        ('slow_period', 30),
    )
    
    def __init__(self):
        super().__init__()
        
        self.ma_fast = bt.indicators.SMA(period=self.p.fast_period)
        self.ma_slow = bt.indicators.SMA(period=self.p.slow_period)
        self.crossover = bt.indicators.CrossOver(self.ma_fast, self.ma_slow)
    
    def next(self):
        if self.in_position:
            # Gérer position
            return
        
        # Signal LONG
        if self.crossover > 0:
            # Calculer SL, entrer position
            pass
        
        # Signal SHORT
        elif self.crossover < 0:
            # Calculer SL, entrer position
            pass
```

### Étape 2: Ajouter à `__init__.py`

```python
from .strategy_ma_cross import MACrossStrategy

__all__ = [
    # ...
    'MACrossStrategy',
]
```

### Étape 3: Créer config

```yaml
# config_ma_cross.yaml
strategy_name: "MACrossStrategy"
strategy_module: "strategy_ma_cross"

strategy_params:
  fast_period: 10
  slow_period: 30
  tp1_rr: 2.0
  tp2_rr: 4.0
```

### Étape 4: Lancer

```bash
python run_backtest.py config_ma_cross.yaml
```

---

## 📊 Classe de Base (`BaseStrategy`)

Toutes les stratégies héritent de `BaseStrategy` qui fournit:

### Paramètres Communs
- `risk_per_trade`: % du capital risqué par trade (0.01 = 1%)
- `tp1_rr`, `tp2_rr`: Ratios Risk/Reward pour TP1 et TP2
- `tp1_ratio`, `tp2_ratio`: Portion fermée à chaque TP
- `enable_breakeven`: Activer break-even après TP1
- `breakeven_offset`: Décalage du BE en pips
- `min_sl_distance_pips`: SL min (filtrage)
- `max_sl_distance_pips`: SL max (filtrage)

### Méthodes Communes
- `log(txt)`: Log avec timestamp
- `check_sl_filters(sl_distance)`: Vérifie filtres SL
- `calculate_position_size(sl_distance)`: Calcule taille position
- `log_trade_event(type, price, ...)`: Log événement trade

### Variables d'État
- `in_position`: En position ou non
- `position_direction`: 'LONG' ou 'SHORT'
- `entry_price`, `entry_size`: Prix/taille d'entrée
- `sl_price`, `sl_distance`: SL et distance
- `trade_id`: ID du trade actuel
- `trades_log`: Liste de tous les événements

---

## 🎯 Bonnes Pratiques

1. **Toujours appeler `super().__init__()`** dans le constructeur
2. **Utiliser `check_sl_filters()`** avant d'entrer un trade
3. **Logger les rejets** pour analyse
4. **Documenter la logique** de chaque stratégie
5. **Tester avec plusieurs timeframes** et symboles

---

## 📈 Exemples d'Utilisation

### Tester Une Stratégie

```bash
python run_backtest.py config_rsi_amplitude.yaml
```

### Comparer Toutes les Stratégies

```bash
python compare_all_strategies.py
```

### Lancer Une Série de Tests

```bash
for config in config_*.yaml; do
    echo "Testing $config..."
    python run_backtest.py "$config"
done
```

---

📚 **Documentation complète**: Voir `MULTI_STRATEGIES_GUIDE.md`
