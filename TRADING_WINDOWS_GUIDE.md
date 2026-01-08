# ⏰ TRADING WINDOWS - FILTRES TEMPORELS

## 📋 DESCRIPTION

Les **Trading Windows** permettent de restreindre les entrées en position à des créneaux horaires spécifiques.

**Comportement** :
- ✅ **Entrées** : Autorisées SEULEMENT pendant les créneaux définis
- ✅ **Sorties** : TOUJOURS autorisées (SL/TP/BE) même hors créneau
- ✅ **Positions existantes** : Continuent d'être gérées hors créneau

---

## 🔧 CONFIGURATION

### Format Compact

```yaml
strategy:
  trading_windows:
    enabled: true
    timezone: "Europe/Paris"
    
    windows:
      - "Monday[13:00-16:00]"
      - "Monday[20:00-22:00]"
      - "Tuesday[09:00-11:30]"
      - "Friday[08:00-12:00]"
```

### Paramètres

| Paramètre | Type | Description | Défaut |
|-----------|------|-------------|--------|
| `enabled` | bool | Activer/désactiver le filtre | `false` |
| `timezone` | str | Timezone des créneaux (format IANA) | `"Europe/Paris"` |
| `windows` | list[str] | Liste des créneaux | `[]` |

### Format Window

**Syntaxe** : `"Day[HH:MM-HH:MM]"`

**Jours valides** :
- `Monday`, `Tuesday`, `Wednesday`, `Thursday`, `Friday`, `Saturday`, `Sunday`

**Exemples** :
- `"Monday[09:00-17:00]"` : Lundi de 9h à 17h
- `"Friday[13:30-15:45]"` : Vendredi de 13h30 à 15h45
- `"Saturday[00:00-23:59]"` : Samedi toute la journée

---

## 🎯 CAS D'USAGE

### 1. Session US uniquement

```yaml
windows:
  - "Monday[15:30-22:00]"
  - "Tuesday[15:30-22:00]"
  - "Wednesday[15:30-22:00]"
  - "Thursday[15:30-22:00]"
  - "Friday[15:30-22:00]"
```

### 2. Éviter la session asiatique

```yaml
windows:
  - "Monday[09:00-22:00]"
  - "Tuesday[09:00-22:00]"
  - "Wednesday[09:00-22:00]"
  - "Thursday[09:00-22:00]"
  - "Friday[09:00-22:00]"
```

### 3. Overlap EU/US seulement

```yaml
windows:
  - "Monday[15:00-17:00]"
  - "Tuesday[15:00-17:00]"
  - "Wednesday[15:00-17:00]"
  - "Thursday[15:00-17:00]"
  - "Friday[15:00-17:00]"
```

### 4. Éviter les news (ex: mercredi)

```yaml
windows:
  - "Monday[09:00-17:00]"
  - "Tuesday[09:00-17:00]"
  # Pas de Wednesday → évité
  - "Thursday[09:00-17:00]"
  - "Friday[09:00-17:00]"
```

### 5. Week-end trading

```yaml
windows:
  - "Saturday[00:00-23:59]"
  - "Sunday[00:00-23:59]"
```

---

## 📊 IMPACT SUR LES STATS

### Dashboard HTML

Une nouvelle carte apparaît dans le dashboard :

```
┌─────────────────────────┐
│ ⏰ Trading Windows      │
│    15.5h/week (9.2%)    │
│    6 windows            │
└─────────────────────────┘
```

### Console Output

Au lancement du backtest :

```
======================================================================
⏰ TRADING WINDOWS CONFIGURATION
======================================================================
Timezone: Europe/Paris
Total windows: 6
Total hours/week: 15.5h (9.2% of week)

Active windows:
  Monday    : 13:00-16:00, 20:00-22:00
  Tuesday   : 09:00-11:30
  Friday    : 08:00-12:00
======================================================================
```

---

## ⚠️ COMPORTEMENT DÉTAILLÉ

### Scénario 1 : Hors Créneau

```
Heure: Monday 12:00 (hors créneau)
Signal: LONG détecté
Action: ❌ Entrée bloquée
```

### Scénario 2 : Dans Créneau

```
Heure: Monday 14:00 (dans créneau)
Signal: LONG détecté
Action: ✅ Entrée autorisée
```

### Scénario 3 : Position Existante Hors Créneau

```
Heure: Monday 17:00 (hors créneau)
Position: LONG active depuis 14:00
Prix atteint: SL
Action: ✅ SL déclenché (sortie toujours autorisée)
```

### Scénario 4 : Fin de Créneau avec Position

```
Heure: Monday 16:00 (fin de créneau 13:00-16:00)
Position: LONG active depuis 15:00
Action: ✅ Position continue (pas de fermeture forcée)
```

---

## 🔍 VALIDATION

### Au Chargement du Config

Le système valide automatiquement :

✅ **Format valide** : `"Day[HH:MM-HH:MM]"`
✅ **Jour valide** : Lundi à Dimanche
✅ **Heures valides** : 00-23
✅ **Minutes valides** : 00-59
✅ **End > Start** : Heure fin après heure début

### Erreurs Possibles

**Format invalide** :
```
⚠️  Invalid window format: Monday[13-16]
```

**Jour invalide** :
```
⚠️  Invalid day: Lundi
```
(Utiliser noms anglais: Monday, Tuesday, etc.)

**Heure invalide** :
```
⚠️  Invalid start time: 25:00
```

**End avant Start** :
```
⚠️  End time must be after start time: Monday[16:00-13:00]
```

---

## 📈 IMPACT SUR RÉSULTATS

### Avant (sans filtre)

```
Total Trades: 150
Win Rate: 55%
PnL: +2500$
```

### Après (avec filtre sur sessions profitables)

```
Total Trades: 80 (53% des trades éliminés)
Win Rate: 62% (amélioration)
PnL: +2200$ (légèrement moins mais plus efficace)
Profit/Hour: +14.19$/h (amélioration significative)
```

**Avantages** :
- ✅ Win rate amélioré
- ✅ Moins de trades = moins de frais
- ✅ Focus sur créneaux profitables
- ✅ Meilleure efficacité temps/rendement

---

## 🛠️ DEBUGGING

### Test des Windows

Le fichier `trading_windows.py` peut être exécuté seul pour tester :

```bash
python trading_windows.py
```

Cela affiche un résumé et teste quelques dates.

### Vérifier si un Moment est Autorisé

```python
from trading_windows import TradingWindows
from datetime import datetime

config = {
    'enabled': True,
    'timezone': 'Europe/Paris',
    'windows': ['Monday[13:00-16:00]']
}

tw = TradingWindows(config)
dt = datetime(2024, 6, 17, 14, 30)  # Monday 14:30

allowed = tw.is_trading_allowed(dt)
print(f"Trading allowed: {allowed}")  # True
```

---

## 💡 RECOMMANDATIONS

### 1. Analyser d'abord

Avant d'activer les filtres :
1. Lancer un backtest **sans filtre**
2. Regarder la **heatmap Expectancy par heure**
3. Identifier les créneaux **les plus profitables**
4. Configurer les windows sur ces créneaux
5. Relancer le backtest avec filtre

### 2. Éviter les Créneaux Trop Courts

```yaml
# ❌ Éviter
- "Monday[14:00-14:15]"  # Trop court (15min)

# ✅ Préférer
- "Monday[14:00-16:00]"  # 2h minimum
```

### 3. Laisser de la Marge

```yaml
# ❌ Risqué (fin de session)
- "Friday[15:00-21:59]"  # Risque de positions overnight

# ✅ Plus sûr
- "Friday[15:00-20:00]"  # Marge avant clôture
```

### 4. Tester Progressivement

1. Commencer avec `enabled: false`
2. Identifier créneaux profitables
3. Activer `enabled: true` avec 2-3 windows
4. Analyser impact
5. Affiner progressivement

---

## 🔧 EXTENSIONS FUTURES

Ces features pourraient être ajoutées :

### Force Exit on Window Close

```yaml
trading_windows:
  enabled: true
  force_exit_on_window_close: true  # Fermer positions à fin de créneau
```

### Blacklist Dates

```yaml
trading_windows:
  enabled: true
  blacklist_dates:
    - "2024-12-25"  # Noël
    - "2024-01-01"  # Nouvel an
```

### Profiles

```yaml
trading_windows:
  profiles:
    US_SESSION:
      - "Monday[15:30-22:00]"
    ASIAN_SESSION:
      - "Monday[01:00-08:00]"
  active_profile: "US_SESSION"
```

---

## ✅ RÉSUMÉ

**Activation** :
```yaml
trading_windows:
  enabled: true
  timezone: "Europe/Paris"
  windows:
    - "Monday[13:00-16:00]"
```

**Comportement** :
- 🚫 Bloque entrées hors créneau
- ✅ Sorties toujours autorisées
- ✅ Positions continuent hors créneau

**Objectif** :
- 🎯 Focus sur créneaux profitables
- 📈 Améliorer efficacité
- 💰 Réduire drawdown

---

✅ Format compact facile à configurer  
✅ Validation automatique  
✅ Stats dans dashboard  
✅ Compatible avec toutes stratégies  
