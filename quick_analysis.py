#!/usr/bin/env python3
"""
QUICK ANALYSIS - Analyse rapide sans configuration YAML

Script simple pour générer rapidement une analyse visuelle
avec Order Blocks + BOS/CHOCH.

Usage:
    # Avec données CSV
    python quick_analysis.py --csv data/NAS100_M3.csv
    
    # Avec MT5 (si loader disponible)
    python quick_analysis.py --symbol NAS100 --days 7
    
    # Avec données de test
    python quick_analysis.py --test
"""

import sys
import argparse
import pandas as pd
import numpy as np
from pathlib import Path
from datetime import datetime, timedelta

sys.path.insert(0, str(Path(__file__).parent))

from visualization.indicators.order_blocks import Indicator as OrderBlocksIndicator
try:
    from visualization.indicators.bos_choch import Indicator as BOSCHOCHIndicator
    BOS_AVAILABLE = True
except ImportError:
    print("⚠️  BOS/CHOCH non disponible - seulement Order Blocks")
    BOS_AVAILABLE = False

from visualization.chart_viewer import generate_html_content


def create_test_data():
    """Crée des données de test avec pattern zigzag"""
    dates = pd.date_range('2024-01-01', periods=500, freq='3min')
    base_price = 25000
    
    # Pattern avec hauts et bas pour Order Blocks + BOS
    wave = np.sin(np.linspace(0, 4*np.pi, 500)) * 150
    trend = np.linspace(0, 200, 500)
    noise = np.cumsum(np.random.randn(500) * 5)
    
    prices = base_price + wave + trend + noise
    
    df = pd.DataFrame({
        'time': dates,
        'open': prices,
        'high': prices + np.random.rand(500) * 15,
        'low': prices - np.random.rand(500) * 15,
        'close': prices + np.random.randn(500) * 5,
        'volume': np.random.randint(100, 1000, 500)
    })
    
    return df


def load_csv_data(filepath):
    """Charge données depuis CSV"""
    print(f"📂 Chargement CSV : {filepath}")
    
    df = pd.read_csv(filepath)
    
    # Essayer de parser la colonne time
    if 'time' in df.columns:
        df['time'] = pd.to_datetime(df['time'])
    elif 'timestamp' in df.columns:
        df['time'] = pd.to_datetime(df['timestamp'])
        df = df.drop('timestamp', axis=1)
    elif 'date' in df.columns:
        df['time'] = pd.to_datetime(df['date'])
        df = df.drop('date', axis=1)
    else:
        print("❌ Aucune colonne de temps trouvée (time/timestamp/date)")
        sys.exit(1)
    
    # Vérifier colonnes requises
    required = ['time', 'open', 'high', 'low', 'close']
    missing = [col for col in required if col not in df.columns]
    if missing:
        print(f"❌ Colonnes manquantes : {missing}")
        sys.exit(1)
    
    # Volume optionnel
    if 'volume' not in df.columns:
        df['volume'] = 1000
    
    print(f"✅ {len(df)} bougies chargées")
    return df


def load_mt5_data(symbol, days):
    """Charge données MT5 (si loader disponible)"""
    try:
        from mt5_data_loader import load_mt5_data as mt5_loader
        
        print(f"📊 Chargement MT5 : {symbol} ({days} jours)")
        
        end_date = datetime.now()
        start_date = end_date - timedelta(days=days)
        
        df = mt5_loader(
            symbol=symbol,
            timeframe='M3',
            start_date=start_date,
            end_date=end_date
        )
        
        print(f"✅ {len(df)} bougies chargées")
        return df
        
    except ImportError:
        print("❌ MT5 data loader non disponible")
        print("💡 Utilise --csv ou --test à la place")
        sys.exit(1)


def main():
    parser = argparse.ArgumentParser(
        description='Analyse rapide NAS100 avec Order Blocks + BOS'
    )
    
    # Sources de données
    data_group = parser.add_mutually_exclusive_group(required=True)
    data_group.add_argument('--csv', help='Fichier CSV de données')
    data_group.add_argument('--symbol', help='Symbole MT5 (ex: NAS100)')
    data_group.add_argument('--test', action='store_true', help='Utiliser données de test')
    
    # Options
    parser.add_argument('--days', type=int, default=7, help='Jours à charger (MT5)')
    parser.add_argument('--output', default='output/quick_analysis.html', help='Fichier de sortie')
    
    # Paramètres indicateurs
    parser.add_argument('--ob-swing', type=int, default=10, help='Order Blocks swing length')
    parser.add_argument('--bos-swing', type=int, default=5, help='BOS swing period')
    parser.add_argument('--bos-validation', choices=['wick', 'close'], default='wick',
                       help='BOS validation method')
    
    args = parser.parse_args()
    
    print("\n" + "="*70)
    print("⚡ QUICK ANALYSIS - Analyse Rapide")
    print("="*70 + "\n")
    
    # 1. CHARGER DONNÉES
    if args.csv:
        candles = load_csv_data(args.csv)
        symbol = Path(args.csv).stem
    elif args.symbol:
        candles = load_mt5_data(args.symbol, args.days)
        symbol = args.symbol
    else:  # --test
        print("🧪 Génération de données de test")
        candles = create_test_data()
        symbol = "TEST"
        print(f"✅ {len(candles)} bougies générées")
    
    # 2. CALCULER ORDER BLOCKS
    print("\n📊 Calcul Order Blocks...")
    ob_params = {
        'swing_length': args.ob_swing,
        'min_body_size': 2.0,
        'max_zones': 15,
        'imbalance_bars': 3,
        'skip_impulse_candles': 2
    }
    
    ob_indicator = OrderBlocksIndicator(ob_params)
    ob_result = ob_indicator.calculate(candles)
    
    print(f"   ✅ {len(ob_result.primitives)} Order Blocks détectés")
    
    # 3. CALCULER BOS/CHOCH (si disponible)
    indicators_results = {'order_blocks': ob_result}
    indicators_config = [{'name': 'order_blocks', 'panel': 'main'}]
    
    if BOS_AVAILABLE:
        print("\n📈 Calcul BOS/CHOCH...")
        bos_params = {
            'swing_period': args.bos_swing,
            'break_validation': args.bos_validation,
            'detect_bos': True
        }
        
        bos_indicator = BOSCHOCHIndicator(bos_params)
        bos_result = bos_indicator.calculate(candles)
        
        print(f"   ✅ {len(bos_result.primitives)} BOS détectés")
        
        indicators_results['bos_choch'] = bos_result
        indicators_config.append({'name': 'bos_choch', 'panel': 'main'})
    
    # 4. GÉNÉRER HTML
    print("\n🎨 Génération HTML...")
    
    config = {
        'data': {
            'symbol': symbol,
            'main_timeframe': 'M3'
        }
    }
    
    candles_by_tf = {'M3': candles}
    
    html = generate_html_content(
        config,
        candles_by_tf,
        indicators_results,
        indicators_config
    )
    
    # 5. SAUVER
    output_path = Path(args.output)
    output_path.parent.mkdir(exist_ok=True)
    output_path.write_text(html, encoding='utf-8')
    
    print(f"   ✅ Fichier généré : {output_path}")
    
    # 6. RÉSUMÉ
    print("\n" + "="*70)
    print("✅ ANALYSE TERMINÉE")
    print("="*70)
    
    print(f"\n📊 Données :")
    print(f"   • Symbole : {symbol}")
    print(f"   • Bougies : {len(candles)}")
    print(f"   • Période : {candles['time'].min()} → {candles['time'].max()}")
    
    print(f"\n📈 Indicateurs :")
    print(f"   • Order Blocks : {len(ob_result.primitives)} zones")
    if BOS_AVAILABLE:
        print(f"   • BOS/CHOCH : {len(bos_result.primitives)} cassures")
    
    print(f"\n📁 Fichier :")
    print(f"   {output_path.absolute()}")
    
    print(f"\n🌐 Ouvre ce fichier dans un navigateur pour voir l'analyse")
    print("="*70 + "\n")


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n\n⚠️  Analyse interrompue par l'utilisateur")
        sys.exit(0)
    except Exception as e:
        print(f"\n❌ ERREUR : {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
