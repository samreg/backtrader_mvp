#!/usr/bin/env python3
"""
📊 CHART VIEWER - Visualisation Pure des Chandelles et Indicateurs

Fichier standalone pour afficher :
- Chandelles (OHLC)
- Bollinger Bands
- RSI
- (Facile d'ajouter d'autres indicateurs)

Usage:
    python chart_viewer.py data/NAS100_M3.csv
    python chart_viewer.py data/BTC_1min.csv
"""

import sys
import pandas as pd
import numpy as np
from pathlib import Path


def calculate_bollinger_bands(df, period=20, std_dev=2.0):
    """Calcule les Bollinger Bands"""
    df['bb_middle'] = df['close'].rolling(window=period).mean()
    df['bb_std'] = df['close'].rolling(window=period).std()
    df['bb_upper'] = df['bb_middle'] + (std_dev * df['bb_std'])
    df['bb_lower'] = df['bb_middle'] - (std_dev * df['bb_std'])
    return df


def calculate_rsi(df, period=14):
    """Calcule le RSI"""
    delta = df['close'].diff()
    gain = (delta.where(delta > 0, 0)).rolling(window=period).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(window=period).mean()
    rs = gain / loss
    df['rsi'] = 100 - (100 / (1 + rs))
    return df


def generate_chart_html(data_file, bb_period=20, bb_std=2.0, rsi_period=14):
    """Génère un HTML avec LightweightCharts"""
    
    print(f"\n📊 Chart Viewer")
    print("="*60)
    print(f"Fichier: {data_file}")
    
    # Charger données
    if not Path(data_file).exists():
        print(f"❌ Fichier non trouvé: {data_file}")
        return
    
    df = pd.read_csv(data_file, parse_dates=['datetime'])
    print(f"✅ {len(df)} chandelles chargées")
    
    # Calculer indicateurs
    df = calculate_bollinger_bands(df, period=bb_period, std_dev=bb_std)
    df = calculate_rsi(df, period=rsi_period)
    
    # Supprimer NaN
    df = df.dropna()
    print(f"✅ Indicateurs calculés (BB{bb_period}, RSI{rsi_period})")
    
    # Convertir datetime en timestamp UTC
    df['timestamp'] = (df['datetime'] - pd.Timestamp("1970-01-01")) // pd.Timedelta('1s')
    
    # Préparer données pour JS
    candles_data = []
    for _, row in df.iterrows():
        candles_data.append({
            'time': int(row['timestamp']),
            'open': float(row['open']),
            'high': float(row['high']),
            'low': float(row['low']),
            'close': float(row['close'])
        })
    
    bb_upper_data = [{'time': int(row['timestamp']), 'value': float(row['bb_upper'])} for _, row in df.iterrows()]
    bb_middle_data = [{'time': int(row['timestamp']), 'value': float(row['bb_middle'])} for _, row in df.iterrows()]
    bb_lower_data = [{'time': int(row['timestamp']), 'value': float(row['bb_lower'])} for _, row in df.iterrows()]
    rsi_data = [{'time': int(row['timestamp']), 'value': float(row['rsi'])} for _, row in df.iterrows()]
    
    # Générer HTML
    html = f'''<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Chart Viewer - {Path(data_file).stem}</title>
    <script src="https://unpkg.com/lightweight-charts@4.1.0/dist/lightweight-charts.standalone.production.js"></script>
    <style>
        * {{
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }}
        
        body {{
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Oxygen, Ubuntu, sans-serif;
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
        
        .controls {{
            display: flex;
            justify-content: center;
            gap: 15px;
            margin-bottom: 20px;
            flex-wrap: wrap;
        }}
        
        .control-group {{
            background: #1a1d29;
            padding: 12px 20px;
            border-radius: 8px;
            display: flex;
            align-items: center;
            gap: 10px;
        }}
        
        .control-group label {{
            color: #888;
            font-size: 13px;
        }}
        
        .control-group input {{
            background: #0d1117;
            border: 1px solid #30363d;
            color: #e6edf3;
            padding: 6px 12px;
            border-radius: 6px;
            width: 80px;
            font-size: 14px;
        }}
        
        .control-group button {{
            background: linear-gradient(135deg, #26a69a 0%, #4dd0e1 100%);
            border: none;
            color: white;
            padding: 8px 16px;
            border-radius: 6px;
            cursor: pointer;
            font-weight: 500;
            transition: opacity 0.2s;
        }}
        
        .control-group button:hover {{
            opacity: 0.9;
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
        }}
        
        #rsiChart {{
            height: 150px;
        }}
        
        .info {{
            background: #1a1d29;
            padding: 15px;
            border-radius: 8px;
            text-align: center;
            color: #888;
            font-size: 13px;
        }}
    </style>
</head>
<body>
    <div class="header">
        <h1>📊 Chart Viewer</h1>
        <p>{Path(data_file).stem} • {len(df)} chandelles</p>
    </div>
    
    <div class="controls">
        <div class="control-group">
            <label>BB Period:</label>
            <input type="number" id="bbPeriod" value="{bb_period}" min="5" max="200">
        </div>
        <div class="control-group">
            <label>BB Std Dev:</label>
            <input type="number" id="bbStd" value="{bb_std}" min="0.5" max="5" step="0.1">
        </div>
        <div class="control-group">
            <label>RSI Period:</label>
            <input type="number" id="rsiPeriod" value="{rsi_period}" min="2" max="50">
        </div>
        <div class="control-group">
            <button onclick="updateIndicators()">🔄 Recalculer</button>
        </div>
    </div>
    
    <div class="chart-container">
        <div class="chart-title">💹 Prix & Bollinger Bands</div>
        <div id="mainChart"></div>
    </div>
    
    <div class="chart-container">
        <div class="chart-title">📊 RSI (Relative Strength Index)</div>
        <div id="rsiChart"></div>
    </div>
    
    <div class="info">
        💡 Astuce: Scroll pour zoomer, drag pour naviguer • Modifiez les paramètres et cliquez sur "Recalculer"
    </div>
    
    <script>
        // Données
        const candlesData = {candles_data};
        const bbUpperData = {bb_upper_data};
        const bbMiddleData = {bb_middle_data};
        const bbLowerData = {bb_lower_data};
        const rsiData = {rsi_data};
        
        // Chart principal
        const mainChart = LightweightCharts.createChart(document.getElementById('mainChart'), {{
            layout: {{ background: {{ color: '#1a1d29' }}, textColor: '#d1d4dc' }},
            grid: {{ vertLines: {{ color: 'rgba(43, 43, 67, 0.2)' }}, horzLines: {{ color: 'rgba(43, 43, 67, 0.2)' }} }},
            width: document.getElementById('mainChart').clientWidth,
            height: 500,
            timeScale: {{ timeVisible: true, secondsVisible: false }},
            crosshair: {{ mode: LightweightCharts.CrosshairMode.Normal }}
        }});
        
        const candlestickSeries = mainChart.addCandlestickSeries({{
            upColor: '#26a69a',
            downColor: '#ef5350',
            borderVisible: false,
            wickUpColor: '#26a69a',
            wickDownColor: '#ef5350'
        }});
        candlestickSeries.setData(candlesData);
        
        const bbUpperSeries = mainChart.addLineSeries({{
            color: '#2196F3',
            lineWidth: 1,
            priceLineVisible: false,
            lastValueVisible: false
        }});
        bbUpperSeries.setData(bbUpperData);
        
        const bbMiddleSeries = mainChart.addLineSeries({{
            color: '#9C27B0',
            lineWidth: 2,
            priceLineVisible: false,
            lastValueVisible: false
        }});
        bbMiddleSeries.setData(bbMiddleData);
        
        const bbLowerSeries = mainChart.addLineSeries({{
            color: '#2196F3',
            lineWidth: 1,
            priceLineVisible: false,
            lastValueVisible: false
        }});
        bbLowerSeries.setData(bbLowerData);
        
        // Chart RSI
        const rsiChart = LightweightCharts.createChart(document.getElementById('rsiChart'), {{
            layout: {{ background: {{ color: '#1a1d29' }}, textColor: '#d1d4dc' }},
            grid: {{ vertLines: {{ color: 'rgba(43, 43, 67, 0.2)' }}, horzLines: {{ color: 'rgba(43, 43, 67, 0.2)' }} }},
            width: document.getElementById('rsiChart').clientWidth,
            height: 150,
            timeScale: {{ timeVisible: true, secondsVisible: false }},
            rightPriceScale: {{ scaleMargins: {{ top: 0.1, bottom: 0.1 }} }}
        }});
        
        const rsiSeries = rsiChart.addLineSeries({{
            color: '#9C27B0',
            lineWidth: 2
        }});
        rsiSeries.setData(rsiData);
        
        // RSI niveaux
        const rsiChart70 = rsiChart.addLineSeries({{
            color: 'rgba(239, 83, 80, 0.5)',
            lineWidth: 1,
            priceLineVisible: false,
            lastValueVisible: false
        }});
        rsiChart70.setData([
            {{ time: rsiData[0].time, value: 70 }},
            {{ time: rsiData[rsiData.length - 1].time, value: 70 }}
        ]);
        
        const rsiChart30 = rsiChart.addLineSeries({{
            color: 'rgba(76, 175, 80, 0.5)',
            lineWidth: 1,
            priceLineVisible: false,
            lastValueVisible: false
        }});
        rsiChart30.setData([
            {{ time: rsiData[0].time, value: 30 }},
            {{ time: rsiData[rsiData.length - 1].time, value: 30 }}
        ]);
        
        // Sync timeScale
        mainChart.timeScale().subscribeVisibleLogicalRangeChange((range) => {{
            if (range) rsiChart.timeScale().setVisibleLogicalRange(range);
        }});
        
        rsiChart.timeScale().subscribeVisibleLogicalRangeChange((range) => {{
            if (range) mainChart.timeScale().setVisibleLogicalRange(range);
        }});
        
        // Resize
        window.addEventListener('resize', () => {{
            mainChart.applyOptions({{ width: document.getElementById('mainChart').clientWidth }});
            rsiChart.applyOptions({{ width: document.getElementById('rsiChart').clientWidth }});
        }});
        
        // Fit content
        mainChart.timeScale().fitContent();
        
        // Fonction pour recalculer (pour l'instant juste reload)
        function updateIndicators() {{
            const bbPeriod = document.getElementById('bbPeriod').value;
            const bbStd = document.getElementById('bbStd').value;
            const rsiPeriod = document.getElementById('rsiPeriod').value;
            
            alert('Pour changer les paramètres, relancez:\\npython chart_viewer.py {data_file} --bb-period ' + bbPeriod + ' --bb-std ' + bbStd + ' --rsi-period ' + rsiPeriod);
        }}
        
        console.log('✅ Charts initialisés');
        console.log(`📊 ${{candlesData.length}} chandelles`);
        console.log(`📈 BB Period: {bb_period}, Std: {bb_std}`);
        console.log(`📊 RSI Period: {rsi_period}`);
    </script>
</body>
</html>'''
    
    # Sauvegarder HTML
    output_file = Path('output/chart_viewer.html')
    output_file.parent.mkdir(exist_ok=True)
    output_file.write_text(html, encoding='utf-8')
    
    print(f"\n✅ HTML généré: {output_file}")
    print(f"🌐 Ouvrez dans un navigateur pour voir les graphiques !\n")
    
    return output_file


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("\n❌ Usage: python chart_viewer.py <data_file.csv>")
        print("\nExemples:")
        print("  python chart_viewer.py data/NAS100_M3.csv")
        print("  python chart_viewer.py data/BTC_1min.csv")
        sys.exit(1)
    
    data_file = sys.argv[1]
    generate_chart_html(data_file)
