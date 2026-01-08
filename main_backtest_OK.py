#!/usr/bin/env python3
"""
MAIN BACKTEST - Sélecteur de configurations

Liste tous les fichiers YAML et lance le backtest.
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

# Importer ton système de backtest
# À adapter selon ton architecture existante
try:
    from backtest.backtest_engine import run_backtest
    BACKTEST_AVAILABLE = True
except ImportError:
    BACKTEST_AVAILABLE = False


def main():
    print("\n" + "="*70)
    print("📈 BACKTEST - Sélection de configuration")
    print("="*70 + "\n")
    
    if not BACKTEST_AVAILABLE:
        print("❌ Module backtest non trouvé")
        print("💡 Crée backtest/backtest_engine.py d'abord")
        sys.exit(1)
    
    # Trouver tous les fichiers YAML
    yaml_files = sorted(Path('.').glob('config*.yaml'))
    
    if not yaml_files:
        print("❌ Aucun fichier config*.yaml trouvé")
        print("💡 Crée un fichier config_xxx.yaml d'abord")
        sys.exit(1)
    
    # Afficher la liste
    print("📋 Configurations disponibles:\n")
    for i, file in enumerate(yaml_files, 1):
        print(f"   {i}. {file.name}")
    
    # Demander sélection
    print()
    try:
        choice = int(input("Sélectionne un numéro: "))
        if choice < 1 or choice > len(yaml_files):
            print("❌ Numéro invalide")
            sys.exit(1)
    except (ValueError, KeyboardInterrupt):
        print("\n❌ Annulé")
        sys.exit(0)
    
    selected = yaml_files[choice - 1]
    
    print(f"\n✅ Configuration sélectionnée: {selected.name}")
    print("\n🔄 Lancement du backtest...")
    
    try:
        # Lancer backtest
        results = run_backtest(str(selected))
        
        print("\n" + "="*70)
        print("✅ BACKTEST TERMINÉ")
        print("="*70)
        
        # Afficher résultats
        if results:
            print("\n📊 Résultats:")
            for key, value in results.items():
                print(f"   • {key}: {value}")
        
        print("\n📁 Voir output/ pour détails")
        print("="*70 + "\n")
        
    except Exception as e:
        print(f"\n❌ ERREUR: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
