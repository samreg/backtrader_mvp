#!/usr/bin/env python
"""
Test rapide Order Blocks - Vérifie la détection
"""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))

import pandas as pd
import MetaTrader5 as mt5
from datetime import datetime
from visualization.indicators.order_blocks import Indicator as OrderBlockIndicator

print("="*80)
print("🧪 TEST ORDER BLOCKS")
print("="*80)
print()

# Init MT5
print("Initialisation MT5...")
if not mt5.initialize():
    print("❌ MT5 failed")
    sys.exit(1)
print("✅ MT5 OK")
print()

# Charger données
print("📥 Chargement NAS100 M1 (1000 bars)...")
rates = mt5.copy_rates_from_pos("NAS100", mt5.TIMEFRAME_M1, 0, 1000)

if rates is None or len(rates) == 0:
    print("❌ Pas de données")
    mt5.shutdown()
    sys.exit(1)

# Convertir en DataFrame
candles = pd.DataFrame(rates)
candles['time'] = pd.to_datetime(candles['time'], unit='s')

print(f"✅ {len(candles)} bars chargées")
print(f"   Période: {candles.iloc[0]['time']} → {candles.iloc[-1]['time']}")
print()

# Tester l'indicateur
print("🔍 Test Order Blocks...")
print("-" * 80)

params = {
    'swing_length': 10,
    'min_body_size': 2.0,
    'imbalance_bars': 3,
    'max_zones': 15
}

print(f"Paramètres:")
for k, v in params.items():
    print(f"  {k}: {v}")
print()

indicator = OrderBlockIndicator(params)
indicator.timeframe = 'M1'

result = indicator.calculate(candles)

print("📊 Résultats:")
print(f"  Total objets: {len(result.objects)}")
print(f"  Séries: {len(result.series)}")
print()

# Analyser les zones
zones = [obj for obj in result.objects]

if len(zones) == 0:
    print("⚠️  AUCUNE ZONE DÉTECTÉE")
    print()
    print("Vérifications:")
    print("  1. Les paramètres sont-ils trop stricts ?")
    print("  2. Y a-t-il des swings dans les données ?")
    print("  3. Y a-t-il des imbalances ?")
    print()
    
    # Stats basiques
    print("Stats données:")
    print(f"  Prix min: {candles['low'].min():.2f}")
    print(f"  Prix max: {candles['high'].max():.2f}")
    print(f"  Amplitude: {candles['high'].max() - candles['low'].min():.2f}")
    
    body_sizes = abs(candles['close'] - candles['open'])
    print(f"  Body moyen: {body_sizes.mean():.2f}")
    print(f"  Body max: {body_sizes.max():.2f}")
    print(f"  Bougies > {params['min_body_size']}: {(body_sizes > params['min_body_size']).sum()}")
    
else:
    print(f"✅ {len(zones)} ZONES DÉTECTÉES")
    print()
    
    # Compter par type
    bullish = [z for z in zones if z.metadata.get('direction') == 'bullish']
    bearish = [z for z in zones if z.metadata.get('direction') == 'bearish']
    active = [z for z in zones if z.state == 'active']
    invalidated = [z for z in zones if z.state == 'invalidated']
    
    print("Répartition:")
    print(f"  Bullish: {len(bullish)}")
    print(f"  Bearish: {len(bearish)}")
    print(f"  Actives: {len(active)}")
    print(f"  Invalidées: {len(invalidated)}")
    print()
    
    # Stats mitigation
    if zones:
        avg_mitigation = sum(z.mitigation_score for z in zones) / len(zones)
        max_mitigation = max(z.mitigation_score for z in zones)
        print(f"Mitigation:")
        print(f"  Score moyen: {avg_mitigation:.2f}")
        print(f"  Score max: {max_mitigation:.2f}")
        print()
    
    # Afficher quelques zones
    print("Détail des zones (5 premières):")
    print("-" * 80)
    
    for i, zone in enumerate(zones[:5], 1):
        direction = zone.metadata.get('direction', 'unknown')
        state = zone.state
        
        print(f"\n{i}. Zone {zone.id}")
        print(f"   Direction: {direction}")
        print(f"   État: {state}")
        print(f"   Low: {zone.low:.2f}")
        print(f"   High: {zone.high:.2f}")
        print(f"   Amplitude: {zone.high - zone.low:.2f} points")
        print(f"   Temps création: {zone.t_start}")
        
        if zone.t_end:
            print(f"   Temps invalidation: {zone.t_end}")
        
        # NOUVEAU: Infos mitigation
        print(f"   Mitigation count: {zone.mitigation_count}")
        print(f"   Mitigation score: {zone.mitigation_score:.2f}")
        if zone.last_mitigation_index:
            print(f"   Dernière touche: bougie {zone.last_mitigation_index}")
        
        body_size = zone.metadata.get('body_size', 0)
        print(f"   Body size: {body_size:.2f}")

print()
print("="*80)
print("FIN DU TEST")
print("="*80)

mt5.shutdown()

input("\nAppuie sur Entrée pour quitter...")
