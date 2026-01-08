# 🎨 DASHBOARD DE TEST - GUIDE D'UTILISATION

## 🚀 LANCEMENT RAPIDE

```bash
cd backtrader_mvp
python dashboard.py
```

---

## 📋 MENU PRINCIPAL

Le dashboard affiche un menu interactif :

```
============================================
      🎨 DASHBOARD DE TEST - INDICATEURS
============================================

PRESETS DISPONIBLES
-------------------
1. Test Minimal (EMA seulement)
   • NAS100 M1, 500 bars
   • Indicateurs: EMA(20)

2. Test Order Blocks
   • NAS100 M1, 1000 bars
   • Indicateurs: EMA + Order Blocks

3. Test Structure (BOS/CHOCH)
   • NAS100 M1, 1000 bars
   • Indicateurs: EMA + BOS/CHOCH

4. Test Complet
   • NAS100 M1, 2000 bars
   • Indicateurs: TOUS

5. Historique Complet NAS100 M1 ⭐
   • NAS100 M1, MAXIMUM DISPONIBLE (~100k bars)
   • Indicateurs: EMA + Order Blocks + BOS/CHOCH

6. Mode Interactif
   • Choisis manuellement tous les paramètres

0. Quitter
```

---

## 📊 INDICATEURS DISPONIBLES

### 1. EMA (Exponential Moving Average)
- **Module** : `ema.py`
- **Description** : Moyenne mobile exponentielle
- **Paramètres** :
  - `period`: 20 (défaut)
- **Panel** : main (superposé sur bougies)

### 2. Order Blocks
- **Module** : `order_blocks.py`
- **Description** : Zones de retournement (Smart Money Concepts)
- **Paramètres** :
  - `min_body_size`: 2.0 (taille minimum bougie)
  - `lookback`: 100 (bars à analyser)
  - `max_zones`: 15 (nombre max de zones)
- **Panel** : main

### 3. BOS/CHOCH
- **Module** : `bos_choch.py`
- **Description** : Break of Structure / Change of Character
- **Paramètres** :
  - `swing_length`: 10 (bars pour swing)
  - `min_break_pct`: 0.001 (0.1% minimum break)
- **Panel** : main

### 4. Zone Aggregator
- **Module** : `zone_aggregator.py`
- **Description** : Agrégateur de zones multi-sources
- **Paramètres** :
  - `sources`: Liste des indicateurs sources
- **Panel** : bottom_1 (panel séparé en bas)

---

## 🎯 UTILISATION

### Option 1 : Preset (Recommandé)

Sélectionne un preset (1-5) :

```
Choix (0-6): 5
```

Le dashboard va :
1. ✅ Créer une config YAML
2. ✅ Lancer chart_viewer
3. ✅ Générer `output/chart_viewer.html`

**Ouvre ensuite** `output/chart_viewer.html` dans ton navigateur !

---

### Option 2 : Mode Interactif

Sélectionne 6 pour le mode interactif :

```
Choix (0-6): 6
```

Tu seras guidé étape par étape :

#### Étape 1 : Symbole
```
Symbole (défaut: NAS100): EURUSD
```

#### Étape 2 : Timeframe
```
Timeframes disponibles: M1, M3, M5, M15, M30, H1, H4, D1
Timeframe (défaut: M1): M3
```

#### Étape 3 : Nombre de bars
```
Nombre de bars (défaut: 2000): 5000
```

#### Étape 4 : Indicateurs
```
Indicateurs disponibles:
  1. ema - EMA (Exponential Moving Average)
  2. order_blocks - Order Blocks
  3. bos_choch - BOS/CHOCH
  4. zone_aggregator - Zone Aggregator

Sélectionne les indicateurs (séparés par des virgules, ex: 1,2,3):
Ou tape 'all' pour tous les sélectionner:
> 1,2
```

Le dashboard génère ensuite le chart !

---

## 📁 FICHIERS GÉNÉRÉS

### Configs YAML
Les configs sont sauvegardées dans `configs_test/` :

```
configs_test/
├── test_minimal.yaml
├── test_order_blocks.yaml
├── test_structure.yaml
├── test_complete.yaml
├── test_full_history.yaml
└── custom_20250102_143022.yaml  (mode interactif)
```

### HTML
Le chart est généré dans `output/` :

```
output/
└── chart_viewer.html  ← Ouvre dans navigateur
```

---

## 🎯 PRESET RECOMMANDÉ : HISTORIQUE COMPLET

Le preset #5 est **optimal pour NAS100 M1** :

```
5. Historique Complet NAS100 M1
   • Bars: 100,000 (maximum disponible MT5)
   • ~69 jours de données
   • Indicateurs: EMA + Order Blocks + BOS/CHOCH
```

**Avantages** :
- ✅ Maximum de données historiques
- ✅ Bonne vue d'ensemble
- ✅ Détection patterns long terme
- ✅ Performance correcte (2-3 minutes génération)

---

## ⚙️ PERSONNALISATION

### Modifier les paramètres d'un indicateur

Édite `dashboard.py`, section `AVAILABLE_INDICATORS` :

```python
'order_blocks': {
    'name': 'Order Blocks',
    'module': 'order_blocks.py',
    'description': '...',
    'params': {
        'min_body_size': 5.0,   # ← Change ici
        'lookback': 200,        # ← Change ici
        'max_zones': 20         # ← Change ici
    },
    'panel': 'main',
    'style': {}
}
```

### Ajouter un nouveau preset

Édite `dashboard.py`, fonction `test_preset()` :

```python
presets = {
    'mon_preset': {
        'name': 'Mon Preset Custom',
        'symbol': 'EURUSD',
        'timeframe': 'M5',
        'n_bars': 3000,
        'indicators': ['ema', 'order_blocks']
    }
}
```

---

## 🐛 TROUBLESHOOTING

### Erreur : "Module not found"

**Solution** : Assure-toi d'être dans le bon dossier :
```bash
cd backtrader_mvp
python dashboard.py
```

### Erreur : "MT5 initialize failed"

**Solution** : 
1. Ouvre MetaTrader 5
2. Connecte-toi
3. Relance le dashboard

### Chart vide

**Solution** : 
1. Ouvre la console JavaScript (F12)
2. Vérifie les erreurs
3. Consulte `DEBUGGING_GUIDE.md`

### Symbole invalide

**Solution** : Change le symbole selon ton broker :
- `"NAS100"`
- `"US100"` (certains brokers)
- `"NAS100.cash"`

---

## 📊 EXEMPLE D'UTILISATION

### Scénario : Tester Order Blocks sur NAS100

```bash
python dashboard.py
# Choix: 2 (Test Order Blocks)
# Attend 30-60 secondes
# Ouvre output/chart_viewer.html
```

**Tu verras** :
- Bougies NAS100 M1 (1000 bars)
- EMA bleue
- Zones Order Blocks (rectangles)
- Chart interactif (zoom/pan)

### Scénario : Analyse complète historique

```bash
python dashboard.py
# Choix: 5 (Historique Complet)
# Attend 2-3 minutes (beaucoup de données!)
# Ouvre output/chart_viewer.html
```

**Tu verras** :
- ~100k bougies NAS100 M1
- EMA sur toute la période
- Order Blocks détectés
- BOS/CHOCH segments
- Performance excellent malgré la quantité de données

---

## 🎨 COULEURS DES INDICATEURS

Les indicateurs utilisent des couleurs distinctes :

- **EMA** : Bleu (#2196F3)
- **Order Blocks** : Bleu transparent (bullish) / Rouge transparent (bearish)
- **BOS/CHOCH** : Segments verts (bullish) / rouges (bearish)
- **Zone Aggregator** : Orange (#FF9800)

---

## ✅ CHECKLIST RAPIDE

Avant de lancer :

- [ ] MT5 ouvert et connecté
- [ ] Dans le dossier `backtrader_mvp`
- [ ] Python installé
- [ ] Dépendances installées (`pip install -r requirements.txt`)

Après génération :

- [ ] Fichier `output/chart_viewer.html` créé
- [ ] Ouvrir dans navigateur (Chrome/Firefox/Edge)
- [ ] Vérifier que chart s'affiche
- [ ] Tester zoom/pan
- [ ] Vérifier indicateurs visibles

---

## 🚀 NEXT STEPS

Une fois que tu as testé les indicateurs :

1. **Affine les paramètres** dans les presets
2. **Crée tes propres indicateurs** dans `visualization/indicators/`
3. **Combine plusieurs timeframes** (ajoute H1, H4 dans config)
4. **Crée une stratégie Backtrader** utilisant ces indicateurs

Voir `REFACTORED_DOCUMENTATION.md` pour plus de détails !

---

**Happy Testing! 📊🚀**
