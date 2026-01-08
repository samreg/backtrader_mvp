# 📊 ORDER BLOCKS - EXPLICATION COMPLÈTE

## 🎯 DÉFINITION

Un **Order Block** est la dernière bougie contraire avant un mouvement impulsif fort créé par les institutions.

---

## 🔍 LOGIQUE DE DÉTECTION

### Étape 1 : Détecter un Swing

**Swing Low** : Le prix le plus bas sur une période
```
        ↗
       ↗
      ↗
     ↗
    ↙ ← Swing Low (lowest point)
   ↙
```

**Swing High** : Le prix le plus haut sur une période
```
   ↗
  ↗ ← Swing High (highest point)
 ↗
↗
```

**Paramètre** : `swing_length = 10`
- Vérifie 10 bougies avant + 10 bougies après
- Si c'est le plus bas/haut → Swing confirmé

---

### Étape 2 : Vérifier Imbalance (Impulsion Forte)

#### Imbalance Haussier

**Définition** : Le bas de la 3ème bougie est plus haut que le haut de la 1ère

```
Bougie 1     Bougie 2     Bougie 3
┌─────┐                   ┌────────┐
│     │      ┌─────┐      │        │
│  1  │      │  2  │      │   3    │  ← Bas de 3 > Haut de 1
└─────┘      └─────┘      └────────┘
  ↑                            ↑
 Haut                         Bas
  de 1                        de 3

GAP = Imbalance !
```

**Code** :
```python
first_candle['high'] = 21450.00
third_candle['low']  = 21455.00

if third_candle['low'] > first_candle['high']:
    # Imbalance détecté !
    # Il y a un "gap" entre les 2 bougies
```

#### Imbalance Baissier

**Définition** : Le haut de la 3ème bougie est plus bas que le bas de la 1ère

```
Bougie 1     Bougie 2     Bougie 3
┌─────┐                   
│     │      ┌─────┐      
│  1  │      │  2  │      ┌────────┐
└─────┘      └─────┘      │   3    │  ← Haut de 3 < Bas de 1
  ↓                        └────────┘
 Bas                            ↑
  de 1                         Haut
                               de 3

GAP = Imbalance !
```

**Paramètre** : `imbalance_bars = 3`
- Vérifie 3 bougies consécutives
- Si gap détecté → Impulsion confirmée

---

### Étape 3 : Identifier la Bougie Order Block

**C'est la DERNIÈRE bougie contraire AVANT l'impulsion**

#### Exemple Bullish Order Block

```
Contexte: Prix baisse, puis impulsion haussière

         IMPULSION (3 bougies avec imbalance)
              ↓
    ...  ┌──────┐  ┌──────┐  ┌──────┐
         │ Vert │  │ Vert │  │ Vert │
         │  2   │  │  3   │  │  4   │
         └──────┘  └──────┘  └──────┘
              ↑
         ┌──────┐
         │Rouge │ ← ORDER BLOCK (dernière rouge avant impulsion)
         │  1   │
         └──────┘
              ↑
    ... (bougies avant)
```

**La zone OB** = De `low` à `high` de cette bougie rouge

**Code** :
```python
# Chercher en arrière depuis le swing
for i in range(swing_idx - 1, swing_idx - swing_length, -1):
    if candles[i]['close'] < candles[i]['open']:  # Bougie rouge
        return i  # C'est l'Order Block !
```

---

### Étape 4 : Créer la Zone

**Zone OB Bullish** :
```
Prix
│
│  ┌─────────────────────────────────────┐
│  │                                     │ ← High de la bougie OB
│  │      ZONE ORDER BLOCK               │
│  │                                     │
│  │                                     │ ← Low de la bougie OB
│  └─────────────────────────────────────┘
│
└─────────────────────────────────────────▶ Temps
   t_start                            t_end (mitigation)
```

**Propriétés** :
- `low` : Bas de la bougie OB
- `high` : Haut de la bougie OB
- `t_start` : Temps de la bougie OB
- `t_end` : `None` (jusqu'à mitigation)
- `state` : `'active'`

---

### Étape 5 : Tracker la Mitigation

**Mitigation** = Le prix traverse TOTALEMENT la zone

#### OB Bullish Mitigé

```
Prix passe SOUS le low de l'OB

    ┌───────────────────┐
    │   OB Zone         │ ← High
    │                   │
    │                   │ ← Low
    └───────────────────┘
             ↓
         Prix descend
             ↓
            ▼▼▼  ← Prix < Low = MITIGATION !
```

**Code** :
```python
if direction == 'bullish':
    if candle['low'] < zone.low:
        zone.state = 'mitigated'
        zone.t_end = current_time
```

#### OB Bearish Mitigé

```
Prix passe AU-DESSUS du high de l'OB

            ▲▲▲  ← Prix > High = MITIGATION !
             ↑
         Prix monte
             ↑
    ┌───────────────────┐
    │                   │ ← High
    │   OB Zone         │
    │                   │ ← Low
    └───────────────────┘
```

---

## 📐 EXEMPLE COMPLET

### Données NAS100 M1

```
Index | Time     | Open    | High    | Low     | Close   | Type
------|----------|---------|---------|---------|---------|-------
100   | 10:00    | 21400   | 21405   | 21398   | 21402   | Vert
101   | 10:01    | 21402   | 21406   | 21400   | 21404   | Vert
102   | 10:02    | 21404   | 21408   | 21402   | 21405   | Vert
103   | 10:03    | 21405   | 21410   | 21403   | 21407   | Vert
104   | 10:04    | 21407   | 21409   | 21404   | 21403   | Rouge ← SWING LOW
105   | 10:05    | 21403   | 21407   | 21401   | 21398   | Rouge ← ORDER BLOCK
106   | 10:06    | 21398   | 21412   | 21398   | 21410   | Vert  ← Impulsion 1
107   | 10:07    | 21410   | 21420   | 21409   | 21418   | Vert  ← Impulsion 2
108   | 10:08    | 21418   | 21428   | 21417   | 21425   | Vert  ← Impulsion 3
```

### Détection

**Étape 1** : Index 104 est un swing low
- Low 104 (21404) < Low 103 (21403) ✅
- Low 104 (21404) < Low 105 (21401) ❌ → Continue

Index 105 est potentiellement un swing
- Low 105 (21401) < Low des 10 bougies avant/après ✅

**Étape 2** : Vérifier imbalance de 106 à 108

```
Bougie 106:
- Low = 21398
- High = 21412

Bougie 108:
- Low = 21417
- High = 21428

Imbalance ? Low de 108 (21417) > High de 106 (21412) ✅
```

**Étape 3** : Trouver dernière bougie rouge avant 106
- Index 105 : close (21398) < open (21403) ✅ → ORDER BLOCK !

**Étape 4** : Créer zone

```python
ZoneObject(
    id='ob_1',
    t_start='10:05',
    t_end=None,
    low=21401,   # Low de la bougie 105
    high=21407,  # High de la bougie 105
    type='order_block',
    state='active',
    metadata={
        'direction': 'bullish',
        'ob_index': 105,
        'imbalance_end': 108
    }
)
```

**Étape 5** : Tracker mitigation

Surveiller les bougies suivantes :
- Si prix < 21401 → Mitigé
- Sinon → Reste actif

---

## 🎨 VISUALISATION

### Dans le Chart

```
Prix
│
│     ╔══════════ Zone OB (21407) ══════════╗  ← Ligne verte pointillée
│     ║                                      ║
│     ║                                      ║
│     ║                                      ║
│     ╚══════════ Zone OB (21401) ══════════╝  ← Ligne verte pointillée
│
│  ▲  ▲  ▲  ← Impulsion (3 bougies vertes)
│ ▲
│▼ ← Order Block (bougie rouge)
│
└────────────────────────────────────────────▶ Temps
```

### Légende

- **Ligne verte pointillée (haut)** : `high` de l'OB
- **Ligne verte pointillée (bas)** : `low` de l'OB
- **Label** : "OB Bull 21401.00-21407.00"

---

## ⚙️ PARAMÈTRES

### `swing_length` (défaut: 10)

**Rôle** : Sensibilité de détection des swings

- **Valeur basse (5)** : Plus de swings détectés → Plus d'OB
- **Valeur haute (20)** : Moins de swings → OB plus significatifs

**Recommandation** : 
- M1-M5 : `swing_length = 10`
- H1-H4 : `swing_length = 15-20`

---

### `min_body_size` (défaut: 2.0 points)

**Rôle** : Taille minimum du body de la bougie OB

- **Valeur basse (1.0)** : Plus d'OB acceptés
- **Valeur haute (5.0)** : Seulement grosses bougies

**Recommandation** :
- NAS100 M1 : `min_body_size = 2.0-3.0`
- EURUSD M5 : `min_body_size = 0.0005-0.001`

---

### `imbalance_bars` (défaut: 3)

**Rôle** : Nombre de bougies pour détecter imbalance

- **Valeur = 3** : Standard (gap entre 1ère et 3ème)
- **Valeur = 5** : Impulsion plus forte requise

**Recommandation** : Garder à `3` (standard SMC)

---

### `max_zones` (défaut: 15)

**Rôle** : Nombre max de zones à afficher

- **Valeur basse (5)** : Chart épuré
- **Valeur haute (30)** : Toutes les zones

**Recommandation** :
- Visualization : `max_zones = 10-15`
- Backtesting : `max_zones = 30+`

---

## 🧪 TESTS

### Test 1 : Détection basique

```python
# Données simulées
candles = pd.DataFrame({
    'time': [...],
    'open': [100, 102, 101, 100, 99, 105, 108, 110],
    'high': [101, 103, 102, 101, 100, 107, 110, 112],
    'low':  [99,  101, 100, 99,  98,  104, 107, 109],
    'close':[100, 102, 101, 99,  98,  106, 109, 111]
})

# Index 4 : Swing low
# Index 106-108 : Imbalance (109 > 100)
# Index 4 : Dernière rouge → ORDER BLOCK
```

### Test 2 : Mitigation

```python
# OB créé à index 4 (low=98, high=100)
# Bougie suivante : low=97 → MITIGATION !
```

---

## 🚀 UTILISATION

### Dashboard

```bash
python dashboard_simple.py
# Choix: 2 (Order Blocks)
```

### Config YAML

```yaml
indicators:
  - name: ob_m1
    module: order_blocks.py
    timeframe: M1
    panel: main
    params:
      swing_length: 10
      min_body_size: 2.0
      imbalance_bars: 3
      max_zones: 15
```

---

## 📊 RÉSULTATS ATTENDUS

### Logs

```
⚙️  Executing indicators...
   Calculating order_blocks...
      ✅ 0 series, 12 objects

Metadata:
   total_zones: 12
   bullish_zones: 7
   bearish_zones: 5
```

### Dans le Chart

- **12 paires de lignes** vertes/rouges (24 lignes total)
- Lignes pointillées horizontales
- Labels "OB Bull" / "OB Bear"

---

**Maintenant tu as la logique complète ! 🎯📊**
