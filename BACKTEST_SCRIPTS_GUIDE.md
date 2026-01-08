# 📋 GUIDE DES SCRIPTS DE BACKTEST

## 🎯 3 SCRIPTS DISPONIBLES

Tu as **3 façons** de lancer un backtest. Voici les différences :

---

## 1. `main_backtest_generic.py` ⭐ RECOMMANDÉ

**Usage** :
```bash
python main_backtest_generic.py config_bollinger_windows.yaml
```

**Caractéristiques** :
- ✅ Script principal du projet
- ✅ Lit les CSV existants (dans `data/`)
- ✅ Supporte `start_date` et `end_date` pour filtrer
- ✅ Génère automatiquement le HTML complet
- ✅ Compatible avec Trading Windows
- ✅ Utilisé dans tous les exemples du projet

**Config attendu** :
```yaml
data:
  symbol: "NAS100"
  timeframe: "3min"
  use_specific_csv_file: true
  file: "data/NAS100_3min.csv"
  start_date: "2024-01-01"  # Optionnel
  end_date: "2024-12-31"    # Optionnel
```

---

## 2. `run_backtest.py` 🔌 AVEC MT5

**Usage** :
```bash
python run_backtest.py config_bollinger_24_7.yaml
```

**Caractéristiques** :
- 🔌 Se connecte à MetaTrader 5
- 📥 Télécharge les données automatiquement
- ⏱️ Utilise `months` pour définir l'historique
- ⚠️ Nécessite MT5 installé et configuré
- ⚠️ Nécessite connexion broker

**Config attendu** :
```yaml
data:
  symbol: "NAS100"
  timeframe: "3min"
  months: 12  # ← OBLIGATOIRE pour run_backtest.py
```

**Avantages** :
- Pas besoin de CSV pré-existants
- Données toujours à jour

**Inconvénients** :
- Nécessite MT5
- Plus lent (téléchargement)
- Dépend de la connexion broker

---

## 3. `test_bollinger.py` 🧪 DEBUG

**Usage** :
```bash
python test_bollinger.py
```

**Caractéristiques** :
- 🧪 Script de test rapide
- 🔧 Paramètres en dur dans le code
- ⚡ Pour tests et debugging rapides
- ❌ Pas de config YAML

**Quand l'utiliser** :
- Tests rapides d'une modification
- Debugging d'une stratégie
- Prototypage

---

## 📊 COMPARAISON

| Script | Source Données | Config | MT5 Requis | HTML Auto | Recommandé |
|--------|---------------|--------|------------|-----------|------------|
| `main_backtest_generic.py` | CSV local | YAML | ❌ Non | ✅ Oui | ⭐⭐⭐⭐⭐ |
| `run_backtest.py` | MT5 download | YAML | ✅ Oui | ❌ Non | ⭐⭐⭐ |
| `test_bollinger.py` | CSV local | Hard-coded | ❌ Non | ❌ Non | ⭐⭐ |

---

## 🎯 QUEL SCRIPT UTILISER ?

### Cas 1 : Backtest normal (RECOMMANDÉ)
```bash
python main_backtest_generic.py config_bollinger_windows.yaml
```
✅ Utilise CSV existant  
✅ Génère HTML automatiquement  
✅ Supporte Trading Windows  

### Cas 2 : Besoin de données fraîches MT5
```bash
python run_backtest.py config_bollinger_24_7.yaml
```
🔌 Télécharge depuis MT5  
⚠️ Nécessite MT5 configuré  

Puis générer HTML manuellement :
```bash
python generate_html_complete.py
```

### Cas 3 : Test rapide
```bash
python test_bollinger.py
```
🧪 Pour debugging uniquement  

---

## 🔧 CONFIGURATION PAR SCRIPT

### Pour `main_backtest_generic.py`

```yaml
data:
  symbol: "NAS100"
  timeframe: "3min"
  use_specific_csv_file: true
  file: "data/NAS100_3min.csv"
  start_date: "2024-01-01"  # Optionnel
  end_date: "2024-12-31"    # Optionnel
```

### Pour `run_backtest.py`

```yaml
data:
  symbol: "NAS100"
  timeframe: "3min"
  months: 12  # OBLIGATOIRE - nombre de mois
  # start_date et end_date ignorés
```

### Pour `test_bollinger.py`

Pas de config YAML - tout est dans le code :
```python
# Modifier directement dans le fichier
data_file = 'data/NAS100_3min.csv'
start_date = '2024-01-01'
```

---

## ⚠️ ERREURS COMMUNES

### `KeyError: 'months'`

```
Traceback: months = config['data']['months']
KeyError: 'months'
```

**Cause** : Tu utilises `run_backtest.py` avec un config fait pour `main_backtest_generic.py`

**Solution** : Ajoute `months` dans le config :
```yaml
data:
  months: 12
```

### `FileNotFoundError: NAS100_3min.csv`

**Cause** : Tu utilises `main_backtest_generic.py` mais le CSV n'existe pas

**Solutions** :
1. Utilise `run_backtest.py` pour télécharger les données
2. Copie ton CSV dans `data/`
3. Change le chemin dans le config

---

## 📁 STRUCTURE PROJET

```
backtrader_mvp/
├── main_backtest_generic.py  ← Script principal (RECOMMANDÉ)
├── run_backtest.py            ← Script avec MT5
├── test_bollinger.py          ← Script de test
├── generate_html_complete.py  ← Génération HTML
├── data/
│   └── NAS100_3min.csv        ← Données CSV
├── output/
│   ├── trades_backtest.csv
│   ├── boxes_backtest.csv
│   └── backtest_complete.html
└── configs/
    ├── config_bollinger_windows.yaml  ← Pour main_backtest_generic.py
    └── config_bollinger_24_7.yaml     ← Pour run_backtest.py
```

---

## 🚀 WORKFLOW RECOMMANDÉ

### Workflow A : Sans MT5 (SIMPLE)

1. Avoir un CSV dans `data/`
2. Créer config YAML (avec `start_date`/`end_date`)
3. Lancer :
   ```bash
   python main_backtest_generic.py config.yaml
   ```
4. Ouvrir `output/backtest_complete.html`

### Workflow B : Avec MT5 (AVANCÉ)

1. Configurer MT5
2. Créer config YAML (avec `months`)
3. Lancer :
   ```bash
   python run_backtest.py config.yaml
   ```
4. Générer HTML :
   ```bash
   python generate_html_complete.py
   ```
5. Ouvrir `output/backtest_complete.html`

---

## 💡 RECOMMANDATION

**Pour 90% des cas** : Utilise `main_backtest_generic.py`

**Avantages** :
- ✅ Pas besoin de MT5
- ✅ Plus rapide (pas de téléchargement)
- ✅ HTML automatique
- ✅ Reproductible (même CSV = mêmes résultats)

**Tu as déjà un CSV ?** → `main_backtest_generic.py`

**Tu n'as pas de CSV ?** → Utilise `run_backtest.py` une fois pour télécharger, puis passe à `main_backtest_generic.py`

---

## ✅ CHECKLIST

Avant de lancer un backtest :

- [ ] Quel script j'utilise ? (`main_backtest_generic.py` ou `run_backtest.py`)
- [ ] Mon config a les bons champs ? (`start_date/end_date` VS `months`)
- [ ] J'ai les données ? (CSV dans `data/` OU MT5 configuré)
- [ ] Trading Windows configuré ? (optionnel)

---

✅ `main_backtest_generic.py` : Script principal recommandé  
✅ `run_backtest.py` : Pour télécharger données MT5  
✅ Configs différents selon le script  
✅ Trading Windows compatible avec les deux  
