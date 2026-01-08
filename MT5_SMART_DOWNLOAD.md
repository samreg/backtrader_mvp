# 📥 TÉLÉCHARGEMENT INTELLIGENT MT5

## ✅ AMÉLIORATION

Le système de téléchargement MT5 gère maintenant **intelligemment** les cas où l'historique demandé dépasse l'historique disponible.

---

## 🎯 COMPORTEMENT

### Avant ❌

```bash
python download_mt5_data.py --months 20
```

**Résultat** :
```
❌ Pas de données disponibles
   Erreur: MT5 error
```

**Plantage** si la période demandée > historique disponible

---

### Après ✅

```bash
python download_mt5_data.py --months 20
```

**Résultat** :
```
📅 Période demandée:
   De: 2023-05-01 12:00
   À:  2025-01-01 12:00
   (20 mois)

⏳ Téléchargement en cours...
⚠️  Période demandée (20 mois) dépasse l'historique disponible
   Récupération du MAXIMUM disponible...
   Tentative avec 288,000 bougies...
✅ 43,200 chandelles récupérées (MAXIMUM disponible)

📊 Statistiques:
   Chandelles: 43,200
   Première bougie: 2024-10-01 00:00:00
   Dernière bougie:  2025-01-01 11:57:00
   Durée réelle: 92 jours (~3.1 mois)
   Prix min: 19245.50
   Prix max: 21340.75
   Volume total: 1,234,567

⚠️  Note: Historique limité à 3.1 mois
   (demandé: 20 mois, disponible: 3.1 mois)
```

**Pas d'erreur** : récupère le **MAXIMUM** disponible

---

## 🔧 FONCTIONNEMENT

### Étape 1 : Tentative avec période demandée

```python
from_date = now - timedelta(days=months * 30)
rates = mt5.copy_rates_range(symbol, timeframe, from_date, to_date)
```

**Si réussi** → OK ✅

---

### Étape 2 : Fallback intelligent (si échec)

```python
# Calculer nombre de bougies théoriques
timeframe_minutes = 3  # Pour M3
minutes_in_period = months * 30 * 24 * 60
estimated_candles = minutes_in_period / timeframe_minutes

# Récupérer le maximum disponible
rates = mt5.copy_rates_from(symbol, timeframe, to_date, estimated_candles)
```

**Résultat** : Récupère le MAXIMUM disponible (jusqu'à 100k bougies)

---

## 📊 LOGS AMÉLIORÉS

### Informations affichées

1. **Période demandée** :
   ```
   De: 2023-01-01 00:00
   À:  2025-01-01 12:00
   (24 mois)
   ```

2. **Nombre de chandelles** :
   ```
   ✅ 43,200 chandelles récupérées (MAXIMUM disponible)
   ```

3. **Période réelle** :
   ```
   Première bougie: 2024-10-01 00:00:00
   Dernière bougie:  2025-01-01 11:57:00
   Durée réelle: 92 jours (~3.1 mois)
   ```

4. **Avertissement si limité** :
   ```
   ⚠️  Note: Historique limité à 3.1 mois
      (demandé: 20 mois, disponible: 3.1 mois)
   ```

---

## 🎯 CAS D'USAGE

### Récupérer le maximum pour un nouveau symbole

```bash
# Demander 100 mois (on sait que c'est impossible)
python download_mt5_data.py --symbol BTC --timeframe 1min --months 100
```

**Résultat** : Récupère tout l'historique disponible pour BTC

---

### Récupérer le maximum sans connaître la limite

```bash
# Pour un symbole inconnu
python download_mt5_data.py --symbol GOLD --timeframe 5min --months 50
```

**Résultat** : Récupère le maximum disponible, affiche la durée réelle

---

## 📋 TIMEFRAMES SUPPORTÉS

Le système calcule automatiquement le nombre de bougies en fonction du timeframe :

| Timeframe | Minutes | Bougies/jour | Bougies/mois |
|-----------|---------|--------------|--------------|
| M1 | 1 | 1,440 | ~43,200 |
| M3 | 3 | 480 | ~14,400 |
| M5 | 5 | 288 | ~8,640 |
| M15 | 15 | 96 | ~2,880 |
| M30 | 30 | 48 | ~1,440 |
| H1 | 60 | 24 | ~720 |
| H4 | 240 | 6 | ~180 |
| D1 | 1440 | 1 | ~30 |

---

## 💡 EXEMPLES

### NAS100 - Demander 12 mois

```bash
python download_mt5_data.py --symbol NAS100 --timeframe 3min --months 12
```

**Si 12 mois disponibles** :
```
✅ 172,800 chandelles téléchargées
   Durée réelle: 360 jours (~12.0 mois)
```

**Si seulement 3 mois disponibles** :
```
⚠️  Période demandée (12 mois) dépasse l'historique disponible
   Récupération du MAXIMUM disponible...
✅ 43,200 chandelles récupérées (MAXIMUM disponible)
   Durée réelle: 90 jours (~3.0 mois)

⚠️  Note: Historique limité à 3.0 mois
   (demandé: 12 mois, disponible: 3.0 mois)
```

---

### BTC - Récupérer le maximum

```bash
python download_mt5_data.py --symbol BTC --timeframe 1min --months 999
```

**Résultat** :
```
⚠️  Période demandée (999 mois) dépasse l'historique disponible
   Récupération du MAXIMUM disponible...
   Tentative avec 100,000 bougies...
✅ 87,456 chandelles récupérées (MAXIMUM disponible)
   Durée réelle: 60 jours (~2.0 mois)
```

---

## ⚠️ LIMITE MT5

MT5 a une limite de **100,000 bougies** par requête.

Le script limite automatiquement à 100k :
```python
estimated_candles = min(estimated_candles, 100000)
```

---

## 🔍 DEBUGGING

### Vérifier l'historique disponible

```bash
# Demander une période énorme
python download_mt5_data.py --symbol EUR_USD --timeframe 5min --months 500
```

Le script affichera :
- Combien de bougies ont été récupérées
- La date de la première bougie (= début de l'historique)
- La durée réelle en jours et mois

---

## 📝 CODE MODIFIÉ

### Fichier : `download_mt5_data.py`

**Ligne 88-149** : Nouvelle logique de téléchargement

```python
# Essayer d'abord avec la période demandée
rates = mt5.copy_rates_range(symbol, timeframe, from_date_requested, to_date)

if rates is None or len(rates) == 0:
    # Fallback: récupérer le maximum
    estimated_candles = calculate_estimated_candles(months, timeframe)
    rates = mt5.copy_rates_from(symbol, timeframe, to_date, estimated_candles)
```

**Ligne 158-171** : Logs améliorés

```python
# Afficher durée réelle
actual_duration = last_candle - first_candle
actual_months = actual_duration.days / 30.0

print(f"   Durée réelle: {actual_days} jours (~{actual_months:.1f} mois)")

if actual_months < months * 0.8:
    print(f"⚠️  Note: Historique limité à {actual_months:.1f} mois")
```

---

## ✅ RÉSUMÉ

**Avant** :
- ❌ Erreur si période > historique
- ❌ Pas d'info sur la durée réelle
- ❌ Script plante

**Après** :
- ✅ Fallback automatique sur le maximum
- ✅ Logs détaillés (durée réelle, date de début)
- ✅ Avertissement si historique limité
- ✅ Jamais de crash

**Usage** : Demande toujours une grande période (ex: 100 mois) pour récupérer le MAXIMUM disponible ! 🎯
