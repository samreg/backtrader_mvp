#!/usr/bin/env python3
"""
Stratégie Bollinger Bands Mean Reversion
Entry au retour dans les bandes
"""

from strategies.base_strategy import BaseStrategy
import backtrader as bt


class BollingerBreakoutStrategy(BaseStrategy):
    """
    Stratégie mean reversion sur Bollinger Bands
    
    Logique:
    1. Prix sort des bandes BB (std=1.5) → En attente
    2. Prix RE-ENTRE dans les bandes → ENTRY
    
    LONG:
    - Attendre: Prix < BB Lower (sortie en bas)
    - Entry: Prix re-croise BB Lower vers le HAUT (retour)
    - TP1: Prix atteint BB Middle (médiane) → 50% + Break-even
    - TP2: Prix atteint BB Upper (bande opposée) → 50%
    - SL: X pips sous le plus bas récent
    
    SHORT:
    - Attendre: Prix > BB Upper (sortie en haut)
    - Entry: Prix re-croise BB Upper vers le BAS (retour)
    - TP1: Prix atteint BB Middle (médiane) → 50% + Break-even
    - TP2: Prix atteint BB Lower (bande opposée) → 50%
    - SL: X pips au-dessus du plus haut récent
    """
    
    params = (
        # Bollinger Bands
        ('bb_period', 20),
        ('bb_std', 1.5),  # Écarts-types (1.5 pour mean reversion)
        
        # SL basé sur swing high/low
        ('sl_lookback', 3),  # Bougies pour trouver swing
        ('sl_offset_pips', 10),  # Pips au-delà du swing
        
        # RSI avec système de flags
        ('rsi_period', 14),
        ('rsi_oversold', 20),      # < 20 → RSI_buy
        ('rsi_oversold_exit', 30), # > 30 → RSI_middle
        ('rsi_overbought', 80),    # > 80 → RSI_sell
        ('rsi_overbought_exit', 70), # < 70 → RSI_middle
    )
    
    def __init__(self):
        """Initialisation de la stratégie"""
        super().__init__()
        
        # Indicateur Bollinger Bands
        self.bb = bt.indicators.BollingerBands(
            self.data.close,
            period=self.p.bb_period,
            devfactor=self.p.bb_std
        )
        
        # Indicateur RSI
        self.rsi = bt.indicators.RSI(
            self.data.close,
            period=self.p.rsi_period
        )
        
        # Tracking état BB
        self.outside_lower = False
        self.outside_upper = False
        
        # Tracking état RSI (3 états: RSI_buy, RSI_middle, RSI_sell)
        self.rsi_state = 'RSI_middle'
    
    def next(self):
        """Logique principale de trading"""
        
        # Si en position, gérer la sortie (TOUJOURS gérer les positions existantes)
        if self.in_position:
            self._manage_position()
            return
        
        # Pas assez de données
        if len(self.data) < max(self.p.bb_period, self.p.sl_lookback, self.p.rsi_period):
            return
        
        # ⏰ CHECK TRADING WINDOWS FILTER
        # Si hors créneau → skip entry logic (mais positions existantes sont gérées ci-dessus)
        current_time = self.datas[0].datetime.datetime(0)
        if not self.trading_windows.is_trading_allowed(current_time):
            return  # Hors créneau → pas d'entrée
        
        current_price = self.data.close[0]
        bb_upper = self.bb.lines.top[0]
        bb_middle = self.bb.lines.mid[0]
        bb_lower = self.bb.lines.bot[0]
        current_rsi = self.rsi[0]
        
        # === GESTION ÉTAT RSI (Machine à états) ===
        # RSI_buy → RSI_middle → RSI_sell → RSI_middle → ...
        
        if self.rsi_state == 'RSI_middle':
            # Passer à RSI_buy si < 20
            if current_rsi < self.p.rsi_oversold:
                self.rsi_state = 'RSI_buy'
                self.log(f'🔵 RSI State → RSI_buy (RSI={current_rsi:.1f})')
            # Passer à RSI_sell si > 80
            elif current_rsi > self.p.rsi_overbought:
                self.rsi_state = 'RSI_sell'
                self.log(f'🔴 RSI State → RSI_sell (RSI={current_rsi:.1f})')
        
        elif self.rsi_state == 'RSI_buy':
            # Rester en RSI_buy tant que < 30
            # Passer à RSI_middle si >= 30
            if current_rsi >= self.p.rsi_oversold_exit:
                self.rsi_state = 'RSI_middle'
                self.log(f'⚪ RSI State → RSI_middle (RSI={current_rsi:.1f})')
        
        elif self.rsi_state == 'RSI_sell':
            # Rester en RSI_sell tant que > 70
            # Passer à RSI_middle si <= 70
            if current_rsi <= self.p.rsi_overbought_exit:
                self.rsi_state = 'RSI_middle'
                self.log(f'⚪ RSI State → RSI_middle (RSI={current_rsi:.1f})')
        
        # === TRACKING BB: Prix sort des bandes ===
        if current_price < bb_lower:
            self.outside_lower = True
            self.outside_upper = False
        elif current_price > bb_upper:
            self.outside_upper = True
            self.outside_lower = False
        
        # === SIGNAL LONG: BB + RSI_buy ===
        # Bollinger: Prix RE-ENTRE par le bas
        # RSI: État = RSI_buy
        if self.outside_lower and current_price >= bb_lower and self.rsi_state == 'RSI_buy':
            
            # Calculer SL basé sur swing low
            swing_low = min([self.data.low[-i] for i in range(self.p.sl_lookback)])
            sl_price = swing_low - self.pips_to_price(self.p.sl_offset_pips)
            sl_distance_price = current_price - sl_price
            sl_distance_pips = self.price_to_pips(sl_distance_price)
            
            # Vérifier filtres
            if self.check_sl_filters(sl_distance_pips):
                self._enter_long(current_price, sl_price, sl_distance_pips, bb_middle, bb_upper, current_rsi)
                # Reset flag BB (RSI state continue sa machine à états)
                self.outside_lower = False
        
        # === SIGNAL SHORT: BB + RSI_sell ===
        # Bollinger: Prix RE-ENTRE par le haut
        # RSI: État = RSI_sell
        elif self.outside_upper and current_price <= bb_upper and self.rsi_state == 'RSI_sell':
            
            # Calculer SL basé sur swing high
            swing_high = max([self.data.high[-i] for i in range(self.p.sl_lookback)])
            sl_price = swing_high + self.pips_to_price(self.p.sl_offset_pips)
            sl_distance_price = sl_price - current_price
            sl_distance_pips = self.price_to_pips(sl_distance_price)
            
            # Vérifier filtres
            if self.check_sl_filters(sl_distance_pips):
                self._enter_short(current_price, sl_price, sl_distance_pips, bb_middle, bb_lower, current_rsi)
                # Reset flag BB (RSI state continue sa machine à états)
                self.outside_upper = False
    
    def _enter_long(self, entry_price, sl_price, sl_distance_pips, tp1_target, tp2_target, current_rsi):
        """Entre en position LONG"""
        
        # Position sizing
        position_size = self.calculate_position_size(sl_distance_pips)
        
        # Stocker TP targets (bandes BB)
        self.tp1_price = tp1_target  # BB Middle
        self.tp2_price = tp2_target  # BB Upper
        
        # IMPORTANT: Réinitialiser flags pour nouveau trade
        self.tp1_hit = False
        self.breakeven_active = False
        
        # Reset RSI state après entrée (ne pas attendre la sortie du trade)
        old_rsi_state = self.rsi_state
        self.rsi_state = 'RSI_middle'
        if old_rsi_state != 'RSI_middle':
            self.log(f'⚪ RSI State → RSI_middle (trade entered, was {old_rsi_state})')
        
        # Entrer
        self.trade_id += 1
        self.in_position = True
        self.position_direction = 'LONG'
        self.entry_price = entry_price
        self.entry_time = self.datas[0].datetime.datetime(0)
        self.entry_size = position_size
        self.sl_price = sl_price
        self.sl_distance = self.pips_to_price(sl_distance_pips)
        
        # Ordre
        self.buy(size=position_size)
        
        # Log trade event (sl_distance doit être en PIPS pour les stats)
        self.log_trade_event('ENTRY', entry_price, position_size, sl_distance=sl_distance_pips)
        
        # Log SL initial box (pour visualisation, même si pas touché)
        # Box rouge transparent du SL initial
        sl_box_low = min(entry_price, sl_price)
        sl_box_high = max(entry_price, sl_price)
        self.log_box('SL_INITIAL', self.entry_time, self.entry_time, sl_box_low, sl_box_high, metadata={'sl_price': sl_price})
        
        # Log console
        self.log(f'📈 LONG ENTRY #{self.trade_id}: Price={entry_price:.2f}, Size={position_size}, RSI={current_rsi:.1f}, SL={sl_price:.2f} ({sl_distance_pips:.1f} pips), TP1={tp1_target:.2f} (BB Mid), TP2={tp2_target:.2f} (BB Upper)')
    
    def _enter_short(self, entry_price, sl_price, sl_distance_pips, tp1_target, tp2_target, current_rsi):
        """Entre en position SHORT"""
        
        # Position sizing
        position_size = self.calculate_position_size(sl_distance_pips)
        
        # Stocker TP targets (bandes BB)
        self.tp1_price = tp1_target  # BB Middle
        self.tp2_price = tp2_target  # BB Lower
        
        # IMPORTANT: Réinitialiser flags pour nouveau trade
        self.tp1_hit = False
        self.breakeven_active = False
        
        # Reset RSI state après entrée (ne pas attendre la sortie du trade)
        old_rsi_state = self.rsi_state
        self.rsi_state = 'RSI_middle'
        if old_rsi_state != 'RSI_middle':
            self.log(f'⚪ RSI State → RSI_middle (trade entered, was {old_rsi_state})')
        
        # Entrer
        self.trade_id += 1
        self.in_position = True
        self.position_direction = 'SHORT'
        self.entry_price = entry_price
        self.entry_time = self.datas[0].datetime.datetime(0)
        self.entry_size = position_size
        self.sl_price = sl_price
        self.sl_distance = self.pips_to_price(sl_distance_pips)
        
        # Ordre
        self.sell(size=position_size)
        
        # Log trade event (sl_distance doit être en PIPS pour les stats)
        self.log_trade_event('ENTRY', entry_price, position_size, sl_distance=sl_distance_pips)
        
        # Log SL initial box (pour visualisation, même si pas touché)
        sl_box_low = min(entry_price, sl_price)
        sl_box_high = max(entry_price, sl_price)
        self.log_box('SL_INITIAL', self.entry_time, self.entry_time, sl_box_low, sl_box_high, metadata={'sl_price': sl_price})
        
        # Log console
        self.log(f'📉 SHORT ENTRY #{self.trade_id}: Price={entry_price:.2f}, Size={position_size}, RSI={current_rsi:.1f}, SL={sl_price:.2f} ({sl_distance_pips:.1f} pips), TP1={tp1_target:.2f} (BB Mid), TP2={tp2_target:.2f} (BB Lower)')
    
    def _manage_position(self):
        """Gère une position existante avec TP dynamiques sur BB"""
        
        # IMPORTANT: Utiliser high/low pour les touches de niveaux, pas close!
        current_high = self.data.high[0]
        current_low = self.data.low[0]
        current_close = self.data.close[0]
        
        # Bandes BB actuelles (dynamiques)
        bb_upper = self.bb.lines.top[0]
        bb_middle = self.bb.lines.mid[0]
        bb_lower = self.bb.lines.bot[0]
        
        if self.position_direction == 'LONG':
            # Check SL / BE (utiliser LOW pour LONG)
            if current_low <= self.sl_price:
                exit_time = self.datas[0].datetime.datetime(0)
                price_low = min(self.entry_price, self.sl_price)
                price_high = max(self.entry_price, self.sl_price)
                
                # PnL basé sur SL price (pas low, car ordre stop au SL exact)
                # Si TP1 touché, calculer sur position restante
                if self.tp1_hit:
                    remaining_size = self.entry_size * (1 - self.p.tp1_ratio)
                    pnl = (self.sl_price - self.entry_price) * remaining_size
                else:
                    pnl = (self.sl_price - self.entry_price) * self.entry_size
                
                # Déterminer le type de sortie
                if self.breakeven_active:
                    exit_type = 'BE'
                    self.log(f'⚪ BE HIT: PnL={pnl:.2f}')
                    # Pas de rectangle pour BE (évite superposition visuelle)
                else:
                    exit_type = 'SL'
                    self.log(f'❌ SL HIT: PnL={pnl:.2f}')
                    # Rectangle rouge pour SL réel
                    self.log_box('SL', self.entry_time, exit_time, price_low, price_high)
                
                self.close()
                self.log_trade_event(exit_type, self.sl_price, pnl=pnl)
                self.in_position = False
            
            else:
                # Check TP1 (utiliser HIGH pour LONG)
                if current_high >= bb_middle and not self.tp1_hit:
                    exit_time = self.datas[0].datetime.datetime(0)
                    tp1_price = bb_middle  # Prix exact du TP1
                    price_low = min(self.entry_price, tp1_price)
                    price_high = max(self.entry_price, tp1_price)
                    self.log_box('TP1', self.entry_time, exit_time, price_low, price_high)
                    
                    self.tp1_hit = True
                    partial_size = self.entry_size * self.p.tp1_ratio
                    pnl = (tp1_price - self.entry_price) * partial_size
                    self.log(f'✅ TP1 HIT (BB Middle): PnL={pnl:.2f}')
                    self.log_trade_event('TP1', tp1_price, pnl=pnl)
                    
                    # Break-even (offset en PIPS)
                    if self.p.enable_breakeven:
                        be_offset_price = self.pips_to_price(self.p.breakeven_offset)
                        self.sl_price = self.entry_price + be_offset_price
                        self.breakeven_active = True  # Marquer qu'on est en BE
                        self.log(f'⚡ Break-even: SL moved to {self.sl_price:.2f} (+{self.p.breakeven_offset} pips)')
                
                # Check TP2 (APRÈS avoir potentiellement déclenché TP1, utiliser HIGH)
                if current_high >= bb_upper:
                    exit_time = self.datas[0].datetime.datetime(0)
                    tp2_price = bb_upper  # Prix exact du TP2
                    price_low = min(self.entry_price, tp2_price)
                    price_high = max(self.entry_price, tp2_price)
                    self.log_box('TP2', self.entry_time, exit_time, price_low, price_high)
                    
                    self.close()
                    # TP2 PnL sur la position RESTANTE (après TP1)
                    remaining_size = self.entry_size * (1 - self.p.tp1_ratio)
                    pnl = (tp2_price - self.entry_price) * remaining_size
                    self.log(f'✅ TP2 HIT (BB Upper): PnL={pnl:.2f}')
                    self.log_trade_event('TP2', tp2_price, pnl=pnl)
                    self.in_position = False
        
        elif self.position_direction == 'SHORT':
            # Check SL / BE (utiliser HIGH pour SHORT)
            if current_high >= self.sl_price:
                exit_time = self.datas[0].datetime.datetime(0)
                price_low = min(self.entry_price, self.sl_price)
                price_high = max(self.entry_price, self.sl_price)
                
                # PnL basé sur SL price (pas high, car ordre stop au SL exact)
                # Si TP1 touché, calculer sur position restante
                if self.tp1_hit:
                    remaining_size = self.entry_size * (1 - self.p.tp1_ratio)
                    pnl = (self.entry_price - self.sl_price) * remaining_size
                else:
                    pnl = (self.entry_price - self.sl_price) * self.entry_size
                
                # Déterminer le type de sortie
                if self.breakeven_active:
                    exit_type = 'BE'
                    self.log(f'⚪ BE HIT: PnL={pnl:.2f}')
                    # Pas de rectangle pour BE
                else:
                    exit_type = 'SL'
                    self.log(f'❌ SL HIT: PnL={pnl:.2f}')
                    # Rectangle rouge pour SL réel
                    self.log_box('SL', self.entry_time, exit_time, price_low, price_high)
                
                self.close()
                self.log_trade_event(exit_type, self.sl_price, pnl=pnl)
                self.in_position = False
            
            else:
                # Check TP1 (utiliser LOW pour SHORT)
                if current_low <= bb_middle and not self.tp1_hit:
                    exit_time = self.datas[0].datetime.datetime(0)
                    tp1_price = bb_middle  # Prix exact du TP1
                    price_low = min(self.entry_price, tp1_price)
                    price_high = max(self.entry_price, tp1_price)
                    self.log_box('TP1', self.entry_time, exit_time, price_low, price_high)
                    
                    self.tp1_hit = True
                    partial_size = self.entry_size * self.p.tp1_ratio
                    pnl = (self.entry_price - tp1_price) * partial_size
                    self.log(f'✅ TP1 HIT (BB Middle): PnL={pnl:.2f}')
                    self.log_trade_event('TP1', tp1_price, pnl=pnl)
                    
                    # Break-even (offset en PIPS)
                    if self.p.enable_breakeven:
                        be_offset_price = self.pips_to_price(self.p.breakeven_offset)
                        self.sl_price = self.entry_price - be_offset_price
                        self.breakeven_active = True  # Marquer qu'on est en BE
                        self.log(f'⚡ Break-even: SL moved to {self.sl_price:.2f} (-{self.p.breakeven_offset} pips)')
                
                # Check TP2 (APRÈS avoir potentiellement déclenché TP1, utiliser LOW)
                if current_low <= bb_lower:
                    exit_time = self.datas[0].datetime.datetime(0)
                    tp2_price = bb_lower  # Prix exact du TP2
                    price_low = min(self.entry_price, tp2_price)
                    price_high = max(self.entry_price, tp2_price)
                    self.log_box('TP2', self.entry_time, exit_time, price_low, price_high)
                    
                    self.close()
                    # TP2 PnL sur la position RESTANTE (après TP1)
                    remaining_size = self.entry_size * (1 - self.p.tp1_ratio)
                    pnl = (self.entry_price - tp2_price) * remaining_size
                    self.log(f'✅ TP2 HIT (BB Lower): PnL={pnl:.2f}')
                    self.log_trade_event('TP2', tp2_price, pnl=pnl)
                    self.in_position = False
