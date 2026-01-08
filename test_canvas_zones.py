#!/usr/bin/env python3
"""
Test canvas rectangles rendering
"""
import sys
import pandas as pd
import numpy as np
from pathlib import Path

# Add project to path
sys.path.insert(0, str(Path(__file__).parent))

from core.models import ZoneObject
from visualization.chart_viewer import generate_html_content

def create_test_data():
    """Create synthetic test data"""
    print("\n📊 Creating test data...")
    
    # Create synthetic candles
    dates = pd.date_range('2024-01-01', periods=1000, freq='3min')
    prices = 25000 + np.cumsum(np.random.randn(1000) * 10)
    
    df = pd.DataFrame({
        'time': dates,
        'open': prices,
        'high': prices + np.random.rand(1000) * 20,
        'low': prices - np.random.rand(1000) * 20,
        'close': prices + np.random.randn(1000) * 10,
        'volume': np.random.randint(100, 1000, 1000)
    })
    
    # Create test zones
    zones = []
    
    # Zone 1: Bullish active
    zones.append(ZoneObject(
        id='ob_1',
        type='order_block',
        low=25100.0,
        high=25150.0,
        t_start=dates[100],
        t_end=None,
        entry_candle_index=100,
        exit_candle_index=None,
        mitigation_count=0,
        mitigation_score=0.0,
        state='active',
        metadata={'direction': 'bullish'}
    ))
    
    # Zone 2: Bullish mitigated
    zones.append(ZoneObject(
        id='ob_2',
        type='order_block',
        low=25200.0,
        high=25250.0,
        t_start=dates[200],
        t_end=None,
        entry_candle_index=200,
        exit_candle_index=None,
        mitigation_count=2,
        mitigation_score=0.4,
        state='active',
        metadata={'direction': 'bullish'}
    ))
    
    # Zone 3: Bearish ACTIVE (pour tester couleur bordeaux)
    zones.append(ZoneObject(
        id='ob_3',
        type='order_block',
        low=24950.0,
        high=25000.0,
        t_start=dates[300],
        t_end=None,
        entry_candle_index=300,
        exit_candle_index=None,
        mitigation_count=1,
        mitigation_score=0.2,
        state='active',  # ← ACTIVE pour voir la couleur bordeaux
        metadata={'direction': 'bearish'}
    ))
    
    # Zone 4: Bullish heavily mitigated
    zones.append(ZoneObject(
        id='ob_4',
        type='order_block',
        low=25300.0,
        high=25350.0,
        t_start=dates[500],
        t_end=None,
        entry_candle_index=500,
        exit_candle_index=None,
        mitigation_count=5,
        mitigation_score=1.0,
        state='active',
        metadata={'direction': 'bullish'}
    ))
    
    print(f"   ✅ {len(df)} candles")
    print(f"   ✅ {len(zones)} test zones")
    
    return df, zones


if __name__ == "__main__":
    print("\n" + "="*70)
    print("TEST CANVAS ZONES RENDERING")
    print("="*70)
    
    # Create data
    df, zones = create_test_data()
    
    # Create mock indicator result
    class MockResult:
        def __init__(self, zones):
            self.objects = zones
            self.series = {}
            self.metadata = {}
    
    indicator_results = {
        'Order Blocks': MockResult(zones)
    }
    
    # Generate HTML
    print("\n🎨 Generating HTML...")
    
    config = {
        'data': {
            'symbol': 'TEST',
            'main_timeframe': '3min'
        },
        'indicators': [
            {
                'name': 'Order Blocks',
                'panel': 'main',
                'style': {'color': '#26a69a'}
            }
        ]
    }
    
    candles_by_tf = {'3min': df}
    
    html = generate_html_content(
        config=config,
        candles_by_tf=candles_by_tf,
        indicator_results=indicator_results,
        indicators_config=config['indicators']
    )
    
    # Save
    output_file = Path('output/test_canvas_zones.html')
    output_file.parent.mkdir(exist_ok=True)
    output_file.write_text(html, encoding='utf-8')
    
    print(f"\n✅ HTML generated: {output_file}")
    print(f"\n📋 Test zones:")
    for zone in zones:
        print(f"   • {zone.id}: {zone.state}, {zone.metadata.get('direction')}, "
              f"score={zone.mitigation_score:.2f}")
    
    print("\n🌐 Ouvre le fichier dans un navigateur pour voir les rectangles!")
    print("="*70 + "\n")
