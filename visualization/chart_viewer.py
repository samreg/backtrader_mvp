"""
Chart Viewer - Refactored Version

Displays candles and indicators using LightweightCharts.
Loads configuration from YAML, fetches data from MT5, and dynamically loads indicators.

Usage:
    python visualization/chart_viewer.py config_chart_viewer.yaml
"""

import sys
import yaml
import json
from pathlib import Path
from datetime import datetime
import pandas as pd

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

try:
    from data.mt5_loader import load_candles_from_config
except ImportError:
    load_candles_from_config = None  # Optional for testing

from core.indicator_loader import IndicatorLoader
from core.models import ZoneObject, SegmentObject


def generate_chart_html(config_file: str):
    """
    Generate interactive chart HTML from config
    
    Args:
        config_file: Path to YAML config file
    """
    print("\n" + "="*80)
    print("📊 CHART VIEWER - REFACTORED")
    print("="*80 + "\n")
    
    # 1. Load config
    print("📄 Loading config...")
    with open(config_file, 'r', encoding='utf-8') as f:
        config = yaml.safe_load(f)
    
    symbol = config['data']['symbol']
    data_cfg = config.get('data', {})
    main_tf = data_cfg.get('main_timeframe') or data_cfg.get('timeframe')
    if not main_tf:
        raise KeyError("Config data.main_timeframe (ou data.timeframe) manquant")

    print(f"   Symbol: {symbol}")
    print(f"   Main TF: {main_tf}")
    n_bars = config['data'].get('n_bars', 'N/A')
    print(f"   Bars: {n_bars}")
    
    # 2. Load candles from MT5
    print("\n📥 Loading candles from MT5...")
    candles_by_tf = load_candles_from_config(config)
    
    # 3. Load indicators
    print("\n📊 Loading indicators...")
    loader = IndicatorLoader()
    indicators = {}
    indicator_results = {}
    
    for ind_config in config.get('indicators', []):
        ind_name = ind_config['name']
        ind_module = ind_config['module']
        ind_tf = ind_config.get('timeframe', main_tf)
        ind_params = ind_config.get('params', {})
        
        print(f"   Loading {ind_name} ({ind_module}, TF={ind_tf})...")
        
        try:
            indicator = loader.load_indicator(
                name=ind_name,
                module_file=ind_module,
                params=ind_params,
                timeframe=ind_tf
            )
            indicators[ind_name] = indicator
            print(f"      ✅ Loaded")
        except Exception as e:
            print(f"      ❌ Error: {e}")
            continue
    
    # 4. Set source indicators for aggregators
    print("\n🔗 Setting up aggregators...")
    for ind_config in config.get('indicators', []):
        ind_name = ind_config['name']
        if ind_name not in indicators:
            continue
        
        indicator = indicators[ind_name]
        
        # Check if it's an aggregator (has set_source_indicators method)
        if hasattr(indicator, 'set_source_indicators'):
            indicator.set_source_indicators(indicators)
            print(f"   ✅ {ind_name} linked to sources")
    
    # 5. Execute indicators
    print("\n⚙️  Executing indicators...")
    for ind_config in config.get('indicators', []):
        ind_name = ind_config['name']
        if ind_name not in indicators:
            continue
        
        indicator = indicators[ind_name]
        ind_tf = ind_config.get('timeframe', main_tf)
        
        print(f"   Calculating {ind_name}...")
        
        try:
            # Get candles for this TF
            candles = candles_by_tf[ind_tf].copy()
            
            # Execute
            result = indicator.calculate(candles)
            indicator_results[ind_name] = result
            
            print(f"      ✅ {len(result.series)} series, {len(result.objects)} objects")
        except Exception as e:
            print(f"      ❌ Error: {e}")
            import traceback
            traceback.print_exc()
            continue
    
    # 6. Generate HTML
    print("\n🎨 Generating HTML...")
    html = generate_html_content(
        config=config,
        candles_by_tf=candles_by_tf,
        indicator_results=indicator_results,
        indicators_config=config.get('indicators', [])
    )
    
    # 7. Save HTML
    output_file = Path('output/chart_viewer.html')
    output_file.parent.mkdir(exist_ok=True)
    output_file.write_text(html, encoding='utf-8')
    
    print(f"\n✅ HTML generated: {output_file}")
    print(f"🌐 Open in browser to view!\n")


def generate_html_content(config, candles_by_tf, indicator_results, indicators_config):
    """Generate HTML content with LightweightCharts"""
    
    symbol = config['data']['symbol']
    data_cfg = config.get('data', {})
    main_tf = data_cfg.get('main_timeframe') or data_cfg.get('timeframe')
    if not main_tf:
        raise KeyError("Config data.main_timeframe (ou data.timeframe) manquant")

    # Get main TF candles
    main_candles = candles_by_tf[main_tf]
    
    # Convert candles to JS format
    candles_data = []

    print("main_candles columns:", main_candles.columns.tolist())
    print("main_candles index type:", type(main_candles.index))

    for idx, row in main_candles.iterrows():
        # Support ancien format (colonne 'time')
        if 'time' in row.index:
            dt = row['time']
        # Support nouveau format (colonne 'datetime')
        elif 'datetime' in row.index:
            dt = row['datetime']
        # Support format recommandé (datetime dans l’index)
        else:
            dt = idx

        dt = pd.to_datetime(dt)
        timestamp = int(dt.timestamp())

        candles_data.append({
            'time': timestamp,
            'open': float(row['open']),
            'high': float(row['high']),
            'low': float(row['low']),
            'close': float(row['close'])
        })

    # Organize indicators by panel
    panels = {'main': [], 'bottom_1': [], 'bottom_2': [], 'bottom_3': []}
    
    for ind_config in indicators_config:
        ind_name = ind_config['name']
        panel = ind_config.get('panel', 'main')
        
        if ind_name not in indicator_results:
            continue
        
        if panel not in panels:
            panels[panel] = []
        
        panels[panel].append({
            'name': ind_name,
            'config': ind_config,
            'result': indicator_results[ind_name]
        })
    
    # Collect all zones and segments
    all_zones = []
    all_segments = []
    
    for ind_name, result in indicator_results.items():
        print(f"   📦 {ind_name}: {len(result.objects)} objects")
        for obj in result.objects:
            if isinstance(obj, ZoneObject):
                all_zones.append(obj)
                print(f"      → Zone {obj.id}: {obj.state}, low={obj.low:.2f}, high={obj.high:.2f}")
            elif isinstance(obj, SegmentObject):
                all_segments.append(obj)
    
    print(f"   📊 Total zones collected: {len(all_zones)}")
    print(f"   📊 Total segments collected: {len(all_segments)}")
    
    # Filter zones if configured
    display_config = config.get('display', {})
    show_inactive = display_config.get('show_inactive_zones', True)
    
    if not show_inactive:
        active_count = len([z for z in all_zones if z.state == 'active'])
        print(f"   ⚠️  Filtering inactive zones: {len(all_zones)} → {active_count}")
        all_zones = [z for z in all_zones if z.state == 'active']
    
    print(f"   ✅ Zones to render: {len(all_zones)}")
    print(f"   ✅ Segments to render: {len(all_segments)}")
    
    # Generate HTML
    html = f'''<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Chart Viewer - {symbol} {main_tf}</title>
    <script src="https://unpkg.com/lightweight-charts@4.1.0/dist/lightweight-charts.standalone.production.js"></script>
    <style>
        * {{
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }}
        
        body {{
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
            background: #0d1117;
            color: #e6edf3;
            padding: 20px;
        }}
        
        .header {{
            text-align: center;
            margin-bottom: 20px;
            padding: 20px;
            background: linear-gradient(135deg, #1a1d29 0%, #2a2e39 100%);
            border-radius: 12px;
        }}
        
        .header h1 {{
            font-size: 28px;
            background: linear-gradient(135deg, #26a69a 0%, #4dd0e1 100%);
            -webkit-background-clip: text;
            -webkit-text-fill-color: transparent;
            margin-bottom: 8px;
        }}
        
        .header p {{
            color: #888;
            font-size: 14px;
        }}
        
        .chart-container {{
            background: #1a1d29;
            border-radius: 12px;
            padding: 20px;
            margin-bottom: 15px;
        }}
        
        .chart-title {{
            color: #4dd0e1;
            font-size: 16px;
            font-weight: 600;
            margin-bottom: 15px;
            padding-left: 5px;
        }}
        
        #mainChart {{
            height: 500px;
            margin-bottom: 10px;
            position: relative;  /* Pour permettre absolute positioning du canvas */
        }}
        
        #zonesCanvas {{
            position: absolute;
            top: 0;
            left: 0;
            pointer-events: none;  /* Pas d'interaction, juste affichage */
            z-index: 10;  /* Au-dessus du chart */
        }}
        
        .bottom-chart {{
            height: 150px;
            margin-bottom: 10px;
        }}
        
        .info {{
            background: #1a1d29;
            padding: 15px;
            border-radius: 8px;
            color: #888;
            font-size: 13px;
        }}
        
        .info-grid {{
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
            gap: 10px;
            margin-top: 10px;
        }}
        
        .info-item {{
            padding: 8px;
            background: #0d1117;
            border-radius: 6px;
        }}
        
        .info-label {{
            color: #4dd0e1;
            font-weight: 600;
            margin-bottom: 4px;
        }}
    </style>
</head>
<body>
    <div class="header">
        <h1>📊 Chart Viewer</h1>
        <p>{symbol} • {main_tf} • {len(main_candles)} candles</p>
    </div>
    
    <div class="chart-container">
        <div class="chart-title">💹 {symbol} - {main_tf}</div>
        <div id="mainChart" style="position: relative;">
            <canvas id="zonesCanvas"></canvas>
        </div>
    </div>
'''
    
    # Add bottom panels if needed
    bottom_panels = [p for p in ['bottom_1', 'bottom_2', 'bottom_3'] if panels[p]]
    
    for panel_name in bottom_panels:
        panel_indicators = panels[panel_name]
        if not panel_indicators:
            continue
        
        panel_title = " + ".join([ind['name'] for ind in panel_indicators])
        
        html += f'''
    <div class="chart-container">
        <div class="chart-title">📊 {panel_title}</div>
        <div id="{panel_name}" class="bottom-chart"></div>
    </div>
'''
    
    # Info section
    html += f'''
    <div class="info">
        <strong>📈 Indicators Loaded:</strong>
        <div class="info-grid">
'''
    
    for ind_config in indicators_config:
        ind_name = ind_config['name']
        if ind_name in indicator_results:
            result = indicator_results[ind_name]
            html += f'''
            <div class="info-item">
                <div class="info-label">{ind_name}</div>
                <div>{len(result.series)} series, {len(result.objects)} objects</div>
            </div>
'''
    
    html += '''
        </div>
    </div>
    
    <script>
'''
    
    # JavaScript data
    html += f'''
        const candlesData = {json.dumps(candles_data)};
    '''
    
    # Create main chart
    html += '''
        // Main chart
        const mainChart = LightweightCharts.createChart(document.getElementById('mainChart'), {
            layout: { background: { color: '#1a1d29' }, textColor: '#d1d4dc' },
            grid: { vertLines: { color: 'rgba(43, 43, 67, 0.2)' }, horzLines: { color: 'rgba(43, 43, 67, 0.2)' } },
            width: document.getElementById('mainChart').clientWidth,
            height: 500,
            rightPriceScale: {
                visible: true,
                borderVisible: true,
                scaleMargins: {
                    top: 0.1,
                    bottom: 0.1
                },
                entireTextOnly: false,
                ticksVisible: true,
                minimumWidth: 60
            },
            timeScale: { timeVisible: true, secondsVisible: false },
            crosshair: { mode: LightweightCharts.CrosshairMode.Normal }
        });
        
        const candlestickSeries = mainChart.addCandlestickSeries({
            upColor: '#26a69a',
            downColor: '#ef5350',
            borderVisible: false,
            wickUpColor: '#26a69a',
            wickDownColor: '#ef5350'
        });
        candlestickSeries.setData(candlesData);
'''
    
    # Add series from main panel indicators
    series_colors = ['#2196F3', '#9C27B0', '#FF9800', '#4CAF50', '#F44336']
    color_idx = 0
    
    for ind_info in panels['main']:
        ind_name = ind_info['name']
        result = ind_info['result']
        style = ind_info['config'].get('style', {})
        
        for series_name, series_data in result.series.items():
            # Convert to JS format
            series_js = []
            for i, val in enumerate(series_data):
                if pd.notna(val):
                    series_js.append({
                        'time': candles_data[i]['time'],
                        'value': float(val)
                    })
            
            color = style.get('color', series_colors[color_idx % len(series_colors)])
            linewidth = style.get('linewidth', 2)
            color_idx += 1
            
            html += f'''
        // Series: {ind_name}.{series_name}
        const series_{ind_name}_{series_name} = mainChart.addLineSeries({{
            color: '{color}',
            lineWidth: {linewidth},
            title: '{ind_name}'
        }});
        series_{ind_name}_{series_name}.setData({json.dumps(series_js)});
'''
    
    # =======================================================================
    # PRIMITIVES RENDERING - Generic and reusable
    # =======================================================================
    
    def prepare_primitives_data(primitives_list):
        """
        Prepare primitives for Canvas rendering.
        
        This is a GENERIC function that works with ANY primitive type.
        NO business logic here - primitives come fully configured.
        """
        primitives_data = {
            'rectangles': [],
            'lines': [],
            'points': [],
            'texts': [],
            'curves': []
        }
        
        from core.models import (
            RectanglePrimitive, LinePrimitive, PointPrimitive,
            TextPrimitive, CurvePrimitive
        )
        
        for prim in primitives_list:
            if isinstance(prim, RectanglePrimitive):
                primitives_data['rectangles'].append({
                    'id': prim.id,
                    'start_index': prim.time_start_index,
                    'end_index': prim.time_end_index,
                    'price_low': prim.price_low,
                    'price_high': prim.price_high,
                    'color': prim.color,
                    'alpha': prim.alpha,
                    'border_color': prim.border_color or prim.color,
                    'border_width': prim.border_width,
                    'label': prim.label,
                    'layer': prim.layer
                })
            
            elif isinstance(prim, LinePrimitive):
                primitives_data['lines'].append({
                    'id': prim.id,
                    'start_index': prim.time_start_index,
                    'end_index': prim.time_end_index,
                    'price_start': prim.price_start,
                    'price_end': prim.price_end,
                    'color': prim.color,
                    'width': prim.width,
                    'style': prim.style,
                    'label': prim.label,
                    'layer': prim.layer
                })
            
            elif isinstance(prim, PointPrimitive):
                primitives_data['points'].append({
                    'id': prim.id,
                    'index': prim.time_index,
                    'price': prim.price,
                    'color': prim.color,
                    'shape': prim.shape,
                    'size': prim.size,
                    'layer': prim.layer
                })
            
            elif isinstance(prim, TextPrimitive):
                primitives_data['texts'].append({
                    'id': prim.id,
                    'index': prim.time_index,
                    'price': prim.price,
                    'text': prim.text,
                    'color': prim.color,
                    'font_size': prim.font_size,
                    'background_color': prim.background_color,
                    'alignment': prim.alignment,
                    'layer': prim.layer
                })
            
            elif isinstance(prim, CurvePrimitive):
                primitives_data['curves'].append({
                    'id': prim.id,
                    'indices': prim.time_indices,
                    'prices': prim.prices,
                    'color': prim.color,
                    'width': prim.width,
                    'style': prim.style,
                    'layer': prim.layer
                })
        
        return primitives_data
    
    # Collect all primitives from all indicators
    all_primitives = []
    for ind_info in panels['main']:
        result = ind_info['result']
        all_primitives.extend(result.primitives)
    
    # Prepare primitives data (GENERIC - no business logic)
    primitives_data = prepare_primitives_data(all_primitives)
    # Convert to JavaScript-safe JSON (None -> null)
    primitives_js = json.dumps(primitives_data, indent=2).replace('None', 'null')
    
    print(f"   ✅ Primitives prepared:")
    print(f"      • Rectangles: {len(primitives_data['rectangles'])}")
    print(f"      • Lines: {len(primitives_data['lines'])}")
    print(f"      • Points: {len(primitives_data['points'])}")
    print(f"      • Texts: {len(primitives_data['texts'])}")
    print(f"      • Curves: {len(primitives_data['curves'])}")

    # =======================================================================
    # LEGACY SUPPORT - ZoneObject and SegmentObject (will be deprecated)
    # =======================================================================
    
    # Prepare zones data for Canvas rendering
    zones_data = []
    
    for zone in all_zones:
        # Determine color based on direction and state
        direction = zone.metadata.get('direction', 'unknown')
        
        if zone.state == 'invalidated':
            color = '#9E9E9E'  # Gray for invalidated
            alpha = 0.1
        elif direction == 'bullish':
            # Green with transparency based on mitigation score
            color = '#26a69a'
            # Less mitigated = more opaque
            alpha = max(0.15, 0.3 - (zone.mitigation_score * 0.05))
        else:  # bearish
            color = '#8B0000'  # Burgundy/Dark red
            alpha = max(0.15, 0.3 - (zone.mitigation_score * 0.05))
        
        zone_data = {
            'id': zone.id,
            'entry_index': zone.entry_candle_index,
            'exit_index': zone.exit_candle_index,  # None if active
            'price_low': zone.low,
            'price_high': zone.high,
            'color': color,
            'alpha': alpha,
            'direction': direction,
            'state': zone.state,
            'mitigation_count': zone.mitigation_count,
            'mitigation_score': zone.mitigation_score
        }
        zones_data.append(zone_data)
    
    print(f"   ✅ {len(zones_data)} LEGACY zones prepared (backwards compat)")
    
    # Prepare segments data for Canvas rendering (lines)
    segments_data = []
    
    # Create timestamp to index mapping
    time_to_index = {int(pd.to_datetime(idx).timestamp()): i for i, idx in enumerate(main_candles.index)}

    for segment in all_segments:
        # Convert timestamps to indices
        start_ts = int(segment.t_start.timestamp())
        end_ts = int(segment.t_end.timestamp())
        
        # Find closest indices
        start_index = time_to_index.get(start_ts)
        end_index = time_to_index.get(end_ts)
        
        if start_index is None or end_index is None:
            print(f"   ⚠️  Skipping segment {segment.id}: timestamps not found in candles")
            continue
        
        # Determine color and style based on segment type and direction
        seg_type = segment.metadata.get('structure_type', segment.type).upper()
        direction = segment.metadata.get('direction', 'unknown')
        
        if 'BOS' in seg_type:
            color = '#26a69a' if direction == 'bullish' else '#8B0000'  # Green / Burgundy
            line_width = 2
            line_style = 'solid'
        elif 'CHOCH' in seg_type:
            color = '#FFA726'  # Orange
            line_width = 2
            line_style = 'dashed'
        elif 'MSS' in seg_type:
            color = '#9C27B0'  # Purple
            line_width = 3
            line_style = 'solid'
        elif 'SUPPORT' in seg_type or 'RESISTANCE' in seg_type:
            color = '#2196F3'  # Blue
            line_width = 1
            line_style = 'dotted'
        else:
            color = '#9E9E9E'  # Gray default
            line_width = 1
            line_style = 'solid'
        
        segment_data = {
            'id': segment.id,
            'type': seg_type,
            'start_index': start_index,
            'end_index': end_index,
            'start_price': segment.y_start,
            'end_price': segment.y_end,
            'color': color,
            'line_width': line_width,
            'line_style': line_style,  # 'solid', 'dashed', 'dotted'
            'direction': direction,
            'label': segment.label if segment.label else f"{seg_type} {direction.upper()}"
        }
        segments_data.append(segment_data)
    
    print(f"   ✅ {len(segments_data)} segments prepared for Canvas rendering")
    
    # Add segments as markers (keep backward compatibility)
    segment_counter = 0
    markers_data = []
    
    for segment in all_segments:
        # Determine marker properties based on segment type
        if 'BOS' in segment.type:
            shape = 'arrowUp' if 'bullish' in segment.label.lower() else 'arrowDown'
            color = '#26a69a' if 'bullish' in segment.label.lower() else '#ef5350'
            position = 'belowBar' if 'bullish' in segment.label.lower() else 'aboveBar'
        elif 'CHOCH' in segment.type:
            shape = 'circle'
            color = '#FFA726'  # Orange
            position = 'inBar'
        else:
            shape = 'circle'
            color = '#9E9E9E'  # Gray
            position = 'inBar'
        
        # Create marker at segment start
        marker = {
            'time': int(segment.t_start.timestamp()),
            'position': position,
            'color': color,
            'shape': shape,
            'text': segment.label[:20] if segment.label else segment.type  # Limit text length
        }
        markers_data.append(marker)
        segment_counter += 1
    
    # Add markers to chart
    if markers_data:
        html += f'''
        // Add BOS/CHOCH markers
        candlestickSeries.setMarkers({json.dumps(markers_data)});
'''
    
    print(f"   ✅ {segment_counter} segments rendered as markers")
    
    # Add bottom panels
    for panel_name in bottom_panels:
        panel_indicators = panels[panel_name]
        if not panel_indicators:
            continue
        
        html += f'''
        // Panel: {panel_name}
        const chart_{panel_name} = LightweightCharts.createChart(document.getElementById('{panel_name}'), {{
            layout: {{ background: {{ color: '#1a1d29' }}, textColor: '#d1d4dc' }},
            grid: {{ vertLines: {{ color: 'rgba(43, 43, 67, 0.2)' }}, horzLines: {{ color: 'rgba(43, 43, 67, 0.2)' }} }},
            width: document.getElementById('{panel_name}').clientWidth,
            height: 150,
            rightPriceScale: {{
                visible: true,
                borderVisible: true
            }},
            timeScale: {{ timeVisible: true, secondsVisible: false }}
        }});
'''

        for ind_info in panel_indicators:
            ind_name = ind_info['name']
            result = ind_info['result']
            style = ind_info['config'].get('style', {})
            
            for series_name, series_data in result.series.items():
                series_js = []
                for i, val in enumerate(series_data):
                    if pd.notna(val):
                        series_js.append({
                            'time': candles_data[i]['time'],
                            'value': float(val)
                        })
                
                color = style.get('color', series_colors[color_idx % len(series_colors)])
                linewidth = style.get('linewidth', 2)
                color_idx += 1
                
                html += f'''
        const series_{panel_name}_{ind_name}_{series_name} = chart_{panel_name}.addLineSeries({{
            color: '{color}',
            lineWidth: {linewidth}
        }});
        series_{panel_name}_{ind_name}_{series_name}.setData({json.dumps(series_js)});
'''
        
        # Sync with main chart
        html += f'''
        mainChart.timeScale().subscribeVisibleLogicalRangeChange((range) => {{
            if (range) chart_{panel_name}.timeScale().setVisibleLogicalRange(range);
        }});
'''
    
    html += '''
        // Resize handler
        window.addEventListener('resize', () => {
            mainChart.applyOptions({ width: document.getElementById('mainChart').clientWidth });
'''
    
    for panel_name in bottom_panels:
        html += f'''
            chart_{panel_name}.applyOptions({{ width: document.getElementById('{panel_name}').clientWidth }});
'''
    
    html += '''
        });
        
        // ========================================
        // CANVAS ZONES RENDERING (MÉTHODE ÉPROUVÉE)
        // ========================================
        
        const zonesData = ''' + json.dumps(zones_data) + ''';
        const canvas = document.getElementById('zonesCanvas');
        const ctx = canvas.getContext('2d');
        
        // Helper: Convert hex to rgba
        function hexToRgba(hex, alpha) {
            const r = parseInt(hex.slice(1, 3), 16);
            const g = parseInt(hex.slice(3, 5), 16);
            const b = parseInt(hex.slice(5, 7), 16);
            return `rgba(${r}, ${g}, ${b}, ${alpha})`;
        }
        
        function drawZones() {
            console.log('🎨 drawZones() called');
            
            if (!ctx) {
                console.error('❌ Canvas context not ready');
                return;
            }
            
            // Sync canvas size with chart
            const chartElement = document.getElementById('mainChart');
            canvas.width = chartElement.clientWidth;
            canvas.height = 500; // Match chart height
            
            console.log(`📐 Canvas size: ${canvas.width}x${canvas.height}`);
            
            // Clear canvas
            ctx.clearRect(0, 0, canvas.width, canvas.height);
            
            const timeScale = mainChart.timeScale();
            
            // Get the visible logical range to calculate chart area width
            const visibleRange = timeScale.getVisibleLogicalRange();
            const timeScaleWidth = timeScale.width();
            
            // Calculate price scale width (right side) - typically ~60px
            const priceScaleWidth = 60;
            const maxX = canvas.width - priceScaleWidth;
            
            let drawnCount = 0;
            
            console.log(`📦 Zones to draw: ${zonesData.length}`);
            console.log(`📐 Chart area: 0 to ${maxX}px (price scale at ${maxX}-${canvas.width})`);
            
            // Draw each zone
            zonesData.forEach((zone, idx) => {
                console.log(`  Zone ${idx} (${zone.id}):`, zone);
                
                // Get X coordinates from time
                if (zone.entry_index === null || zone.entry_index >= candlesData.length) {
                    console.warn(`    ❌ Invalid entry_index: ${zone.entry_index}`);
                    return;
                }
                
                const entryTime = candlesData[zone.entry_index].time;
                const x1 = timeScale.timeToCoordinate(entryTime);
                
                console.log(`    Entry: index=${zone.entry_index}, time=${entryTime}, x=${x1}`);
                
                if (x1 === null) {
                    console.warn(`    ❌ x1 is null`);
                    return;
                }
                
                // Exit X coordinate
                let x2;
                if (zone.exit_index !== null && zone.exit_index < candlesData.length) {
                    const exitTime = candlesData[zone.exit_index].time;
                    x2 = timeScale.timeToCoordinate(exitTime);
                    console.log(`    Exit: index=${zone.exit_index}, time=${exitTime}, x=${x2}`);
                    if (x2 === null) x2 = maxX;
                } else {
                    // Active zone - extend to chart edge (NOT canvas edge)
                    x2 = maxX;
                    console.log(`    Exit: extend to chart edge (${x2})`);
                }
                
                // Clamp x2 to not exceed chart area
                x2 = Math.min(x2, maxX);
                
                // Get Y coordinates using SERIES.priceToCoordinate (not priceScale!)
                const y1 = candlestickSeries.priceToCoordinate(zone.price_high);
                const y2 = candlestickSeries.priceToCoordinate(zone.price_low);
                
                console.log(`    Y coords: high=${zone.price_high} → y1=${y1}, low=${zone.price_low} → y2=${y2}`);
                
                if (y1 === null || y2 === null) {
                    console.warn(`    ❌ Y coordinate is null: y1=${y1}, y2=${y2}`);
                    return;
                }
                
                const left = Math.min(x1, x2);
                const top = Math.min(y1, y2);
                const width = Math.abs(x2 - x1);
                const height = Math.abs(y2 - y1);
                
                console.log(`    Rectangle: left=${left}, top=${top}, width=${width}, height=${height}`);
                
                // Draw filled rectangle with rgba
                const fillColor = hexToRgba(zone.color, zone.alpha);
                console.log(`    Fill color: ${fillColor}`);
                
                ctx.fillStyle = fillColor;
                ctx.fillRect(left, top, width, height);
                
                // Draw border
                ctx.strokeStyle = zone.color;
                ctx.lineWidth = 1;
                ctx.strokeRect(left, top, width, height);
                
                // Draw label for active zones
                if (zone.state === 'active') {
                    ctx.fillStyle = zone.color;
                    ctx.font = '10px Arial';
                    const label = `${zone.direction.toUpperCase()} (${zone.mitigation_count})`;
                    ctx.fillText(label, left + 5, top + 12);
                }
                
                console.log(`    ✅ Zone ${idx} drawn!`);
                drawnCount++;
            });
            
            if (drawnCount === 0) {
                console.warn('⚠️ No zones drawn - check data');
            } else {
                console.log(`✅ Drew ${drawnCount} zones`);
            }
        }
        
        // ========================================
        // CANVAS SEGMENTS RENDERING (LINES)
        // ========================================
        
        const segmentsData = ''' + json.dumps(segments_data) + ''';
        
        function drawSegments() {
            console.log('📏 drawSegments() called');
            
            if (!ctx) {
                console.error('❌ Canvas context not ready');
                return;
            }
            
            const timeScale = mainChart.timeScale();
            let drawnCount = 0;
            
            console.log(`📦 Segments to draw: ${segmentsData.length}`);
            
            // Draw each segment (line)
            segmentsData.forEach((seg, idx) => {
                console.log(`  Segment ${idx} (${seg.id}):`, seg);
                
                // Get X coordinates from time
                if (seg.start_index === null || seg.start_index >= candlesData.length) {
                    console.warn(`    ❌ Invalid start_index: ${seg.start_index}`);
                    return;
                }
                if (seg.end_index === null || seg.end_index >= candlesData.length) {
                    console.warn(`    ❌ Invalid end_index: ${seg.end_index}`);
                    return;
                }
                
                const startTime = candlesData[seg.start_index].time;
                const endTime = candlesData[seg.end_index].time;
                const x1 = timeScale.timeToCoordinate(startTime);
                const x2 = timeScale.timeToCoordinate(endTime);
                
                console.log(`    Start: index=${seg.start_index}, time=${startTime}, x=${x1}`);
                console.log(`    End: index=${seg.end_index}, time=${endTime}, x=${x2}`);
                
                if (x1 === null || x2 === null) {
                    console.warn(`    ❌ X coordinate is null: x1=${x1}, x2=${x2}`);
                    return;
                }
                
                // Get Y coordinates using SERIES.priceToCoordinate
                const y1 = candlestickSeries.priceToCoordinate(seg.start_price);
                const y2 = candlestickSeries.priceToCoordinate(seg.end_price);
                
                console.log(`    Y coords: start=${seg.start_price} → y1=${y1}, end=${seg.end_price} → y2=${y2}`);
                
                if (y1 === null || y2 === null) {
                    console.warn(`    ❌ Y coordinate is null: y1=${y1}, y2=${y2}`);
                    return;
                }
                
                // Set line style
                ctx.strokeStyle = seg.color;
                ctx.lineWidth = seg.line_width;
                
                // Apply line dash pattern
                if (seg.line_style === 'dashed') {
                    ctx.setLineDash([10, 5]);  // 10px dash, 5px gap
                } else if (seg.line_style === 'dotted') {
                    ctx.setLineDash([2, 3]);   // 2px dot, 3px gap
                } else {
                    ctx.setLineDash([]);       // Solid line
                }
                
                // Draw the line
                ctx.beginPath();
                ctx.moveTo(x1, y1);
                ctx.lineTo(x2, y2);
                ctx.stroke();
                
                // Reset line dash
                ctx.setLineDash([]);
                
                // Draw label at midpoint
                const midX = (x1 + x2) / 2;
                const midY = (y1 + y2) / 2;
                
                ctx.fillStyle = seg.color;
                ctx.font = 'bold 11px Arial';
                ctx.textAlign = 'center';
                ctx.textBaseline = 'middle';
                
                // Draw background for label
                const labelText = seg.label;
                const textMetrics = ctx.measureText(labelText);
                const padding = 4;
                
                ctx.fillStyle = 'rgba(13, 17, 23, 0.8)';  // Dark background
                ctx.fillRect(
                    midX - textMetrics.width/2 - padding,
                    midY - 8,
                    textMetrics.width + padding*2,
                    16
                );
                
                // Draw text
                ctx.fillStyle = seg.color;
                ctx.fillText(labelText, midX, midY);
                
                console.log(`    ✅ Segment ${idx} drawn!`);
                drawnCount++;
            });
            
            if (drawnCount === 0) {
                console.warn('⚠️ No segments drawn - check data');
            } else {
                console.log(`✅ Drew ${drawnCount} segments`);
            }
        }
        
        // =====================================================================
        // GENERIC PRIMITIVES RENDERING - No business logic, just rendering
        // =====================================================================
'''
    html += f'''
        const primitivesData = {primitives_js};
'''
    html += '''
        function drawPrimitiveRectangles() {
            console.log('🎨 drawPrimitiveRectangles() called');
            
            if (!ctx) return;
            
            const timeScale = mainChart.timeScale();
            const rectangles = primitivesData.rectangles || [];
            
            // Calculate price scale width
            const priceScaleWidth = 60;
            const maxX = canvas.width - priceScaleWidth;
            
            console.log(`📦 Primitive rectangles to draw: ${rectangles.length}`);
            
            let drawnCount = 0;
            
            rectangles.forEach((rect, idx) => {
                // Get X coordinates
                if (rect.start_index === null || rect.start_index >= candlesData.length) {
                    return;
                }
                
                const x1 = timeScale.timeToCoordinate(candlesData[rect.start_index].time);
                if (x1 === null) return;
                
                let x2;
                if (rect.end_index !== null && rect.end_index < candlesData.length) {
                    x2 = timeScale.timeToCoordinate(candlesData[rect.end_index].time);
                    if (x2 === null) x2 = maxX;
                } else {
                    x2 = maxX;
                }
                
                // Clamp to chart area
                x2 = Math.min(x2, maxX);
                
                // Get Y coordinates
                const y1 = candlestickSeries.priceToCoordinate(rect.price_high);
                const y2 = candlestickSeries.priceToCoordinate(rect.price_low);
                
                if (y1 === null || y2 === null) return;
                
                const left = Math.min(x1, x2);
                const top = Math.min(y1, y2);
                const width = Math.abs(x2 - x1);
                const height = Math.abs(y2 - y1);
                
                // Draw filled rectangle (color and alpha already decided by indicator)
                const fillColor = hexToRgba(rect.color, rect.alpha);
                ctx.fillStyle = fillColor;
                ctx.fillRect(left, top, width, height);
                
                // Draw border
                ctx.strokeStyle = rect.border_color;
                ctx.lineWidth = rect.border_width;
                ctx.strokeRect(left, top, width, height);
                
                // Draw label if present
                if (rect.label) {
                    ctx.fillStyle = rect.color;
                    ctx.font = '10px Arial';
                    ctx.fillText(rect.label, left + 5, top + 12);
                }
                
                drawnCount++;
            });
            
            console.log(`✅ Drew ${drawnCount} primitive rectangles`);
        }
        
        function drawPrimitiveLines() {
            console.log('🎨 drawPrimitiveLines() called');
            
            if (!ctx) return;
            
            const timeScale = mainChart.timeScale();
            const lines = primitivesData.lines || [];
            
            console.log(`📦 Primitive lines to draw: ${lines.length}`);
            
            let drawnCount = 0;
            
            lines.forEach((line, idx) => {
                // Get coordinates
                if (line.start_index >= candlesData.length || line.end_index >= candlesData.length) {
                    return;
                }
                
                const x1 = timeScale.timeToCoordinate(candlesData[line.start_index].time);
                const x2 = timeScale.timeToCoordinate(candlesData[line.end_index].time);
                
                if (x1 === null || x2 === null) return;
                
                const y1 = candlestickSeries.priceToCoordinate(line.price_start);
                const y2 = candlestickSeries.priceToCoordinate(line.price_end);
                
                if (y1 === null || y2 === null) return;
                
                // Set line style
                ctx.strokeStyle = line.color;
                ctx.lineWidth = line.width;
                
                if (line.style === 'dashed') {
                    ctx.setLineDash([10, 5]);
                } else if (line.style === 'dotted') {
                    ctx.setLineDash([2, 3]);
                } else {
                    ctx.setLineDash([]);
                }
                
                // Draw line
                ctx.beginPath();
                ctx.moveTo(x1, y1);
                ctx.lineTo(x2, y2);
                ctx.stroke();
                ctx.setLineDash([]);
                
                // Draw label if present
                if (line.label) {
                    const midX = (x1 + x2) / 2;
                    const midY = (y1 + y2) / 2;
                    
                    ctx.font = '10px Arial';
                    const metrics = ctx.measureText(line.label);
                    const labelWidth = metrics.width + 8;
                    
                    // Background
                    ctx.fillStyle = 'rgba(13, 17, 23, 0.8)';
                    ctx.fillRect(midX - labelWidth/2, midY - 8, labelWidth, 16);
                    
                    // Text
                    ctx.fillStyle = line.color;
                    ctx.textAlign = 'center';
                    ctx.fillText(line.label, midX, midY + 4);
                    ctx.textAlign = 'left';
                }
                
                drawnCount++;
            });
            
            console.log(`✅ Drew ${drawnCount} primitive lines`);
        }
        
        function drawPrimitivePoints() {
            console.log('🎨 drawPrimitivePoints() called');
            
            if (!ctx) return;
            
            const timeScale = mainChart.timeScale();
            const points = primitivesData.points || [];
            
            console.log(`📦 Primitive points to draw: ${points.length}`);
            
            let drawnCount = 0;
            
            points.forEach((point, idx) => {
                if (point.index >= candlesData.length) return;
                
                const x = timeScale.timeToCoordinate(candlesData[point.index].time);
                const y = candlestickSeries.priceToCoordinate(point.price);
                
                if (x === null || y === null) return;
                
                ctx.fillStyle = point.color;
                ctx.strokeStyle = point.color;
                
                // Draw based on shape
                if (point.shape === 'circle') {
                    ctx.beginPath();
                    ctx.arc(x, y, point.size, 0, Math.PI * 2);
                    ctx.fill();
                } else if (point.shape === 'square') {
                    ctx.fillRect(x - point.size, y - point.size, point.size * 2, point.size * 2);
                } else if (point.shape === 'arrow_up') {
                    ctx.beginPath();
                    ctx.moveTo(x, y - point.size);
                    ctx.lineTo(x + point.size, y + point.size);
                    ctx.lineTo(x - point.size, y + point.size);
                    ctx.closePath();
                    ctx.fill();
                } else if (point.shape === 'arrow_down') {
                    ctx.beginPath();
                    ctx.moveTo(x, y + point.size);
                    ctx.lineTo(x + point.size, y - point.size);
                    ctx.lineTo(x - point.size, y - point.size);
                    ctx.closePath();
                    ctx.fill();
                }
                
                drawnCount++;
            });
            
            console.log(`✅ Drew ${drawnCount} primitive points`);
        }
        
        function drawPrimitiveTexts() {
            console.log('🎨 drawPrimitiveTexts() called');
            
            if (!ctx) return;
            
            const timeScale = mainChart.timeScale();
            const texts = primitivesData.texts || [];
            
            console.log(`📦 Primitive texts to draw: ${texts.length}`);
            
            let drawnCount = 0;
            
            texts.forEach((text, idx) => {
                if (text.index >= candlesData.length) return;
                
                const x = timeScale.timeToCoordinate(candlesData[text.index].time);
                const y = candlestickSeries.priceToCoordinate(text.price);
                
                if (x === null || y === null) return;
                
                ctx.font = `${text.font_size}px Arial`;
                const metrics = ctx.measureText(text.text);
                
                // Draw background if specified
                if (text.background_color) {
                    const padding = 4;
                    const width = metrics.width + padding * 2;
                    const height = text.font_size + padding * 2;
                    
                    let xOffset = 0;
                    if (text.alignment === 'center') xOffset = -width / 2;
                    else if (text.alignment === 'right') xOffset = -width;
                    
                    ctx.fillStyle = text.background_color;
                    ctx.fillRect(x + xOffset, y - height/2, width, height);
                }
                
                // Draw text
                ctx.fillStyle = text.color;
                ctx.textAlign = text.alignment;
                ctx.fillText(text.text, x, y);
                ctx.textAlign = 'left';
                
                drawnCount++;
            });
            
            console.log(`✅ Drew ${drawnCount} primitive texts`);
        }
        
        // Draw zones first, then segments on top
        function drawAll() {
            // LEGACY rendering (backwards compatibility)
            drawZones();
            drawSegments();
            
            // NEW: Generic primitives rendering
            drawPrimitiveRectangles();
            drawPrimitiveLines();
            drawPrimitivePoints();
            drawPrimitiveTexts();
        }
        
        // ========================================
        
        // Initial draw (wait for chart to be ready)
        setTimeout(() => {
            drawAll();
        }, 100);
        
        // Redraw on zoom/pan
        mainChart.timeScale().subscribeVisibleLogicalRangeChange(() => {
            drawAll();
        });
        
        // Redraw on window resize
        window.addEventListener('resize', () => {
            drawAll();
        });
        
        // ========================================
        
        mainChart.timeScale().fitContent();
        
        console.log('✅ Chart initialized');
        console.log('✅ Canvas zones prepared:', zonesData.length);
    </script>
</body>
</html>'''
    
    return html


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("\n❌ Usage: python visualization/chart_viewer.py <config.yaml>")
        print("\nExample:")
        print("  python visualization/chart_viewer.py config_chart_viewer.yaml")
        sys.exit(1)
    
    config_file = sys.argv[1]
    
    if not Path(config_file).exists():
        print(f"\n❌ Config file not found: {config_file}")
        sys.exit(1)
    
    generate_chart_html(config_file)
