# ⏰ TRADING 24h/24 - GUIDE RAPIDE

## 🎯 3 OPTIONS POUR TRADER 24/7

### ✅ OPTION 1: Désactiver (RECOMMANDÉ)

**Config** :
```yaml
strategy:
  trading_windows:
    enabled: false  # Pas de filtre = 24/7
```

**Avantages** :
- ✅ Le plus simple
- ✅ Le plus performant (aucun check)
- ✅ Le plus clair

---

### ✅ OPTION 2: Mode "always"

**Config** :
```yaml
strategy:
  trading_windows:
    enabled: true
    windows: "always"  # Raccourci magique
```

**Console** :
```
⏰ TRADING WINDOWS CONFIGURATION
Mode: 24/7 (Always trading)
Total hours/week: 168.0h (100% of week)
```

**Avantages** :
- ✅ Explicite dans le config
- ✅ Statistiques affichées
- ✅ Compatible avec le système

---

### ⚠️ OPTION 3: Liste complète (NON RECOMMANDÉ)

**Config** :
```yaml
strategy:
  trading_windows:
    enabled: true
    timezone: "Europe/Paris"
    windows:
      - "Monday[00:00-23:59]"
      - "Tuesday[00:00-23:59]"
      - "Wednesday[00:00-23:59]"
      - "Thursday[00:00-23:59]"
      - "Friday[00:00-23:59]"
      - "Saturday[00:00-23:59]"
      - "Sunday[00:00-23:59]"
```

**Inconvénients** :
- ❌ Verbeux
- ❌ Inutilement complexe
- ❌ Moins performant

---

## 📊 COMPARAISON

| Option | Simplicité | Performance | Explicite |
|--------|-----------|-------------|-----------|
| `enabled: false` | ⭐⭐⭐⭐⭐ | ⭐⭐⭐⭐⭐ | ⭐⭐⭐ |
| `windows: "always"` | ⭐⭐⭐⭐ | ⭐⭐⭐⭐ | ⭐⭐⭐⭐⭐ |
| Liste complète | ⭐ | ⭐⭐⭐ | ⭐⭐⭐⭐ |

---

## 💡 RECOMMANDATION

**Pour 99% des cas** : `enabled: false`

**Si tu veux être explicite** : `windows: "always"`

**Jamais** : Liste complète des 7 jours

---

## 🔧 EXEMPLES COMPLETS

### Crypto 24/7

```yaml
# config_crypto_24_7.yaml
data:
  symbol: "BTCUSD"
  timeframe: "5min"

strategy:
  name: "BollingerBreakout"
  
  # Crypto trade 24/7
  trading_windows:
    enabled: false  # Pas de filtre
  
  # ... autres paramètres
```

### Forex 24/5

```yaml
# config_forex_24_5.yaml
data:
  symbol: "EURUSD"
  timeframe: "1min"

strategy:
  name: "BollingerBreakout"
  
  # Forex ferme le week-end
  trading_windows:
    enabled: true
    windows:
      - "Monday[00:00-23:59]"
      - "Tuesday[00:00-23:59]"
      - "Wednesday[00:00-23:59]"
      - "Thursday[00:00-23:59]"
      - "Friday[00:00-23:59]"
  
  # ... autres paramètres
```

### Indices US (sessions spécifiques)

```yaml
# config_nas100_sessions.yaml
data:
  symbol: "NAS100"
  timeframe: "3min"

strategy:
  name: "BollingerBreakout"
  
  # Seulement sessions US
  trading_windows:
    enabled: true
    timezone: "America/New_York"
    windows:
      - "Monday[09:30-16:00]"
      - "Tuesday[09:30-16:00]"
      - "Wednesday[09:30-16:00]"
      - "Thursday[09:30-16:00]"
      - "Friday[09:30-16:00]"
  
  # ... autres paramètres
```

---

## ✅ RÉSUMÉ

**24/7 simplement** :
```yaml
trading_windows:
  enabled: false
```

**24/7 explicite** :
```yaml
trading_windows:
  enabled: true
  windows: "always"
```

C'est tout ! 🎉
