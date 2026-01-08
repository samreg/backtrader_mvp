#!/usr/bin/env python3
"""
TEST BOS/CHOCH - Vérification de l'indicateur

Teste l'indicateur BOS/CHOCH avec des données synthétiques
pour vérifier qu'il fonctionne correctement avant utilisation réelle.
"""

import sys
import pandas as pd
import numpy as np
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

# Importer depuis le fichier téléchargé
# Note: Assure-toi que bos_choch.py est dans visualization/indicators/
try:
    from visualization.indicators.bos_choch import Indicator as BOSCHOCHIndicator
except ImportError:
    print("❌ ERREUR: Copie bos_choch.py dans visualization/indicators/")
    sys.exit(1)

from core.models import LinePrimitive


def create_test_data():
    """Crée des données avec des swings clairs"""
    dates = pd.date_range('2024-01-01', periods=300, freq='3min')
    
    # Pattern zigzag pour créer des swings évidents
    base = 25000
    prices = []
    for i in range(300):
        # Vagues pour créer hauts et bas
        wave = np.sin(i * 0.1) * 100
        trend = i * 0.5
        noise = np.random.randn() * 5
        prices.append(base + wave + trend + noise)
    
    prices = np.array(prices)
    
    df = pd.DataFrame({
        'time': dates,
        'open': prices,
        'high': prices + np.random.rand(300) * 10,
        'low': prices - np.random.rand(300) * 10,
        'close': prices + np.random.randn(300) * 5,
        'volume': np.random.randint(100, 1000, 300)
    })
    
    return df


def test_bos_choch():
    print("\n" + "="*70)
    print("TEST BOS/CHOCH INDICATOR")
    print("="*70)
    
    # Test 1: Créer données
    print("\n✅ Test 1: Création de données test")
    candles = create_test_data()
    print(f"   {len(candles)} bougies créées")
    
    # Test 2: Initialiser indicateur (validation wick)
    print("\n✅ Test 2: Initialisation avec validation 'wick'")
    indicator_wick = BOSCHOCHIndicator({
        'swing_period': 5,
        'break_validation': 'wick',
        'detect_bos': True
    })
    print("   Indicateur initialisé")
    
    # Test 3: Calculer
    print("\n✅ Test 3: Calcul BOS (validation wick)")
    result_wick = indicator_wick.calculate(candles)
    print(f"   Primitives générées : {len(result_wick.primitives)}")
    
    # Vérifications
    assert len(result_wick.primitives) > 0, "Devrait détecter au moins un BOS"
    assert all(isinstance(p, LinePrimitive) for p in result_wick.primitives), \
        "Toutes les primitives doivent être des LinePrimitive"
    
    # Analyser résultats
    bullish = sum(1 for p in result_wick.primitives if p.metadata.get('direction') == 'bullish')
    bearish = sum(1 for p in result_wick.primitives if p.metadata.get('direction') == 'bearish')
    
    print(f"   • BOS Bullish : {bullish}")
    print(f"   • BOS Bearish : {bearish}")
    
    # Test 4: Vérifier structure des primitives
    print("\n✅ Test 4: Vérification structure des primitives")
    sample = result_wick.primitives[0]
    
    # Vérifier que c'est bien horizontal
    assert sample.price_start == sample.price_end, \
        "BOS doit être une ligne horizontale"
    print("   ✓ Ligne horizontale")
    
    # Vérifier couleur
    assert sample.color in ['#26a69a', '#8B0000'], \
        "Couleur doit être verte ou bordeaux"
    print(f"   ✓ Couleur: {sample.color}")
    
    # Vérifier label
    assert sample.label in ['BOS ↑', 'BOS ↓'], \
        "Label doit être 'BOS ↑' ou 'BOS ↓'"
    print(f"   ✓ Label: {sample.label}")
    
    # Vérifier metadata
    assert 'swing_price' in sample.metadata, \
        "Metadata doit contenir swing_price"
    assert 'validation' in sample.metadata, \
        "Metadata doit contenir validation"
    print("   ✓ Metadata complète")
    
    # Test 5: Validation 'close'
    print("\n✅ Test 5: Calcul BOS (validation close)")
    indicator_close = BOSCHOCHIndicator({
        'swing_period': 5,
        'break_validation': 'close',
        'detect_bos': True
    })
    result_close = indicator_close.calculate(candles)
    print(f"   Primitives générées : {len(result_close.primitives)}")
    
    # Validation 'close' devrait être plus stricte (moins de BOS)
    print(f"\n📊 Comparaison validations:")
    print(f"   • 'wick' : {len(result_wick.primitives)} BOS")
    print(f"   • 'close': {len(result_close.primitives)} BOS")
    print(f"   → 'close' plus conservateur : {len(result_close.primitives) <= len(result_wick.primitives)}")
    
    # Test 6: Afficher un exemple
    print("\n📋 Exemple de primitive BOS:")
    example = result_wick.primitives[0]
    print(f"   ID: {example.id}")
    print(f"   Indices: {example.time_start_index} → {example.time_end_index}")
    print(f"   Prix: {example.price_start:.2f} (horizontal)")
    print(f"   Couleur: {example.color}")
    print(f"   Label: {example.label}")
    print(f"   Direction: {example.metadata['direction']}")
    print(f"   Validation: {example.metadata['validation']}")
    
    print("\n" + "="*70)
    print("✅ TOUS LES TESTS PASSÉS !")
    print("="*70)
    
    print("\n🎯 L'indicateur BOS/CHOCH fonctionne correctement")
    print("   Tu peux maintenant l'utiliser avec tes données réelles MT5")
    
    print("\n📝 Prochaines étapes:")
    print("   1. Copie bos_choch.py dans visualization/indicators/")
    print("   2. Utilise config_real.yaml pour configurer")
    print("   3. Lance: python analyze_real.py")
    print("="*70 + "\n")


if __name__ == "__main__":
    try:
        test_bos_choch()
    except AssertionError as e:
        print(f"\n❌ TEST ÉCHOUÉ: {e}")
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ ERREUR: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
