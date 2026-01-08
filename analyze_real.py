#!/usr/bin/env python3
"""
ANALYSE RÉELLE NAS100 avec Order Blocks + BOS/CHOCH

Ce script génère une analyse visuelle complète de tes données MT5
avec le nouveau système de primitives génériques.

Usage:
    python analyze_real.py
    python analyze_real.py --config config_custom.yaml
    python analyze_real.py --symbol NAS100 --days 7
"""

import sys
import argparse
from pathlib import Path
from datetime import datetime, timedelta

# Add project to path
sys.path.insert(0, str(Path(__file__).parent))

from visualization.chart_viewer import generate_chart_html


def main():
    parser = argparse.ArgumentParser(
        description='Analyse SMC avec données réelles MT5'
    )
    parser.add_argument(
        '--config',
        default='config_real.yaml',
        help='Fichier de configuration YAML (défaut: config_real.yaml)'
    )
    parser.add_argument(
        '--symbol',
        help='Symbole à analyser (override config)'
    )
    parser.add_argument(
        '--days',
        type=int,
        help='Nombre de jours à analyser (override config)'
    )
    
    args = parser.parse_args()
    
    print("\n" + "="*70)
    print("📊 ANALYSE SMC - DONNÉES RÉELLES MT5")
    print("="*70)
    
    print(f"\n📄 Configuration : {args.config}")
    
    if args.symbol:
        print(f"📈 Symbole : {args.symbol}")
    
    if args.days:
        end_date = datetime.now()
        start_date = end_date - timedelta(days=args.days)
        print(f"📅 Période : {start_date.date()} → {end_date.date()}")
    
    print("\n🔄 Génération du chart...")
    
    try:
        # Générer le chart HTML
        html_output = generate_chart_html(args.config)
        
        print("\n✅ Analyse terminée avec succès !")
        print(f"📁 Fichier généré : output/nas100_analysis.html")
        print("\n🌐 Ouvre ce fichier dans un navigateur pour voir l'analyse")
        
        print("\n📊 Contenu affiché :")
        print("   • Bougies NAS100 M3")
        print("   • Order Blocks (rectangles verts/bordeaux)")
        print("   • BOS/CHOCH (lignes horizontales)")
        print("   • Zoom/Pan interactif")
        
        print("\n💡 Navigation :")
        print("   • Zoom : Molette souris")
        print("   • Pan : Glisser avec souris")
        print("   • Reset : Double-clic")
        
    except FileNotFoundError as e:
        print(f"\n❌ ERREUR : Fichier non trouvé")
        print(f"   {e}")
        print(f"\n💡 Assure-toi que le fichier {args.config} existe")
        sys.exit(1)
        
    except Exception as e:
        print(f"\n❌ ERREUR lors de la génération :")
        print(f"   {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
    
    print("="*70 + "\n")


if __name__ == "__main__":
    main()
