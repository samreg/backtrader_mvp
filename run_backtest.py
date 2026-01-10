#!/usr/bin/env python3
"""
RUN BACKTEST - Workflow Complet
--------------------------------
1. Assure données disponibles (MT5 si nécessaire)
2. Lance backtest
3. Génère HTML
4. Ouvre automatiquement le navigateur

Usage:
    python run_backtest.py [config_file.yaml]
"""

import os
import sys
from pathlib import Path
import yaml
import webbrowser
import subprocess
import platform

# Import stratégie
from strategies.strategy_rsi_amplitude import RSIAmplitudeStrategy

# Import module MT5
from data.mt5_loader import ensure_data_file


def run_backtest(data_file, config_file='config_rsi_amplitude.yaml'):
    """
    Lance le backtest
    
    Args:
        data_file: Chemin du fichier de données
        config_file: Fichier de configuration stratégie
    
    Returns:
        bool: Success
    """
    
    print("\n" + "="*70)
    print("🚀 BACKTEST")
    print("="*70 + "\n")
    
    # Charger config
    with open(config_file, 'r', encoding='utf-8') as f:
        config = yaml.safe_load(f)
    
    print(f"📋 Configuration: {config_file}")
    print(f"📊 Données: {data_file}")
    
    # Forcer UTF-8 pour Windows
    import os
    env = os.environ.copy()
    env['PYTHONIOENCODING'] = 'utf-8'
    
    # Lancer backtest via subprocess (pour avoir l'output complet)
    print("\n" + "-"*70)
    result = subprocess.run(
        [sys.executable, 'main_backtest_generic.py', config_file],  # ← Moteur générique
        capture_output=False,
        text=True,
        encoding='utf-8',
        errors='replace',
        env=env
    )
    
    if result.returncode != 0:
        print("\n❌ Erreur backtest")
        return False
    
    print("-"*70)
    print("\n✅ Backtest terminé\n")
    
    return True


def generate_html(config_file='config_rsi_amplitude.yaml'):
    """
    Génère le dashboard HTML
    
    Args:
        config_file: Fichier de configuration à utiliser
    
    Returns:
        str: Chemin du fichier HTML
    """
    
    print("\n" + "="*70)
    print("🌐 GÉNÉRATION DASHBOARD HTML")
    print("="*70 + "\n")
    
    # Forcer UTF-8 pour Windows
    import os
    env = os.environ.copy()
    env['PYTHONIOENCODING'] = 'utf-8'
    
    # Note: Heatmaps temporelles sont maintenant générées directement dans generate_html_complete.py
    # L'appel à step3_temporal_heatmaps.py (supprimé) n'est plus nécessaire
    print("🔥 Génération heatmaps temporelles... (intégré dans HTML)")
    
    # Étape 2: Générer HTML dashboard
    print("📊 Génération dashboard HTML...")
    result = subprocess.run(
        [sys.executable, 'generate_html_complete.py', config_file],  # ← Passer config_file
        capture_output=True,
        text=True,
        encoding='utf-8',
        errors='replace',
        env=env  # ← UTF-8
    )
    
    # Debug
    print(f"   🔍 Return code: {result.returncode}")
    if result.stdout:
        print(f"   📄 Output: {result.stdout[:200]}")
    if result.stderr:
        print(f"   ⚠️  Stderr: {result.stderr[:200]}")
    
    if result.returncode != 0:
        print("❌ Erreur génération HTML")
        if result.stderr:
            print(result.stderr)
        return None
    
    html_file = 'output/visualization_complete.html'
    
    print(f"   🔍 Vérification fichier: {html_file}")
    print(f"   🔍 Existe? {Path(html_file).exists()}")
    
    if Path(html_file).exists():
        print(f"✅ Dashboard généré: {html_file}\n")
        return html_file
    else:
        print("❌ Fichier HTML non trouvé")
        # Lister ce qui est dans output/
        import os
        if os.path.exists('output'):
            files = os.listdir('output')
            print(f"   📂 Contenu output/: {files}")
        return None


def open_html(html_path):
    """
    Ouvre le HTML dans le navigateur
    
    Args:
        html_path: Chemin du fichier HTML
    
    Returns:
        bool: Success
    """
    
    print("="*70)
    print("🌍 OUVERTURE NAVIGATEUR")
    print("="*70 + "\n")
    
    html_path = Path(html_path).resolve()
    
    if not html_path.exists():
        print(f"❌ Fichier introuvable: {html_path}")
        return False
    
    print(f"📂 Fichier: {html_path}")
    
    try:
        # Méthode 1: webbrowser
        webbrowser.open(f'file://{html_path}')
        print("✅ Dashboard ouvert dans le navigateur !\n")
        return True
        
    except Exception as e:
        print(f"⚠️  Erreur webbrowser: {e}")
        
        # Méthode 2: Commandes système
        try:
            system = platform.system()
            
            if system == 'Darwin':  # macOS
                subprocess.run(['open', str(html_path)], check=True)
            elif system == 'Windows':
                subprocess.run(['start', str(html_path)], shell=True, check=True)
            elif system == 'Linux':
                subprocess.run(['xdg-open', str(html_path)], check=True)
            else:
                print(f"⚠️  OS non supporté: {system}")
                print(f"👉 Ouvrez manuellement: {html_path}")
                return False
            
            print("✅ Dashboard ouvert !\n")
            return True
            
        except Exception as e2:
            print(f"⚠️  Erreur: {e2}")
            print(f"👉 Ouvrez manuellement: {html_path}\n")
            return False


def main():
    """Point d'entrée principal"""
    
    print("\n" + "🚀"*35)
    print("WORKFLOW COMPLET - Backtest MT5")
    print("🚀"*35 + "\n")
    
    # Charger configuration
    import sys
    config_file = sys.argv[1] if len(sys.argv) > 1 else 'config_rsi_amplitude.yaml'
    
    if not Path(config_file).exists():
        print(f"❌ Fichier config non trouvé: {config_file}")
        print("\n💡 Usage: python run_backtest.py [config_file.yaml]")
        print("\n📋 Configs disponibles:")
        for f in sorted(Path('.').glob('config_*.yaml')):
            print(f"   - {f.name}")
        return
    
    print(f"📋 Config sélectionnée: {config_file}\n")
    
    with open(config_file, 'r', encoding='utf-8') as f:
        config = yaml.safe_load(f)
    
    # Extraire paramètres
    symbol = config['data']['symbol']
    main_timeframe = config['data']['main_timeframe']
    months = config['data']['months']
    auto_html = config['execution']['auto_html']
    auto_open_browser = config['execution']['auto_open_browser']
    
    print("📋 Configuration:")
    print(f"   Config: {config_file}")
    print(f"   Symbole: {symbol}")
    print(f"   main_timeframe: {main_timeframe}")
    print(f"   Historique: {months} mois")
    
    # ÉTAPE 1: Assurer fichier de données existe
    print("\n" + "="*70)
    print("📥 VÉRIFICATION DONNÉES")
    print("="*70 + "\n")
    
    try:
        data_file = ensure_data_file(config)
    except (FileNotFoundError, ConnectionError, ValueError) as e:
        print(f"\n❌ Erreur données: {e}")
        return
    
    print(f"\n✅ Fichier données prêt: {data_file}")
    
    # ÉTAPE 2: Backtest
    if not run_backtest(data_file, config_file):
        print("\n❌ Workflow interrompu")
        return
    
    # ÉTAPE 3: Générer HTML
    if auto_html:
        html_file = generate_html(config_file)
        if not html_file:
            print("\n⚠️  Dashboard HTML non généré")
            print("   Mais le backtest est terminé !")
            return
        
        # ÉTAPE 4: Ouvrir navigateur
        if auto_open_browser:
            open_html(html_file)
        else:
            print(f"\n📂 Dashboard généré: {html_file}")
            print("   (auto_open_browser désactivé)")
    else:
        print("\n💡 HTML désactivé (auto_html=false)")
        print("   Pour générer: python generate_html_complete.py")
    
    # Résumé
    print("="*70)
    print("✅ WORKFLOW TERMINÉ")
    print("="*70)
    print(f"\n📊 Config: {config_file}")
    print(f"📈 Données: {data_file}")
    print(f"📋 Résultats: output/trades_backtest.csv")
    if auto_html:
        print(f"🌐 Dashboard: output/visualization_complete.html")
    print("\n" + "="*70 + "\n")


if __name__ == "__main__":
    main()
