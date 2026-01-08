#!/usr/bin/env python
"""
Test direct du rendu HTML - bypasse tout le flow
"""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))

from core.models import ZoneObject
from datetime import datetime

print("="*80)
print("🧪 TEST RENDU HTML - ZONES")
print("="*80)
print()

# Créer zones de test
zones = [
    ZoneObject(
        id='test_1',
        t_start=datetime.now(),
        t_end=None,
        low=25200.0,
        high=25210.0,
        type='order_block',
        state='active',
        entry_candle_index=100,
        exit_candle_index=None,
        mitigation_count=0,
        mitigation_score=0.0,
        metadata={'direction': 'bullish'}
    ),
    ZoneObject(
        id='test_2',
        t_start=datetime.now(),
        t_end=datetime.now(),
        low=25220.0,
        high=25230.0,
        type='order_block',
        state='invalidated',
        entry_candle_index=200,
        exit_candle_index=250,
        mitigation_count=3,
        mitigation_score=0.6,
        metadata={'direction': 'bearish'}
    )
]

print(f"Zones créées: {len(zones)}")
print()

# Générer code JavaScript
html_lines = []

for i, zone in enumerate(zones):
    direction = zone.metadata.get('direction', 'unknown')
    color = '#26a69a' if direction == 'bullish' else '#ef5350'
    label = f'OB {direction.capitalize()} [{zone.low:.2f}-{zone.high:.2f}]'
    
    print(f"Zone {i+1}:")
    print(f"  Direction: {direction}")
    print(f"  État: {zone.state}")
    print(f"  Prix: {zone.low:.2f} - {zone.high:.2f}")
    print(f"  Mitigation: {zone.mitigation_count} touches, score {zone.mitigation_score}")
    print()
    
    # Générer JavaScript
    js_top = f"""
    // Zone {i} - Top
    candlestickSeries.createPriceLine({{
        price: {zone.high},
        color: '{color}',
        lineWidth: 2,
        lineStyle: 2,
        axisLabelVisible: true,
        title: '{label}'
    }});
    """
    
    js_bottom = f"""
    // Zone {i} - Bottom
    candlestickSeries.createPriceLine({{
        price: {zone.low},
        color: '{color}',
        lineWidth: 2,
        lineStyle: 2,
        axisLabelVisible: false
    }});
    """
    
    html_lines.append(js_top)
    html_lines.append(js_bottom)

# Sauvegarder HTML test
html_content = '''<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <title>Test Zones</title>
    <script src="https://unpkg.com/lightweight-charts@4.1.0/dist/lightweight-charts.standalone.production.js"></script>
</head>
<body>
    <div id="chart" style="width: 100%; height: 600px;"></div>
    
    <script>
        const chart = LightweightCharts.createChart(document.getElementById('chart'), {
            width: 800,
            height: 600,
            layout: {
                background: { color: '#ffffff' },
                textColor: '#333'
            },
            grid: {
                vertLines: { color: '#f0f0f0' },
                horzLines: { color: '#f0f0f0' }
            }
        });
        
        const candlestickSeries = chart.addCandlestickSeries();
        
        // Données test (NAS100-like)
        const data = [
            { time: '2026-01-03', open: 25180, high: 25220, low: 25170, close: 25200 },
            { time: '2026-01-04', open: 25200, high: 25240, low: 25195, close: 25230 },
            { time: '2026-01-05', open: 25230, high: 25250, low: 25210, close: 25225 },
            { time: '2026-01-06', open: 25225, high: 25235, low: 25190, close: 25205 },
            { time: '2026-01-07', open: 25205, high: 25245, low: 25200, close: 25240 }
        ];
        
        candlestickSeries.setData(data);
        
        // Ajouter zones
''' + '\n'.join(html_lines) + '''
        
        chart.timeScale().fitContent();
    </script>
</body>
</html>
'''

output_file = Path('output/test_zones_simple.html')
output_file.parent.mkdir(exist_ok=True)

with open(output_file, 'w', encoding='utf-8') as f:
    f.write(html_content)

print("="*80)
print(f"✅ HTML généré: {output_file}")
print("="*80)
print()
print("Ouvre ce fichier dans ton navigateur pour voir les zones !")
print()

input("Appuie sur Entrée pour quitter...")
