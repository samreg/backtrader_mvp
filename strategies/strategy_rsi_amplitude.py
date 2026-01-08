#!/usr/bin/env python3
"""
Stratégie RSI + Amplitude SL
Migration de la stratégie actuelle vers l'architecture modulaire
"""

from strategies.base_strategy import BaseStrategy
import backtrader as bt


class RSIAmplitudeStrategy(BaseStrategy):
    """
    Stratégie basée sur RSI avec SL calculé sur l'amplitude des bougies
    
    Signaux:
    - LONG: RSI < seuil → SL = low des N dernières bougies
    - SHORT: RSI > seuil → SL = high des N dernières bougies
    """
    
    params = (
        # RSI
        ('rsi_period', 14),
        ('rsi_long_threshold', 30),
        ('rsi_short_threshold', 70),
        
        # SL
        ('sl_lookback', 3),
    )
    
    def __init__(self):
        """Initialisation de la stratégie"""
        super().__init__()
        
        # Indicateur RSI
        self.rsi = bt.indicators.RSI(
            self.data.close,
            period=self.p.rsi_period
        )
    
    def _calculate_amplitude_sl(self):
        """
        Calcule l'amplitude des N dernières bougies pour le SL
        
        Returns:
            float: Amplitude en PIPS (pas en points de prix!)
        """
        lookback = min(self.p.sl_lookback, len(self.data))
        
        if lookback == 0:
            return 0
        
        highs = [self.data.high[-i] for i in range(lookback)]
        lows = [self.data.low[-i] for i in range(lookback)]
        
        # Amplitude en points de prix
        amplitude_price = max(highs) - min(lows)
        
        # Convertir en PIPS
        amplitude_pips = self.price_to_pips(amplitude_price)
        
        return amplitude_pips
    
    def next(self):
        """Logique principale de trading"""
        
        # Si en position, gérer la sortie
        if self.in_position:
            self._manage_position()
            return
        
        # Pas assez de données
        if len(self.data) < max(self.p.rsi_period, self.p.sl_lookback):
            return
        
        # === SIGNAL LONG ===
        if self.rsi[0] < self.p.rsi_long_threshold:
            
            # Calculer SL basé sur amplitude
            amplitude = self._calculate_amplitude_sl()
            
            # Vérifier filtres
            if not self.check_sl_filters(amplitude):
                return
            
            # Entrer LONG
            self._enter_long(amplitude)
        
        # === SIGNAL SHORT ===
        elif self.rsi[0] > self.p.rsi_short_threshold:
            
            # Calculer SL basé sur amplitude
            amplitude = self._calculate_amplitude_sl()
            
            # Vérifier filtres
            if not self.check_sl_filters(amplitude):
                return
            
            # Entrer SHORT
            self._enter_short(amplitude)
    
    def _enter_long(self, sl_distance_pips):
        """Entre en position LONG
        
        Args:
            sl_distance_pips: Distance du SL en PIPS
        """
        
        entry_price = self.data.close[0]
        
        # Calculer SL (en points de prix)
        lookback = min(self.p.sl_lookback, len(self.data))
        lows = [self.data.low[-i] for i in range(lookback)]
        sl_price = min(lows)
        
        # Position sizing (passe les PIPS à calculate_position_size)
        position_size = self.calculate_position_size(sl_distance_pips)
        
        # Convertir pips en prix pour les TPs
        sl_distance_price = self.pips_to_price(sl_distance_pips)
        tp1_price = entry_price + (sl_distance_price * self.p.tp1_rr)
        tp2_price = entry_price + (sl_distance_price * self.p.tp2_rr)
        
        # Entrer
        self.trade_id += 1
        self.in_position = True
        self.position_direction = 'LONG'
        self.entry_price = entry_price
        self.entry_time = self.datas[0].datetime.datetime(0)  # ← Stocker entry_time
        self.entry_size = position_size
        self.sl_price = sl_price
        self.sl_distance = sl_distance_price  # Stocker en prix pour gestion position
        
        # Stocker TPs pour box creation later
        self.tp1_price = tp1_price
        self.tp2_price = tp2_price
        
        # Ordres
        self.buy(size=position_size)
        
        # Log
        self.log(f'📈 LONG ENTRY #{self.trade_id}: Price={entry_price:.2f}, Size={position_size}, SL={sl_price:.2f} ({sl_distance_pips:.1f} pips), TP1={tp1_price:.2f}, TP2={tp2_price:.2f}')
        self.log_trade_event('ENTRY', entry_price, position_size)
    
    def _enter_short(self, sl_distance_pips):
        """Entre en position SHORT
        
        Args:
            sl_distance_pips: Distance du SL en PIPS
        """
        
        entry_price = self.data.close[0]
        
        # Calculer SL (en points de prix)
        lookback = min(self.p.sl_lookback, len(self.data))
        highs = [self.data.high[-i] for i in range(lookback)]
        sl_price = max(highs)
        
        # Position sizing (passe les PIPS à calculate_position_size)
        position_size = self.calculate_position_size(sl_distance_pips)
        
        # Convertir pips en prix pour les TPs
        sl_distance_price = self.pips_to_price(sl_distance_pips)
        tp1_price = entry_price - (sl_distance_price * self.p.tp1_rr)
        tp2_price = entry_price - (sl_distance_price * self.p.tp2_rr)
        
        # Entrer
        self.trade_id += 1
        self.in_position = True
        self.position_direction = 'SHORT'
        self.entry_price = entry_price
        self.entry_time = self.datas[0].datetime.datetime(0)  # ← Stocker entry_time
        self.entry_size = position_size
        self.sl_price = sl_price
        self.sl_distance = sl_distance_price  # Stocker en prix pour gestion position
        
        # Stocker TPs pour box creation later
        self.tp1_price = tp1_price
        self.tp2_price = tp2_price
        
        # Ordres
        self.sell(size=position_size)
        
        # Log
        self.log(f'📉 SHORT ENTRY #{self.trade_id}: Price={entry_price:.2f}, Size={position_size}, SL={sl_price:.2f} ({sl_distance_pips:.1f} pips), TP1={tp1_price:.2f}, TP2={tp2_price:.2f}')
        self.log_trade_event('ENTRY', entry_price, position_size)
    
    def _manage_position(self):
        """Gère une position existante (SL, TP, BE)"""
        
        current_price = self.data.close[0]
        
        if self.position_direction == 'LONG':
            # Check SL
            if current_price <= self.sl_price:
                exit_time = self.datas[0].datetime.datetime(0)
                
                # Créer box SL
                price_low = min(self.entry_price, self.sl_price)
                price_high = max(self.entry_price, self.sl_price)
                self.log_box('SL', self.entry_time, exit_time, price_low, price_high)
                
                self.close()
                pnl = (current_price - self.entry_price) * self.entry_size
                self.log(f'❌ SL HIT: PnL={pnl:.2f}')
                self.log_trade_event('SL', current_price, pnl=pnl)
                self.in_position = False
            
            # Check TPs
            tp1_price = self.entry_price + (self.sl_distance * self.p.tp1_rr)
            tp2_price = self.entry_price + (self.sl_distance * self.p.tp2_rr)
            
            if current_price >= tp2_price:
                exit_time = self.datas[0].datetime.datetime(0)
                
                # Créer box TP2
                price_low = min(self.entry_price, tp2_price)
                price_high = max(self.entry_price, tp2_price)
                self.log_box('TP2', self.entry_time, exit_time, price_low, price_high)
                
                self.close()
                pnl = (current_price - self.entry_price) * self.entry_size
                self.log(f'✅ TP2 HIT: PnL={pnl:.2f}')
                self.log_trade_event('TP2', current_price, pnl=pnl)
                self.in_position = False
            
            elif current_price >= tp1_price and not self.tp1_hit:
                exit_time = self.datas[0].datetime.datetime(0)
                
                # Créer box TP1
                price_low = min(self.entry_price, tp1_price)
                price_high = max(self.entry_price, tp1_price)
                self.log_box('TP1', self.entry_time, exit_time, price_low, price_high)
                
                self.tp1_hit = True
                partial_size = self.entry_size * self.p.tp1_ratio
                pnl = (current_price - self.entry_price) * partial_size
                self.log(f'✅ TP1 HIT (partial): PnL={pnl:.2f}')
                self.log_trade_event('TP1', current_price, pnl=pnl)
                
                # Move to BE si activé
                if self.p.enable_breakeven:
                    self.sl_price = self.entry_price + self.p.breakeven_offset
                    self.log(f'⚡ Break-even: SL moved to {self.sl_price:.2f}')
        
        elif self.position_direction == 'SHORT':
            # Check SL
            if current_price >= self.sl_price:
                exit_time = self.datas[0].datetime.datetime(0)
                
                # Créer box SL
                price_low = min(self.entry_price, self.sl_price)
                price_high = max(self.entry_price, self.sl_price)
                self.log_box('SL', self.entry_time, exit_time, price_low, price_high)
                
                self.close()
                pnl = (self.entry_price - current_price) * self.entry_size
                self.log(f'❌ SL HIT: PnL={pnl:.2f}')
                self.log_trade_event('SL', current_price, pnl=pnl)
                self.in_position = False
            
            # Check TPs
            tp1_price = self.entry_price - (self.sl_distance * self.p.tp1_rr)
            tp2_price = self.entry_price - (self.sl_distance * self.p.tp2_rr)
            
            if current_price <= tp2_price:
                exit_time = self.datas[0].datetime.datetime(0)
                
                # Créer box TP2
                price_low = min(self.entry_price, tp2_price)
                price_high = max(self.entry_price, tp2_price)
                self.log_box('TP2', self.entry_time, exit_time, price_low, price_high)
                
                self.close()
                pnl = (self.entry_price - current_price) * self.entry_size
                self.log(f'✅ TP2 HIT: PnL={pnl:.2f}')
                self.log_trade_event('TP2', current_price, pnl=pnl)
                self.in_position = False
            
            elif current_price <= tp1_price and not self.tp1_hit:
                exit_time = self.datas[0].datetime.datetime(0)
                
                # Créer box TP1
                price_low = min(self.entry_price, tp1_price)
                price_high = max(self.entry_price, tp1_price)
                self.log_box('TP1', self.entry_time, exit_time, price_low, price_high)
                
                self.tp1_hit = True
                partial_size = self.entry_size * self.p.tp1_ratio
                pnl = (self.entry_price - current_price) * partial_size
                self.log(f'✅ TP1 HIT (partial): PnL={pnl:.2f}')
                self.log_trade_event('TP1', current_price, pnl=pnl)
                
                # Move to BE si activé
                if self.p.enable_breakeven:
                    self.sl_price = self.entry_price - self.p.breakeven_offset
                    self.log(f'⚡ Break-even: SL moved to {self.sl_price:.2f}')
