#!/usr/bin/env python3
"""
Stratégie MACD + EMA (Trend Following)
Basée sur l'architecture BaseStrategy
"""

from strategies.base_strategy import BaseStrategy
import backtrader as bt


class MACDEMAStrategy(BaseStrategy):
    """
    Stratégie trend following avec MACD et EMA
    
    Signaux:
    - LONG: MACD > Signal ET prix > EMA200 → Tendance haussière confirmée
    - SHORT: MACD < Signal ET prix < EMA200 → Tendance baissière confirmée
    
    SL: ATR × multiplicateur (volatilité adaptative)
    """
    
    params = (
        # MACD
        ('macd_fast', 12),
        ('macd_slow', 26),
        ('macd_signal', 9),
        
        # EMA trend filter
        ('ema_period', 200),
        
        # SL basé sur ATR
        ('atr_period', 14),
        ('atr_multiplier', 2.0),  # SL = 2 × ATR
    )
    
    def __init__(self):
        """Initialisation de la stratégie"""
        super().__init__()
        
        # Indicateurs
        self.macd = bt.indicators.MACD(
            self.data.close,
            period_me1=self.p.macd_fast,
            period_me2=self.p.macd_slow,
            period_signal=self.p.macd_signal
        )
        
        self.ema = bt.indicators.EMA(
            self.data.close,
            period=self.p.ema_period
        )
        
        self.atr = bt.indicators.ATR(
            self.data,
            period=self.p.atr_period
        )
    
    def _calculate_atr_sl(self):
        """
        Calcule le SL basé sur ATR
        
        Returns:
            float: Distance SL en PIPS
        """
        atr_value = self.atr[0]
        sl_distance_price = atr_value * self.p.atr_multiplier
        sl_distance_pips = self.price_to_pips(sl_distance_price)
        return sl_distance_pips
    
    def next(self):
        """Logique principale de trading"""
        
        # Si en position, gérer la sortie
        if self.in_position:
            self._manage_position()
            return
        
        # Pas assez de données
        if len(self.data) < max(self.p.macd_slow, self.p.ema_period, self.p.atr_period):
            return
        
        # === SIGNAL LONG ===
        # MACD croise au-dessus du signal ET prix au-dessus EMA200
        if self.macd.macd[0] > self.macd.signal[0] and self.data.close[0] > self.ema[0]:
            
            # Calculer SL basé sur ATR
            sl_distance_pips = self._calculate_atr_sl()
            
            # Vérifier filtres
            if not self.check_sl_filters(sl_distance_pips):
                return
            
            # Entrer LONG
            self._enter_long(sl_distance_pips)
        
        # === SIGNAL SHORT ===
        # MACD croise en-dessous du signal ET prix en-dessous EMA200
        elif self.macd.macd[0] < self.macd.signal[0] and self.data.close[0] < self.ema[0]:
            
            # Calculer SL basé sur ATR
            sl_distance_pips = self._calculate_atr_sl()
            
            # Vérifier filtres
            if not self.check_sl_filters(sl_distance_pips):
                return
            
            # Entrer SHORT
            self._enter_short(sl_distance_pips)
    
    def _enter_long(self, sl_distance_pips):
        """Entre en position LONG"""
        
        entry_price = self.data.close[0]
        
        # SL = Entry - (ATR × multiplicateur)
        sl_distance_price = self.pips_to_price(sl_distance_pips)
        sl_price = entry_price - sl_distance_price
        
        # Position sizing
        position_size = self.calculate_position_size(sl_distance_pips)
        
        # Calculer TPs
        tp1_price = entry_price + (sl_distance_price * self.p.tp1_rr)
        tp2_price = entry_price + (sl_distance_price * self.p.tp2_rr)
        
        # Entrer
        self.trade_id += 1
        self.in_position = True
        self.position_direction = 'LONG'
        self.entry_price = entry_price
        self.entry_time = self.datas[0].datetime.datetime(0)
        self.entry_size = position_size
        self.sl_price = sl_price
        self.sl_distance = sl_distance_price
        
        # Stocker TPs
        self.tp1_price = tp1_price
        self.tp2_price = tp2_price
        
        # Ordre
        self.buy(size=position_size)
        
        # Log
        self.log(f'📈 LONG ENTRY #{self.trade_id}: Price={entry_price:.2f}, Size={position_size}, SL={sl_price:.2f} ({sl_distance_pips:.1f} pips), TP1={tp1_price:.2f}, TP2={tp2_price:.2f}')
        self.log_trade_event('ENTRY', entry_price, position_size)
    
    def _enter_short(self, sl_distance_pips):
        """Entre en position SHORT"""
        
        entry_price = self.data.close[0]
        
        # SL = Entry + (ATR × multiplicateur)
        sl_distance_price = self.pips_to_price(sl_distance_pips)
        sl_price = entry_price + sl_distance_price
        
        # Position sizing
        position_size = self.calculate_position_size(sl_distance_pips)
        
        # Calculer TPs
        tp1_price = entry_price - (sl_distance_price * self.p.tp1_rr)
        tp2_price = entry_price - (sl_distance_price * self.p.tp2_rr)
        
        # Entrer
        self.trade_id += 1
        self.in_position = True
        self.position_direction = 'SHORT'
        self.entry_price = entry_price
        self.entry_time = self.datas[0].datetime.datetime(0)
        self.entry_size = position_size
        self.sl_price = sl_price
        self.sl_distance = sl_distance_price
        
        # Stocker TPs
        self.tp1_price = tp1_price
        self.tp2_price = tp2_price
        
        # Ordre
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
                price_low = min(self.entry_price, self.sl_price)
                price_high = max(self.entry_price, self.sl_price)
                self.log_box('SL', self.entry_time, exit_time, price_low, price_high)
                
                self.close()
                pnl = (current_price - self.entry_price) * self.entry_size
                self.log(f'❌ SL HIT: PnL={pnl:.2f}')
                self.log_trade_event('SL', current_price, pnl=pnl)
                self.in_position = False
            
            # Check TP2
            elif current_price >= self.tp2_price:
                exit_time = self.datas[0].datetime.datetime(0)
                price_low = min(self.entry_price, self.tp2_price)
                price_high = max(self.entry_price, self.tp2_price)
                self.log_box('TP2', self.entry_time, exit_time, price_low, price_high)
                
                self.close()
                pnl = (current_price - self.entry_price) * self.entry_size
                self.log(f'✅ TP2 HIT: PnL={pnl:.2f}')
                self.log_trade_event('TP2', current_price, pnl=pnl)
                self.in_position = False
            
            # Check TP1
            elif current_price >= self.tp1_price and not self.tp1_hit:
                exit_time = self.datas[0].datetime.datetime(0)
                price_low = min(self.entry_price, self.tp1_price)
                price_high = max(self.entry_price, self.tp1_price)
                self.log_box('TP1', self.entry_time, exit_time, price_low, price_high)
                
                self.tp1_hit = True
                partial_size = self.entry_size * self.p.tp1_ratio
                pnl = (current_price - self.entry_price) * partial_size
                self.log(f'✅ TP1 HIT (partial): PnL={pnl:.2f}')
                self.log_trade_event('TP1', current_price, pnl=pnl)
                
                # Break-even
                if self.p.enable_breakeven:
                    self.sl_price = self.entry_price + self.p.breakeven_offset
                    self.log(f'⚡ Break-even: SL moved to {self.sl_price:.2f}')
        
        elif self.position_direction == 'SHORT':
            # Check SL
            if current_price >= self.sl_price:
                exit_time = self.datas[0].datetime.datetime(0)
                price_low = min(self.entry_price, self.sl_price)
                price_high = max(self.entry_price, self.sl_price)
                self.log_box('SL', self.entry_time, exit_time, price_low, price_high)
                
                self.close()
                pnl = (self.entry_price - current_price) * self.entry_size
                self.log(f'❌ SL HIT: PnL={pnl:.2f}')
                self.log_trade_event('SL', current_price, pnl=pnl)
                self.in_position = False
            
            # Check TP2
            elif current_price <= self.tp2_price:
                exit_time = self.datas[0].datetime.datetime(0)
                price_low = min(self.entry_price, self.tp2_price)
                price_high = max(self.entry_price, self.tp2_price)
                self.log_box('TP2', self.entry_time, exit_time, price_low, price_high)
                
                self.close()
                pnl = (self.entry_price - current_price) * self.entry_size
                self.log(f'✅ TP2 HIT: PnL={pnl:.2f}')
                self.log_trade_event('TP2', current_price, pnl=pnl)
                self.in_position = False
            
            # Check TP1
            elif current_price <= self.tp1_price and not self.tp1_hit:
                exit_time = self.datas[0].datetime.datetime(0)
                price_low = min(self.entry_price, self.tp1_price)
                price_high = max(self.entry_price, self.tp1_price)
                self.log_box('TP1', self.entry_time, exit_time, price_low, price_high)
                
                self.tp1_hit = True
                partial_size = self.entry_size * self.p.tp1_ratio
                pnl = (self.entry_price - current_price) * partial_size
                self.log(f'✅ TP1 HIT (partial): PnL={pnl:.2f}')
                self.log_trade_event('TP1', current_price, pnl=pnl)
                
                # Break-even
                if self.p.enable_breakeven:
                    self.sl_price = self.entry_price - self.p.breakeven_offset
                    self.log(f'⚡ Break-even: SL moved to {self.sl_price:.2f}')
