"""
Order Blocks Indicator - Smart Money Concepts

Détecte les zones où les institutions ont placé des ordres massifs.

Logique SMC complète:
1. Détecte les swings highs/lows
2. Vérifie impulsion forte (3 bougies avec imbalance)
   - Imbalance haussier: bas de la 3ème bougie > haut de la 1ère
   - Imbalance baissier: haut de la 3ème bougie < bas de la 1ère
3. Identifie la bougie Order Block (dernière contraire avant impulsion)
4. Track mitigation (invalidation si prix traverse totalement)

Usage YAML:
    indicators:
      - name: order_blocks
        module: order_blocks.py
        timeframe: M1
        panel: main
        params:
          swing_length: 10      # Période pour détecter swings
          min_body_size: 2.0    # Taille min body (en points)
          imbalance_bars: 3     # Nombre bougies pour imbalance
          max_zones: 15         # Zones max à garder
"""

from core.indicator_base import IndicatorBase
from core.models import IndicatorResult, ZoneObject
from core.zone_registry import ZoneRegistry
import pandas as pd


class Indicator(IndicatorBase):
    """Order Blocks Indicator"""
    
    def __init__(self, params: dict):
        super().__init__(params)
        self.swing_length = params.get('swing_length', 10)
        self.min_body_size = params.get('min_body_size', 2.0)
        self.imbalance_bars = params.get('imbalance_bars', 3)
        self.max_zones = params.get('max_zones', 15)
        self.skip_impulse_candles = params.get('skip_impulse_candles', 2)  # NOUVEAU: Ignorer N bougies après création
        
        self.zone_registry = ZoneRegistry()
    
    def calculate(self, candles: pd.DataFrame) -> IndicatorResult:
        self.validate_candles(candles)
        result = IndicatorResult()
        
        # Clear previous zones
        self.zone_registry.zones.clear()
        
        # Detect order blocks
        order_blocks = self._detect_order_blocks(candles)
        
        # Add to registry
        for ob in order_blocks:
            self.zone_registry.add_zone(ob)
        
        # Add to result (LEGACY objects for backwards compatibility)
        for zone in self.zone_registry.zones:
            result.add_object(zone)

        # NEW: Convert zones to primitives
        #for zone in self.zone_registry.zones:
        #    primitive = self._zone_to_primitive(zone, candles)
        #    print(f"🟨 order_blocks.py: Creating primitive {primitive.id}, label='{primitive.label}'")
        #    result.add_primitive(primitive)
        
        # Metadata
        result.add_meta('total_zones', len(self.zone_registry.zones))
        result.add_meta('active_zones', len([z for z in self.zone_registry.zones if z.state == 'active']))
        result.add_meta('invalidated_zones', len([z for z in self.zone_registry.zones if z.state == 'invalidated']))
        result.add_meta('bullish_zones', len([z for z in self.zone_registry.zones if z.metadata.get('direction') == 'bullish']))
        result.add_meta('bearish_zones', len([z for z in self.zone_registry.zones if z.metadata.get('direction') == 'bearish']))
        
        # Stats mitigation
        avg_mitigation = sum(z.mitigation_score for z in self.zone_registry.zones) / max(len(self.zone_registry.zones), 1)
        result.add_meta('avg_mitigation_score', round(avg_mitigation, 2))
        
        return result
    
    def _detect_order_blocks(self, candles: pd.DataFrame) -> list:
        """Détecte les order blocks"""
        order_blocks = []
        time_col = self.get_time_column(candles)
        
        # Parcourir les bougies
        for i in range(self.swing_length, len(candles) - self.imbalance_bars - 1):
            
            # === BULLISH ORDER BLOCK ===
            if self._is_swing_low(candles, i):
                has_bullish_imbalance, imbalance_end = self._has_bullish_imbalance(candles, i)
                
                if has_bullish_imbalance:
                    ob_index = self._find_last_bearish_before(candles, i)
                    
                    if ob_index is not None:
                        body_size = abs(candles.iloc[ob_index]['close'] - candles.iloc[ob_index]['open'])
                        
                        if body_size >= self.min_body_size:
                            ob = self._create_order_block(
                                candles=candles,
                                index=ob_index,
                                direction='bullish',
                                time_col=time_col,
                                imbalance_end=imbalance_end
                            )
                            
                            ob = self._check_mitigation(candles, ob, ob_index)
                            order_blocks.append(ob)
            
            # === BEARISH ORDER BLOCK ===
            if self._is_swing_high(candles, i):
                has_bearish_imbalance, imbalance_end = self._has_bearish_imbalance(candles, i)
                
                if has_bearish_imbalance:
                    ob_index = self._find_last_bullish_before(candles, i)
                    
                    if ob_index is not None:
                        body_size = abs(candles.iloc[ob_index]['close'] - candles.iloc[ob_index]['open'])
                        
                        if body_size >= self.min_body_size:
                            ob = self._create_order_block(
                                candles=candles,
                                index=ob_index,
                                direction='bearish',
                                time_col=time_col,
                                imbalance_end=imbalance_end
                            )
                            
                            ob = self._check_mitigation(candles, ob, ob_index)
                            order_blocks.append(ob)
        
        # Garder seulement les meilleures zones
        order_blocks = self._filter_best_zones(order_blocks)
        
        return order_blocks
    
    def _is_swing_low(self, candles: pd.DataFrame, i: int) -> bool:
        """Vérifie si c'est un swing low"""
        current_low = candles.iloc[i]['low']
        
        start = max(0, i - self.swing_length)
        end = min(len(candles), i + self.swing_length + 1)
        
        for j in range(start, end):
            if j != i and candles.iloc[j]['low'] < current_low:
                return False
        
        return True
    
    def _is_swing_high(self, candles: pd.DataFrame, i: int) -> bool:
        """Vérifie si c'est un swing high"""
        current_high = candles.iloc[i]['high']
        
        start = max(0, i - self.swing_length)
        end = min(len(candles), i + self.swing_length + 1)
        
        for j in range(start, end):
            if j != i and candles.iloc[j]['high'] > current_high:
                return False
        
        return True
    
    def _has_bullish_imbalance(self, candles: pd.DataFrame, start_idx: int) -> tuple:
        """
        Vérifie impulsion haussière avec imbalance
        
        Imbalance haussier: bas de la 3ème bougie > haut de la 1ère
        """
        if start_idx + self.imbalance_bars >= len(candles):
            return False, start_idx
        
        first_candle = candles.iloc[start_idx]
        third_candle = candles.iloc[start_idx + self.imbalance_bars - 1]
        
        # Imbalance: bas de la 3ème > haut de la 1ère
        if third_candle['low'] > first_candle['high']:
            return True, start_idx + self.imbalance_bars - 1
        
        return False, start_idx
    
    def _has_bearish_imbalance(self, candles: pd.DataFrame, start_idx: int) -> tuple:
        """
        Vérifie impulsion baissière avec imbalance
        
        Imbalance baissier: haut de la 3ème bougie < bas de la 1ère
        """
        if start_idx + self.imbalance_bars >= len(candles):
            return False, start_idx
        
        first_candle = candles.iloc[start_idx]
        third_candle = candles.iloc[start_idx + self.imbalance_bars - 1]
        
        # Imbalance: haut de la 3ème < bas de la 1ère
        if third_candle['high'] < first_candle['low']:
            return True, start_idx + self.imbalance_bars - 1
        
        return False, start_idx
    
    def _find_last_bearish_before(self, candles: pd.DataFrame, swing_idx: int) -> int:
        """Trouve la dernière bougie bearish avant le swing"""
        for i in range(swing_idx - 1, max(0, swing_idx - self.swing_length), -1):
            candle = candles.iloc[i]
            
            # Bougie bearish (rouge)
            if candle['close'] < candle['open']:
                return i
        
        return None
    
    def _find_last_bullish_before(self, candles: pd.DataFrame, swing_idx: int) -> int:
        """Trouve la dernière bougie bullish avant le swing"""
        for i in range(swing_idx - 1, max(0, swing_idx - self.swing_length), -1):
            candle = candles.iloc[i]
            
            # Bougie bullish (verte)
            if candle['close'] > candle['open']:
                return i
        
        return None
    
    def _create_order_block(self, candles: pd.DataFrame, index: int, direction: str, 
                           time_col: pd.Series, imbalance_end: int) -> ZoneObject:
        """Crée un ZoneObject pour l'order block"""
        candle = candles.iloc[index]
        
        zone_id = self.zone_registry.generate_id(f'ob_{self.timeframe}')

        # DEBUG
        print(
            f"🔷 Creating OB {zone_id}: index={index}, time={time_col.iloc[index]}, direction={direction}, low={candle['low']}, high={candle['high']}")
        # La zone va de la bougie OB jusqu'à invalidation
        t_start = time_col.iloc[index]
        t_end = None
        
        zone = ZoneObject(
            id=zone_id,
            t_start=t_start,
            t_end=t_end,
            low=candle['low'],
            high=candle['high'],
            type='order_block',
            state='active',
            source_tf=self.timeframe,
            entry_candle_index=index,      # NOUVEAU: Index de création
            exit_candle_index=None,        # NOUVEAU: Sera défini lors mitigation
            metadata={
                'direction': direction,
                'ob_index': index,
                'imbalance_end': imbalance_end,
                'body_size': abs(candle['close'] - candle['open']),
                'creation_time': t_start
            }
        )
        
        return zone

    def _check_mitigation(self, candles: pd.DataFrame, zone: ZoneObject,
                          ob_index: int) -> ZoneObject:
        """
        Vérifie mitigation (touches) et invalidation (traversée complète)

        NOUVELLE LOGIQUE:

        1. SKIP les N premières bougies (impulsion qui a créé l'OB)
        2. MITIGATION: Chaque touche de la zone incrémente le score
        3. INVALIDATION: Traversée complète termine l'affichage du bloc

        Mitigation Score:
        - 0.0: Jamais touché (fresh zone)
        - 0.1-0.5: Peu mitigé (1-2 touches)
        - 0.5-1.0: Modérément mitigé (3-5 touches)
        - 1.0+: Très mitigé (>5 touches)

        Invalidation:
        - OB bullish: Prix traverse SOUS le low
        - OB bearish: Prix traverse AU-DESSUS du high
        """
        time_col = self.get_time_column(candles)
        direction = zone.metadata.get('direction')
        imbalance_end = zone.metadata.get('imbalance_end', ob_index)

        # Calculer l'index de début d'analyse
        # = imbalance_end + skip_impulse_candles
        start_check_index = imbalance_end + self.skip_impulse_candles

        # DEBUG
        print(
            f"  🔸 {zone.id} ({direction}): checking from i={start_check_index} to {len(candles)}, zone=[{zone.low:.2f}, {zone.high:.2f}]")

        # Parcourir les bougies APRÈS la période d'impulsion
        for i in range(start_check_index, len(candles)):
            candle = candles.iloc[i]

            # === VÉRIFIER MITIGATION (touches) ===
            # Une bougie touche la zone si elle overlap avec la zone
            touches_zone = (candle['high'] >= zone.low and candle['low'] <= zone.high)

            if touches_zone:
                # Incrémenter le compteur de mitigation
                zone.mitigation_count += 1
                zone.last_mitigation_index = i

                # Calculer le score de mitigation
                # Formule: score = mitigation_count * 0.2
                # 1 touch = 0.2, 5 touches = 1.0, 10 touches = 2.0
                zone.mitigation_score = zone.mitigation_count * 0.2

            # === VÉRIFIER INVALIDATION (traversée) ===
            if direction == 'bullish':
                # OB bullish invalidé si prix CLÔTURE sous le low
                if candle['close'] < zone.low:
                    print(
                        f"    ❌ {zone.id} INVALIDATED at i={i}, time={time_col.iloc[i]}, close={candle['close']:.2f} < low={zone.low:.2f}")
                    zone.state = 'invalidated'
                    zone.t_end = time_col.iloc[i]
                    zone.exit_candle_index = i
                    zone.metadata['invalidation_index'] = i
                    zone.metadata['invalidation_type'] = 'close_below_low'
                    break

            elif direction == 'bearish':
                # OB bearish invalidé si prix CLÔTURE au-dessus du high
                if candle['close'] > zone.high:
                    print(
                        f"    ❌ {zone.id} INVALIDATED at i={i}, time={time_col.iloc[i]}, close={candle['close']:.2f} > high={zone.high:.2f}")
                    zone.state = 'invalidated'
                    zone.t_end = time_col.iloc[i]
                    zone.exit_candle_index = i
                    zone.metadata['invalidation_index'] = i
                    zone.metadata['invalidation_type'] = 'close_above_high'
                    break

        # DEBUG final
        if zone.state == 'active':
            print(f"    ✅ {zone.id} still ACTIVE, mitigation_count={zone.mitigation_count}")

        return zone
    
    def _filter_best_zones(self, zones: list) -> list:
        """
        Garde seulement les meilleures zones
        
        Priorité:
        1. Zones actives (non invalidées)
        2. Zones avec faible mitigation_score
        3. Zones les plus récentes
        """
        # Séparer actives et invalidées
        active = [z for z in zones if z.state == 'active']
        invalidated = [z for z in zones if z.state == 'invalidated']
        
        # Trier actives par score de mitigation (moins mitigé d'abord)
        active.sort(key=lambda z: (z.mitigation_score, -z.entry_candle_index))
        
        # Trier invalidées par temps (plus récent d'abord)
        invalidated.sort(key=lambda z: z.t_start, reverse=True)
        
        # Garder toutes les actives + quelques invalidées récentes
        max_active = self.max_zones
        max_invalidated = max(3, self.max_zones // 3)
        
        result = active[:max_active] + invalidated[:max_invalidated]
        
        return result
    
    def _zone_to_primitive(self, zone: ZoneObject, candles: pd.DataFrame):
        """
        Convert ZoneObject to RectanglePrimitive.
        
        This method encapsulates ALL visual decision logic:
        - Colors based on direction and state
        - Alpha/transparency based on mitigation score
        - Labels with mitigation count
        
        The Chart Viewer receives fully configured primitives
        and just renders them without any business logic.
        """
        from core.models import RectanglePrimitive
        
        # Get indices directly from zone (already set during detection)
        entry_idx = zone.entry_candle_index
        exit_idx = zone.exit_candle_index
        
        # BUSINESS LOGIC: Determine color and alpha
        direction = zone.metadata.get('direction', 'unknown')
        
        if zone.state == 'invalidated':
            # Invalidated zones: gray, very transparent
            color = '#9E9E9E'
            alpha = 0.1
        elif direction == 'bullish':
            # Bullish zones: green
            color = '#26a69a'
            # Less mitigated = more opaque
            alpha = max(0.15, 0.3 - (zone.mitigation_score * 0.05))
        else:  # bearish
            # Bearish zones: burgundy
            color = '#F08080'
            alpha = max(0.12, 0.25 - (zone.mitigation_score * 0.05))
        
        # Create label
        if zone.state == 'active':
            label = f"{direction.upper()} ({zone.mitigation_count})"
        else:
            label = None
        
        # Create primitive
        primitive = RectanglePrimitive(
            id=zone.id,
            time_start_index=entry_idx,
            time_end_index=exit_idx,
            price_low=zone.low,
            price_high=zone.high,
            color=color,
            alpha=alpha,
            border_color=color,
            border_width=1,
            label=label,
            layer=0,
            metadata={
                'zone_type': 'order_block',
                'direction': direction,
                'state': zone.state,
                'mitigation_count': zone.mitigation_count,
                'mitigation_score': zone.mitigation_score
            }
        )
        
        return primitive

    def get_active_zones(self):
        """
        Retourne toutes les zones non invalidées.
        Utile pour le trading multi-timeframes.
        """
        return [z for z in self.zones if z.state != "invalid"]

    def get_new_zones(self):
        """
        Retourne les zones qui ont été créées sur cette bougie.
        On utilise last_index pour identifier celles-ci.
        """
        if not hasattr(self, "last_processed_index"):
            self.last_processed_index = -1

        # bougie courante
        current_index = len(self.data) - 1

        # zones dont start_index == current_index (donc créées maintenant)
        new_zones = [z for z in self.zones if z.start_index == current_index]

        # mettre à jour l’index
        self.last_processed_index = current_index

        return new_zones

