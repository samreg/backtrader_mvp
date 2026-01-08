#!/usr/bin/env python
"""
🎨 DASHBOARD INTERACTIF - TEST INDICATEURS

Lance chart_viewer avec différentes configs pour tester tous les indicateurs.
"""

import sys
import subprocess
import yaml
from pathlib import Path
from datetime import datetime

# Colors for terminal
class Colors:
    HEADER = '\033[95m'
    BLUE = '\033[94m'
    CYAN = '\033[96m'
    GREEN = '\033[92m'
    YELLOW = '\033[93m'
    RED = '\033[91m'
    END = '\033[0m'
    BOLD = '\033[1m'

def print_header(text):
    print(f"\n{Colors.BOLD}{Colors.CYAN}{'='*80}{Colors.END}")
    print(f"{Colors.BOLD}{Colors.CYAN}{text.center(80)}{Colors.END}")
    print(f"{Colors.BOLD}{Colors.CYAN}{'='*80}{Colors.END}\n")

def print_section(text):
    print(f"\n{Colors.BOLD}{Colors.YELLOW}{text}{Colors.END}")
    print(f"{Colors.YELLOW}{'-'*len(text)}{Colors.END}")

def print_success(text):
    print(f"{Colors.GREEN}✅ {text}{Colors.END}")

def print_error(text):
    print(f"{Colors.RED}❌ {text}{Colors.END}")

def print_info(text):
    print(f"{Colors.BLUE}ℹ️  {text}{Colors.END}")

# Liste des indicateurs disponibles
AVAILABLE_INDICATORS = {
    'ema': {
        'name': 'EMA (Exponential Moving Average)',
        'module': 'ema.py',
        'description': 'Moyenne mobile exponentielle',
        'params': {
            'period': 20
        },
        'panel': 'main',
        'style': {'color': '#2196F3', 'linewidth': 2}
    },
    'order_blocks': {
        'name': 'Order Blocks',
        'module': 'order_blocks.py',
        'description': 'Zones de retournement (Smart Money Concepts)',
        'params': {
            'min_body_size': 2.0,
            'lookback': 100,
            'max_zones': 15
        },
        'panel': 'main',
        'style': {}
    },
    'bos_choch': {
        'name': 'BOS/CHOCH',
        'module': 'bos_choch.py',
        'description': 'Break of Structure / Change of Character',
        'params': {
            'swing_length': 10,
            'min_break_pct': 0.001
        },
        'panel': 'main',
        'style': {}
    },
    'zone_aggregator': {
        'name': 'Zone Aggregator',
        'module': 'zone_aggregator.py',
        'description': 'Agrégateur de zones multi-timeframes',
        'params': {
            'sources': []  # Sera rempli dynamiquement
        },
        'panel': 'bottom_1',
        'style': {'color': '#FF9800', 'linewidth': 2}
    }
}

def create_config(symbol, timeframe, n_bars, indicators_list):
    """
    Crée une config YAML avec les indicateurs sélectionnés
    
    Args:
        symbol: Symbole (ex: "NAS100")
        timeframe: Timeframe (ex: "M1")
        n_bars: Nombre de bars
        indicators_list: Liste des indicateurs à inclure
    
    Returns:
        dict: Configuration
    """
    config = {
        'data': {
            'source': 'mt5',
            'symbol': symbol,
            'main_timeframe': timeframe,
            'n_bars': n_bars
        },
        'indicators': [],
        'display': {
            'show_inactive_zones': False
        }
    }
    
    # Ajouter les indicateurs sélectionnés
    for ind_key in indicators_list:
        if ind_key not in AVAILABLE_INDICATORS:
            continue
        
        ind_info = AVAILABLE_INDICATORS[ind_key]
        
        indicator_config = {
            'name': f"{ind_key}_{timeframe}",
            'module': ind_info['module'],
            'timeframe': timeframe,
            'panel': ind_info['panel'],
            'params': ind_info['params'].copy()
        }
        
        if ind_info['style']:
            indicator_config['style'] = ind_info['style']
        
        config['indicators'].append(indicator_config)
    
    # Si zone_aggregator est inclus, configurer ses sources
    for ind_config in config['indicators']:
        if 'zone_aggregator' in ind_config['name']:
            # Trouver tous les order_blocks
            sources = []
            for other_ind in config['indicators']:
                if 'order_blocks' in other_ind['name']:
                    sources.append({
                        'indicator': other_ind['name'],
                        'type': 'order_block'
                    })
            ind_config['params']['sources'] = sources
    
    return config

def save_config(config, filename):
    """Sauvegarde la config dans un fichier YAML"""
    config_path = Path('configs_test') / filename
    config_path.parent.mkdir(exist_ok=True)
    
    with open(config_path, 'w', encoding='utf-8') as f:
        yaml.dump(config, f, default_flow_style=False, allow_unicode=True)
    
    return config_path

def run_chart_viewer(config_path):
    """Lance chart_viewer avec la config"""
    try:
        # Option 1: Try with output capture (UTF-8)
        result = subprocess.run(
            ['python', 'visualization/chart_viewer.py', str(config_path)],
            capture_output=True,
            text=True,
            encoding='utf-8',  # Force UTF-8 encoding
            errors='replace',   # Replace invalid chars instead of crashing
            timeout=120  # 2 minutes max
        )
        
        if result.returncode == 0:
            return True, result.stdout
        else:
            return False, result.stderr
    
    except (UnicodeDecodeError, UnicodeEncodeError) as e:
        # Fallback: Run without capturing output (encoding issues)
        print_info("Encoding issue, running without output capture...")
        try:
            result = subprocess.run(
                ['python', 'visualization/chart_viewer.py', str(config_path)],
                timeout=120
            )
            if result.returncode == 0:
                return True, "Chart generated (output not captured due to encoding)"
            else:
                return False, "Failed (check console output above)"
        except Exception as e2:
            return False, str(e2)
    
    except subprocess.TimeoutExpired:
        return False, "Timeout (>2 minutes)"
    
    except Exception as e:
        return False, str(e)

def display_menu():
    """Affiche le menu principal"""
    print_header("🎨 DASHBOARD DE TEST - INDICATEURS")
    
    print_section("📊 INDICATEURS DISPONIBLES")
    for i, (key, info) in enumerate(AVAILABLE_INDICATORS.items(), 1):
        print(f"{Colors.BOLD}{i}. {info['name']}{Colors.END}")
        print(f"   Module: {info['module']}")
        print(f"   Description: {info['description']}")
        print(f"   Panel: {info['panel']}")
        print(f"   Params: {info['params']}")
        print()

def test_preset(preset_name):
    """Lance un test preset"""
    presets = {
        'minimal': {
            'name': 'Test Minimal (EMA)',
            'symbol': 'NAS100',
            'timeframe': 'M1',
            'n_bars': 500,
            'indicators': ['ema']
        },
        'order_blocks': {
            'name': 'Test Order Blocks',
            'symbol': 'NAS100',
            'timeframe': 'M1',
            'n_bars': 1000,
            'indicators': ['ema', 'order_blocks']
        },
        'structure': {
            'name': 'Test Structure (BOS/CHOCH)',
            'symbol': 'NAS100',
            'timeframe': 'M1',
            'n_bars': 1000,
            'indicators': ['ema', 'bos_choch']
        },
        'complete': {
            'name': 'Test Complet',
            'symbol': 'NAS100',
            'timeframe': 'M1',
            'n_bars': 2000,
            'indicators': ['ema', 'order_blocks', 'bos_choch', 'zone_aggregator']
        },
        'full_history': {
            'name': 'Historique Complet NAS100 M1',
            'symbol': 'NAS100',
            'timeframe': 'M1',
            'n_bars': 100000,  # MT5 retournera le max disponible
            'indicators': ['ema', 'order_blocks', 'bos_choch']
        }
    }
    
    if preset_name not in presets:
        print_error(f"Preset '{preset_name}' inconnu")
        return False
    
    preset = presets[preset_name]
    
    print_section(f"🚀 Lancement : {preset['name']}")
    print_info(f"Symbole: {preset['symbol']}")
    print_info(f"Timeframe: {preset['timeframe']}")
    print_info(f"Bars: {preset['n_bars']}")
    print_info(f"Indicateurs: {', '.join(preset['indicators'])}")
    print()
    
    # Créer config
    config = create_config(
        preset['symbol'],
        preset['timeframe'],
        preset['n_bars'],
        preset['indicators']
    )
    
    # Sauvegarder
    config_path = save_config(config, f"test_{preset_name}.yaml")
    print_success(f"Config créée: {config_path}")
    
    # Lancer chart_viewer
    print_info("Lancement de chart_viewer...")
    success, output = run_chart_viewer(config_path)
    
    if success:
        print_success("Chart généré avec succès!")
        print_info("Ouvre output/chart_viewer.html dans ton navigateur")
        return True
    else:
        print_error("Erreur lors de la génération")
        print(output)
        return False

def interactive_mode():
    """Mode interactif"""
    print_header("🎨 MODE INTERACTIF")
    
    # Sélection symbole
    print_section("1. SYMBOLE")
    symbol = input(f"{Colors.CYAN}Symbole (défaut: NAS100): {Colors.END}").strip() or "NAS100"
    
    # Sélection timeframe
    print_section("2. TIMEFRAME")
    print("Timeframes disponibles: M1, M3, M5, M15, M30, H1, H4, D1")
    timeframe = input(f"{Colors.CYAN}Timeframe (défaut: M1): {Colors.END}").strip() or "M1"
    
    # Nombre de bars
    print_section("3. NOMBRE DE BARS")
    n_bars_input = input(f"{Colors.CYAN}Nombre de bars (défaut: 2000): {Colors.END}").strip()
    n_bars = int(n_bars_input) if n_bars_input else 2000
    
    # Sélection indicateurs
    print_section("4. INDICATEURS")
    print("Indicateurs disponibles:")
    for i, (key, info) in enumerate(AVAILABLE_INDICATORS.items(), 1):
        print(f"  {i}. {key} - {info['name']}")
    
    print(f"\n{Colors.CYAN}Sélectionne les indicateurs (séparés par des virgules, ex: 1,2,3):{Colors.END}")
    print(f"{Colors.CYAN}Ou tape 'all' pour tous les sélectionner:{Colors.END}")
    selection = input("> ").strip()
    
    if selection.lower() == 'all':
        indicators = list(AVAILABLE_INDICATORS.keys())
    else:
        try:
            indices = [int(x.strip()) for x in selection.split(',')]
            indicators = [list(AVAILABLE_INDICATORS.keys())[i-1] for i in indices]
        except:
            print_error("Sélection invalide, utilisation de 'ema' par défaut")
            indicators = ['ema']
    
    print_success(f"Indicateurs sélectionnés: {', '.join(indicators)}")
    
    # Créer et lancer
    print_section("5. GÉNÉRATION")
    config = create_config(symbol, timeframe, n_bars, indicators)
    
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    config_path = save_config(config, f"custom_{timestamp}.yaml")
    print_success(f"Config créée: {config_path}")
    
    print_info("Lancement de chart_viewer...")
    success, output = run_chart_viewer(config_path)
    
    if success:
        print_success("Chart généré avec succès!")
        print_info("Ouvre output/chart_viewer.html dans ton navigateur")
    else:
        print_error("Erreur lors de la génération")
        print(output)

def main():
    """Menu principal"""
    print_header("🎨 DASHBOARD DE TEST - INDICATEURS")
    
    print_section("PRESETS DISPONIBLES")
    print(f"{Colors.BOLD}1.{Colors.END} Test Minimal (EMA seulement)")
    print(f"   • Symbole: NAS100")
    print(f"   • Timeframe: M1")
    print(f"   • Bars: 500")
    print(f"   • Indicateurs: EMA(20)")
    print()
    
    print(f"{Colors.BOLD}2.{Colors.END} Test Order Blocks")
    print(f"   • Symbole: NAS100")
    print(f"   • Timeframe: M1")
    print(f"   • Bars: 1000")
    print(f"   • Indicateurs: EMA + Order Blocks")
    print()
    
    print(f"{Colors.BOLD}3.{Colors.END} Test Structure (BOS/CHOCH)")
    print(f"   • Symbole: NAS100")
    print(f"   • Timeframe: M1")
    print(f"   • Bars: 1000")
    print(f"   • Indicateurs: EMA + BOS/CHOCH")
    print()
    
    print(f"{Colors.BOLD}4.{Colors.END} Test Complet")
    print(f"   • Symbole: NAS100")
    print(f"   • Timeframe: M1")
    print(f"   • Bars: 2000")
    print(f"   • Indicateurs: EMA + Order Blocks + BOS/CHOCH + Aggregator")
    print()
    
    print(f"{Colors.BOLD}5.{Colors.END} {Colors.GREEN}Historique Complet NAS100 M1{Colors.END}")
    print(f"   • Symbole: NAS100")
    print(f"   • Timeframe: M1")
    print(f"   • Bars: MAXIMUM DISPONIBLE (~100k)")
    print(f"   • Indicateurs: EMA + Order Blocks + BOS/CHOCH")
    print()
    
    print(f"{Colors.BOLD}6.{Colors.END} Mode Interactif (choisir manuellement)")
    print()
    
    print(f"{Colors.BOLD}0.{Colors.END} Quitter")
    print()
    
    choice = input(f"{Colors.CYAN}Choix (0-6): {Colors.END}").strip()
    
    if choice == '0':
        print("👋 Au revoir!")
        return
    
    elif choice == '1':
        test_preset('minimal')
    
    elif choice == '2':
        test_preset('order_blocks')
    
    elif choice == '3':
        test_preset('structure')
    
    elif choice == '4':
        test_preset('complete')
    
    elif choice == '5':
        test_preset('full_history')
    
    elif choice == '6':
        interactive_mode()
    
    else:
        print_error("Choix invalide")
    
    print()
    input(f"{Colors.CYAN}Appuie sur Entrée pour continuer...{Colors.END}")

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n\n👋 Interrupted by user")
    except Exception as e:
        print_error(f"Erreur: {e}")
        import traceback
        traceback.print_exc()
