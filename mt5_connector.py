#!/usr/bin/env python3
"""
Module d'intégration MetaTrader 5
Permet de passer de backtest à trading live
"""

import MetaTrader5 as mt5
import pandas as pd
from datetime import datetime, timedelta
import time
import yaml
from pathlib import Path


class MT5Connector:
    """Gestionnaire de connexion MT5"""
    
    def __init__(self, config_path='config_mt5.yaml'):
        """
        Initialise la connexion MT5
        
        Args:
            config_path: Chemin vers fichier config MT5
        """
        self.config = self._load_config(config_path)
        self.connected = False
        self.account_info = None
        
    def _load_config(self, config_path):
        """Charge la configuration MT5"""
        if not Path(config_path).exists():
            print(f"⚠️  Config {config_path} non trouvée, création config par défaut...")
            self._create_default_config(config_path)
        
        with open(config_path, 'r') as f:
            return yaml.safe_load(f)
    
    def _create_default_config(self, config_path):
        """Crée une config MT5 par défaut"""
        default_config = {
            'account': 12345678,  # À remplacer
            'password': 'YourPassword',  # À remplacer
            'server': 'YourBroker-Demo',  # À remplacer
            'symbol': 'NAS100',
            'timeframe': 'M3',  # 3 minutes
            'magic_number': 234567,  # Identifiant unique stratégie
            'slippage': 10,  # Points de slippage max
            'comment': 'RSI_Amplitude_Bot',
        }
        
        with open(config_path, 'w') as f:
            yaml.dump(default_config, f, default_flow_style=False)
        
        print(f"✅ Config créée: {config_path}")
        print("⚠️  MODIFIEZ les paramètres account/password/server !")
    
    def connect(self):
        """Établit la connexion avec MT5"""
        if not mt5.initialize():
            print(f"❌ Erreur initialize() MT5: {mt5.last_error()}")
            return False
        
        # Login
        authorized = mt5.login(
            login=self.config['account'],
            password=self.config['password'],
            server=self.config['server']
        )
        
        if not authorized:
            print(f"❌ Erreur login MT5: {mt5.last_error()}")
            mt5.shutdown()
            return False
        
        self.connected = True
        self.account_info = mt5.account_info()
        
        print(f"✅ Connecté à MT5:")
        print(f"   Compte: {self.account_info.login}")
        print(f"   Serveur: {self.account_info.server}")
        print(f"   Balance: ${self.account_info.balance:.2f}")
        print(f"   Equity: ${self.account_info.equity:.2f}")
        
        return True
    
    def disconnect(self):
        """Ferme la connexion MT5"""
        if self.connected:
            mt5.shutdown()
            self.connected = False
            print("✅ Déconnecté de MT5")
    
    def get_symbol_info(self, symbol=None):
        """Récupère infos sur un symbole"""
        if not self.connected:
            print("❌ Non connecté à MT5")
            return None
        
        symbol = symbol or self.config['symbol']
        info = mt5.symbol_info(symbol)
        
        if info is None:
            print(f"❌ Symbole {symbol} non trouvé")
            return None
        
        return {
            'name': info.name,
            'bid': info.bid,
            'ask': info.ask,
            'spread': info.spread,
            'point': info.point,
            'digits': info.digits,
            'volume_min': info.volume_min,
            'volume_max': info.volume_max,
            'volume_step': info.volume_step,
        }
    
    def get_ohlc_data(self, symbol=None, timeframe='M3', bars=1000):
        """
        Récupère données OHLC depuis MT5
        
        Args:
            symbol: Nom du symbole
            timeframe: Timeframe ('M1', 'M3', 'M5', 'M15', 'M30', 'H1', 'H4', 'D1')
            bars: Nombre de barres
            
        Returns:
            DataFrame avec colonnes [datetime, open, high, low, close, volume]
        """
        if not self.connected:
            print("❌ Non connecté à MT5")
            return None
        
        symbol = symbol or self.config['symbol']
        
        # Conversion timeframe
        tf_map = {
            'M1': mt5.TIMEFRAME_M1,
            'M3': mt5.TIMEFRAME_M3,
            'M5': mt5.TIMEFRAME_M5,
            'M15': mt5.TIMEFRAME_M15,
            'M30': mt5.TIMEFRAME_M30,
            'H1': mt5.TIMEFRAME_H1,
            'H4': mt5.TIMEFRAME_H4,
            'D1': mt5.TIMEFRAME_D1,
        }
        
        if timeframe not in tf_map:
            print(f"❌ Timeframe invalide: {timeframe}")
            return None
        
        # Récupérer données
        rates = mt5.copy_rates_from_pos(symbol, tf_map[timeframe], 0, bars)
        
        if rates is None or len(rates) == 0:
            print(f"❌ Pas de données pour {symbol} {timeframe}")
            return None
        
        # Convertir en DataFrame
        df = pd.DataFrame(rates)
        df['datetime'] = pd.to_datetime(df['time'], unit='s')
        df = df[['datetime', 'open', 'high', 'low', 'close', 'tick_volume']]
        df = df.rename(columns={'tick_volume': 'volume'})
        
        print(f"✅ {len(df)} barres récupérées ({symbol} {timeframe})")
        return df
    
    def calculate_lot_size(self, symbol, entry_price, sl_price, risk_amount):
        """
        Calcule la taille de position (lots) basée sur le risque
        
        Args:
            symbol: Nom du symbole
            entry_price: Prix d'entrée
            sl_price: Prix du stop loss
            risk_amount: Montant à risquer ($)
            
        Returns:
            Taille en lots
        """
        info = self.get_symbol_info(symbol)
        if not info:
            return None
        
        # Distance SL en points
        sl_distance_points = abs(entry_price - sl_price) / info['point']
        
        # Valeur d'un pip (pour indices CFD, généralement 1 lot = $1/point)
        # ATTENTION: À adapter selon le contrat de ton broker
        pip_value_per_lot = 1.0  # $1 par point par lot pour NAS100
        
        # Calcul taille
        lot_size = risk_amount / (sl_distance_points * pip_value_per_lot)
        
        # Arrondir au step
        lot_size = round(lot_size / info['volume_step']) * info['volume_step']
        
        # Limiter aux min/max
        lot_size = max(info['volume_min'], min(lot_size, info['volume_max']))
        
        print(f"💰 Calcul lot size:")
        print(f"   Risk: ${risk_amount:.2f}")
        print(f"   SL distance: {sl_distance_points:.1f} points")
        print(f"   Lot size: {lot_size:.2f}")
        
        return lot_size
    
    def send_order(self, symbol, order_type, volume, price=None, sl=None, tp=None, comment=None):
        """
        Envoie un ordre à MT5
        
        Args:
            symbol: Nom du symbole
            order_type: 'BUY' ou 'SELL'
            volume: Taille en lots
            price: Prix limit (None = market)
            sl: Stop loss
            tp: Take profit
            comment: Commentaire
            
        Returns:
            Résultat de l'ordre
        """
        if not self.connected:
            print("❌ Non connecté à MT5")
            return None
        
        # Type d'ordre
        if order_type == 'BUY':
            order_type_mt5 = mt5.ORDER_TYPE_BUY if price is None else mt5.ORDER_TYPE_BUY_LIMIT
        elif order_type == 'SELL':
            order_type_mt5 = mt5.ORDER_TYPE_SELL if price is None else mt5.ORDER_TYPE_SELL_LIMIT
        else:
            print(f"❌ Type d'ordre invalide: {order_type}")
            return None
        
        # Prix (si market)
        if price is None:
            info = self.get_symbol_info(symbol)
            price = info['ask'] if order_type == 'BUY' else info['bid']
        
        # Request
        request = {
            'action': mt5.TRADE_ACTION_DEAL,
            'symbol': symbol,
            'volume': volume,
            'type': order_type_mt5,
            'price': price,
            'sl': sl if sl else 0,
            'tp': tp if tp else 0,
            'deviation': self.config.get('slippage', 10),
            'magic': self.config.get('magic_number', 234567),
            'comment': comment or self.config.get('comment', 'Bot'),
            'type_time': mt5.ORDER_TIME_GTC,
            'type_filling': mt5.ORDER_FILLING_IOC,
        }
        
        # Envoi
        result = mt5.order_send(request)
        
        if result.retcode != mt5.TRADE_RETCODE_DONE:
            print(f"❌ Erreur ordre: {result.retcode} - {result.comment}")
            return None
        
        print(f"✅ Ordre exécuté:")
        print(f"   Ticket: {result.order}")
        print(f"   Type: {order_type}")
        print(f"   Volume: {volume}")
        print(f"   Prix: {result.price}")
        
        return result
    
    def get_open_positions(self, symbol=None):
        """Récupère les positions ouvertes"""
        if not self.connected:
            print("❌ Non connecté à MT5")
            return []
        
        positions = mt5.positions_get(symbol=symbol) if symbol else mt5.positions_get()
        
        if positions is None or len(positions) == 0:
            return []
        
        return [{
            'ticket': p.ticket,
            'symbol': p.symbol,
            'type': 'BUY' if p.type == mt5.POSITION_TYPE_BUY else 'SELL',
            'volume': p.volume,
            'price_open': p.price_open,
            'price_current': p.price_current,
            'sl': p.sl,
            'tp': p.tp,
            'profit': p.profit,
            'comment': p.comment,
        } for p in positions]
    
    def close_position(self, ticket):
        """Ferme une position par ticket"""
        if not self.connected:
            print("❌ Non connecté à MT5")
            return False
        
        position = mt5.positions_get(ticket=ticket)
        if not position:
            print(f"❌ Position {ticket} non trouvée")
            return False
        
        position = position[0]
        
        # Order de fermeture (inverse)
        order_type = mt5.ORDER_TYPE_SELL if position.type == mt5.POSITION_TYPE_BUY else mt5.ORDER_TYPE_BUY
        price = mt5.symbol_info_tick(position.symbol).bid if order_type == mt5.ORDER_TYPE_SELL else mt5.symbol_info_tick(position.symbol).ask
        
        request = {
            'action': mt5.TRADE_ACTION_DEAL,
            'symbol': position.symbol,
            'volume': position.volume,
            'type': order_type,
            'position': ticket,
            'price': price,
            'deviation': self.config.get('slippage', 10),
            'magic': self.config.get('magic_number', 234567),
            'comment': 'Close by bot',
            'type_time': mt5.ORDER_TIME_GTC,
            'type_filling': mt5.ORDER_FILLING_IOC,
        }
        
        result = mt5.order_send(request)
        
        if result.retcode != mt5.TRADE_RETCODE_DONE:
            print(f"❌ Erreur fermeture: {result.retcode}")
            return False
        
        print(f"✅ Position {ticket} fermée")
        return True


def demo_mt5_connection():
    """Démo de connexion MT5"""
    
    print("\n" + "="*80)
    print("📊 DEMO CONNEXION MT5")
    print("="*80 + "\n")
    
    # Créer connecteur
    mt5_conn = MT5Connector()
    
    # Connexion
    if not mt5_conn.connect():
        print("\n⚠️  Modifiez config_mt5.yaml avec vos identifiants")
        return
    
    # Info symbole
    print("\n📊 Info symbole:")
    info = mt5_conn.get_symbol_info('NAS100')
    if info:
        for key, value in info.items():
            print(f"   {key}: {value}")
    
    # Récupérer données
    print("\n📈 Récupération données:")
    df = mt5_conn.get_ohlc_data('NAS100', 'M3', 100)
    if df is not None:
        print(df.tail())
    
    # Positions ouvertes
    print("\n💼 Positions ouvertes:")
    positions = mt5_conn.get_open_positions()
    if positions:
        for pos in positions:
            print(f"   {pos}")
    else:
        print("   Aucune position ouverte")
    
    # Déconnexion
    mt5_conn.disconnect()
    
    print("\n" + "="*80 + "\n")


if __name__ == "__main__":
    demo_mt5_connection()
