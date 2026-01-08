#!/usr/bin/env python
"""
Script de test rapide pour débugger chart_viewer
"""
import sys
from pathlib import Path

# Add project root
sys.path.insert(0, str(Path(__file__).parent))

print("="*80)
print("🐛 DEBUG CHART VIEWER")
print("="*80)

# Test 1: Imports
print("\n1️⃣ Testing imports...")
try:
    from core.models import ZoneObject, SegmentObject, IndicatorResult
    print("  ✅ core.models OK")
except Exception as e:
    print(f"  ❌ core.models FAILED: {e}")
    sys.exit(1)

try:
    from core.indicator_loader import IndicatorLoader
    print("  ✅ core.indicator_loader OK")
except Exception as e:
    print(f"  ❌ core.indicator_loader FAILED: {e}")
    sys.exit(1)

try:
    from data.mt5_loader import load_candles_from_config
    print("  ✅ data.mt5_loader OK")
except Exception as e:
    print(f"  ❌ data.mt5_loader FAILED: {e}")
    sys.exit(1)

# Test 2: Load config
print("\n2️⃣ Loading test config...")
import yaml
try:
    with open('tests/configs/test_minimal.yaml', 'r') as f:
        config = yaml.safe_load(f)
    print(f"  ✅ Config loaded")
    print(f"     Symbol: {config['data']['symbol']}")
    print(f"     TF: {config['data']['main_timeframe']}")
    print(f"     Bars: {config['data']['n_bars']}")
except Exception as e:
    print(f"  ❌ Config FAILED: {e}")
    sys.exit(1)

# Test 3: Load candles
print("\n3️⃣ Loading candles from MT5...")
try:
    candles_by_tf = load_candles_from_config(config)
    main_tf = config['data']['main_timeframe']
    main_candles = candles_by_tf[main_tf]
    print(f"  ✅ Candles loaded: {len(main_candles)} bars")
    print(f"     First: {main_candles.iloc[0]['time']}")
    print(f"     Last: {main_candles.iloc[-1]['time']}")
    print(f"     Columns: {list(main_candles.columns)}")
except Exception as e:
    print(f"  ❌ Candles FAILED: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)

# Test 4: Load indicators
print("\n4️⃣ Loading indicators...")
try:
    loader = IndicatorLoader()
    indicators = {}
    
    for ind_config in config.get('indicators', []):
        ind_name = ind_config['name']
        ind_module = ind_config['module']
        ind_tf = ind_config.get('timeframe', main_tf)
        ind_params = ind_config.get('params', {})
        
        print(f"  Loading {ind_name}...")
        indicator = loader.load_indicator(
            name=ind_name,
            module_file=ind_module,
            params=ind_params,
            timeframe=ind_tf
        )
        indicators[ind_name] = indicator
        print(f"    ✅ {ind_name} loaded")
except Exception as e:
    print(f"  ❌ Indicators FAILED: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)

# Test 5: Execute indicators
print("\n5️⃣ Executing indicators...")
try:
    indicator_results = {}
    
    for ind_config in config.get('indicators', []):
        ind_name = ind_config['name']
        indicator = indicators[ind_name]
        ind_tf = ind_config.get('timeframe', main_tf)
        
        print(f"  Calculating {ind_name}...")
        candles = candles_by_tf[ind_tf].copy()
        result = indicator.calculate(candles)
        indicator_results[ind_name] = result
        
        print(f"    ✅ {ind_name} calculated")
        print(f"       Series: {list(result.series.keys())}")
        print(f"       Objects: {len(result.objects)}")
        
        # Check series data
        for series_name, series_data in result.series.items():
            non_na = series_data.notna().sum()
            print(f"       {series_name}: {non_na}/{len(series_data)} non-NA values")
            if non_na > 0:
                print(f"         First value: {series_data[series_data.notna()].iloc[0]:.5f}")
except Exception as e:
    print(f"  ❌ Execution FAILED: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)

# Test 6: Generate HTML snippet
print("\n6️⃣ Testing HTML generation...")
try:
    import json
    
    # Convert candles
    candles_data = []
    for _, row in main_candles.iterrows():
        timestamp = int(row['time'].timestamp())
        candles_data.append({
            'time': timestamp,
            'open': float(row['open']),
            'high': float(row['high']),
            'low': float(row['low']),
            'close': float(row['close'])
        })
    
    print(f"  Candles data: {len(candles_data)} items")
    print(f"  First candle: {candles_data[0]}")
    
    # Test JSON serialization
    json_str = json.dumps(candles_data)
    print(f"  JSON length: {len(json_str)} chars")
    print(f"  ✅ JSON serialization OK")
    
except Exception as e:
    print(f"  ❌ HTML generation FAILED: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)

print("\n" + "="*80)
print("✅ ALL DEBUG TESTS PASSED")
print("="*80)
print("\nIf chart_viewer.html is empty or broken, the issue is in generate_html_content()")
print("Try running: python visualization/chart_viewer.py tests/configs/test_minimal.yaml")
