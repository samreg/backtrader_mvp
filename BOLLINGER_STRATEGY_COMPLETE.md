# 📋 STRATÉGIE BOLLINGER BREAKOUT - DOCUMENTATION COMPLÈTE

## 🎯 CONCEPT GÉNÉRAL

**Type** : Mean Reversion sur Bollinger Bands  
**Principe** : Prix sort des bandes → Prix RE-ENTRE → Signal d'entrée

---

## 📊 PARAMÈTRES DE LA STRATÉGIE

### Bollinger Bands
```python
self.p.bb_period = 20        # Période BB
self.p.bb_std = 1.5          # Écarts-types (1.5 pour mean reversion)
```

### Stop Loss (basé sur swing high/low)
```python
self.p.sl_lookback = 3       # Nombre de bougies pour trouver swing
self.p.sl_offset_pips = 10   # Pips au-delà du swing
```

### RSI (système de flags)
```python
self.p.rsi_period = 14
self.p.rsi_oversold = 20          # < 20 → RSI_buy
self.p.rsi_oversold_exit = 30     # > 30 → RSI_middle
self.p.rsi_overbought = 80        # > 80 → RSI_sell
self.p.rsi_overbought_exit = 70   # < 70 → RSI_middle
```

### Take Profit (hérités de base_strategy)
```python
self.p.tp1_ratio = 0.5       # 50% sortie à TP1
self.p.tp2_ratio = 0.5       # 50% sortie à TP2
self.p.enable_breakeven = True
self.p.breakeven_offset = 0  # Pips au-dessus de l'entry
```

---

## 🔧 INDICATEURS

### Bollinger Bands
```python
self.bb = bt.indicators.BollingerBands(
    self.data.close,
    period=self.p.bb_period,    # 20
    devfactor=self.p.bb_std     # 1.5
)

# Accès aux valeurs:
bb_upper = self.bb.lines.top[0]    # Bande supérieure
bb_middle = self.bb.lines.mid[0]   # Bande médiane
bb_lower = self.bb.lines.bot[0]    # Bande inférieure
```

### RSI
```python
self.rsi = bt.indicators.RSI(
    self.data.close,
    period=self.p.rsi_period    # 14
)

# Accès à la valeur:
current_rsi = self.rsi[0]
```

---

## 🚩 FLAGS ET ÉTATS

### FLAGS Bollinger Bands (tracking sortie)
```python
self.outside_lower = False   # True si prix < BB Lower (sorti en bas)
self.outside_upper = False   # True si prix > BB Upper (sorti en haut)
```

**Mise à jour** (dans `next()` ligne 127-132) :
```python
if current_price < bb_lower:
    self.outside_lower = True
    self.outside_upper = False
elif current_price > bb_upper:
    self.outside_upper = True
    self.outside_lower = False
```

### ÉTAT RSI (machine à 3 états)
```python
self.rsi_state = 'RSI_middle'   # Valeurs possibles: 'RSI_buy', 'RSI_middle', 'RSI_sell'
```

**RÈGLE CRITIQUE** : `self.rsi_state` revient **TOUJOURS à 'RSI_middle' dès qu'un trade est PRIS** (à l'entrée, pas à la sortie).

Cela empêche de prendre plusieurs trades consécutifs dans le même état RSI.

**Transitions RSI** (lignes 102-124) :

```
                    RSI < 20
   RSI_middle  ─────────────────►  RSI_buy
       ▲                              │
       │                              │ RSI >= 30
       └──────────────────────────────┘
       
                    RSI > 80
   RSI_middle  ─────────────────►  RSI_sell
       ▲                              │
       │                              │ RSI <= 70
       └──────────────────────────────┘
```

**Code des transitions** :
```python
# État RSI_middle
if self.rsi_state == 'RSI_middle':
    if current_rsi < self.p.rsi_oversold:           # < 20
        self.rsi_state = 'RSI_buy'
    elif current_rsi > self.p.rsi_overbought:       # > 80
        self.rsi_state = 'RSI_sell'

# État RSI_buy
elif self.rsi_state == 'RSI_buy':
    if current_rsi >= self.p.rsi_oversold_exit:     # >= 30
        self.rsi_state = 'RSI_middle'

# État RSI_sell
elif self.rsi_state == 'RSI_sell':
    if current_rsi <= self.p.rsi_overbought_exit:   # <= 70
        self.rsi_state = 'RSI_middle'
```

### FLAGS Position Management
```python
# Hérités de base_strategy
self.in_position = False          # True si en position
self.position_direction = None    # 'LONG' ou 'SHORT'
self.tp1_hit = False              # True si TP1 touché
self.breakeven_active = False     # True si SL déplacé au BE
```

### VARIABLES Position
```python
# Hérités de base_strategy
self.trade_id = 0                 # ID du trade actuel
self.entry_price = None           # Prix d'entrée
self.entry_time = None            # Datetime d'entrée
self.entry_size = None            # Taille position (contrats)
self.sl_price = None              # Prix du SL
self.sl_distance = None           # Distance SL en PRICE
```

### VARIABLES TP (spécifiques à Bollinger)
```python
self.tp1_price = None    # Prix TP1 = BB Middle (dynamique)
self.tp2_price = None    # Prix TP2 = BB Upper/Lower (dynamique)
```

---

## 🎯 LOGIQUE D'ENTRÉE

### CONDITIONS PRÉALABLES

```python
# 1. Pas en position
if self.in_position:
    self._manage_position()
    return

# 2. Assez de données historiques
if len(self.data) < max(self.p.bb_period, self.p.sl_lookback, self.p.rsi_period):
    return

# 3. Dans trading window (si configuré)
current_time = self.datas[0].datetime.datetime(0)
if not self.trading_windows.is_trading_allowed(current_time):
    return
```

### SIGNAL LONG (ligne 137-149)

**Conditions** :
1. `self.outside_lower == True` (prix était sorti en bas)
2. `current_price >= bb_lower` (prix RE-ENTRE dans la bande)
3. `self.rsi_state == 'RSI_buy'` (RSI en zone d'achat)
4. Filtres SL OK (`check_sl_filters(sl_distance_pips)`)

**Calcul SL** :
```python
swing_low = min([self.data.low[-i] for i in range(self.p.sl_lookback)])  # Plus bas des 3 dernières bougies
sl_price = swing_low - self.pips_to_price(self.p.sl_offset_pips)        # - 10 pips
sl_distance_pips = self.price_to_pips(current_price - sl_price)          # Distance en pips
```

**Action** :
```python
self._enter_long(current_price, sl_price, sl_distance_pips, bb_middle, bb_upper, current_rsi)
self.outside_lower = False  # Reset flag BB
```

### SIGNAL SHORT (ligne 154-166)

**Conditions** :
1. `self.outside_upper == True` (prix était sorti en haut)
2. `current_price <= bb_upper` (prix RE-ENTRE dans la bande)
3. `self.rsi_state == 'RSI_sell'` (RSI en zone de vente)
4. Filtres SL OK (`check_sl_filters(sl_distance_pips)`)

**Calcul SL** :
```python
swing_high = max([self.data.high[-i] for i in range(self.p.sl_lookback)])  # Plus haut des 3 dernières bougies
sl_price = swing_high + self.pips_to_price(self.p.sl_offset_pips)         # + 10 pips
sl_distance_pips = self.price_to_pips(sl_price - current_price)            # Distance en pips
```

**Action** :
```python
self._enter_short(current_price, sl_price, sl_distance_pips, bb_middle, bb_lower, current_rsi)
self.outside_upper = False  # Reset flag BB
```

---

## 📈 ENTRÉE LONG (fonction `_enter_long`)

### Étapes (lignes 168-205)

1. **Position Sizing** :
```python
position_size = self.calculate_position_size(sl_distance_pips)
```

2. **Stocker TP targets** :
```python
self.tp1_price = tp1_target   # BB Middle (dynamique)
self.tp2_price = tp2_target   # BB Upper (dynamique)
```

3. **Réinitialiser flags** :
```python
self.tp1_hit = False
self.breakeven_active = False
```

4. **Mettre à jour état** :
```python
self.trade_id += 1
self.in_position = True
self.position_direction = 'LONG'
self.entry_price = entry_price
self.entry_time = self.datas[0].datetime.datetime(0)
self.entry_size = position_size
self.sl_price = sl_price
self.sl_distance = self.pips_to_price(sl_distance_pips)
```

5. **Ordre Backtrader** :
```python
self.buy(size=position_size)
```

6. **Logger** :
```python
self.log_trade_event('ENTRY', entry_price, position_size, sl_distance=sl_distance_pips)
self.log_box('SL_INITIAL', self.entry_time, self.entry_time, sl_box_low, sl_box_high, metadata={'sl_price': sl_price})
```

---

## 📉 ENTRÉE SHORT (fonction `_enter_short`)

### Étapes (lignes 207-243)

Identique à LONG sauf :

1. **TP targets inversés** :
```python
self.tp1_price = tp1_target   # BB Middle
self.tp2_price = tp2_target   # BB Lower (opposé de LONG)
```

2. **Ordre SHORT** :
```python
self.sell(size=position_size)
```

---

## 🎮 GESTION POSITION (fonction `_manage_position`)

### Données utilisées (lignes 248-256)

```python
current_high = self.data.high[0]    # IMPORTANT: Utiliser high/low, pas close!
current_low = self.data.low[0]
current_close = self.data.close[0]

# Bandes BB actuelles (dynamiques, se mettent à jour à chaque bougie)
bb_upper = self.bb.lines.top[0]
bb_middle = self.bb.lines.mid[0]
bb_lower = self.bb.lines.bot[0]
```

---

## 📈 GESTION POSITION LONG (lignes 258-323)

### 1. CHECK SL / BE (lignes 260-286)

**Condition** : `current_low <= self.sl_price`

**Calcul PnL** :
```python
if self.tp1_hit:
    # TP1 déjà touché → PnL sur position restante
    remaining_size = self.entry_size * (1 - self.p.tp1_ratio)  # 50%
    pnl = (self.sl_price - self.entry_price) * remaining_size
else:
    # TP1 pas touché → PnL sur position complète
    pnl = (self.sl_price - self.entry_price) * self.entry_size
```

**Type de sortie** :
```python
if self.breakeven_active:
    exit_type = 'BE'   # Break-even (pas de box)
else:
    exit_type = 'SL'   # SL réel (box rouge)
    self.log_box('SL', self.entry_time, exit_time, price_low, price_high)
```

**Action** :
```python
self.close()
self.log_trade_event(exit_type, self.sl_price, pnl=pnl)
self.in_position = False

# Reset RSI state
self.rsi_state = 'RSI_middle'
```

### 2. CHECK TP1 (lignes 290-307)

**Conditions** :
- `current_high >= bb_middle` (prix touche BB Middle)
- `not self.tp1_hit` (pas déjà touché)

**Calcul PnL** :
```python
partial_size = self.entry_size * self.p.tp1_ratio  # 50%
pnl = (tp1_price - self.entry_price) * partial_size
```

**Actions** :
```python
self.tp1_hit = True
self.log_trade_event('TP1', tp1_price, pnl=pnl)
self.log_box('TP1', self.entry_time, exit_time, price_low, price_high)

# Break-even
if self.p.enable_breakeven:
    self.sl_price = self.entry_price + self.p.breakeven_offset
    self.breakeven_active = True
```

### 3. CHECK TP2 (lignes 310-323)

**Condition** : `current_high >= bb_upper` (prix touche BB Upper)

**Calcul PnL** :
```python
# TP2 sur position RESTANTE (après TP1)
remaining_size = self.entry_size * (1 - self.p.tp1_ratio)  # 50%
pnl = (tp2_price - self.entry_price) * remaining_size
```

**Action** :
```python
self.close()
self.log_trade_event('TP2', tp2_price, pnl=pnl)
self.log_box('TP2', self.entry_time, exit_time, price_low, price_high)
self.in_position = False

# Reset RSI state
self.rsi_state = 'RSI_middle'
```

---

## 📉 GESTION POSITION SHORT (lignes 325-390)

### 1. CHECK SL / BE (lignes 327-353)

**Condition** : `current_high >= self.sl_price` (utiliser HIGH pour SHORT)

**Calcul PnL** :
```python
if self.tp1_hit:
    remaining_size = self.entry_size * (1 - self.p.tp1_ratio)
    pnl = (self.entry_price - self.sl_price) * remaining_size
else:
    pnl = (self.entry_price - self.sl_price) * self.entry_size
```

**Type de sortie** :
```python
if self.breakeven_active:
    exit_type = 'BE'
else:
    exit_type = 'SL'
    self.log_box('SL', self.entry_time, exit_time, price_low, price_high)
```

### 2. CHECK TP1 (lignes 357-374)

**Conditions** :
- `current_low <= bb_middle` (utiliser LOW pour SHORT)
- `not self.tp1_hit`

**Calcul PnL** :
```python
partial_size = self.entry_size * self.p.tp1_ratio
pnl = (self.entry_price - tp1_price) * partial_size
```

**Actions** :
```python
self.tp1_hit = True
self.log_trade_event('TP1', tp1_price, pnl=pnl)
self.log_box('TP1', self.entry_time, exit_time, price_low, price_high)

# Break-even
if self.p.enable_breakeven:
    self.sl_price = self.entry_price - self.p.breakeven_offset
    self.breakeven_active = True
```

### 3. CHECK TP2 (lignes 377-390)

**Condition** : `current_low <= bb_lower` (utiliser LOW pour SHORT)

**Calcul PnL** :
```python
remaining_size = self.entry_size * (1 - self.p.tp1_ratio)
pnl = (self.entry_price - tp2_price) * remaining_size
```

**Action** :
```python
self.close()
self.log_trade_event('TP2', tp2_price, pnl=pnl)
self.log_box('TP2', self.entry_time, exit_time, price_low, price_high)
self.in_position = False
```

---

## 🔍 POINTS CLÉS

### HIGH vs LOW pour les touches
- **LONG** : Utilise `current_high` pour TP1/TP2, `current_low` pour SL
- **SHORT** : Utilise `current_low` pour TP1/TP2, `current_high` pour SL

### PnL sur position restante
- **TP2** : Toujours calculé sur `remaining_size` (50% si TP1 touché)
- **SL/BE après TP1** : Calculé sur `remaining_size` si `tp1_hit == True`

### Flags critiques
- `self.tp1_hit` : DOIT être réinitialisé à False à chaque nouveau trade
- `self.breakeven_active` : DOIT être réinitialisé à False à chaque nouveau trade
- `self.outside_lower/upper` : Reset après signal d'entrée

### TP dynamiques
- TP1 et TP2 ne sont PAS fixes mais suivent les bandes BB qui bougent à chaque bougie
- `bb_middle`, `bb_upper`, `bb_lower` sont recalculés dans `_manage_position()`

---

## 📊 ORDRE D'EXÉCUTION

```
next() appelé à chaque bougie
│
├─► Si in_position == True
│   └─► _manage_position()
│       ├─► Check SL/BE
│       ├─► Check TP1 (si pas encore touché)
│       └─► Check TP2
│
└─► Si in_position == False
    ├─► Update RSI state machine
    ├─► Track BB outside flags
    ├─► Check LONG conditions
    │   └─► _enter_long()
    └─► Check SHORT conditions
        └─► _enter_short()
```

---

## 🎯 RÉSUMÉ DES VARIABLES CLÉS

| Variable | Type | Description |
|----------|------|-------------|
| `self.bb` | Indicator | Bollinger Bands (top/mid/bot) |
| `self.rsi` | Indicator | RSI |
| `self.outside_lower` | bool | Prix sorti en bas |
| `self.outside_upper` | bool | Prix sorti en haut |
| `self.rsi_state` | str | 'RSI_buy', 'RSI_middle', 'RSI_sell' |
| `self.in_position` | bool | En position ou non |
| `self.position_direction` | str | 'LONG' ou 'SHORT' |
| `self.tp1_hit` | bool | TP1 touché |
| `self.breakeven_active` | bool | BE activé |
| `self.trade_id` | int | ID trade actuel |
| `self.entry_price` | float | Prix entrée |
| `self.entry_time` | datetime | Temps entrée |
| `self.entry_size` | float | Taille position |
| `self.sl_price` | float | Prix SL |
| `self.tp1_price` | float | Prix TP1 (BB Middle) |
| `self.tp2_price` | float | Prix TP2 (BB Upper/Lower) |
