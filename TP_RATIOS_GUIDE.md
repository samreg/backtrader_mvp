# 📊 CONFIGURATION DES RATIOS TP1/TP2

## ✅ PARAMÈTRES DANS CONFIG YAML

```yaml
strategy:
  tp1_ratio: 0.5    # 50% de la position sortie à TP1
  tp2_ratio: 0.5    # 50% de la position sortie à TP2
```

**Valeurs par défaut** : 0.5 / 0.5 (défini dans `base_strategy.py`)

---

## 🎯 EXEMPLES DE CONFIGURATIONS

### Config 1 : Équilibrée (défaut)
```yaml
tp1_ratio: 0.5  # 50% à TP1
tp2_ratio: 0.5  # 50% à TP2
```
Position 10 contrats : 5 sortis à TP1, 5 à TP2

### Config 2 : Sécuriser plus tôt
```yaml
tp1_ratio: 0.7  # 70% à TP1
tp2_ratio: 0.3  # 30% à TP2
```
Position 10 contrats : 7 sortis à TP1, 3 à TP2

### Config 3 : Maximiser potentiel
```yaml
tp1_ratio: 0.3  # 30% à TP1
tp2_ratio: 0.7  # 70% à TP2
```
Position 10 contrats : 3 sortis à TP1, 7 à TP2

### Config 4 : Sortie complète à TP1
```yaml
tp1_ratio: 1.0  # 100% à TP1
tp2_ratio: 0.0  # TP2 désactivé
```
Position 10 contrats : 10 sortis à TP1

---

## ⚠️ RÈGLES IMPORTANTES

### Règle 1 : Somme = 1.0
```yaml
# ✅ CORRECT
tp1_ratio: 0.5
tp2_ratio: 0.5
# Total: 1.0 (100%)

# ❌ FAUX
tp1_ratio: 0.6
tp2_ratio: 0.6
# Total: 1.2 (120%)
```

### Règle 2 : Valeurs entre 0 et 1
```yaml
# ✅ CORRECT
tp1_ratio: 0.5   # 50%
tp1_ratio: 0.0   # 0% (désactivé)
tp1_ratio: 1.0   # 100%

# ❌ FAUX
tp1_ratio: 50    # Devrait être 0.5
tp1_ratio: 1.5   # > 100%
```

---

## 🧮 EXEMPLE DE CALCUL PnL

**Config** : tp1_ratio: 0.7, tp2_ratio: 0.3

**Trade LONG** :
- Entry : 17000, Size : 10
- TP1 : 17100, TP2 : 17200

```python
# TP1 touché
partial_size = 10 * 0.7 = 7
pnl_tp1 = (17100 - 17000) * 7 = +700

# TP2 touché
remaining_size = 10 * 0.3 = 3
pnl_tp2 = (17200 - 17000) * 3 = +600

# Total
pnl_total = 700 + 600 = +1300
```

---

## 💡 STRATÉGIES PAR PROFIL

### Scalper agressif
```yaml
tp1_ratio: 0.8
tp2_ratio: 0.2
```
Sécurise 80% vite, garde 20% pour runner

### Swing trader
```yaml
tp1_ratio: 0.4
tp2_ratio: 0.6
```
Vise des mouvements plus grands

---

## 📋 CHECKLIST

Avant de lancer un backtest :
- [ ] tp1_ratio + tp2_ratio = 1.0 ?
- [ ] Les deux valeurs entre 0 et 1 ?
- [ ] Cohérent avec ta stratégie ?
- [ ] Break-even enabled si protection après TP1 ?

---

## ✅ RÉSUMÉ

✅ Code utilise `self.p.tp1_ratio` et `self.p.tp2_ratio`  
✅ Pas de valeurs hard-codées  
✅ Complètement configurable via YAML  
✅ Valeurs par défaut : 50/50
