#!/usr/bin/env python
"""
DASHBOARD SIMPLE - Lance directement chart_viewer (pas de subprocess)

Version simplifiée qui évite les problèmes d'encodage subprocess sur Windows.
"""

import sys
import yaml
from pathlib import Path
from datetime import datetime

# Import direct du chart_viewer
sys.path.insert(0, str(Path(__file__).parent))
from visualization.chart_viewer import generate_chart_html

print("="*80)
print("📊 DASHBOARD SIMPLE - TEST INDICATEURS".center(80))
print("="*80)
print()

# Presets
PRESETS = {
    '1': {
        'name': 'Test Minimal (EMA)',
        'symbol': 'NAS100',
        'timeframe': 'M1',
        'n_bars': 500,
        'indicators': [
            {
                'name': 'ema_20',
                'module': 'ema.py',
                'timeframe': 'M1',
                'panel': 'main',
                'params': {'period': 20},
                'style': {'color': '#2196F3', 'linewidth': 2}
            }
        ]
    },
    '2': {
        'name': 'Test Order Blocks',
        'symbol': 'NAS100',
        'timeframe': 'M1',
        'n_bars': 1000,
        'indicators': [
            {
                'name': 'ema_20',
                'module': 'ema.py',
                'timeframe': 'M1',
                'panel': 'main',
                'params': {'period': 20},
                'style': {'color': '#2196F3', 'linewidth': 2}
            },
            {
                'name': 'order_blocks',
                'module': 'order_blocks.py',
                'timeframe': 'M1',
                'panel': 'main',
                'params': {
                    'min_body_size': 2.0,
                    'lookback': 100,
                    'max_zones': 15
                }
            }
        ]
    },
    '3': {
        'name': 'Test Structure (BOS/CHOCH)',
        'symbol': 'NAS100',
        'timeframe': 'M1',
        'n_bars': 1000,
        'indicators': [
            {
                'name': 'ema_20',
                'module': 'ema.py',
                'timeframe': 'M1',
                'panel': 'main',
                'params': {'period': 20},
                'style': {'color': '#2196F3', 'linewidth': 2}
            },
            {
                'name': 'bos_choch',
                'module': 'bos_choch.py',
                'timeframe': 'M1',
                'panel': 'main',
                'params': {
                    'swing_length': 10,
                    'min_break_pct': 0.001
                }
            }
        ]
    },
    '4': {
        'name': 'Test Complet',
        'symbol': 'NAS100',
        'timeframe': 'M1',
        'n_bars': 2000,
        'indicators': [
            {
                'name': 'ema_20',
                'module': 'ema.py',
                'timeframe': 'M1',
                'panel': 'main',
                'params': {'period': 20},
                'style': {'color': '#2196F3', 'linewidth': 2}
            },
            {
                'name': 'order_blocks',
                'module': 'order_blocks.py',
                'timeframe': 'M1',
                'panel': 'main',
                'params': {
                    'min_body_size': 2.0,
                    'lookback': 100,
                    'max_zones': 15
                }
            },
            {
                'name': 'bos_choch',
                'module': 'bos_choch.py',
                'timeframe': 'M1',
                'panel': 'main',
                'params': {
                    'swing_length': 10,
                    'min_break_pct': 0.001
                }
            },
            {
                'name': 'zone_aggregator',
                'module': 'zone_aggregator.py',
                'timeframe': 'M1',
                'panel': 'bottom_1',
                'params': {
                    'sources': [
                        {'indicator': 'order_blocks', 'type': 'order_block'}
                    ]
                },
                'style': {'color': '#FF9800', 'linewidth': 2}
            }
        ]
    },
    '5': {
        'name': 'Historique Complet NAS100 M1',
        'symbol': 'NAS100',
        'timeframe': 'M1',
        'n_bars': 50000,  # Réduit pour éviter dépassement historique
        'indicators': [
            {
                'name': 'ema_20',
                'module': 'ema.py',
                'timeframe': 'M1',
                'panel': 'main',
                'params': {'period': 20},
                'style': {'color': '#2196F3', 'linewidth': 2}
            },
            {
                'name': 'order_blocks',
                'module': 'order_blocks.py',
                'timeframe': 'M1',
                'panel': 'main',
                'params': {
                    'min_body_size': 2.0,
                    'lookback': 100,
                    'max_zones': 15
                }
            },
            {
                'name': 'bos_choch',
                'module': 'bos_choch.py',
                'timeframe': 'M1',
                'panel': 'main',
                'params': {
                    'swing_length': 10,
                    'min_break_pct': 0.001
                }
            }
        ]
    }
}

# Afficher menu
print("PRESETS DISPONIBLES")
print("-" * 80)
for key, preset in PRESETS.items():
    print(f"{key}. {preset['name']}")
    print(f"   - Symbole: {preset['symbol']}")
    print(f"   - Timeframe: {preset['timeframe']}")
    print(f"   - Bars: {preset['n_bars']}")
    print(f"   - Indicateurs: {len(preset['indicators'])}")
    print()

print("0. Quitter")
print()

choice = input("Choix (0-5): ").strip()

if choice == '0':
    print("Au revoir!")
    sys.exit(0)

if choice not in PRESETS:
    print(f"Erreur: Choix '{choice}' invalide")
    sys.exit(1)

preset = PRESETS[choice]

print()
print("="*80)
print(f"LANCEMENT: {preset['name']}")
print("="*80)
print()

# Créer config
config = {
    'data': {
        'source': 'mt5',
        'symbol': preset['symbol'],
        'main_timeframe': preset['timeframe'],
        'n_bars': preset['n_bars']
    },
    'indicators': preset['indicators'],
    'display': {
        'show_inactive_zones': True  # Afficher toutes les zones (actives ET mitigées)
    }
}

# Sauvegarder config
config_dir = Path('configs_test')
config_dir.mkdir(exist_ok=True)
config_file = config_dir / f"preset_{choice}.yaml"

with open(config_file, 'w', encoding='utf-8') as f:
    yaml.dump(config, f, default_flow_style=False, allow_unicode=True)

print(f"Config creee: {config_file}")
print()

# Lancer chart_viewer DIRECTEMENT (pas de subprocess)
try:
    generate_chart_html(str(config_file))
    print()
    print("="*80)
    print("SUCCES! Chart genere".center(80))
    print("="*80)
    print()
    print("Ouvre: output/chart_viewer.html")
    print()
except Exception as e:
    print()
    print("="*80)
    print("ERREUR".center(80))
    print("="*80)
    print()
    print(f"Erreur: {e}")
    import traceback
    traceback.print_exc()

input("\nAppuie sur Entree pour continuer...")
