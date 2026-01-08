#!/usr/bin/env python3
"""
Classe de base pour toutes les stratégies
Contient la logique commune de gestion des trades, ordres, logs
"""

import backtrader as bt
from datetime import datetime


class BaseStrategy(bt.Strategy):
    """
    Classe de base pour toutes les stratégies
    
    Fournit:
    - Gestion des ordres
    - Logging des trades
    - Export des événements
    - Gestion break-even commune
    - Statistiques de rejets
    """
    
    params = (
        # Configuration complète (pour trading_windows, etc.)
        ('config', None),
        
        # Position sizing
        ('risk_per_trade', 0.01),
        
        # Pip configuration
        ('pip_value', 0.1),  # 1 pip = 0.1 point de prix (NAS100)
        
        # Take Profits
        ('tp1_rr', 1.5),
        ('tp2_rr', 3.0),
        ('tp1_ratio', 0.5),
        ('tp2_ratio', 0.5),
        
        # Break-even
        ('enable_breakeven', True),
        ('breakeven_offset', 5),  # Décalage en PIPS (5 pips par défaut)
        
        # Filtres SL
        ('min_sl_distance_pips', 10),
        ('max_sl_distance_pips', 200),
    )
    
    def __init__(self):
        """Initialisation commune"""
        
        # État du trade
        self.in_position = False
        self.position_direction = None
        self.entry_price = None
        self.entry_time = None  # ← NOUVEAU
        self.entry_size = None
        self.sl_price = None
        self.sl_distance = None
        self.trade_id = 0
        
        # Ordres actifs
        self.entry_order = None
        self.sl_order = None
        self.tp1_order = None
        self.tp2_order = None
        
        # État break-even
        self.breakeven_set = False
        self.tp1_hit = False
        self.breakeven_active = False  # True si SL déplacé au BE
        
        # Log des trades (utiliser trades_log comme source unique)
        self.trades_log = []
        
        # Log des boxes (pour visualisation)
        self.boxes_log = []
        
        # Stats rejets
        self.rejected_too_small = 0
        self.rejected_too_large = 0
        
        # Pour debug
        self.log_signals = True
        
        # Trading Windows Filter (charger si défini dans config)
        from trading_windows import TradingWindows
        # Vérifier si config existe (passé en paramètre)
        if hasattr(self.p, 'config') and self.p.config is not None:
            tw_config = self.p.config.get('trading_windows', {})
        else:
            tw_config = {}  # Config vide = filtre désactivé
        self.trading_windows = TradingWindows(tw_config)
    
    def log(self, txt, dt=None):
        """Log avec timestamp - compatible Windows"""
        dt = dt or self.datas[0].datetime.datetime(0)
        try:
            timestamp = dt.strftime('%Y-%m-%d %H:%M:%S')
        except:
            timestamp = str(dt)
        print(f'[{timestamp}] {txt}')
    
    def check_sl_filters(self, sl_distance_pips):
        """
        Vérifie si le SL respecte les filtres min/max
        
        Args:
            sl_distance_pips: Distance du SL en pips
            
        Returns:
            bool: True si accepté, False si rejeté
        """
        if self.p.min_sl_distance_pips > 0 and sl_distance_pips < self.p.min_sl_distance_pips:
            self.log(f'  [REJECTED] SL trop petit: {sl_distance_pips:.2f} < {self.p.min_sl_distance_pips} pips')
            self.rejected_too_small += 1
            return False
        
        if self.p.max_sl_distance_pips > 0 and sl_distance_pips > self.p.max_sl_distance_pips:
            self.log(f'  [REJECTED] SL trop grand: {sl_distance_pips:.2f} > {self.p.max_sl_distance_pips} pips')
            self.rejected_too_large += 1
            return False
        
        return True
    
    def pips_to_price(self, pips):
        """
        Convertit des pips en points de prix
        
        Args:
            pips: Distance en pips
            
        Returns:
            float: Distance en points de prix
        """
        return pips * self.p.pip_value
    
    def price_to_pips(self, price_distance):
        """
        Convertit des points de prix en pips
        
        Args:
            price_distance: Distance en points de prix
            
        Returns:
            float: Distance en pips
        """
        return price_distance / self.p.pip_value
    
    def calculate_position_size(self, sl_distance_pips):
        """
        Calcule la taille de position selon le risque
        
        Args:
            sl_distance_pips: Distance du SL en PIPS (ex: 50 pips)
            
        Returns:
            float: Taille de position (nombre de contrats)
        """
        # Convertir pips en points de prix
        sl_distance_price = self.pips_to_price(sl_distance_pips)
        
        risk_amount = self.broker.getcash() * self.p.risk_per_trade
        
        if sl_distance_price <= 0:
            return 1  # Fallback sécurité
        
        # Pour NAS100 : 1 contrat = 1$ par point
        # Ex: SL de 50 pips = 5 points → risque de 5$ par contrat
        # Si risk_amount = 100$, position = 100/5 = 20 contrats
        position_size = risk_amount / sl_distance_price
        
        # Limiter la taille pour éviter margin calls
        # Marge de sécurité : ne pas utiliser plus de 10% du capital par trade
        max_contracts = int(self.broker.getcash() / (sl_distance_price * 10))
        position_size = min(position_size, max_contracts)
        
        return max(1, int(position_size))
    
    def log_trade_event(self, event_type, price, size=None, pnl=None, sl_distance=None):
        """Log un événement de trade"""
        event_data = {
            'datetime': self.datas[0].datetime.datetime(0),
            'trade_id': self.trade_id,
            'event_type': event_type,
            'direction': self.position_direction,
            'price': price,
            'size': size if size else self.entry_size,
            'pnl': pnl if pnl is not None else 0.0
        }
        
        # Ajouter sl_distance si fourni (utile pour ENTRY events)
        if sl_distance is not None:
            event_data['sl_distance'] = sl_distance
        
        self.trades_log.append(event_data)
    
    def log_box(self, box_type, entry_time, exit_time, price_low, price_high, metadata=None):
        """
        Log une box pour visualisation HTML
        
        Args:
            box_type: 'SL', 'SL_INITIAL', 'TP1', 'TP2'
            entry_time: Datetime d'entrée
            exit_time: Datetime de sortie
            price_low: Prix bas de la box
            price_high: Prix haut de la box
            metadata: Dict optionnel avec infos supplémentaires (ex: sl_price)
        """
        box_data = {
            'trade_id': self.trade_id,
            'type': box_type,
            'start_time': entry_time,
            'end_time': exit_time,
            'price_low': price_low,
            'price_high': price_high
        }
        
        # Ajouter metadata si fourni
        if metadata:
            box_data['metadata'] = metadata
        
        self.boxes_log.append(box_data)
    
    def notify_order(self, order):
        """Notification d'exécution d'ordre"""
        
        if order.status in [order.Submitted, order.Accepted]:
            return
        
        if order.status in [order.Completed]:
            if order.isbuy():
                self.log(f'BUY EXECUTED, Price: {order.executed.price:.2f}, Size: {order.executed.size}')
            elif order.issell():
                self.log(f'SELL EXECUTED, Price: {order.executed.price:.2f}, Size: {order.executed.size}')
        
        elif order.status in [order.Canceled, order.Margin, order.Rejected]:
            self.log(f'Order Canceled/Margin/Rejected')
        
        self.entry_order = None
    
    def notify_trade(self, trade):
        """Notification de clôture de trade"""
        if not trade.isclosed:
            return
        
        self.log(f'TRADE PROFIT, GROSS {trade.pnl:.2f}, NET {trade.pnlcomm:.2f}')
    
    def stop(self):
        """Appelé à la fin du backtest - fermer positions ouvertes"""
        if self.in_position:
            current_price = self.data.close[0]
            pnl = 0
            
            if self.position_direction == 'LONG':
                pnl = (current_price - self.entry_price) * self.entry_size
            elif self.position_direction == 'SHORT':
                pnl = (self.entry_price - current_price) * self.entry_size
            
            # Logger la sortie forcée
            self.log(f'⚠️  FORCED CLOSE at end of backtest: PnL={pnl:.2f}')
            self.log_trade_event('FORCED_CLOSE', current_price, pnl=pnl)
            
            # Fermer la position
            self.close()
            self.in_position = False
    
    # Méthodes à implémenter par les stratégies filles
    def next(self):
        """Logique principale - À IMPLÉMENTER"""
        raise NotImplementedError("Les stratégies doivent implémenter next()")


