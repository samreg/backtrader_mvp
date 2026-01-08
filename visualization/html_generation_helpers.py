"""
HTML Generation Helpers

Helper functions for generate_html_complete.py
"""

import pandas as pd
from pathlib import Path
from typing import List, Dict, Any
from core.indicator_loader import IndicatorLoader
from core.models import IndicatorResult
from visualization.primitive_serializer import PrimitiveSerializer
from data.mt5_loader import ensure_data_file



def load_candles(config: dict) -> pd.DataFrame:
    """
    Load candles DataFrame from data file
    
    Args:
        config: YAML config dict
    
    Returns:
        DataFrame with candles
    """
    from data.mt5_loader import get_data_filename
    
    # Determine data file
    symbol = config['data']['symbol']
    timeframe = config['data']['timeframe']
    use_specific = config['data'].get('use_specific_csv_file', False)
    
    if use_specific:
        data_file = config['data']['file']
    else:
        data_file = f"data/{get_data_filename(symbol, timeframe)}"
    
    print(f"📂 Loading candles: {data_file}")
    
    if not Path(data_file).exists():
        raise FileNotFoundError(f"Data file not found: {data_file}")
    
    df = pd.read_csv(data_file, parse_dates=['datetime'])
    
    # Handle timezone
    if df['datetime'].dt.tz is None:
        df['datetime'] = df['datetime'].dt.tz_localize('Europe/Paris')
    else:
        df['datetime'] = df['datetime'].dt.tz_convert('Europe/Paris')
    
    return df


def build_candles_json(df: pd.DataFrame) -> List[Dict[str, Any]]:
    """
    Convert DataFrame to Lightweight Charts candles format
    
    Args:
        df: Candles DataFrame
    
    Returns:
        List of candle dicts
    """
    candles_data = []
    
    for _, row in df.iterrows():
        candles_data.append({
            'time': int(row['datetime'].timestamp()),
            'open': float(row['open']),
            'high': float(row['high']),
            'low': float(row['low']),
            'close': float(row['close'])
        })
    
    return candles_data


def get_visualization_indicators(config: dict) -> list:
    """Retourne la liste des indicateurs à exécuter pour la visualisation.

    Ordre de priorité:
    1) config['visualization']['indicators'] si présent (format déjà attendu)
    2) config['indicators'] si présent (format déjà attendu: {name, module_file, params, panel?})
    3) fallback minimal (pour ne pas afficher un RSI "en dur" par surprise):
       - bollinger_bands
       - trades_overlay
    """
    def _normalize(items: list) -> list:
        """Ensure each indicator dict has at least: name, module_file, params."""
        out = []
        for it in items or []:
            if not isinstance(it, dict) or 'name' not in it:
                continue
            name = it['name']
            out.append({
                'name': name,
                'module_file': it.get('module_file', f"{name}.py"),
                'params': it.get('params', {}),
                **({k: v for k, v in it.items() if k not in {'name', 'module_file', 'params'}})
            })
        return out

    viz = config.get('visualization', {})
    if isinstance(viz, dict) and 'indicators' in viz:
        indicators = _normalize(viz.get('indicators', []))
    elif 'indicators' in config:
        indicators = _normalize(config.get('indicators', []))
    else:
        # Minimal fallback: no RSI by default.
        indicators = _normalize([
            {'name': 'bollinger_bands', 'params': {'period': 20, 'std_dev': 1.5}},
        ])

    # Full HTML viewer expects trades navigation + boxes → always add trades_overlay if missing.
    if not any(i.get('name') == 'trades_overlay' for i in indicators):
        indicators.append({'name': 'trades_overlay', 'module_file': 'trades_overlay.py', 'params': {}})

    return indicators

def run_indicators(
    df: pd.DataFrame,
    indicators_config: List[Dict[str, Any]]
) -> Dict[str, IndicatorResult]:
    """
    Load and execute all indicators
    
    Args:
        df: Candles DataFrame
        indicators_config: List of indicator configs
    
    Returns:
        Dict mapping indicator name → IndicatorResult
    """
    loader = IndicatorLoader()
    results = {}
    
    print(f"\n🔧 Running {len(indicators_config)} indicators...")
    
    for ind_conf in indicators_config:
        name = ind_conf['name']
        # Support both historical keys: "module" and "module_file"
        module_file = ind_conf.get('module') or ind_conf.get('module_file')
        if not module_file:
            raise KeyError(f"Indicator config missing 'module'/'module_file' for {name}: {ind_conf}")
        params = ind_conf.get('params', {})
        
        print(f"   Loading {name}...", end=" ")
        
        try:
            indicator = loader.load_indicator(
                name=name,
                module_file=module_file,
                params=params
            )
            
            # Rename datetime column to time if needed for compatibility
            df_copy = df.copy()
            if 'datetime' in df_copy.columns and 'time' not in df_copy.columns:
                df_copy['time'] = df_copy['datetime']
            
            results[name] = indicator.calculate(df_copy)
            print("✅")
            
        except Exception as e:
            print(f"❌ Error: {e}")
            # Create empty result
            results[name] = IndicatorResult()
    
    return results


def serialize_indicators(
    candles_data: List[Dict],
    results: Dict[str, IndicatorResult]
) -> Dict[str, Any]:
    """
    Serialize indicator results to JS structures
    
    Args:
        candles_data: Candles JSON list
        results: Dict of indicator results
    
    Returns:
        Dict with all serialized data
    """
    serializer = PrimitiveSerializer(candles_data)
    
    serialized = {}
    
    # Bollinger Bands (support legacy key "bollinger" and new key "bollinger_bands")
    bb_key = 'bollinger_bands' if 'bollinger_bands' in results else ('bollinger' if 'bollinger' in results else None)
    if bb_key:
        serialized['bb_upper'] = serializer.series_to_js(results[bb_key], 'bb_upper')
        serialized['bb_middle'] = serializer.series_to_js(results[bb_key], 'bb_middle')
        serialized['bb_lower'] = serializer.series_to_js(results[bb_key], 'bb_lower')
    else:
        serialized['bb_upper'] = []
        serialized['bb_middle'] = []
        serialized['bb_lower'] = []
    
    # RSI
    if 'rsi' in results:
        serialized['rsi'] = serializer.series_to_js(results['rsi'], 'rsi')
    else:
        serialized['rsi'] = []
    
    # Trades overlay
    if 'trades_overlay' in results:
        serialized['trades_markers'] = serializer.points_to_markers(results['trades_overlay'])
        serialized['rectangles'] = serializer.rectangles_to_js(results['trades_overlay'])
        trades_nav = []
        try:
            trades_nav = getattr(results['trades_overlay'], 'meta', {}).get('trades_navigation', [])
        except Exception:
            trades_nav = []
        serialized['trades_nav'] = trades_nav
    else:
        serialized['trades_markers'] = []
        serialized['rectangles'] = []
        serialized['trades_nav'] = []

    # Generic primitives from any indicator (e.g., equal_high_lows)
    # We merge them into "markers" and "rectangles" for the front-end.
    markers = []
    rectangles = list(serialized.get('rectangles', []))
    # Start with trade markers (if any)
    markers.extend(serialized.get('trades_markers', []))

    for ind_name, ind_result in results.items():
        if ind_name == 'trades_overlay':
            continue
        # Most indicators return IndicatorResult (core/models.py). Some legacy
        # or experimental ones may return a raw list/dict of primitives.
        try:
            if isinstance(ind_result, IndicatorResult):
                markers.extend(serializer.points_to_markers(ind_result))
                rectangles.extend(serializer.rectangles_to_js(ind_result))
                continue

            primitives = None
            if isinstance(ind_result, list):
                primitives = ind_result
            elif isinstance(ind_result, dict) and 'primitives' in ind_result:
                primitives = ind_result.get('primitives')

            if not primitives:
                continue

            # Adapt legacy raw primitives to the new IndicatorResult contract
            tmp = IndicatorResult(name=ind_name, primitives=primitives)
            markers.extend(serializer.points_to_markers(tmp))
            rectangles.extend(serializer.rectangles_to_js(tmp))
        except Exception:
            # If an indicator returns non-primitive data, ignore it here.
            continue

    # Deduplicate markers by (time, position, text, shape)
    seen = set()
    deduped = []
    for m in markers:
        k = (m.get('time'), m.get('position'), m.get('text'), m.get('shape'))
        if k in seen:
            continue
        seen.add(k)
        deduped.append(m)

    serialized['markers'] = deduped
    serialized['rectangles'] = rectangles
    return serialized
