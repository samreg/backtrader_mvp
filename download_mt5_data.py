#!/usr/bin/env python3
"""
Script CLI pour télécharger manuellement des données MT5
WRAPPER autour de data/mt5_loader.py
"""

from data.mt5_loader import MT5Loader, get_data_filename
import MetaTrader5 as mt5
from pathlib import Path
import argparse


def main():
    parser = argparse.ArgumentParser(description="Télécharger données MT5")
    parser.add_argument('--symbol', default='NAS100', help='Symbole (défaut: NAS100)')
    parser.add_argument('--timeframe', default='M3', help='Timeframe (défaut: M3)')
    parser.add_argument('--months', type=int, default=6, help='Mois d\'historique (défaut: 6)')

    args = parser.parse_args()

    print("\n" + "=" * 80)
    print("📥 TÉLÉCHARGEMENT DONNÉES MT5")
    print("=" * 80)
    print(f"\n📋 Configuration:")
    print(f"   Symbole: {args.symbol}")
    print(f"   Timeframe: {args.timeframe}")
    print(f"   Période: {args.months} mois")

    response = input("\nContinuer ? (o/n) : ")
    if response.lower() != 'o':
        print("\n❌ Annulé")
        return

    # Utiliser MT5Loader
    loader = MT5Loader()

    if not loader.initialize():
        print("❌ Impossible de se connecter à MT5")
        return

    try:
        # Télécharger
        df = loader.download_historical(
            symbol=args.symbol,
            timeframe_str=args.timeframe,
            months=args.months
        )

        # Sauvegarder
        filename = get_data_filename(args.symbol, args.timeframe)
        filepath = Path('data') / filename
        filepath.parent.mkdir(exist_ok=True)

        df.to_csv(filepath, index=False)

        size_mb = filepath.stat().st_size / 1024 / 1024

        print("\n" + "=" * 80)
        print("✅ SUCCÈS")
        print("=" * 80)
        print(f"\n💾 Fichier: {filepath}")
        print(f"   Taille: {size_mb:.2f} MB")
        print(f"   Chandelles: {len(df):,}")
        print(f"\n🚀 Prêt pour le backtest !")

    finally:
        loader.shutdown()


if __name__ == "__main__":
    main()