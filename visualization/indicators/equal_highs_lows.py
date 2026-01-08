"""
Equal High/Low (EQH/EQL) Liquidity Indicator

Détecte les zones de liquidité où le prix forme des égalités de hauts/bas.
Porté depuis Pine Script AlgoAlpha.

Usage YAML:
    indicators:
      - name: equal_highs_lows
        module: equal_highs_lows.py
        timeframe: M3
        panel: main
        params:
          tolerance: 0.05           # Tolérance pour égalité (0.001-0.1)
          use_rsi_filter: true      # Filtrer par RSI
          rsi_threshold: 5          # Seuil RSI (1-30)
          max_zone_age: 1000        # Âge max zone (bars)
          sweep_type: body          # 'body' ou 'wick'
          allow_rejection: false    # Nécessite 2 closes pour mitigation
"""

from core.indicator_base import IndicatorBase
from core.models import IndicatorResult, RectanglePrimitive, PointPrimitive
import pandas as pd
import numpy as np


class Indicator(IndicatorBase):
    """Equal High/Low (EQH/EQL) - Zones de liquidité"""
    
    def __init__(self, params: dict):
        super().__init__(params)
        self.tolerance = params.get('tolerance', 0.05)
        self.use_rsi_filter = params.get('use_rsi_filter', True)
        self.rsi_threshold = params.get('rsi_threshold', 5)
        self.max_zone_age = params.get('max_zone_age', 1000)
        self.sweep_type = params.get('sweep_type', 'body')  # 'body' ou 'wick'
        self.allow_rejection = params.get('allow_rejection', False)
    
    def calculate(self, candles: pd.DataFrame) -> IndicatorResult:
        self.validate_candles(candles)
        result = IndicatorResult()
        
        # 1. Calculer variance (pour tolérance dynamique)
        variance = self._calculate_variance(candles)
        
        # 2. Calculer RSI pour filtrage
        rsi = self._calculate_rsi(candles)
        
        # 3. Détecter égalités de hauts/bas
        eqh_indices = self._detect_equal_highs(candles, variance, rsi)
        eql_indices = self._detect_equal_lows(candles, variance, rsi)
        
        # 4. Créer zones actives et gérer mitigation
        active_zones = []
        
        # Créer zones EQH (resistance)
        for idx in eqh_indices:
            zone = self._create_eqh_zone(candles, idx)
            active_zones.append(zone)
        
        # Créer zones EQL (support)
        for idx in eql_indices:
            zone = self._create_eql_zone(candles, idx)
            active_zones.append(zone)
        
        # 5. Vérifier mitigation des zones
        mitigated_zones = []
        for zone in active_zones:
            is_mitigated, mitigation_idx = self._check_mitigation(
                candles, zone['index'], zone['price'], zone['type']
            )
            
            if is_mitigated:
                zone['exit_index'] = mitigation_idx
                mitigated_zones.append(zone)

        # NOUVEAU : Créer séries pour Backtrader
        eqh_signal = pd.Series(0, index=candles.index)
        eql_signal = pd.Series(0, index=candles.index)
        zone_strength = pd.Series(0, index=candles.index)

        for zone in active_zones:
            idx = zone['index']
            if zone['type'] == 'eqh':
                eqh_signal.iloc[idx] = 1
            else:
                eql_signal.iloc[idx] = 1

            # Force = nombre de touches
            zone_strength.iloc[idx] = zone['touch_count']

        # Ajouter aux séries (pour Backtrader)
        result.add_series('eqh_signal', eqh_signal)
        result.add_series('eql_signal', eql_signal)
        result.add_series('zone_strength', zone_strength)

        # 6. Créer primitives pour zones actives
        current_idx = len(candles) - 1
        
        for zone in active_zones:
            age = current_idx - zone['index']
            
            # Vérifier si zone expirée
            if age > self.max_zone_age:
                continue

            # Compter touches
            zone['touch_count'] = self._count_zone_touches(candles, zone)  # ← NOUVEAU
            
            # Créer rectangle
            primitive = self._zone_to_primitive(zone, current_idx)
            result.add_primitive(primitive)
            
            # Ajouter point de signal
            point = self._create_signal_point(zone)
            result.add_primitive(point)
        
        result.add_meta('total_eqh', len([z for z in active_zones if z['type'] == 'eqh']))
        result.add_meta('total_eql', len([z for z in active_zones if z['type'] == 'eql']))
        result.add_meta('mitigated', len(mitigated_zones))
        
        return result
    
    def _calculate_variance(self, candles):
        """Calcule variance lissée pour tolérance dynamique"""
        high_diff = np.abs(candles['high'].diff())
        low_diff = np.abs(candles['low'].diff())
        variance = (high_diff + low_diff) / 2
        
        # EMA lissage (500 périodes comme Pine Script)
        smoothed = variance.ewm(span=500, adjust=False).mean()
        return smoothed.fillna(0)
    
    def _calculate_rsi(self, candles, period=14):
        """Calcule RSI pour filtrage"""
        delta = candles['close'].diff()
        gain = (delta.where(delta > 0, 0)).rolling(window=period).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(window=period).mean()
        rs = gain / loss
        rsi = 100 - (100 / (1 + rs))
        return rsi.fillna(50)
    
    def _detect_equal_highs(self, candles, variance, rsi):
        """Détecte Equal Highs (EQH)"""
        highs = candles['high'].values
        indices = []
        
        for i in range(1, len(candles)):
            # Vérifier égalité avec tolérance
            diff = abs(highs[i] - highs[i-1])
            threshold = variance.iloc[i] * self.tolerance
            
            is_equal = diff < threshold
            
            # Filtrage RSI (overbought)
            if self.use_rsi_filter:
                is_filtered = rsi.iloc[i] > 50 + self.rsi_threshold
            else:
                is_filtered = True
            
            # Pas de répétition immédiate
            prev_equal = i > 1 and abs(highs[i-1] - highs[i-2]) < threshold
            
            if is_equal and is_filtered and not prev_equal:
                indices.append(i)
        
        return indices
    
    def _detect_equal_lows(self, candles, variance, rsi):
        """Détecte Equal Lows (EQL)"""
        lows = candles['low'].values
        indices = []
        
        for i in range(1, len(candles)):
            # Vérifier égalité avec tolérance
            diff = abs(lows[i] - lows[i-1])
            threshold = variance.iloc[i] * self.tolerance
            
            is_equal = diff < threshold
            
            # Filtrage RSI (oversold)
            if self.use_rsi_filter:
                is_filtered = rsi.iloc[i] < 50 - self.rsi_threshold
            else:
                is_filtered = True
            
            # Pas de répétition immédiate
            prev_equal = i > 1 and abs(lows[i-1] - lows[i-2]) < threshold
            
            if is_equal and is_filtered and not prev_equal:
                indices.append(i)
        
        return indices

    def _create_eqh_zone(self, candles, idx):
        """Crée zone EQH (resistance)"""
        high_price = max(candles.iloc[idx]['high'], candles.iloc[idx - 1]['high'])
        body_price = max(
            candles.iloc[idx]['open'],
            candles.iloc[idx]['close'],
            candles.iloc[idx - 1]['open'],
            candles.iloc[idx - 1]['close']
        )

        return {
            'type': 'eqh',
            'index': idx - 1,
            'price': high_price,
            'body_price': body_price,
            'exit_index': None,
            'touch_count': 0  # ← NOUVEAU
        }
    
    def _create_eql_zone(self, candles, idx):
        """Crée zone EQL (support)"""
        low_price = min(candles.iloc[idx]['low'], candles.iloc[idx-1]['low'])
        body_price = min(
            candles.iloc[idx]['open'], candles.iloc[idx]['close'],
            candles.iloc[idx-1]['open'], candles.iloc[idx-1]['close']
        )
        
        return {
            'type': 'eql',
            'index': idx - 1,
            'price': low_price,
            'body_price': body_price,
            'exit_index': None,
            'touch_count': 0  # ← NOUVEAU
        }
    
    def _check_mitigation(self, candles, zone_idx, zone_price, zone_type):
        """Vérifie si zone est mitigée"""
        for i in range(zone_idx + 1, len(candles)):
            candle = candles.iloc[i]
            
            if zone_type == 'eqh':
                # Resistance cassée
                if self.sweep_type == 'body':
                    cross = candle['close'] > zone_price
                    if self.allow_rejection:
                        # Vérifier 2 closes consécutifs
                        if i > 0:
                            prev_cross = candles.iloc[i-1]['close'] > zone_price
                            if cross and prev_cross:
                                return True, i
                    else:
                        if cross:
                            return True, i
                else:  # wick
                    if candle['high'] > zone_price:
                        return True, i
            
            else:  # eql
                # Support cassé
                if self.sweep_type == 'body':
                    cross = candle['close'] < zone_price
                    if self.allow_rejection:
                        # Vérifier 2 closes consécutifs
                        if i > 0:
                            prev_cross = candles.iloc[i-1]['close'] < zone_price
                            if cross and prev_cross:
                                return True, i
                    else:
                        if cross:
                            return True, i
                else:  # wick
                    if candle['low'] < zone_price:
                        return True, i
        
        return False, None

    def _count_zone_touches(self, candles, zone):
        """Compte les touches dans la zone sans traverser"""
        touches = 0
        zone_low = min(zone['price'], zone['body_price'])
        zone_high = max(zone['price'], zone['body_price'])

        for i in range(zone['index'] + 1, len(candles)):
            candle = candles.iloc[i]

            if zone['type'] == 'eqh':
                # Mèche touche zone mais close reste en-dessous
                wick_in_zone = candle['high'] >= zone_low and candle['high'] <= zone_high
                body_below = candle['close'] < zone_low

                if wick_in_zone and body_below:
                    touches += 1
            else:  # eql
                # Mèche touche zone mais close reste au-dessus
                wick_in_zone = candle['low'] >= zone_low and candle['low'] <= zone_high
                body_above = candle['close'] > zone_high

                if wick_in_zone and body_above:
                    touches += 1

        return touches
    
    def _zone_to_primitive(self, zone, current_idx):
        """Convertit zone en primitive rectangle"""
        # DÉCISIONS VISUELLES
        if zone['type'] == 'eqh':
            color = '#5b9cf6'  # Bleu (resistance)
            label = f"EQH ({zone['touch_count']})"  # ← AVEC COMPTEUR
        else:
            color = '#808080'  # Gris (support)
            label = f"EQL ({zone['touch_count']})"  # ← AVEC COMPTEUR
        
        # Zone = rectangle entre price (wick) et body_price
        price_low = min(zone['price'], zone['body_price'])
        price_high = max(zone['price'], zone['body_price'])
        
        return RectanglePrimitive(
            id=f"{zone['type']}_{zone['index']}",
            time_start_index=zone['index'],
            time_end_index=zone['exit_index'],  # None si actif
            price_low=price_low,
            price_high=price_high,
            color=color,
            alpha=0.2,
            border_color=color,
            border_width=1,
            label=label,
            layer=1,
            metadata={
                'type': zone['type'],
                'sweep_type': self.sweep_type,
                'zone_price': zone['price']
            }
        )
    
    def _create_signal_point(self, zone):
        """Crée point de signal (flèche)"""
        if zone['type'] == 'eqh':
            color = '#5b9cf6'
            shape = 'arrow_down'
            price = zone['price'] + 2  # Au-dessus
        else:
            color = '#808080'
            shape = 'arrow_up'
            price = zone['price'] - 2  # En-dessous
        
        return PointPrimitive(
            id=f"signal_{zone['type']}_{zone['index']}",
            time_index=zone['index'],
            price=price,
            color=color,
            shape=shape,
            size=6,
            layer=2
        )
