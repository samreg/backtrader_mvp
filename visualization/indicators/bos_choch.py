"""
BOS/CHOCH Detector - Smart Money Concepts

Détecte les Break of Structure (BOS) et Change of Character (CHOCH)
avec validation paramétrable (wick ou close).

Usage YAML:
    indicators:
      - name: bos_choch
        module: bos_choch.py
        timeframe: M3
        panel: main
        params:
          swing_period: 5           # Période pour détecter swings
          break_validation: wick    # 'wick' ou 'close'
          detect_bos: true
          detect_choch: true
          detect_mss: false
"""

from core.indicator_base import IndicatorBase
from core.models import IndicatorResult, LinePrimitive
import pandas as pd
import numpy as np


class Indicator(IndicatorBase):
    """BOS/CHOCH Detector avec primitives génériques"""
    
    def __init__(self, params: dict):
        super().__init__(params)
        self.swing_period = params.get('swing_period', 5)
        self.break_validation = params.get('break_validation', 'wick')  # 'wick' ou 'close'
        self.wick_count_required = params.get('wick_count_required', 1)
        self.detect_bos = params.get('detect_bos', True)
        self.detect_choch = params.get('detect_choch', False)
        self.detect_mss = params.get('detect_mss', False)
    
    def calculate(self, candles: pd.DataFrame) -> IndicatorResult:
        self.validate_candles(candles)
        result = IndicatorResult()
        
        # 1. Détecter swings
        swing_highs, swing_lows = self._detect_swings(candles)
        
        # 2. Détecter BOS (Break of Structure)
        if self.detect_bos:
            # BOS Bullish (cassure de swing high)
            for swing in swing_highs:
                break_idx = self._find_break_high(candles, swing)
                if break_idx:
                    line = self._create_bos_primitive(
                        swing, break_idx, 'bullish'
                    )
                    result.add_primitive(line)
            
            # BOS Bearish (cassure de swing low)
            for swing in swing_lows:
                break_idx = self._find_break_low(candles, swing)
                if break_idx:
                    line = self._create_bos_primitive(
                        swing, break_idx, 'bearish'
                    )
                    result.add_primitive(line)
        
        # Métadonnées
        result.add_meta('total_bos', len(result.primitives))
        result.add_meta('swing_period', self.swing_period)
        result.add_meta('break_validation', self.break_validation)
        
        return result
    
    def _detect_swings(self, candles):
        """
        Détecte swing highs et lows
        
        Un swing high = le plus haut dans une fenêtre de N bougies
        Un swing low = le plus bas dans une fenêtre de N bougies
        """
        highs = candles['high'].values
        lows = candles['low'].values
        n = self.swing_period
        
        swing_highs = []
        swing_lows = []
        
        for i in range(n, len(candles) - n):
            # Swing high : plus haut que N bougies avant et après
            if highs[i] == max(highs[i-n:i+n+1]):
                swing_highs.append({
                    'index': i,
                    'price': highs[i],
                    'time': candles.iloc[i]['time'] if 'time' in candles.columns else i
                })
            
            # Swing low : plus bas que N bougies avant et après
            if lows[i] == min(lows[i-n:i+n+1]):
                swing_lows.append({
                    'index': i,
                    'price': lows[i],
                    'time': candles.iloc[i]['time'] if 'time' in candles.columns else i
                })
        
        return swing_highs, swing_lows

    def _find_break_high(self, candles, swing):
        """Trouve la bougie qui casse un swing high (BOS bullish)"""
        if self.break_validation == 'close':
            # Validation par close (inchangé)
            for i in range(swing['index'] + 1, len(candles)):
                if candles.iloc[i]['close'] > swing['price']:
                    return i
        else:  # wick avec compteur
            wick_count = 0
            for i in range(swing['index'] + 1, len(candles)):
                if candles.iloc[i]['high'] > swing['price']:
                    wick_count += 1
                    if wick_count >= self.wick_count_required:
                        return i
        return None

    def _find_break_low(self, candles, swing):
        """Trouve la bougie qui casse un swing low (BOS bearish)"""
        if self.break_validation == 'close':
            # Validation par close (inchangé)
            for i in range(swing['index'] + 1, len(candles)):
                if candles.iloc[i]['close'] < swing['price']:
                    return i
        else:  # wick avec compteur
            wick_count = 0
            for i in range(swing['index'] + 1, len(candles)):
                if candles.iloc[i]['low'] < swing['price']:
                    wick_count += 1
                    if wick_count >= self.wick_count_required:
                        return i
        return None
    
    def _create_bos_primitive(self, swing, break_idx, direction):
        """
        Crée une primitive LinePrimitive pour BOS
        
        TOUTE la logique visuelle est ici :
        - Couleurs selon direction
        - Style de ligne
        - Label
        """
        # DÉCISIONS VISUELLES
        if direction == 'bullish':
            color = '#26a69a'  # Vert
            label = 'BOS ↑'
        else:  # bearish
            color = '#8B0000'  # Bordeaux
            label = 'BOS ↓'
        
        # Créer primitive de ligne HORIZONTALE
        return LinePrimitive(
            id=f"bos_{direction}_{swing['index']}",
            time_start_index=swing['index'],
            time_end_index=break_idx,
            price_start=swing['price'],
            price_end=swing['price'],  # Horizontal
            color=color,
            width=2,
            style='solid',
            label=label,
            layer=1,  # Au-dessus des zones (layer 0)
            metadata={
                'type': 'BOS',
                'direction': direction,
                'swing_type': 'high' if direction == 'bullish' else 'low',
                'swing_price': swing['price'],
                'swing_index': swing['index'],
                'break_index': break_idx,
                'validation': self.break_validation
            }
        )
