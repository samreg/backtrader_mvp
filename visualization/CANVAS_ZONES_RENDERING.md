# 🎨 RENDU DES ZONES AVEC CANVAS - GUIDE

## 📊 PROBLÈME ACTUEL

**LightweightCharts** ne supporte pas nativement les **rectangles**.

Actuellement on utilise des **price lines** (lignes horizontales) :
- 2 lignes par zone (high + low)
- Pas de remplissage
- Difficile de voir les zones

## ✅ SOLUTION : Canvas Overlay

Dessiner les rectangles sur un **canvas HTML5** superposé au chart.

### Architecture

```
┌─────────────────────────────────┐
│    Canvas (zones rectangles)    │ ← Overlay transparent
├─────────────────────────────────┤
│  LightweightCharts (bougies)    │ ← Chart principal
└─────────────────────────────────┘
```

---

## 🔧 IMPLÉMENTATION

### 1. Structure HTML

```html
<div id="chart-container" style="position: relative;">
    <!-- Chart LightweightCharts -->
    <div id="chart"></div>
    
    <!-- Canvas overlay pour zones -->
    <canvas id="zones-canvas" style="position: absolute; top: 0; left: 0; pointer-events: none;"></canvas>
</div>
```

### 2. Données des Zones

Au lieu de price lines, on passe les données complètes :

```javascript
const zonesData = [
    {
        id: 'ob_1',
        entry_index: 105,      // Index bougie d'entrée
        exit_index: 250,       // Index bougie de sortie (ou null)
        price_low: 21445.50,
        price_high: 21450.25,
        color: '#26a69a',      // Vert (bullish)
        alpha: 0.2,            // Transparence
        direction: 'bullish'
    },
    {
        id: 'ob_2',
        entry_index: 180,
        exit_index: null,      // Actif jusqu'à la fin
        price_low: 21455.00,
        price_high: 21460.50,
        color: '#ef5350',      // Rouge (bearish)
        alpha: 0.2,
        direction: 'bearish'
    }
];
```

### 3. Fonction de Dessin

```javascript
function drawZones(chart, series, zonesData) {
    const canvas = document.getElementById('zones-canvas');
    const ctx = canvas.getContext('2d');
    
    // Synchroniser taille canvas avec chart
    canvas.width = chart.clientWidth;
    canvas.height = chart.clientHeight;
    
    // Effacer canvas
    ctx.clearRect(0, 0, canvas.width, canvas.height);
    
    // Dessiner chaque zone
    zonesData.forEach(zone => {
        // Convertir index bougie → coordonnées pixel (X)
        const entryX = getXCoordinateForIndex(zone.entry_index);
        const exitX = zone.exit_index ? getXCoordinateForIndex(zone.exit_index) : canvas.width;
        
        // Convertir prix → coordonnées pixel (Y)
        const highY = series.priceToCoordinate(zone.price_high);
        const lowY = series.priceToCoordinate(zone.price_low);
        
        // Dessiner rectangle
        ctx.fillStyle = hexToRgba(zone.color, zone.alpha);
        ctx.fillRect(entryX, highY, exitX - entryX, lowY - highY);
        
        // Bordure (optionnel)
        ctx.strokeStyle = zone.color;
        ctx.lineWidth = 1;
        ctx.strokeRect(entryX, highY, exitX - entryX, lowY - highY);
    });
}

// Redessiner lors du zoom/pan
chart.timeScale().subscribeVisibleLogicalRangeChange(() => {
    drawZones(chart, candlestickSeries, zonesData);
});
```

### 4. Helpers

```javascript
function getXCoordinateForIndex(index) {
    // Convertir index de bougie en coordonnée X pixel
    const timeScale = chart.timeScale();
    const candle = candlesData[index];
    return timeScale.timeToCoordinate(candle.time);
}

function hexToRgba(hex, alpha) {
    const r = parseInt(hex.slice(1, 3), 16);
    const g = parseInt(hex.slice(3, 5), 16);
    const b = parseInt(hex.slice(5, 7), 16);
    return `rgba(${r}, ${g}, ${b}, ${alpha})`;
}
```

---

## 📐 EXEMPLE COMPLET

### Zone Active (entry → fin chart)

```
Canvas:
  ┌──────────────────────────────┐
  │                              │
  │  entry_index=105             │ ← x1
  │     ↓                        │
  │     ╔═══════════════════════╗│ ← price_high
  │     ║   Zone OB Bullish     ║│
  │     ║   (vert, alpha 0.2)   ║│
  │     ╚═══════════════════════╝│ ← price_low
  │                        ↑     │
  │                   canvas.width (x2)
  └──────────────────────────────┘
```

### Zone Mitigée (entry → exit)

```
Canvas:
  ┌──────────────────────────────┐
  │                              │
  │  entry_index=80  exit_index=150
  │     ↓               ↓        │
  │     ╔══════════════╗         │
  │     ║ Zone mitigée ║         │
  │     ║ (gris, alpha║         │
  │     ║    0.1)      ║         │
  │     ╚══════════════╝         │
  │                              │
  └──────────────────────────────┘
```

---

## 🎨 COULEURS ET STYLES

### Zones Actives

```javascript
{
    bullish: { color: '#26a69a', alpha: 0.2 },  // Vert
    bearish: { color: '#ef5350', alpha: 0.2 }   // Rouge
}
```

### Zones Mitigées

```javascript
{
    mitigated: { color: '#9E9E9E', alpha: 0.1 }  // Gris
}
```

---

## 🚀 AVANTAGES

✅ **Rectangles complets** (pas juste des lignes)
✅ **Transparence** (alpha channel)
✅ **Performance** (Canvas 2D rapide)
✅ **Synchronisation** avec zoom/pan
✅ **Couleurs personnalisables**

---

## ⚠️ LIMITATIONS

❌ **Pas d'interaction** (pointer-events: none)
❌ **Redessiner à chaque zoom/pan**
❌ **Plus complexe** que price lines

---

## 📝 À IMPLÉMENTER

### Phase 1 : Basique
- [x] Modèle ZoneObject avec entry/exit indices
- [ ] Génération JSON des zones
- [ ] Canvas overlay HTML
- [ ] Fonction drawZones()
- [ ] Event listeners (zoom/pan)

### Phase 2 : Avancé
- [ ] Tooltips au hover
- [ ] Toggle visibility
- [ ] Filtrer par type/état
- [ ] Animations (fade in/out)

---

## 🧪 TEST

Script de test minimal :

```html
<!DOCTYPE html>
<html>
<head>
    <script src="https://unpkg.com/lightweight-charts@4.1.0/dist/lightweight-charts.standalone.production.js"></script>
</head>
<body>
    <div id="chart-container" style="position: relative; width: 800px; height: 400px;">
        <div id="chart"></div>
        <canvas id="zones-canvas" style="position: absolute; top: 0; left: 0; pointer-events: none;"></canvas>
    </div>
    
    <script>
        // Créer chart
        const chart = LightweightCharts.createChart(document.getElementById('chart'), {
            width: 800,
            height: 400
        });
        
        const candlestickSeries = chart.addCandlestickSeries();
        
        // Données test
        const candlesData = [/* ... */];
        candlestickSeries.setData(candlesData);
        
        const zonesData = [
            {
                entry_index: 10,
                exit_index: 50,
                price_low: 100,
                price_high: 105,
                color: '#26a69a',
                alpha: 0.2
            }
        ];
        
        // Dessiner zones
        drawZones(chart, candlestickSeries, zonesData);
    </script>
</body>
</html>
```

---

**Cette approche donnera un rendu professionnel ! 🎨✨**
