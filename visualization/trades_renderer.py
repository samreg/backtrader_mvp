"""
Rendu des trades sous forme de rectangles sur Lightweight Charts
Conforme aux spécifications du cahier des charges
"""

import pandas as pd
import numpy as np
from lightweight_charts import Chart
from typing import Optional, Dict, List
from dataclasses import dataclass

from .config import TradeRenderConfig, DEFAULT_TRADE_RENDER_CONFIG


@dataclass
class TradeRectangle:
    """Définition d'un rectangle de trade"""
    trade_id: int
    rect_type: str  # 'SL', 'TP1', 'TP2', 'BE'
    time_start: pd.Timestamp
    time_end: pd.Timestamp
    price_low: float
    price_high: float
    color: str
    border_color: str
    opacity: float
    
    # Métadonnées pour tooltip
    direction: str  # LONG/SHORT
    entry_price: float
    exit_price: Optional[float] = None
    pnl: Optional[float] = None


class TradesRenderer:
    """
    Rendu des trades sous forme de rectangles
    
    Spécifications (cahier des charges) :
    
    A) Stop Loss (rectangle rouge)
       - Toujours affiché
       - time_start = ENTRY.time
       - time_end = sortie finale (SL/TP2/CLOSE_INVALID/BE_HIT)
       - LONG: [sl_price, entry_price]
       - SHORT: [entry_price, sl_price]
    
    B) TP1 (rectangle vert)
       - Affiché si événement TP1 existe
       - time_start = ENTRY.time
       - time_end = TP1.time
       - LONG: [entry_price, tp1_price]
       - SHORT: [tp1_price, entry_price]
    
    C) TP2 (rectangle vert plus large)
       - Affiché si événement TP2 existe
       - Recouvre aussi la zone TP1
       - time_start = ENTRY.time
       - time_end = TP2.time
       - LONG: [entry_price, tp2_price]
       - SHORT: [tp2_price, entry_price]
    
    D) Break-even
       - Si BE_HIT sans TP1/TP2 : rectangle gris
       - Même taille verticale que le SL
       - time_start = ENTRY.time
       - time_end = BE_HIT.time
    """
    
    def __init__(
        self,
        chart: Chart,
        config: TradeRenderConfig = DEFAULT_TRADE_RENDER_CONFIG
    ):
        self.chart = chart
        self.config = config
        self.rectangles: List[TradeRectangle] = []
    
    def load_trades_from_events(
        self,
        events_df: pd.DataFrame
    ) -> None:
        """
        Charge les événements de trades et génère les rectangles
        
        Args:
            events_df: DataFrame avec colonnes:
                - trade_id
                - time (datetime)
                - event_type (ENTRY, TP1, TP2, SL, BE_MOVE, SL_BE, BE_HIT, etc.)
                - price
                - direction (LONG/SHORT)
                - size (optionnel)
                - pnl (optionnel)
        """
        if events_df.empty:
            print("⚠️ Aucun événement de trade à afficher")
            return
        
        # NORMALISATION: datetime → time
        events_df = events_df.copy()
        if 'datetime' in events_df.columns and 'time' not in events_df.columns:
            events_df = events_df.rename(columns={'datetime': 'time'})
        
        # Grouper par trade_id
        trades = self._group_events_by_trade(events_df)
        
        print(f"\n📦 Génération des rectangles pour {len(trades)} trades...")
        
        # Générer les rectangles pour chaque trade
        for trade_id, trade_events in trades.items():
            rects = self._generate_rectangles_for_trade(trade_id, trade_events)
            self.rectangles.extend(rects)
        
        print(f"✅ {len(self.rectangles)} rectangles générés")
        
        # Rendu des rectangles
        self._render_all_rectangles()
    
    def _group_events_by_trade(
        self,
        events_df: pd.DataFrame
    ) -> Dict[int, pd.DataFrame]:
        """Groupe les événements par trade_id"""
        trades = {}
        
        for trade_id, group in events_df.groupby('trade_id'):
            # Tri chronologique (colonne 'time' normalisée)
            group = group.sort_values('time')
            trades[int(trade_id)] = group
        
        return trades
    
    def _generate_rectangles_for_trade(
        self,
        trade_id: int,
        events: pd.DataFrame
    ) -> List[TradeRectangle]:
        """
        Génère les rectangles pour un trade donné
        selon les spécifications du cahier des charges
        """
        rectangles = []
        
        # Extraction des événements clés
        entry = events[events['event_type'] == 'ENTRY']
        tp1 = events[events['event_type'] == 'TP1']
        tp2 = events[events['event_type'] == 'TP2']
        sl = events[events['event_type'] == 'SL']
        be_hit = events[events['event_type'].isin(['BE_HIT', 'SL_BE'])]
        close_invalid = events[events['event_type'] == 'CLOSE_INVALID']
        
        if entry.empty:
            print(f"⚠️ Trade {trade_id}: pas d'ENTRY, skip")
            return rectangles
        
        entry_event = entry.iloc[0]
        entry_time = pd.to_datetime(entry_event['time'])
        entry_price = float(entry_event['price'])
        direction = str(entry_event['direction'])
        
        # Calcul des prix SL/TP (depuis les événements ou estimation)
        sl_price = self._get_sl_price(events, entry_price, direction)
        tp1_price = self._get_tp1_price(events, entry_price, direction)
        tp2_price = self._get_tp2_price(events, entry_price, direction)
        
        # Temps de sortie finale
        exit_time = self._get_final_exit_time(events)
        
        # NOUVELLE LOGIQUE SIMPLIFIÉE:
        # - Si SL direct (pas de TP1/TP2) → Box SL rouge
        # - Si TP1 touché → Box TP1 verte (pas de SL)
        # - Si TP2 touché → Box TP1 + TP2 vertes (pas de SL)
        
        has_tp1 = not tp1.empty and tp1_price is not None
        has_tp2 = not tp2.empty and tp2_price is not None
        
        # A) Rectangle STOP LOSS (seulement si AUCUN TP touché)
        if not has_tp1 and not has_tp2:
            sl_rect = self._create_sl_rectangle(
                trade_id=trade_id,
                entry_time=entry_time,
                exit_time=exit_time,
                entry_price=entry_price,
                sl_price=sl_price,
                direction=direction
            )
            rectangles.append(sl_rect)
        
        # B) Rectangle TP1 (si TP1 existe)
        if has_tp1:
            tp1_event = tp1.iloc[0]
            tp1_time = pd.to_datetime(tp1_event['time'])
            
            tp1_rect = self._create_tp1_rectangle(
                trade_id=trade_id,
                entry_time=entry_time,
                tp1_time=tp1_time,
                entry_price=entry_price,
                tp1_price=tp1_price,
                direction=direction
            )
            rectangles.append(tp1_rect)
        
        # C) Rectangle TP2 (si TP2 existe)
        if has_tp2:
            tp2_event = tp2.iloc[0]
            tp2_time = pd.to_datetime(tp2_event['time'])
            
            tp2_rect = self._create_tp2_rectangle(
                trade_id=trade_id,
                entry_time=entry_time,
                tp2_time=tp2_time,
                entry_price=entry_price,
                tp2_price=tp2_price,
                direction=direction
            )
            rectangles.append(tp2_rect)
        
        # D) PAS de rectangle BE séparé (simplifié)
        # Le BE est implicite après TP1
        
        return rectangles
    
    def _create_sl_rectangle(
        self,
        trade_id: int,
        entry_time: pd.Timestamp,
        exit_time: pd.Timestamp,
        entry_price: float,
        sl_price: float,
        direction: str
    ) -> TradeRectangle:
        """Crée le rectangle Stop Loss"""
        if direction == 'LONG':
            price_low = sl_price
            price_high = entry_price
        else:  # SHORT
            price_low = entry_price
            price_high = sl_price
        
        return TradeRectangle(
            trade_id=trade_id,
            rect_type='SL',
            time_start=entry_time,
            time_end=exit_time,
            price_low=price_low,
            price_high=price_high,
            color=self.config.sl_color,
            border_color=self.config.sl_border,
            opacity=self.config.sl_opacity,
            direction=direction,
            entry_price=entry_price
        )
    
    def _create_tp1_rectangle(
        self,
        trade_id: int,
        entry_time: pd.Timestamp,
        tp1_time: pd.Timestamp,
        entry_price: float,
        tp1_price: float,
        direction: str
    ) -> TradeRectangle:
        """Crée le rectangle TP1"""
        if direction == 'LONG':
            price_low = entry_price
            price_high = tp1_price
        else:  # SHORT
            price_low = tp1_price
            price_high = entry_price
        
        return TradeRectangle(
            trade_id=trade_id,
            rect_type='TP1',
            time_start=entry_time,
            time_end=tp1_time,
            price_low=price_low,
            price_high=price_high,
            color=self.config.tp1_color,
            border_color=self.config.tp_border,
            opacity=self.config.tp1_opacity,
            direction=direction,
            entry_price=entry_price
        )
    
    def _create_tp2_rectangle(
        self,
        trade_id: int,
        entry_time: pd.Timestamp,
        tp2_time: pd.Timestamp,
        entry_price: float,
        tp2_price: float,
        direction: str
    ) -> TradeRectangle:
        """Crée le rectangle TP2 (plus large que TP1)"""
        if direction == 'LONG':
            price_low = entry_price
            price_high = tp2_price
        else:  # SHORT
            price_low = tp2_price
            price_high = entry_price
        
        return TradeRectangle(
            trade_id=trade_id,
            rect_type='TP2',
            time_start=entry_time,
            time_end=tp2_time,
            price_low=price_low,
            price_high=price_high,
            color=self.config.tp2_color,
            border_color=self.config.tp_border,
            opacity=self.config.tp2_opacity,
            direction=direction,
            entry_price=entry_price
        )
    
    def _create_be_rectangle(
        self,
        trade_id: int,
        entry_time: pd.Timestamp,
        be_time: pd.Timestamp,
        entry_price: float,
        sl_price: float,  # Pour garder la même taille que SL
        direction: str
    ) -> TradeRectangle:
        """Crée le rectangle Break-Even (même taille que SL)"""
        if direction == 'LONG':
            price_low = sl_price
            price_high = entry_price
        else:  # SHORT
            price_low = entry_price
            price_high = sl_price
        
        return TradeRectangle(
            trade_id=trade_id,
            rect_type='BE',
            time_start=entry_time,
            time_end=be_time,
            price_low=price_low,
            price_high=price_high,
            color=self.config.be_color,
            border_color=self.config.be_border,
            opacity=self.config.be_opacity,
            direction=direction,
            entry_price=entry_price
        )
    
    def _get_sl_price(
        self,
        events: pd.DataFrame,
        entry_price: float,
        direction: str
    ) -> float:
        """
        Récupère le prix du Stop Loss
        
        Logique:
        1. Cherche SL_BE (break-even) en premier (dernier SL actif)
        2. Sinon cherche SL initial
        3. Sinon estime à ±2%
        """
        # Cherche d'abord SL_BE (break-even après TP1)
        sl_be_events = events[events['event_type'] == 'SL_BE']
        if not sl_be_events.empty:
            # Pour BE, le prix est généralement l'entry price
            # Mais on prend quand même le prix de l'événement
            return float(sl_be_events.iloc[0]['price'])
        
        # Cherche un événement SL initial
        sl_events = events[events['event_type'] == 'SL']
        if not sl_events.empty:
            return float(sl_events.iloc[0]['price'])
        
        # Cherche BE_MOVE pour savoir si le SL a été déplacé
        be_move_events = events[events['event_type'] == 'BE_MOVE']
        if not be_move_events.empty:
            # Si BE_MOVE existe, le SL final est au prix d'entrée
            return entry_price
        
        # Sinon, estimation basée sur la direction (arbitraire)
        # Tu peux ajuster selon tes besoins
        risk_percent = 0.02  # 2% de risque par défaut
        if direction == 'LONG':
            return entry_price * (1 - risk_percent)
        else:  # SHORT
            return entry_price * (1 + risk_percent)
    
    def _get_tp1_price(
        self,
        events: pd.DataFrame,
        entry_price: float,
        direction: str
    ) -> Optional[float]:
        """Récupère le prix du TP1"""
        tp1_events = events[events['event_type'] == 'TP1']
        if not tp1_events.empty:
            return float(tp1_events.iloc[0]['price'])
        return None
    
    def _get_tp2_price(
        self,
        events: pd.DataFrame,
        entry_price: float,
        direction: str
    ) -> Optional[float]:
        """Récupère le prix du TP2"""
        tp2_events = events[events['event_type'] == 'TP2']
        if not tp2_events.empty:
            return float(tp2_events.iloc[0]['price'])
        return None
    
    def _get_final_exit_time(self, events: pd.DataFrame) -> pd.Timestamp:
        """Trouve le temps de sortie finale du trade"""
        # Événements de sortie possibles
        exit_types = ['TP2', 'SL', 'BE_HIT', 'SL_BE', 'CLOSE_INVALID']
        
        exit_events = events[events['event_type'].isin(exit_types)]
        
        if not exit_events.empty:
            # Prendre le dernier événement de sortie
            return pd.to_datetime(exit_events.iloc[-1]['time'])
        
        # Si pas de sortie explicite, prendre le dernier événement
        return pd.to_datetime(events.iloc[-1]['time'])
    
    def _render_all_rectangles(self) -> None:
        """
        Rend tous les rectangles sur le graphique
        
        Note: Lightweight Charts ne supporte pas nativement les rectangles remplis.
        On utilise donc des lignes horizontales avec opacité pour simuler.
        """
        if not self.rectangles:
            print("⚠️ Aucun rectangle à afficher")
            return
        
        print(f"\n🎨 Rendu de {len(self.rectangles)} rectangles...")
        
        # Créer fichier de log détaillé
        import json
        from pathlib import Path
        
        log_data = []
        
        # Grouper par type pour z-order correct
        # Ordre de rendu : TP2 (fond) -> TP1 -> SL/BE (dessus)
        tp2_rects = [r for r in self.rectangles if r.rect_type == 'TP2']
        tp1_rects = [r for r in self.rectangles if r.rect_type == 'TP1']
        sl_rects = [r for r in self.rectangles if r.rect_type == 'SL']
        be_rects = [r for r in self.rectangles if r.rect_type == 'BE']
        
        # Rendu dans l'ordre (fond vers dessus)
        for rect_list, label in [
            (tp2_rects, 'TP2'),
            (tp1_rects, 'TP1'),
            (be_rects, 'BE'),
            (sl_rects, 'SL')
        ]:
            if rect_list:
                print(f"\n{'='*70}")
                print(f"📦 Rendu {len(rect_list)} rectangles {label}")
                print(f"{'='*70}")
                for rect in rect_list:
                    log_entry = self._render_single_rectangle(rect)
                    log_data.append(log_entry)
                print(f"  ✅ {len(rect_list)} rectangles {label} dessinés")
        
        # Sauvegarder le log
        output_dir = Path('output')
        output_dir.mkdir(exist_ok=True)
        log_file = output_dir / 'boxes_log.json'
        
        with open(log_file, 'w') as f:
            json.dump(log_data, f, indent=2, default=str)
        
        print(f"\n📝 Log détaillé sauvegardé: {log_file}")
        
        # Créer aussi un CSV lisible
        import pandas as pd
        log_df = pd.DataFrame(log_data)
        csv_file = output_dir / 'boxes_log.csv'
        log_df.to_csv(csv_file, index=False)
        print(f"📊 Log CSV sauvegardé: {csv_file}")
        
        # Afficher résumé
        print(f"\n{'='*70}")
        print("📊 RÉSUMÉ DES BOXES")
        print(f"{'='*70}")
        summary = log_df.groupby('type').agg({
            'trade_id': 'count',
            'duration_minutes': 'mean',
            'price_range': 'mean'
        }).round(2)
        summary.columns = ['count', 'avg_duration_min', 'avg_price_range']
        print(summary.to_string())
        print(f"{'='*70}\n")
    
    def _render_single_rectangle(self, rect: TradeRectangle) -> dict:
        """
        Rend un rectangle individuel en utilisant chart.box() de lightweight-charts
        
        Syntaxe correcte selon l'exemple fourni :
        chart.box(
            start_time=pd.Timestamp,
            start_value=float,
            end_time=pd.Timestamp,
            end_value=float,
            fill_color='rgba(...)',
            color='rgba(...)',  # bordure
            width=2
        )
        
        Returns:
            dict: Log détaillé de la box créée
        """
        # Déterminer les couleurs selon le type
        if rect.rect_type == 'SL':
            fill_color = 'rgba(255, 0, 0, 0.2)'
            border_color = 'rgba(255, 0, 0, 0.8)'
        elif rect.rect_type == 'TP1':
            fill_color = 'rgba(0, 255, 0, 0.15)'
            border_color = 'rgba(0, 255, 0, 0.6)'
        elif rect.rect_type == 'TP2':
            fill_color = 'rgba(0, 200, 0, 0.2)'
            border_color = 'rgba(0, 200, 0, 0.7)'
        elif rect.rect_type == 'BE':
            fill_color = 'rgba(128, 128, 128, 0.2)'
            border_color = 'rgba(128, 128, 128, 0.6)'
        else:
            fill_color = rect.color
            border_color = rect.border_color
        
        # Calcul durée et range
        duration_minutes = (rect.time_end - rect.time_start).total_seconds() / 60
        price_range = abs(rect.price_high - rect.price_low)
        
        # Log détaillé
        log_entry = {
            'trade_id': rect.trade_id,
            'type': rect.rect_type,
            'direction': rect.direction,
            'entry_price': rect.entry_price,
            
            # Timestamps
            'start_time': rect.time_start.strftime('%Y-%m-%d %H:%M:%S'),
            'end_time': rect.time_end.strftime('%Y-%m-%d %H:%M:%S'),
            'duration_minutes': round(duration_minutes, 1),
            
            # Prix
            'price_low': round(rect.price_low, 2),
            'price_high': round(rect.price_high, 2),
            'price_range': round(price_range, 2),
            
            # Couleurs
            'fill_color': fill_color,
            'border_color': border_color,
            
            # PnL si disponible
            'pnl': rect.pnl if rect.pnl is not None else 0
        }
        
        # Affichage console détaillé
        print(f"\n📦 Trade #{rect.trade_id} - {rect.rect_type} ({rect.direction})")
        print(f"   ⏰ Temps:  {rect.time_start.strftime('%Y-%m-%d %H:%M')} → {rect.time_end.strftime('%H:%M')} ({duration_minutes:.0f} min)")
        print(f"   💰 Prix:   {rect.price_low:.2f} → {rect.price_high:.2f} (range: {price_range:.2f})")
        print(f"   🎯 Entry:  {rect.entry_price:.2f}")
        
        if rect.rect_type == 'SL':
            distance_from_entry = abs(rect.entry_price - rect.price_low if rect.direction == 'LONG' else rect.price_high - rect.entry_price)
            print(f"   ⚠️  SL distance: {distance_from_entry:.2f} points")
        
        if rect.pnl is not None:
            print(f"   💵 PnL:    {rect.pnl:.2f}")
        
        print(f"   🎨 Couleur: {fill_color}")
        
        # Dessiner le rectangle avec la syntaxe chart.box()
        try:
            self.chart.box(
                start_time=rect.time_start,  # pd.Timestamp
                start_value=rect.price_low,
                end_time=rect.time_end,      # pd.Timestamp
                end_value=rect.price_high,
                fill_color=fill_color,
                color=border_color,          # Couleur de bordure
                width=2
            )
            print(f"   ✅ Box dessinée avec succès")
            log_entry['status'] = 'SUCCESS'
        except Exception as e:
            print(f"   ❌ Erreur box: {e}")
            log_entry['status'] = 'ERROR'
            log_entry['error'] = str(e)
        
        return log_entry


# Fonction utilitaire rapide
def quick_add_trades(
    chart: Chart,
    trades_file: str,
    config: Optional[TradeRenderConfig] = None
) -> TradesRenderer:
    """
    Ajoute rapidement les trades à un graphique existant
    
    Args:
        chart: Instance Chart existante
        trades_file: Chemin vers CSV/JSON des événements
        config: Configuration optionnelle
    
    Returns:
        TradesRenderer instance
    """
    from .data_loader import DataLoader
    
    # Chargement
    events = DataLoader.load_trades(trades_file)
    
    # Rendu
    renderer = TradesRenderer(chart, config or DEFAULT_TRADE_RENDER_CONFIG)
    renderer.load_trades_from_events(events)
    
    return renderer
