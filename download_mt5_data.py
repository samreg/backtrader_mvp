#!/usr/bin/env python3
"""
RÉCUPÉRATION DONNÉES MT5 - NAS100 3min
---------------------------------------
Télécharge 6 mois d'historique depuis MT5
AUCUN TRADING - Juste récupération de données
"""

import MetaTrader5 as mt5
import pandas as pd
from datetime import datetime, timedelta
from pathlib import Path
import yaml


def download_mt5_data(symbol='NAS100', timeframe=mt5.TIMEFRAME_M3, months=6):
    """
    Télécharge les données historiques depuis MT5
    
    Args:
        symbol: Symbole à télécharger (défaut: NAS100)
        timeframe: Timeframe MT5 (défaut: M3 = 3 minutes)
        months: Nombre de mois d'historique (défaut: 6)
    
    Returns:
        DataFrame avec OHLCV
    """
    
    print("\n" + "="*80)
    print("📥 TÉLÉCHARGEMENT DONNÉES MT5")
    print("="*80 + "\n")
    
    # 1. Connexion MT5
    print("🔌 Connexion à MT5...")
    
    if not mt5.initialize():
        print(f"❌ Erreur MT5 initialize: {mt5.last_error()}")
        return None
    
    # Vérifier si login nécessaire
    account_info = mt5.account_info()
    if account_info is None:
        print("⚠️  Pas de compte connecté")
        
        # Essayer de charger config
        config_path = Path('config_mt5.yaml')
        if config_path.exists():
            with open(config_path, 'r') as f:
                config = yaml.safe_load(f)
            
            print(f"   Tentative login avec config_mt5.yaml...")
            authorized = mt5.login(
                login=config['account'],
                password=config['password'],
                server=config['server']
            )
            
            if not authorized:
                print(f"❌ Erreur login: {mt5.last_error()}")
                mt5.shutdown()
                return None
            
            print(f"✅ Connecté au compte {config['account']}")
        else:
            print("❌ Pas de config_mt5.yaml trouvée")
            print("   Ouvrez MT5 Desktop et connectez-vous manuellement")
            mt5.shutdown()
            return None
    else:
        print(f"✅ Déjà connecté au compte {account_info.login}")
    
    # 2. Vérifier symbole
    print(f"\n📊 Symbole: {symbol}")
    
    symbol_info = mt5.symbol_info(symbol)
    if symbol_info is None:
        print(f"❌ Symbole {symbol} introuvable")
        print("\n💡 Essayez:")
        print("   - 'USTEC' (IC Markets)")
        print("   - 'US100' (certains brokers)")
        print("   - 'NAS100.raw' (certains brokers)")
        mt5.shutdown()
        return None
    
    print(f"✅ Symbole trouvé: {symbol_info.name}")
    print(f"   Description: {symbol_info.description}")
    
    # 3. Calculer la période demandée
    to_date = datetime.now()
    from_date_requested = to_date - timedelta(days=months * 30)
    
    print(f"\n📅 Période demandée:")
    print(f"   De: {from_date_requested.strftime('%Y-%m-%d %H:%M')}")
    print(f"   À:  {to_date.strftime('%Y-%m-%d %H:%M')}")
    print(f"   ({months} mois)")
    
    # 4. Télécharger les données (avec fallback intelligent)
    print(f"\n⏳ Téléchargement en cours...")
    
    # Essayer d'abord avec la période demandée
    rates = mt5.copy_rates_range(symbol, timeframe, from_date_requested, to_date)
    
    if rates is None or len(rates) == 0:
        print(f"⚠️  Période demandée ({months} mois) dépasse l'historique disponible")
        print(f"   Récupération du MAXIMUM disponible...")
        
        # Stratégie 1: Utiliser copy_rates_from (récupère COUNT bougies à partir de to_date)
        # Estimer le nombre de bougies pour X mois
        timeframe_minutes = {
            mt5.TIMEFRAME_M1: 1,
            mt5.TIMEFRAME_M3: 3,
            mt5.TIMEFRAME_M5: 5,
            mt5.TIMEFRAME_M15: 15,
            mt5.TIMEFRAME_M30: 30,
            mt5.TIMEFRAME_H1: 60,
            mt5.TIMEFRAME_H4: 240,
            mt5.TIMEFRAME_D1: 1440,
        }.get(timeframe, 3)
        
        # Calculer nombre de bougies théoriques pour la période demandée
        # (en supposant 5 jours de trading par semaine, 24h/24 pour crypto)
        minutes_in_period = months * 30 * 24 * 60  # Total minutes
        estimated_candles = int(minutes_in_period / timeframe_minutes)
        
        # Limiter à 100k bougies max (limite MT5)
        estimated_candles = min(estimated_candles, 100000)
        
        print(f"   Tentative avec {estimated_candles:,} bougies...")
        rates = mt5.copy_rates_from(symbol, timeframe, to_date, estimated_candles)
        
        if rates is None or len(rates) == 0:
            print(f"❌ Pas de données disponibles même avec fallback")
            print(f"   Erreur MT5: {mt5.last_error()}")
            mt5.shutdown()
            return None
        
        print(f"✅ {len(rates):,} chandelles récupérées (MAXIMUM disponible)")
    else:
        print(f"✅ {len(rates):,} chandelles téléchargées")
    
    # 5. Convertir en DataFrame
    df = pd.DataFrame(rates)
    
    # Convertir timestamp en datetime
    df['datetime'] = pd.to_datetime(df['time'], unit='s')
    
    # Renommer colonnes
    df = df[['datetime', 'open', 'high', 'low', 'close', 'tick_volume']]
    df.columns = ['datetime', 'open', 'high', 'low', 'close', 'volume']
    
    # Trier par date
    df = df.sort_values('datetime').reset_index(drop=True)
    
    # Stats détaillées
    first_candle = df['datetime'].iloc[0]
    last_candle = df['datetime'].iloc[-1]
    actual_duration = last_candle - first_candle
    actual_days = actual_duration.days
    actual_months = actual_days / 30.0
    
    print(f"\n📊 Statistiques:")
    print(f"   Chandelles: {len(df):,}")
    print(f"   Première bougie: {first_candle.strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"   Dernière bougie:  {last_candle.strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"   Durée réelle: {actual_days} jours (~{actual_months:.1f} mois)")
    print(f"   Prix min: {df['low'].min():.2f}")
    print(f"   Prix max: {df['high'].max():.2f}")
    print(f"   Volume total: {df['volume'].sum():,.0f}")
    
    if actual_months < months * 0.8:  # Si moins de 80% de ce qui était demandé
        print(f"\n⚠️  Note: Historique limité à {actual_months:.1f} mois")
        print(f"   (demandé: {months} mois, disponible: {actual_months:.1f} mois)")
    
    # 6. Déconnexion
    mt5.shutdown()
    print(f"\n🔌 Déconnecté de MT5")
    
    return df


def save_data(df, filename='data/NAS100_M3.csv'):
    """
    Sauvegarde les données en CSV
    
    Args:
        df: DataFrame avec données
        filename: Nom du fichier
    """
    
    if df is None or len(df) == 0:
        print("❌ Pas de données à sauvegarder")
        return False
    
    # Créer répertoire si nécessaire
    Path(filename).parent.mkdir(parents=True, exist_ok=True)
    
    # Sauvegarder
    df.to_csv(filename, index=False)
    
    print(f"\n💾 Données sauvegardées:")
    print(f"   Fichier: {filename}")
    print(f"   Taille: {Path(filename).stat().st_size / 1024 / 1024:.2f} MB")
    
    return True


def main():
    """Point d'entrée principal"""
    
    print("\n" + "🚀"*40)
    print("TÉLÉCHARGEMENT DONNÉES MT5 - NAS100 3min")
    print("🚀"*40)
    
    print("\n⚠️  CE SCRIPT NE TRADE PAS")
    print("   Il télécharge UNIQUEMENT les données historiques")
    print("   Pour backtester la stratégie dessus")
    
    # Configuration
    symbol = 'NAS100'
    timeframe = mt5.TIMEFRAME_M3  # 3 minutes
    months = 6  # 6 mois d'historique
    
    # Demander confirmation
    print(f"\n📋 Configuration:")
    print(f"   Symbole: {symbol}")
    print(f"   Timeframe: 3 minutes")
    print(f"   Période: {months} mois")
    
    response = input("\nContinuer ? (o/n) : ")
    if response.lower() != 'o':
        print("\n❌ Annulé")
        return
    
    # Télécharger
    df = download_mt5_data(symbol=symbol, timeframe=timeframe, months=months)
    
    if df is None:
        print("\n❌ Échec téléchargement")
        return
    
    # Sauvegarder
    if save_data(df):
        print("\n" + "="*80)
        print("✅ SUCCÈS - Données prêtes pour backtest")
        print("="*80)
        
        print(f"\n🚀 Prochaine étape:")
        print(f"   python main_rsi_amplitude.py")
        print(f"\n💡 Le backtest utilisera automatiquement ces données fraîches")
    
    print("\n" + "="*80 + "\n")


if __name__ == "__main__":
    main()
