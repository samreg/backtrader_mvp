#!/usr/bin/env python3
"""
Test canvas segments rendering (CHOCH/BOS/MSS)
"""
import sys
import pandas as pd
import numpy as np
from pathlib import Path

# Add project to path
sys.path.insert(0, str(Path(__file__).parent))

from core.models import SegmentObject
from visualization.chart_viewer import generate_html_content

def create_test_data():
    """Create synthetic test data with segments"""
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
    
    # Create test segments
    segments = []
    
    # Segment 1: BOS Bullish (Break of Structure)
    # Cassure d'un swing high à 25200
    segments.append(SegmentObject(
        id='bos_1',
        type='bos',
        t_start=dates[150],      # Swing high
        t_end=dates[200],        # Point de cassure
        y_start=25200.0,         # Prix du swing
        y_end=25200.0,           # ← MÊME PRIX = ligne horizontale
        label='BOS BULLISH',
        metadata={
            'direction': 'bullish',
            'structure_type': 'BOS',
            'swing_type': 'high',
            'swing_price': 25200.0,
            'break_validation': 'wick',
            'strength': 0.8
        }
    ))
    
    # Segment 2: CHOCH Bearish (Change of Character)
    # Cassure d'un swing low à 24900
    segments.append(SegmentObject(
        id='choch_1',
        type='choch',
        t_start=dates[300],
        t_end=dates[350],
        y_start=24900.0,
        y_end=24900.0,           # ← Ligne horizontale
        label='CHOCH BEARISH',
        metadata={
            'direction': 'bearish',
            'structure_type': 'CHOCH',
            'swing_type': 'low',
            'swing_price': 24900.0,
            'break_validation': 'close',
            'strength': 0.6
        }
    ))
    
    # Segment 3: MSS Bullish (Market Structure Shift)
    # Cassure d'un swing high à 25300
    segments.append(SegmentObject(
        id='mss_1',
        type='mss',
        t_start=dates[500],
        t_end=dates[550],
        y_start=25300.0,
        y_end=25300.0,           # ← Ligne horizontale
        label='MSS BULLISH',
        metadata={
            'direction': 'bullish',
            'structure_type': 'MSS',
            'swing_type': 'high',
            'swing_price': 25300.0,
            'break_validation': 'wick',
            'strength': 0.9
        }
    ))
    
    # Segment 4: BOS Bearish
    # Cassure d'un swing low à 24800
    segments.append(SegmentObject(
        id='bos_2',
        type='bos',
        t_start=dates[700],
        t_end=dates[750],
        y_start=24800.0,
        y_end=24800.0,           # ← Ligne horizontale
        label='BOS BEARISH',
        metadata={
            'direction': 'bearish',
            'structure_type': 'BOS',
            'swing_type': 'low',
            'swing_price': 24800.0,
            'break_validation': 'close',
            'strength': 0.7
        }
    ))
    
    # Segment 5: Ligne horizontale (support/resistance)
    segments.append(SegmentObject(
        id='support_1',
        type='support',
        t_start=dates[100],
        t_end=dates[800],
        y_start=25000.0,
        y_end=25000.0,           # ← Ligne horizontale
        label='SUPPORT',
        metadata={
            'direction': 'neutral',
            'structure_type': 'SUPPORT',
            'strength': 0.5
        }
    ))
    
    print(f"   ✅ {len(df)} candles")
    print(f"   ✅ {len(segments)} test segments")
    
    return df, segments


if __name__ == "__main__":
    print("\n" + "="*70)
    print("TEST CANVAS SEGMENTS RENDERING (CHOCH/BOS/MSS)")
    print("="*70)
    
    # Create data
    df, segments = create_test_data()
    
    # Create mock indicator result
    class MockResult:
        def __init__(self, segments):
            self.objects = segments
            self.series = {}
            self.metadata = {}
    
    indicator_results = {
        'BOS/CHOCH': MockResult(segments)
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
                'name': 'BOS/CHOCH',
                'panel': 'main',
                'style': {'color': '#4dd0e1'}
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
    output_file = Path('output/test_canvas_segments.html')
    output_file.parent.mkdir(exist_ok=True)
    output_file.write_text(html, encoding='utf-8')
    
    print(f"\n✅ HTML generated: {output_file}")
    print(f"\n📋 Test segments:")
    for seg in segments:
        print(f"   • {seg.id}: {seg.type}, "
              f"{seg.metadata.get('direction')}, "
              f"{seg.metadata.get('structure_type')}, "
              f"strength={seg.metadata.get('strength'):.1f}")
    
    print("\n🌐 Ouvre le fichier dans un navigateur pour voir les segments!")
    print("="*70 + "\n")
