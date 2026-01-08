#!/usr/bin/env python3
"""
MAIN VISUALISATION - Sélecteur de configurations

Liste tous les fichiers YAML et génère la visualisation HTML.
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from visualization.chart_viewer import generate_chart_html


def main():
    print("\n" + "="*70)
    print("📊 VISUALISATION - Sélection de configuration")
    print("="*70 + "\n")
    
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
    print("\n🔄 Génération de la visualisation...")
    
    try:
        # Générer HTML
        generate_chart_html(str(selected))
        
        print("\n" + "="*70)
        print("✅ VISUALISATION GÉNÉRÉE")
        print("="*70)
        print(f"\n📁 Fichier: output/")
        print("🌐 Ouvre le fichier HTML dans un navigateur")
        print("="*70 + "\n")
        
    except Exception as e:
        print(f"\n❌ ERREUR: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
