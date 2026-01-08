# 📊 GUIDE DE VISUALISATION

## 🎨 Comment sont affichés les indicateurs

### ✅ SERIES (Lignes)
**Exemples** : EMA, RSI, MACD

**Affichage** : Lignes colorées sur le chart

**Dans le HTML** :
- Panel `main` → Superposé sur bougies (TOP)
- Panel `bottom_1/2/3` → Chart séparé (BOTTOM)

---

### 🟦 ZONES (Order Blocks)
**Affichage** : Lignes horizontales en pointillés

**Couleurs** :
- 🟢 **Vert** (#26a69a) : Zones bullish (support)
- 🔴 **Rouge** (#ef5350) : Zones bearish (resistance)

**Format** :
- Ligne du **haut** : Niveau high de la zone
- Ligne du **bas** : Niveau low de la zone
- Label : `OB Bull 21450.00-21460.00`

**Limitation** : LightweightCharts ne supporte pas les rectangles natifs, donc on utilise des lignes horizontales (price lines).

---

### 📍 SEGMENTS (BOS/CHOCH)
**Affichage** : Marqueurs (flèches, cercles)

**Types de marqueurs** :

#### BOS (Break of Structure)
- 🟢 **Flèche vers le haut** (bullish BOS)
- 🔴 **Flèche vers le bas** (bearish BOS)

#### CHOCH (Change of Character)
- 🟠 **Cercle orange** (changement de tendance)

**Position** :
- BOS bullish → Sous la bougie
- BOS bearish → Au-dessus de la bougie
- CHOCH → Sur la bougie

---

## 🔍 CE QUE TU VOIS DANS LE CHART

### Exemple avec preset #5 (Historique complet)

```
📊 NAS100 - M1

Chart principal:
├─ 🕯️ Bougies (vertes/rouges)
├─ 📈 EMA bleue (ligne continue)
├─ 🟢🔴 Lignes pointillées horizontales (Order Blocks)
│   └─ Paires de lignes : haut/bas de chaque zone
└─ 🎯 Flèches et cercles (BOS/CHOCH)
    ├─ ↑ Flèches vertes (BOS bullish)
    ├─ ↓ Flèches rouges (BOS bearish)
    └─ ⚪ Cercles orange (CHOCH)
```

---

## 📋 LOGS DE GÉNÉRATION

Quand tu lances le dashboard, tu vois :

```
⚙️  Executing indicators...
   Calculating ema_20...
      ✅ 1 series, 0 objects
   Calculating order_blocks...
      ✅ 0 series, 15 objects        ← 15 zones détectées
   Calculating bos_choch...
      ✅ 0 series, 459 objects       ← 459 segments détectés

🎨 Generating HTML...
   ✅ 15 zones rendered as price lines     ← Zones affichées
   ✅ 459 segments rendered as markers     ← Segments affichés
```

**Interprétation** :
- `1 series` = 1 ligne (EMA)
- `15 objects` = 15 zones Order Blocks
- `459 objects` = 459 segments BOS/CHOCH

---

## 🎯 VÉRIFICATIONS DANS LE CHART

Après avoir ouvert `output/chart_viewer.html` :

### 1. EMA (ligne bleue)
- [ ] Ligne bleue visible sur tout le chart
- [ ] Suit les bougies

### 2. Order Blocks (lignes pointillées)
- [ ] Paires de lignes horizontales
- [ ] Vertes (bullish) ou rouges (bearish)
- [ ] Label visible sur la droite (ex: "OB Bull 21450.00-21460.00")

### 3. BOS/CHOCH (marqueurs)
- [ ] Flèches ↑↓ visibles sous/sur les bougies
- [ ] Cercles ⚪ orange pour CHOCH
- [ ] Hover sur marqueur → Affiche le label

### 4. Interactivité
- [ ] Zoom molette souris
- [ ] Pan clic+glisser
- [ ] Crosshair (hover)

---

## 🐛 SI TU NE VOIS PAS LES ZONES/SEGMENTS

### Console JavaScript (F12)

Ouvre la console et cherche :

```javascript
// Vérifier les données
console.log('Zones:', candlestickSeries.priceLines());  // Lignes de prix
console.log('Markers:', candlestickSeries.markers());   // Marqueurs
```

### Problèmes courants

#### Problème 1 : Aucune ligne visible
**Cause** : Zoom trop serré, les lignes sont hors vue

**Solution** :
1. Clic droit sur chart → "Fit Content"
2. Ou scroll molette pour dézoomer

#### Problème 2 : Trop de lignes (chart illisible)
**Cause** : Trop de zones détectées (ex: 50+ zones)

**Solution** : Réduis `max_zones` dans config :
```python
'params': {
    'max_zones': 10  # Au lieu de 15
}
```

#### Problème 3 : Pas de marqueurs BOS/CHOCH
**Cause** : Segments hors de la plage visible

**Solution** : Dézoome ou scroll pour voir d'autres périodes

---

## 🔧 PERSONNALISATION

### Changer couleur des zones

Édite `visualization/chart_viewer.py`, ligne ~415 :

```python
# Zones bullish
color = '#26a69a'  # Vert (défaut)
# Change en:
color = '#4CAF50'  # Vert plus clair

# Zones bearish
color = '#ef5350'  # Rouge (défaut)
# Change en:
color = '#F44336'  # Rouge plus clair
```

### Changer style des lignes

```python
candlestickSeries.createPriceLine({
    price: {zone.high},
    color: '{color}',
    lineWidth: 2,         # Épaisseur (défaut: 1)
    lineStyle: 0,         # 0=Solid, 1=Dotted, 2=Dashed
    axisLabelVisible: true
})
```

### Limiter le nombre de zones affichées

Dans config YAML :

```yaml
indicators:
  - name: order_blocks
    params:
      max_zones: 5  # Seulement 5 zones max
```

---

## 📊 AMÉLIORATION FUTURE

### Canvas Overlay (rectangles complets)

Pour afficher les zones comme de vrais rectangles :

1. Ajouter canvas HTML
2. Dessiner rectangles sur canvas
3. Synchroniser avec chart

**Avantage** : Zones remplies visuellement
**Inconvénient** : Plus complexe

---

## ✅ RÉSUMÉ

| Indicateur | Type | Affichage | Couleur |
|------------|------|-----------|---------|
| **EMA** | Series | Ligne | Bleu |
| **Order Blocks** | Zones | 2 lignes pointillées | Vert/Rouge |
| **BOS** | Segment | Flèche | Vert/Rouge |
| **CHOCH** | Segment | Cercle | Orange |

**Maintenant tu sais comment lire le chart ! 📊✨**
