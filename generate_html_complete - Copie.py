#!/usr/bin/env python3
"""
Générateur HTML Complet avec :
- Bollinger Bands (std 1.5)
- RSI en pied
- Stats backtest
- Navigation entre trades
- Modal heatmaps
- Tooltips trades
"""

import pandas as pd
import numpy as np
import json
import yaml
from pathlib import Path

# Import module MT5 pour get_data_filename
from data.mt5_loader import get_data_filename


def load_config(config_file='config_rsi_amplitude.yaml'):
    """Charge la configuration depuis le YAML"""
    if not Path(config_file).exists():
        print(f"⚠️  Config {config_file} non trouvée, utilisation valeurs par défaut")
        return {'data': {'symbol': 'NAS100', 'timeframe': 'M3'}}
    
    with open(config_file, 'r', encoding='utf-8') as f:
        config = yaml.safe_load(f)
    
    return config


def to_utc_timestamp(dt):
    """Convertit un datetime (tz-aware ou tz-naive) en timestamp UNIX
    Note: timestamp() retourne TOUJOURS un timestamp universel (secondes depuis epoch UTC)
    peu importe le timezone du datetime. Donc on garde Europe/Paris sans conversion.
    """
    dt = pd.to_datetime(dt)
    if dt.tz is None:
        # Naive → localiser en Europe/Paris
        dt = dt.tz_localize('Europe/Paris')
    # Ne PAS convertir en UTC ! timestamp() est déjà universel
    # Que le datetime soit en Europe/Paris ou UTC, timestamp() retourne le même nombre
    return int(dt.timestamp())


def calculate_bollinger_bands(df, period=20, std_dev=1.5):
    """Calcule les bandes de Bollinger"""
    df = df.copy()
    df['sma'] = df['close'].rolling(window=period).mean()
    df['std'] = df['close'].rolling(window=period).std()
    df['bb_upper'] = df['sma'] + (std_dev * df['std'])
    df['bb_lower'] = df['sma'] - (std_dev * df['std'])
    return df


def calculate_rsi(df, period=14):
    """Calcule le RSI avec la même méthode que Backtrader (EMA, pas SMA)"""
    df = df.copy()
    delta = df['close'].diff()
    
    # Séparer gains et pertes
    gain = delta.where(delta > 0, 0)
    loss = -delta.where(delta < 0, 0)
    
    # IMPORTANT: Utiliser EWM (Exponential Weighted Moving) comme Backtrader
    # au lieu de rolling().mean() (Simple Moving Average)
    avg_gain = gain.ewm(alpha=1/period, adjust=False).mean()
    avg_loss = loss.ewm(alpha=1/period, adjust=False).mean()
    
    rs = avg_gain / avg_loss
    df['rsi'] = 100 - (100 / (1 + rs))
    
    return df


def generate_complete_html(config_file='config_rsi_amplitude.yaml'):
    """Génère HTML complet interactif"""
    
    print("\n" + "="*70)
    print("GÉNÉRATION HTML COMPLET INTERACTIF")
    print("="*70 + "\n")
    
    # Extraire nom du fichier config (sans extension) pour le titre
    config_name = Path(config_file).stem  # Ex: config_rsi_amplitude
    
    # Charger config (IMPORTANT: passer config_file en paramètre)
    config = load_config(config_file)
    
    # Extraire infos pour le titre
    symbol = config.get('data', {}).get('symbol', 'NAS100')
    timeframe = config.get('data', {}).get('timeframe', 'M3')
    strategy_name = config.get('strategy_name', 'Strategy')
    
    # Déterminer fichier de données
    use_specific = config.get('data', {}).get('use_specific_csv_file', False)
    
    if use_specific:
        # Mode spécifique
        data_file = config['data']['file']
    else:
        # Mode auto: utiliser get_data_filename
        data_file = f"data/{get_data_filename(symbol, timeframe)}"
    
    print(f"📂 Fichier données: {data_file}")
    
    # Charger données
    if not Path(data_file).exists():
        print(f"❌ Fichier non trouvé: {data_file}")
        print("   Lancez d'abord: python run_backtest.py")
        return
    
    df = pd.read_csv(data_file, parse_dates=['datetime'])
    
    # IMPORTANT: Gérer timezone (tz-aware ou tz-naive)
    # Les données MT5 sont en Europe/Paris (avec DST automatique)
    if df['datetime'].dt.tz is None:
        # Datetime naïf → localiser en Europe/Paris (gère DST automatiquement)
        df['datetime'] = df['datetime'].dt.tz_localize('Europe/Paris')
    else:
        # Déjà tz-aware → convertir en Europe/Paris si nécessaire
        df['datetime'] = df['datetime'].dt.tz_convert('Europe/Paris')
    
    # Vérifier si trades_backtest.csv existe
    trades_file = Path('output/trades_backtest.csv')
    if not trades_file.exists():
        print(f"\n❌ Fichier trades manquant: {trades_file}")
        print("   Le backtest n'a probablement généré aucun trade.")
        print("   Causes possibles:")
        print("   - Filtres SL trop stricts (tous les trades rejetés)")
        print("   - Pas de signaux générés")
        print("   - Erreur dans la stratégie")
        return
    
    trades = pd.read_csv('output/trades_backtest.csv', parse_dates=['datetime'])
    
    # IMPORTANT: Gérer timezone
    # Les données MT5 sont en Europe/Paris (avec DST automatique)
    if trades['datetime'].dt.tz is None:
        trades['datetime'] = trades['datetime'].dt.tz_localize('Europe/Paris')
    else:
        trades['datetime'] = trades['datetime'].dt.tz_convert('Europe/Paris')
    
    # Portfolio stats (PnL avec commissions)
    portfolio_stats_file = Path('output/portfolio_stats.json')
    if portfolio_stats_file.exists():
        import json
        with open(portfolio_stats_file, 'r') as f:
            portfolio_stats = json.load(f)
        portfolio_pnl_with_commissions = portfolio_stats.get('total_pnl', None)
    else:
        portfolio_pnl_with_commissions = None
    
    # Boxes optionnelles (peuvent ne pas exister)
    boxes_file = Path('output/boxes_log.csv')
    if boxes_file.exists():
        boxes = pd.read_csv(boxes_file)
        print(f"   ✅ {len(df)} chandelles")
        print(f"   ✅ {len(boxes)} boxes")
        print(f"   ✅ {len(trades['trade_id'].unique())} trades")
    else:
        print(f"   ✅ {len(df)} chandelles")
        print(f"   ⚠️  Pas de boxes (boxes_log.csv manquant)")
        print(f"   ✅ {len(trades['trade_id'].unique())} trades")
        boxes = pd.DataFrame()  # DataFrame vide
    
    # Calculer indicateurs
    print("\n📊 Calcul des indicateurs...")
    df = calculate_bollinger_bands(df, period=20, std_dev=1.5)
    df = calculate_rsi(df, period=14)
    
    # Convertir en JSON
    candles = []
    bb_upper = []
    bb_middle = []
    bb_lower = []
    rsi_data = []
    
    for _, row in df.iterrows():
        timestamp = int(row['datetime'].timestamp())
        
        candles.append({
            'time': timestamp,
            'open': float(row['open']),
            'high': float(row['high']),
            'low': float(row['low']),
            'close': float(row['close'])
        })
        
        if not pd.isna(row['bb_upper']):
            bb_upper.append({'time': timestamp, 'value': float(row['bb_upper'])})
            bb_middle.append({'time': timestamp, 'value': float(row['sma'])})
            bb_lower.append({'time': timestamp, 'value': float(row['bb_lower'])})
        
        if not pd.isna(row['rsi']):
            rsi_data.append({'time': timestamp, 'value': float(row['rsi'])})
    
    # Rectangles
    rectangles = []
    for _, box in boxes.iterrows():
        # Utiliser fonction helper pour gérer tz-aware/tz-naive
        start_time = to_utc_timestamp(box['start_time'])
        end_time = to_utc_timestamp(box['end_time'])
        
        colors = {
            'SL': {'fill': 'rgba(255, 0, 0, 0.15)', 'border': 'rgba(255, 0, 0, 0.8)'},
            'SL_INITIAL': {'fill': 'rgba(255, 100, 0, 0.08)', 'border': 'rgba(255, 100, 0, 0.5)'},  # Orange transparent
            'TP1': {'fill': 'rgba(0, 255, 0, 0.1)', 'border': 'rgba(0, 255, 0, 0.6)'},
            'TP2': {'fill': 'rgba(0, 200, 0, 0.15)', 'border': 'rgba(0, 200, 0, 0.7)'}
        }
        
        box_type = box['type']
        color = colors.get(box_type, colors['SL'])
        
        rect_data = {
            'type': box_type,
            'trade_id': int(box['trade_id']),
            'time1': start_time,
            'time2': end_time,
            'price1': float(box['price_low']),
            'price2': float(box['price_high']),
            'fillColor': color['fill'],
            'borderColor': color['border']
        }
        
        # Ajouter metadata si disponible (ex: sl_price pour triangle)
        if 'metadata' in box and pd.notna(box['metadata']):
            rect_data['metadata'] = box['metadata']
        
        rectangles.append(rect_data)
    
    # Stats backtest - Par TRADE
    total_trades = len(trades['trade_id'].unique())
    
    # Événements de sortie
    exit_events = trades[trades['event_type'].isin(['SL', 'BE', 'TP1', 'TP2', 'FORCED_CLOSE'])]
    
    # 1. Événement FINAL par trade (comment le trade s'est terminé)
    final_exit = exit_events.groupby('trade_id')['event_type'].last()
    num_final_sl = (final_exit == 'SL').sum()
    num_final_be = (final_exit == 'BE').sum()
    num_final_tp1 = (final_exit == 'TP1').sum()
    num_final_tp2 = (final_exit == 'TP2').sum()
    num_forced_close = (final_exit == 'FORCED_CLOSE').sum()
    
    # 2. Niveaux ATTEINTS (combien de trades ont touché chaque niveau)
    num_reached_tp1 = exit_events[exit_events['event_type'] == 'TP1'].groupby('trade_id').size().shape[0]
    num_reached_tp2 = exit_events[exit_events['event_type'] == 'TP2'].groupby('trade_id').size().shape[0]
    
    # 3. LOGIQUE CORRECTE WINS/LOSSES
    # WIN = Trade ayant atteint TP1 (peu importe si TP2 ou BE après)
    # LOSS = Trade fermé au SL
    # SCRATCH = Trade fermé au BE sans avoir atteint TP1 (rare)
    wins = num_reached_tp1  # Tous les trades ayant touché TP1
    losses = num_final_sl    # Tous les trades fermés au SL
    
    # Simplification: Si BE activé après TP1, tous les BE sont déjà comptés dans wins
    # Donc scratches = trades qui n'ont touché ni TP1 ni SL = 0 normalement
    scratches = total_trades - wins - losses
    
    win_rate = (wins / total_trades * 100) if total_trades > 0 else 0
    
    # PnL stats - AJUSTEMENT POUR COMMISSIONS
    trade_pnl = exit_events.groupby('trade_id')['pnl'].sum().reset_index()
    total_pnl_brut = trade_pnl['pnl'].sum()  # PnL SANS commissions
    
    # Si on a le PnL réel du portfolio (avec commissions), on ajuste
    if portfolio_pnl_with_commissions is not None:
        # Calculer commissions totales
        total_commissions = total_pnl_brut - portfolio_pnl_with_commissions
        
        # Répartir les commissions proportionnellement au PnL brut de chaque trade
        # Pour éviter division par zéro, on utilise la valeur absolue pour la proportion
        trade_pnl['abs_pnl'] = trade_pnl['pnl'].abs()
        total_abs_pnl = trade_pnl['abs_pnl'].sum()
        
        if total_abs_pnl > 0:
            # Commission proportionnelle = (|PnL trade| / |Total PnL|) × Total commissions
            trade_pnl['commission'] = (trade_pnl['abs_pnl'] / total_abs_pnl) * total_commissions
            trade_pnl['pnl_net'] = trade_pnl['pnl'] - trade_pnl['commission']
        else:
            # Cas edge: tous les trades à 0
            trade_pnl['commission'] = total_commissions / len(trade_pnl)
            trade_pnl['pnl_net'] = trade_pnl['pnl'] - trade_pnl['commission']
        
        # Utiliser PnL NET pour tous les calculs
        total_pnl = portfolio_pnl_with_commissions
        avg_win = trade_pnl[trade_pnl['pnl_net'] > 0]['pnl_net'].mean() if len(trade_pnl[trade_pnl['pnl_net'] > 0]) > 0 else 0
        avg_loss = trade_pnl[trade_pnl['pnl_net'] < 0]['pnl_net'].mean() if len(trade_pnl[trade_pnl['pnl_net'] < 0]) > 0 else 0
        
        # Profit Factor avec PnL NET
        total_wins_pnl = trade_pnl[trade_pnl['pnl_net'] > 0]['pnl_net'].sum()
        total_losses_pnl = abs(trade_pnl[trade_pnl['pnl_net'] < 0]['pnl_net'].sum())
    else:
        # Fallback: utiliser PnL brut si portfolio stats non disponible
        total_pnl = total_pnl_brut
        avg_win = trade_pnl[trade_pnl['pnl'] > 0]['pnl'].mean() if len(trade_pnl[trade_pnl['pnl'] > 0]) > 0 else 0
        avg_loss = trade_pnl[trade_pnl['pnl'] < 0]['pnl'].mean() if len(trade_pnl[trade_pnl['pnl'] < 0]) > 0 else 0
        
        # Profit Factor avec PnL brut
        total_wins_pnl = trade_pnl[trade_pnl['pnl'] > 0]['pnl'].sum()
        total_losses_pnl = abs(trade_pnl[trade_pnl['pnl'] < 0]['pnl'].sum())
    
    profit_factor = (total_wins_pnl / total_losses_pnl) if total_losses_pnl > 0 else 0
    
    # Expectancy en R (Risk multiples)
    # Expectancy = (Win Rate × Avg Win) - (Loss Rate × |Avg Loss|)
    # En R = Expectancy / Avg Risk (moyenne des SL distances)
    loss_rate = (losses / total_trades) if total_trades > 0 else 0
    expectancy_dollars = (win_rate/100 * avg_win) - (loss_rate * abs(avg_loss))
    
    # Calculer la taille moyenne du risque (distance SL)
    # Extraire sl_distance des trades d'entrée
    entry_events = trades[trades['event_type'] == 'ENTRY']
    if 'sl_distance' in entry_events.columns and len(entry_events) > 0:
        avg_risk = entry_events['sl_distance'].mean()
        expectancy_R = expectancy_dollars / avg_risk if avg_risk > 0 else 0
    else:
        avg_risk = abs(avg_loss)  # Fallback: utiliser avg loss comme proxy
        expectancy_R = expectancy_dollars / avg_risk if avg_risk > 0 else 0
    
    # VÉRIFICATIONS (warnings au lieu de crash)
    total_events = num_final_sl + num_final_be + num_final_tp1 + num_final_tp2 + num_forced_close
    if total_events != total_trades:
        print(f"⚠️  WARNING: Total events ({total_events}) != total trades ({total_trades})")
        print(f"   Possible cause: position still open at end of backtest")
    
    if num_reached_tp2 > num_reached_tp1:
        print(f"⚠️  WARNING: TP2 ({num_reached_tp2}) > TP1 ({num_reached_tp1}) - unexpected!")
    
    if wins != num_reached_tp1:
        print(f"⚠️  WARNING: Wins ({wins}) != TP1 reached ({num_reached_tp1})")
    
    if losses != num_final_sl:
        print(f"⚠️  WARNING: Losses ({losses}) != SL ({num_final_sl})")
    
    # === STATS AVANCÉES ===
    
    # Plus longues séries de wins/losses
    # Basé sur l'exit type, pas sur PnL (plus cohérent avec notre logique)
    trade_pnl_sorted = trade_pnl.sort_values('trade_id')
    
    # Merger avec exit events pour avoir le type de sortie
    final_exit_type = exit_events.groupby('trade_id')['event_type'].last().reset_index()
    trade_pnl_sorted = trade_pnl_sorted.merge(final_exit_type, on='trade_id', how='left')
    
    # is_win basé sur exit type: TP1 ou TP2 = win, SL = loss
    trade_pnl_sorted['is_win'] = trade_pnl_sorted['event_type'].isin(['TP1', 'TP2'])
    
    current_win_streak = 0
    current_loss_streak = 0
    max_win_streak = 0
    max_loss_streak = 0
    
    for is_win in trade_pnl_sorted['is_win']:
        if is_win:
            current_win_streak += 1
            current_loss_streak = 0
            max_win_streak = max(max_win_streak, current_win_streak)
        else:
            current_loss_streak += 1
            current_win_streak = 0
            max_loss_streak = max(max_loss_streak, current_loss_streak)
    
    # Taux de rejet (depuis config si disponible)
    import yaml
    try:
        with open(config_file, 'r', encoding='utf-8') as f:
            config = yaml.safe_load(f)
        min_sl_pips = config.get('min_sl_distance_pips', 0)
        max_sl_pips = config.get('max_sl_distance_pips', 0)
    except:
        min_sl_pips = 0
        max_sl_pips = 0
    
    # === EXPECTANCY BREAKDOWN ===
    
    # Merger entry events avec exit events pour avoir SL distance et outcomes
    entry_cols = ['trade_id', 'datetime']
    # Vérifier si sl_distance existe
    if 'sl_distance' in trades.columns:
        entry_cols.append('sl_distance')
    
    entry_data = trades[trades['event_type'] == 'ENTRY'][entry_cols].copy()
    exit_data = exit_events.groupby('trade_id').agg({
        'pnl': 'sum',
        'event_type': 'last'
    }).reset_index()
    
    trade_details = entry_data.merge(exit_data, on='trade_id', how='inner')
    trade_details['datetime'] = pd.to_datetime(trade_details['datetime'])
    trade_details['hour'] = trade_details['datetime'].dt.hour
    trade_details['dayofweek'] = trade_details['datetime'].dt.dayofweek
    
    # Expectancy par heure (avec PF, Drawdown, Variance)
    hourly_stats = []
    for hour in range(24):
        hour_trades = trade_details[trade_details['hour'] == hour]
        if len(hour_trades) > 0:
            hour_wins = len(hour_trades[hour_trades['pnl'] > 0])
            hour_losses = len(hour_trades[hour_trades['pnl'] <= 0])
            hour_wr = hour_wins / len(hour_trades) if len(hour_trades) > 0 else 0
            hour_avg_win = hour_trades[hour_trades['pnl'] > 0]['pnl'].mean() if hour_wins > 0 else 0
            hour_avg_loss = hour_trades[hour_trades['pnl'] <= 0]['pnl'].mean() if hour_losses > 0 else 0
            hour_expectancy = (hour_wr * hour_avg_win) + ((1-hour_wr) * hour_avg_loss)
            
            # Profit Factor
            total_wins = hour_trades[hour_trades['pnl'] > 0]['pnl'].sum()
            total_losses = abs(hour_trades[hour_trades['pnl'] < 0]['pnl'].sum())
            hour_pf = (total_wins / total_losses) if total_losses > 0 else 0
            
            # Drawdown (max drawdown cumulé)
            cumulative_pnl = hour_trades.sort_values('datetime')['pnl'].cumsum()
            running_max = cumulative_pnl.cummax()
            drawdown = running_max - cumulative_pnl
            max_drawdown = drawdown.max() if len(drawdown) > 0 else 0
            
            # Variance
            hour_variance = hour_trades['pnl'].var() if len(hour_trades) > 1 else 0
            
            hourly_stats.append({
                'hour': hour,
                'count': len(hour_trades),
                'expectancy': hour_expectancy,
                'win_rate': hour_wr * 100,
                'profit_factor': hour_pf,
                'max_drawdown': max_drawdown,
                'variance': hour_variance
            })
    
    # Expectancy par taille de SL (bins dynamiques) - SEULEMENT si sl_distance existe
    sl_stats = []
    if 'sl_distance' in trade_details.columns:
        # Récupérer min/max SL depuis le config
        min_sl_pips = config.get('min_sl_distance_pips', 0)
        max_sl_pips = config.get('max_sl_distance_pips', 0)
        
        # Si pas dans config racine, chercher dans strategy
        if min_sl_pips == 0 and 'strategy' in config:
            min_sl_pips = config['strategy'].get('sl_min_pips', 0)
        if max_sl_pips == 0 and 'strategy' in config:
            max_sl_pips = config['strategy'].get('sl_max_pips', 0)
        
        # Fallback sur les valeurs réelles si config vide
        if min_sl_pips == 0 or max_sl_pips == 0:
            print("⚠️  Warning: min/max SL not in config, using actual data range")
            min_sl_pips = trade_details['sl_distance'].min()
            max_sl_pips = trade_details['sl_distance'].max()
        
        # Créer 10 bins dynamiques couvrant TOUT le range du config
        import numpy as np
        num_bins = 10
        bin_edges = np.linspace(min_sl_pips, max_sl_pips, num_bins + 1)
        
        # Créer les labels des bins
        bin_labels = [f"{int(bin_edges[i])}-{int(bin_edges[i+1])}" for i in range(num_bins)]
        
        # Assigner chaque trade à un bin
        trade_details['sl_bin'] = pd.cut(
            trade_details['sl_distance'], 
            bins=bin_edges,
            labels=bin_labels,
            include_lowest=True  # Inclure la borne inférieure
        )
        
        print(f"\n📊 SL Distribution: {num_bins} bins dynamiques de {min_sl_pips:.0f} à {max_sl_pips:.0f} pips")
        print(f"   Bins: {bin_labels[0]}, {bin_labels[1]}, ..., {bin_labels[-1]}")
        
        for sl_bin_label in bin_labels:
            sl_trades = trade_details[trade_details['sl_bin'] == sl_bin_label]
            if len(sl_trades) > 0:
                # Utiliser le centre du bin pour les calculs
                bin_start, bin_end = sl_bin_label.split('-')
                sl_size = (float(bin_start) + float(bin_end)) / 2
                
                sl_wins = len(sl_trades[sl_trades['pnl'] > 0])
                sl_losses = len(sl_trades[sl_trades['pnl'] <= 0])
                sl_wr = sl_wins / len(sl_trades) if len(sl_trades) > 0 else 0
                sl_avg_win = sl_trades[sl_trades['pnl'] > 0]['pnl'].mean() if sl_wins > 0 else 0
                sl_avg_loss = sl_trades[sl_trades['pnl'] <= 0]['pnl'].mean() if sl_losses > 0 else 0
                sl_expectancy = (sl_wr * sl_avg_win) + ((1-sl_wr) * sl_avg_loss)
                
                # Expectancy en R
                sl_expectancy_R = sl_expectancy / sl_size if sl_size > 0 else 0
                
                sl_stats.append({
                    'sl_size': sl_size,
                    'sl_range': sl_bin_label,  # Garder le label pour affichage
                    'count': len(sl_trades),
                    'expectancy': sl_expectancy,
                    'expectancy_R': sl_expectancy_R,
                    'win_rate': sl_wr * 100
                })
    
    # Calcul du taux de rejet (approximatif depuis les logs de stratégie si disponible)
    # On le met à 0 par défaut car on n'a pas accès direct à strategy ici
    rejected_small = 0
    rejected_large = 0
    rejection_rate = 0  # Sera calculé côté Python si disponible
    
    # Market benchmark (buy & hold vs stratégie)
    # Calculer le return total du marché sur la période
    market_return_pct = ((df['close'].iloc[-1] - df['close'].iloc[0]) / df['close'].iloc[0]) * 100
    
    # === TRADING WINDOWS STATS ===
    # Charger config trading windows si défini
    tw_enabled = False
    tw_total_hours = 0
    tw_pct_of_week = 0
    tw_windows_count = 0
    
    if 'trading_windows' in config.get('strategy', {}):
        tw_config = config['strategy']['trading_windows']
        tw_enabled = tw_config.get('enabled', False)
        
        if tw_enabled:
            # Importer TradingWindows pour calculer stats
            import sys
            sys.path.insert(0, str(Path(__file__).parent))
            from trading_windows import TradingWindows
            
            tw = TradingWindows(tw_config)
            tw_total_hours = tw.get_total_hours_per_week()
            tw_pct_of_week = tw_total_hours / 168 * 100
            tw_windows_count = len(tw.windows)
    
    # === GÉNÉRATION HEATMAP EXPECTANCY ===
    print("\n📊 Génération heatmaps temporelles...")
    try:
        import matplotlib
        matplotlib.use('Agg')
        import matplotlib.pyplot as plt
        import seaborn as sns
        
        if len(trade_details) > 0:
            # === HEATMAP 1: FRÉQUENCE ===
            freq_data = []
            for day in range(7):
                for hour in range(24):
                    count = len(trade_details[
                        (trade_details['hour'] == hour) & 
                        (trade_details['dayofweek'] == day)
                    ])
                    freq_data.append({'day': day, 'hour': hour, 'count': count if count > 0 else np.nan})
            
            freq_df = pd.DataFrame(freq_data)
            freq_pivot = freq_df.pivot(index='day', columns='hour', values='count')
            
            fig, ax = plt.subplots(figsize=(14, 7))
            sns.heatmap(freq_pivot, cmap='YlOrRd', annot=True, fmt='.0f', 
                       cbar_kws={'label': 'Nombre de trades'}, linewidths=0.5, ax=ax)
            ax.set_title('Fréquence des Trades par Jour et Heure', fontsize=14, weight='bold', pad=15)
            ax.set_xlabel('Heure de la journée', fontsize=11)
            ax.set_ylabel('Jour de la semaine', fontsize=11)
            ax.set_yticklabels(['Lun', 'Mar', 'Mer', 'Jeu', 'Ven', 'Sam', 'Dim'], rotation=0)
            plt.tight_layout()
            plt.savefig('output/heatmap_1_frequency.png', dpi=150, bbox_inches='tight')
            plt.close()
            print("✅ Heatmap 1 (Fréquence) générée")
            
            # === HEATMAP 2: WIN RATE ===
            wr_data = []
            for day in range(7):
                for hour in range(24):
                    hour_trades = trade_details[
                        (trade_details['hour'] == hour) & 
                        (trade_details['dayofweek'] == day)
                    ]
                    if len(hour_trades) > 0:
                        wins = len(hour_trades[hour_trades['pnl'] > 0])
                        wr = (wins / len(hour_trades)) * 100
                    else:
                        wr = np.nan
                    wr_data.append({'day': day, 'hour': hour, 'winrate': wr})
            
            wr_df = pd.DataFrame(wr_data)
            wr_pivot = wr_df.pivot(index='day', columns='hour', values='winrate')
            
            fig, ax = plt.subplots(figsize=(14, 7))
            sns.heatmap(wr_pivot, cmap='RdYlGn', center=50, vmin=0, vmax=100,
                       annot=True, fmt='.0f', cbar_kws={'label': 'Win Rate (%)'}, 
                       linewidths=0.5, ax=ax)
            ax.set_title('Win Rate par Jour et Heure', fontsize=14, weight='bold', pad=15)
            ax.set_xlabel('Heure de la journée', fontsize=11)
            ax.set_ylabel('Jour de la semaine', fontsize=11)
            ax.set_yticklabels(['Lun', 'Mar', 'Mer', 'Jeu', 'Ven', 'Sam', 'Dim'], rotation=0)
            plt.tight_layout()
            plt.savefig('output/heatmap_2_winrate.png', dpi=150, bbox_inches='tight')
            plt.close()
            print("✅ Heatmap 2 (Win Rate) générée")
            
            # === HEATMAP 3: PNL MOYEN ===
            pnl_data = []
            for day in range(7):
                for hour in range(24):
                    hour_trades = trade_details[
                        (trade_details['hour'] == hour) & 
                        (trade_details['dayofweek'] == day)
                    ]
                    avg_pnl = hour_trades['pnl'].mean() if len(hour_trades) > 0 else np.nan
                    pnl_data.append({'day': day, 'hour': hour, 'pnl': avg_pnl})
            
            pnl_df = pd.DataFrame(pnl_data)
            pnl_pivot = pnl_df.pivot(index='day', columns='hour', values='pnl')
            
            fig, ax = plt.subplots(figsize=(14, 7))
            vmax = max(abs(pnl_pivot.min().min()), abs(pnl_pivot.max().max()))
            sns.heatmap(pnl_pivot, cmap='RdYlGn', center=0, vmin=-vmax, vmax=vmax,
                       annot=True, fmt='.1f', cbar_kws={'label': 'PnL Moyen ($)'}, 
                       linewidths=0.5, ax=ax)
            ax.set_title('PnL Moyen par Jour et Heure', fontsize=14, weight='bold', pad=15)
            ax.set_xlabel('Heure de la journée', fontsize=11)
            ax.set_ylabel('Jour de la semaine', fontsize=11)
            ax.set_yticklabels(['Lun', 'Mar', 'Mer', 'Jeu', 'Ven', 'Sam', 'Dim'], rotation=0)
            plt.tight_layout()
            plt.savefig('output/heatmap_3_pnl.png', dpi=150, bbox_inches='tight')
            plt.close()
            print("✅ Heatmap 3 (PnL) générée")
            
            # === HEATMAP 4: SCORE COMBINÉ ===
            # Score = (WinRate - 50) + (PnL normalisé * 10)
            score_data = []
            for day in range(7):
                for hour in range(24):
                    hour_trades = trade_details[
                        (trade_details['hour'] == hour) & 
                        (trade_details['dayofweek'] == day)
                    ]
                    if len(hour_trades) > 0:
                        wins = len(hour_trades[hour_trades['pnl'] > 0])
                        wr = (wins / len(hour_trades)) * 100
                        avg_pnl = hour_trades['pnl'].mean()
                        # Score combiné
                        score = (wr - 50) + (avg_pnl / 10)
                    else:
                        score = np.nan
                    score_data.append({'day': day, 'hour': hour, 'score': score})
            
            score_df = pd.DataFrame(score_data)
            score_pivot = score_df.pivot(index='day', columns='hour', values='score')
            
            fig, ax = plt.subplots(figsize=(14, 7))
            vmax = max(abs(score_pivot.min().min()), abs(score_pivot.max().max()))
            sns.heatmap(score_pivot, cmap='RdYlGn', center=0, vmin=-vmax, vmax=vmax,
                       annot=True, fmt='.1f', cbar_kws={'label': 'Score Combiné'}, 
                       linewidths=0.5, ax=ax)
            ax.set_title('Score Combiné (WR + PnL) par Jour et Heure', fontsize=14, weight='bold', pad=15)
            ax.set_xlabel('Heure de la journée', fontsize=11)
            ax.set_ylabel('Jour de la semaine', fontsize=11)
            ax.set_yticklabels(['Lun', 'Mar', 'Mer', 'Jeu', 'Ven', 'Sam', 'Dim'], rotation=0)
            plt.tight_layout()
            plt.savefig('output/heatmap_4_combined.png', dpi=150, bbox_inches='tight')
            plt.close()
            print("✅ Heatmap 4 (Score Combiné) générée")
            
        else:
            print("⚠️  Pas assez de données pour heatmaps temporelles")
    except Exception as e:
        print(f"⚠️  Erreur génération heatmaps temporelles: {e}")
    
    print("\n📊 Génération heatmap Expectancy...")
    try:
        import matplotlib
        matplotlib.use('Agg')  # Backend sans display
        import matplotlib.pyplot as plt
        import seaborn as sns
        
        # Créer pivot table pour heatmap jour × heure
        # Utiliser trade_details qui a déjà hour et dayofweek
        if len(trade_details) > 0:
            # Créer pivot pour expectancy moyenne par jour/heure
            pivot_data = []
            for day in range(7):  # Lundi=0 à Dimanche=6
                for hour in range(24):
                    hour_day_trades = trade_details[
                        (trade_details['hour'] == hour) & 
                        (trade_details['dayofweek'] == day)
                    ]
                    
                    if len(hour_day_trades) > 0:
                        wins = len(hour_day_trades[hour_day_trades['pnl'] > 0])
                        losses = len(hour_day_trades[hour_day_trades['pnl'] <= 0])
                        wr = wins / len(hour_day_trades) if len(hour_day_trades) > 0 else 0
                        hour_avg_win = hour_day_trades[hour_day_trades['pnl'] > 0]['pnl'].mean() if wins > 0 else 0
                        hour_avg_loss = hour_day_trades[hour_day_trades['pnl'] <= 0]['pnl'].mean() if losses > 0 else 0
                        expectancy = (wr * hour_avg_win) + ((1-wr) * hour_avg_loss)
                    else:
                        expectancy = np.nan
                    
                    pivot_data.append({
                        'day': day,
                        'hour': hour,
                        'expectancy': expectancy
                    })
            
            pivot_df = pd.DataFrame(pivot_data)
            pivot_table = pivot_df.pivot(index='day', columns='hour', values='expectancy')
            
            # Créer heatmap
            fig, ax = plt.subplots(figsize=(14, 7))
            
            # Trouver min/max pour centrer sur 0
            vmax = max(abs(pivot_table.min().min()), abs(pivot_table.max().max()))
            vmin = -vmax
            
            sns.heatmap(
                pivot_table, 
                cmap='RdYlGn',  # Rouge (négatif) -> Jaune (neutre) -> Vert (positif)
                center=0,
                vmin=vmin,
                vmax=vmax,
                annot=True, 
                fmt='.1f',
                cbar_kws={'label': 'Expectancy ($)'},
                linewidths=0.5,
                ax=ax
            )
            
            ax.set_title('Expectancy par Jour et Heure', fontsize=14, weight='bold', pad=15)
            ax.set_xlabel('Heure de la journée', fontsize=11)
            ax.set_ylabel('Jour de la semaine', fontsize=11)
            ax.set_yticklabels(['Lun', 'Mar', 'Mer', 'Jeu', 'Ven', 'Sam', 'Dim'], rotation=0)
            
            plt.tight_layout()
            plt.savefig('output/heatmap_5_expectancy.png', dpi=150, bbox_inches='tight')
            plt.close()
            
            print("✅ Heatmap Expectancy générée: output/heatmap_5_expectancy.png")
        else:
            print("⚠️  Pas assez de données pour heatmap Expectancy")
    except Exception as e:
        print(f"⚠️  Erreur génération heatmap Expectancy: {e}")
    
    # Graphiques par créneau horaire
    try:
        if len(hourly_stats) > 0:
            import matplotlib
            matplotlib.use('Agg')
            import matplotlib.pyplot as plt
            
            # Extraire données
            hours = [h['hour'] for h in hourly_stats]
            expectancy = [h['expectancy'] for h in hourly_stats]
            pf = [h['profit_factor'] for h in hourly_stats]
            dd = [h['max_drawdown'] for h in hourly_stats]
            variance = [h['variance'] for h in hourly_stats]
            counts = [h['count'] for h in hourly_stats]
            
            # 1. Expectancy par heure (bar chart)
            fig, ax = plt.subplots(figsize=(14, 5), facecolor='#1a1d29')
            ax.set_facecolor('#1a1d29')
            colors = ['#26a69a' if e > 0 else '#ef5350' for e in expectancy]
            bars = ax.bar(hours, expectancy, color=colors, alpha=0.8, edgecolor='white', linewidth=0.5)
            
            # Ajouter compte sur chaque barre
            for i, (h, e, c) in enumerate(zip(hours, expectancy, counts)):
                ax.text(h, e, f'{c}', ha='center', va='bottom' if e > 0 else 'top', 
                       fontsize=8, color='white', weight='bold')
            
            ax.axhline(y=0, color='white', linestyle='--', linewidth=1, alpha=0.3)
            ax.set_xlabel('Heure (UTC)', fontsize=11, color='white')
            ax.set_ylabel('Expectancy ($)', fontsize=11, color='white')
            ax.set_title('Expectancy par Créneau Horaire', fontsize=13, weight='bold', color='#4dd0e1', pad=15)
            ax.set_xticks(range(24))
            ax.tick_params(colors='white')
            ax.spines['bottom'].set_color('white')
            ax.spines['left'].set_color('white')
            ax.spines['top'].set_visible(False)
            ax.spines['right'].set_visible(False)
            ax.grid(True, alpha=0.1, color='white')
            
            plt.tight_layout()
            plt.savefig('output/expectancy_hourly_expectancy.png', dpi=150, bbox_inches='tight')
            plt.close()
            print("✅ Graphique Expectancy horaire généré")
            
            # 2. Profit Factor par heure (bar chart)
            fig, ax = plt.subplots(figsize=(14, 5), facecolor='#1a1d29')
            ax.set_facecolor('#1a1d29')
            colors = ['#26a69a' if p > 1 else '#ef5350' for p in pf]
            bars = ax.bar(hours, pf, color=colors, alpha=0.8, edgecolor='white', linewidth=0.5)
            
            ax.axhline(y=1, color='white', linestyle='--', linewidth=1, alpha=0.5, label='PF = 1 (Break-even)')
            ax.set_xlabel('Heure (UTC)', fontsize=11, color='white')
            ax.set_ylabel('Profit Factor', fontsize=11, color='white')
            ax.set_title('Profit Factor par Créneau Horaire', fontsize=13, weight='bold', color='#4dd0e1', pad=15)
            ax.set_xticks(range(24))
            ax.tick_params(colors='white')
            ax.spines['bottom'].set_color('white')
            ax.spines['left'].set_color('white')
            ax.spines['top'].set_visible(False)
            ax.spines['right'].set_visible(False)
            ax.grid(True, alpha=0.1, color='white')
            ax.legend(loc='upper right', facecolor='#2a2e39', edgecolor='white', fontsize=9)
            
            plt.tight_layout()
            plt.savefig('output/expectancy_hourly_pf.png', dpi=150, bbox_inches='tight')
            plt.close()
            print("✅ Graphique Profit Factor horaire généré")
            
            # 3. Drawdown par heure (bar chart inversé)
            fig, ax = plt.subplots(figsize=(14, 5), facecolor='#1a1d29')
            ax.set_facecolor('#1a1d29')
            bars = ax.bar(hours, [-d for d in dd], color='#ef5350', alpha=0.8, edgecolor='white', linewidth=0.5)
            
            ax.axhline(y=0, color='white', linestyle='--', linewidth=1, alpha=0.3)
            ax.set_xlabel('Heure (UTC)', fontsize=11, color='white')
            ax.set_ylabel('Max Drawdown ($)', fontsize=11, color='white')
            ax.set_title('Max Drawdown par Créneau Horaire', fontsize=13, weight='bold', color='#4dd0e1', pad=15)
            ax.set_xticks(range(24))
            ax.tick_params(colors='white')
            ax.spines['bottom'].set_color('white')
            ax.spines['left'].set_color('white')
            ax.spines['top'].set_visible(False)
            ax.spines['right'].set_visible(False)
            ax.grid(True, alpha=0.1, color='white')
            
            plt.tight_layout()
            plt.savefig('output/expectancy_hourly_drawdown.png', dpi=150, bbox_inches='tight')
            plt.close()
            print("✅ Graphique Drawdown horaire généré")
            
            # 4. Variance par heure (bar chart)
            fig, ax = plt.subplots(figsize=(14, 5), facecolor='#1a1d29')
            ax.set_facecolor('#1a1d29')
            bars = ax.bar(hours, variance, color='#9C27B0', alpha=0.8, edgecolor='white', linewidth=0.5)
            
            ax.set_xlabel('Heure (UTC)', fontsize=11, color='white')
            ax.set_ylabel('Variance PnL', fontsize=11, color='white')
            ax.set_title('Variance par Créneau Horaire', fontsize=13, weight='bold', color='#4dd0e1', pad=15)
            ax.set_xticks(range(24))
            ax.tick_params(colors='white')
            ax.spines['bottom'].set_color('white')
            ax.spines['left'].set_color('white')
            ax.spines['top'].set_visible(False)
            ax.spines['right'].set_visible(False)
            ax.grid(True, alpha=0.1, color='white')
            
            plt.tight_layout()
            plt.savefig('output/expectancy_hourly_variance.png', dpi=150, bbox_inches='tight')
            plt.close()
            print("✅ Graphique Variance horaire généré")
            
        else:
            print("⚠️  Pas de données pour graphiques horaires")
    except Exception as e:
        print(f"⚠️  Erreur génération graphiques horaires: {e}")
    
    # Return de la stratégie
    config_capital = config.get('capital', 10000) if 'config' in locals() else 10000
    strategy_return_pct = (total_pnl / config_capital) * 100
    
    outperformance = strategy_return_pct - market_return_pct
    
    # Liste des trades pour navigation
    trade_times = []
    for trade_id in sorted(trades['trade_id'].unique()):
        entry_evt = trades[(trades['trade_id'] == trade_id) & (trades['event_type'] == 'ENTRY')].iloc[0]
        # Utiliser fonction helper
        entry_time = to_utc_timestamp(entry_evt['datetime'])
        trade_times.append({
            'id': int(trade_id),
            'time': entry_time,
            'direction': entry_evt['direction'],
            'price': float(entry_evt['price'])
        })
    
    # Générer HTML
    html = f'''<!DOCTYPE html>
<html lang="fr">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Backtest - {symbol} {timeframe} - {strategy_name}</title>
    <script src="https://unpkg.com/lightweight-charts@4.2.0/dist/lightweight-charts.standalone.production.js"></script>
    <style>
        * {{ margin: 0; padding: 0; box-sizing: border-box; }}
        
        body {{
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif;
            background: linear-gradient(135deg, #1a1d29 0%, #252938 100%);
            color: #d1d4dc;
            height: 100vh;
            display: flex;
            flex-direction: column;
            overflow: hidden;
        }}
        
        .header {{
            background: rgba(42, 46, 57, 0.98);
            padding: 16px 24px;
            border-bottom: 1px solid rgba(77, 208, 225, 0.1);
            box-shadow: 0 2px 8px rgba(0, 0, 0, 0.3);
        }}
        
        .header-top {{
            display: flex;
            justify-content: space-between;
            align-items: center;
            margin-bottom: 12px;
        }}
        
        .title {{
            font-size: 22px;
            font-weight: 700;
            background: linear-gradient(135deg, #26a69a 0%, #4dd0e1 100%);
            -webkit-background-clip: text;
            -webkit-text-fill-color: transparent;
        }}
        
        .nav-controls {{
            display: flex;
            gap: 8px;
        }}
        
        .nav-btn {{
            background: rgba(77, 208, 225, 0.15);
            border: 1px solid rgba(77, 208, 225, 0.3);
            color: #4dd0e1;
            padding: 8px 16px;
            border-radius: 6px;
            font-size: 12px;
            font-weight: 600;
            cursor: pointer;
            transition: all 0.2s;
        }}
        
        .nav-btn:hover {{
            background: rgba(77, 208, 225, 0.25);
            border-color: #4dd0e1;
            transform: translateY(-1px);
        }}
        
        .nav-btn:disabled {{
            opacity: 0.3;
            cursor: not-allowed;
        }}
        
        .stats-grid {{
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(120px, 1fr));
            gap: 12px;
        }}
        
        .stat-card {{
            background: rgba(30, 34, 45, 0.6);
            border: 1px solid rgba(77, 208, 225, 0.15);
            border-radius: 6px;
            padding: 10px 14px;
            transition: all 0.2s;
        }}
        
        .stat-card:hover {{
            background: rgba(30, 34, 45, 0.8);
            border-color: rgba(77, 208, 225, 0.3);
        }}
        
        .stat-label {{
            font-size: 10px;
            text-transform: uppercase;
            color: #868993;
            margin-bottom: 4px;
            letter-spacing: 0.5px;
        }}
        
        .stat-value {{
            font-size: 18px;
            font-weight: 700;
        }}
        
        .stat-green {{ color: #26a69a; }}
        .stat-red {{ color: #ef5350; }}
        .stat-blue {{ color: #4dd0e1; }}
        .stat-yellow {{ color: #ffc107; }}
        
        .chart-wrapper {{
            flex: 1;
            display: flex;
            flex-direction: column;
            padding: 16px;
            gap: 16px;
            overflow: hidden;
        }}
        
        .main-chart-container {{
            flex: 3;
            position: relative;
            border-radius: 10px;
            overflow: hidden;
            box-shadow: 0 4px 16px rgba(0, 0, 0, 0.4);
            background: #1a1d29;
        }}
        
        .rsi-chart-container {{
            flex: 1;
            position: relative;
            border-radius: 10px;
            overflow: hidden;
            box-shadow: 0 4px 16px rgba(0, 0, 0, 0.4);
            background: #1a1d29;
        }}
        
        #chart, #rsiChart {{
            width: 100%;
            height: 100%;
            position: absolute;
            top: 0;
            left: 0;
        }}
        
        #overlay {{
            position: absolute;
            top: 0;
            left: 0;
            pointer-events: none;
            z-index: 10;
        }}
        
        .legend {{
            position: absolute;
            top: 12px;
            right: 12px;
            background: rgba(30, 34, 45, 0.95);
            border: 1px solid rgba(77, 208, 225, 0.2);
            border-radius: 8px;
            padding: 12px;
            box-shadow: 0 4px 12px rgba(0, 0, 0, 0.4);
            font-size: 11px;
            z-index: 20;
        }}
        
        .legend-title {{
            font-weight: 700;
            color: #4dd0e1;
            margin-bottom: 8px;
            font-size: 12px;
        }}
        
        .legend-item {{
            display: flex;
            align-items: center;
            gap: 8px;
            padding: 4px 0;
        }}
        
        .legend-box {{
            width: 20px;
            height: 12px;
            border-radius: 2px;
            border: 2px solid;
        }}
        
        .legend-line {{
            width: 20px;
            height: 2px;
        }}
        
        .controls {{
            position: absolute;
            bottom: 12px;
            left: 12px;
            display: flex;
            gap: 8px;
            z-index: 20;
        }}
        
        .btn {{
            background: rgba(30, 34, 45, 0.95);
            border: 1px solid rgba(77, 208, 225, 0.2);
            color: #d1d4dc;
            padding: 8px 14px;
            border-radius: 6px;
            font-size: 12px;
            font-weight: 600;
            cursor: pointer;
            transition: all 0.2s;
        }}
        
        .btn:hover {{
            background: rgba(38, 166, 154, 0.15);
            border-color: #26a69a;
            color: #26a69a;
        }}
        
        .modal {{
            display: none;
            position: fixed;
            top: 0;
            left: 0;
            width: 100%;
            height: 100%;
            background: rgba(0, 0, 0, 0.9);
            z-index: 1000;
            padding: 20px;
            overflow: auto;
        }}
        
        .modal.active {{
            display: flex;
            flex-direction: column;
            align-items: center;
            justify-content: center;
        }}
        
        .modal-content {{
            background: rgba(30, 34, 45, 0.98);
            border-radius: 12px;
            padding: 24px;
            max-width: 1400px;
            width: 100%;
            max-height: 90vh;
            overflow: auto;
        }}
        
        .modal-header {{
            display: flex;
            justify-content: space-between;
            align-items: center;
            margin-bottom: 20px;
        }}
        
        .modal-title {{
            font-size: 24px;
            font-weight: 700;
            color: #4dd0e1;
        }}
        
        .close-btn {{
            background: rgba(239, 83, 80, 0.2);
            border: 1px solid rgba(239, 83, 80, 0.5);
            color: #ef5350;
            padding: 8px 16px;
            border-radius: 6px;
            cursor: pointer;
            font-weight: 600;
        }}
        
        .close-btn:hover {{
            background: rgba(239, 83, 80, 0.3);
        }}
        
        .heatmaps-grid {{
            display: grid;
            grid-template-columns: repeat(2, 1fr);
            gap: 20px;
        }}
        
        .heatmap-item {{
            text-align: center;
        }}
        
        .heatmap-item h3 {{
            color: #4dd0e1;
            margin-bottom: 10px;
            font-size: 16px;
        }}
        
        .heatmap-item img {{
            width: 100%;
            border-radius: 8px;
            box-shadow: 0 4px 12px rgba(0, 0, 0, 0.3);
        }}
        
        .stats-details {{
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(350px, 1fr));
            gap: 24px;
        }}
        
        .stats-section {{
            background: rgba(42, 46, 57, 0.6);
            border: 1px solid rgba(77, 208, 225, 0.15);
            border-radius: 8px;
            padding: 20px;
        }}
        
        .stats-section h3 {{
            color: #4dd0e1;
            font-size: 18px;
            margin-bottom: 16px;
            padding-bottom: 12px;
            border-bottom: 1px solid rgba(77, 208, 225, 0.2);
        }}
        
        .stats-row {{
            display: flex;
            justify-content: space-between;
            align-items: center;
            padding: 10px 0;
            border-bottom: 1px solid rgba(77, 208, 225, 0.1);
        }}
        
        .stats-row:last-child {{
            border-bottom: none;
        }}
        
        .stats-row span:first-child {{
            color: #868993;
            font-size: 14px;
        }}
        
        .stat-value-large {{
            font-size: 20px;
            font-weight: 700;
        }}
        
        .stats-info {{
            margin-top: 12px;
            padding: 12px;
            background: rgba(77, 208, 225, 0.1);
            border-radius: 6px;
            font-size: 13px;
            color: #d1d4dc;
            text-align: center;
        }}
        
        .legend {{
            cursor: pointer;
            transition: all 0.3s;
        }}
        
        .legend.collapsed {{
            height: 40px;
            overflow: hidden;
        }}
        
        .legend.collapsed .legend-item {{
            display: none;
        }}
        
        .legend-title {{
            position: relative;
        }}
        
        .legend-title::after {{
            content: '▼';
            position: absolute;
            right: 0;
            font-size: 10px;
            transition: transform 0.3s;
        }}
        
        .legend.collapsed .legend-title::after {{
            transform: rotate(-90deg);
        }}
        
        .trade-info {{
            position: absolute;
            top: 12px;
            left: 12px;
            background: rgba(30, 34, 45, 0.95);
            border: 1px solid rgba(77, 208, 225, 0.2);
            border-radius: 8px;
            padding: 12px;
            font-size: 12px;
            z-index: 20;
            min-width: 200px;
        }}
        
        .trade-info-title {{
            font-weight: 700;
            color: #4dd0e1;
            margin-bottom: 8px;
        }}
        
        .trade-info-item {{
            display: flex;
            justify-content: space-between;
            padding: 3px 0;
        }}
        
        .trade-info-label {{
            color: #868993;
        }}
        
        .trade-info-value {{
            font-weight: 600;
        }}
    </style>
</head>
<body>
    <div class="header">
        <div class="header-top">
            <div class="title">
                <span style="font-size: 1em;">📊 Backtest</span>
                <span style="font-size: 0.85em; margin-left: 8px;">{symbol} - {timeframe} - {strategy_name}</span>
            </div>
            <div class="nav-controls">
                <button class="nav-btn" onclick="previousTrade()">⬅️ Trade Précédent</button>
                <button class="nav-btn" onclick="nextTrade()">Trade Suivant ➡️</button>
                <button class="nav-btn" onclick="showStats()">📊 Stats</button>
                <button class="nav-btn" onclick="showHeatmaps()">🔥 Heatmaps</button>
                <button class="nav-btn" onclick="showExpectancy()">📈 Expectancy</button>
            </div>
        </div>
        <div class="stats-grid">
            <div class="stat-card">
                <div class="stat-label">Total Trades</div>
                <div class="stat-value stat-blue">{total_trades}</div>
            </div>
            <div class="stat-card">
                <div class="stat-label">Win Rate</div>
                <div class="stat-value stat-{'green' if win_rate >= 50 else 'red'}">{win_rate:.1f}%</div>
            </div>
            <div class="stat-card">
                <div class="stat-label">Expectancy (R)</div>
                <div class="stat-value stat-{'green' if expectancy_R > 0 else 'red'}">{expectancy_R:.2f}R</div>
                <div style="font-size: 0.65em; color: #888; margin-top: 2px;">${expectancy_dollars:.2f} per trade</div>
            </div>
            <div class="stat-card">
                <div class="stat-label">PnL Total {'(net)' if portfolio_pnl_with_commissions is not None else '(brut)'}</div>
                <div class="stat-value stat-{'green' if total_pnl > 0 else 'red'}">${total_pnl:.2f}</div>
                {'<div style="font-size: 0.65em; color: #888; margin-top: 2px;">Brut: $' + f"{total_pnl_brut:.2f}" + '</div>' if portfolio_pnl_with_commissions is not None else ''}
            </div>
            <div class="stat-card">
                <div class="stat-label">Avg Win</div>
                <div class="stat-value stat-green">{avg_win:.2f}</div>
            </div>
            <div class="stat-card">
                <div class="stat-label">Avg Loss</div>
                <div class="stat-value stat-red">{avg_loss:.2f}</div>
            </div>
            <div class="stat-card">
                <div class="stat-label">Profit Factor</div>
                <div class="stat-value stat-yellow">{profit_factor:.2f}</div>
            </div>
            {'<div class="stat-card">' if tw_enabled else ''}
            {f'<div class="stat-label">⏰ Trading Windows</div>' if tw_enabled else ''}
            {f'<div class="stat-value" style="font-size: 1.1em;">{tw_total_hours:.1f}h/week ({tw_pct_of_week:.1f}%)</div>' if tw_enabled else ''}
            {f'<div style="font-size: 0.8em; color: #888; margin-top: 5px;">{tw_windows_count} windows</div>' if tw_enabled else ''}
            {'</div>' if tw_enabled else ''}
            <div class="stat-card" style="grid-column: span 2;">
                <div class="stat-label">Exits: SL / TP1 / BE / TP2</div>
                <div class="stat-value" style="font-size: 1.3em;">{num_final_sl} / {num_reached_tp1} / {num_final_be} / {num_reached_tp2}</div>
            </div>
        </div>
        {'<div style="text-align: center; color: #888; font-size: 0.85em; margin-top: 10px; padding: 8px; background: rgba(0,0,0,0.2); border-radius: 4px;">ℹ️ Toutes les statistiques (Avg Win/Loss, Profit Factor, Expectancy) sont calculées avec le PnL NET (après commissions)</div>' if portfolio_pnl_with_commissions is not None else ''}
    </div>
    
    <div class="chart-wrapper">
        <div class="main-chart-container">
            <canvas id="overlay"></canvas>
            <div id="chart"></div>
            
            <div class="trade-info" id="tradeInfo" style="display: none;">
                <div class="trade-info-title">Trade #<span id="tradeId"></span></div>
                <div class="trade-info-item">
                    <span class="trade-info-label">Direction:</span>
                    <span class="trade-info-value" id="tradeDirection"></span>
                </div>
                <div class="trade-info-item">
                    <span class="trade-info-label">Entry:</span>
                    <span class="trade-info-value" id="tradeEntry"></span>
                </div>
                <div class="trade-info-item">
                    <span class="trade-info-label">SL:</span>
                    <span class="trade-info-value" id="tradeSL" style="color: #ef5350;"></span>
                </div>
                <div class="trade-info-item">
                    <span class="trade-info-label">TP1:</span>
                    <span class="trade-info-value" id="tradeTP1" style="color: #4caf50;"></span>
                </div>
                <div class="trade-info-item">
                    <span class="trade-info-label">TP2:</span>
                    <span class="trade-info-value" id="tradeTP2" style="color: #2e7d32;"></span>
                </div>
                <div class="trade-info-item">
                    <span class="trade-info-label">Risk/Reward:</span>
                    <span class="trade-info-value" id="tradeRR" style="color: #ffa726;"></span>
                </div>
                <div class="trade-info-item">
                    <span class="trade-info-label">Time:</span>
                    <span class="trade-info-value" id="tradeTime"></span>
                </div>
            </div>
            
            <div class="legend">
                <div class="legend-title">Indicateurs</div>
                <div class="legend-item">
                    <div class="legend-line" style="background: #2196F3;"></div>
                    <span>BB Upper/Lower</span>
                </div>
                <div class="legend-item">
                    <div class="legend-line" style="background: #9C27B0;"></div>
                    <span>BB Middle (SMA 20)</span>
                </div>
                <div class="legend-item">
                    <div class="legend-box" style="background: rgba(255, 0, 0, 0.15); border-color: rgba(255, 0, 0, 0.8);"></div>
                    <span>SL</span>
                </div>
                <div class="legend-item">
                    <div class="legend-box" style="background: rgba(0, 255, 0, 0.1); border-color: rgba(0, 255, 0, 0.6);"></div>
                    <span>TP1</span>
                </div>
                <div class="legend-item">
                    <div class="legend-box" style="background: rgba(0, 200, 0, 0.15); border-color: rgba(0, 200, 0, 0.7);"></div>
                    <span>TP2</span>
                </div>
            </div>
            
            <div class="controls">
                <button class="btn" onclick="fitContent()">🔍 Fit</button>
                <button class="btn" onclick="scrollToEnd()">📍 Fin</button>
                <button class="btn" onclick="toggleBoxes()">
                    <span id="toggleIcon">👁️</span> <span id="toggleText">Cacher</span>
                </button>
            </div>
        </div>
        
        <div class="rsi-chart-container">
            <div id="rsiChart"></div>
            <div class="legend" style="bottom: 12px; top: auto;">
                <div class="legend-title">RSI (14)</div>
                <div class="legend-item">
                    <div class="legend-line" style="background: #9C27B0; height: 3px;"></div>
                    <span>Overbought > 70</span>
                </div>
                <div class="legend-item">
                    <div class="legend-line" style="background: #9C27B0; height: 3px;"></div>
                    <span>Oversold < 30</span>
                </div>
            </div>
        </div>
    </div>
    
    <div class="modal" id="heatmapsModal">
        <div class="modal-content">
            <div class="modal-header">
                <div class="modal-title">🔥 Heatmaps Temporelles</div>
                <button class="close-btn" onclick="closeHeatmaps()">✕ Fermer</button>
            </div>
            <div class="heatmaps-grid">
                <div class="heatmap-item">
                    <h3>Fréquence des Trades</h3>
                    <img src="heatmap_1_frequency.png" alt="Fréquence" onerror="this.src='data:image/svg+xml,<svg xmlns=%22http://www.w3.org/2000/svg%22><text y=%2250%%22>Image non disponible</text></svg>'">
                </div>
                <div class="heatmap-item">
                    <h3>Taux de Réussite (%)</h3>
                    <img src="heatmap_2_winrate.png" alt="Win Rate" onerror="this.src='data:image/svg+xml,<svg xmlns=%22http://www.w3.org/2000/svg%22><text y=%2250%%22>Image non disponible</text></svg>'">
                </div>
                <div class="heatmap-item">
                    <h3>PnL Moyen</h3>
                    <img src="heatmap_3_pnl.png" alt="PnL" onerror="this.src='data:image/svg+xml,<svg xmlns=%22http://www.w3.org/2000/svg%22><text y=%2250%%22>Image non disponible</text></svg>'">
                </div>
                <div class="heatmap-item">
                    <h3>Vue d'Ensemble</h3>
                    <img src="heatmap_4_combined.png" alt="Combiné" onerror="this.src='data:image/svg+xml,<svg xmlns=%22http://www.w3.org/2000/svg%22><text y=%2250%%22>Image non disponible</text></svg>'">
                </div>
            </div>
        </div>
    </div>
    
    <div class="modal" id="expectancyModal">
        <div class="modal-content">
            <div class="modal-header">
                <div class="modal-title">📈 Expectancy Analysis</div>
                <button class="close-btn" onclick="closeExpectancy()">✕ Fermer</button>
            </div>
            <div style="padding: 20px; overflow-y: auto; max-height: 80vh;">
                <!-- Heatmap Expectancy -->
                <div style="margin-bottom: 30px;">
                    <h3 style="color: #4dd0e1; margin-bottom: 15px;">Expectancy par Jour et Heure</h3>
                    <img src="heatmap_5_expectancy.png" alt="Expectancy Heatmap" style="width: 100%; border-radius: 8px;" onerror="this.style.display='none'; this.nextElementSibling.style.display='block';">
                    <div style="display: none; padding: 40px; text-align: center; color: #888; background: rgba(42, 46, 57, 0.5); border-radius: 8px;">
                        <p>Heatmap Expectancy non disponible</p>
                        <p style="font-size: 0.9em; margin-top: 10px;">Relancez le backtest pour générer la heatmap</p>
                    </div>
                </div>
                
                <!-- Graphiques par créneau horaire -->
                <div style="margin-top: 30px;">
                    <h3 style="color: #4dd0e1; margin-bottom: 15px;">📊 Analyse par Créneau Horaire</h3>
                    
                    <!-- Expectancy -->
                    <div style="margin-bottom: 30px;">
                        <h4 style="color: #26a69a; margin-bottom: 10px;">Expectancy / Trade</h4>
                        <img src="expectancy_hourly_expectancy.png" alt="Expectancy Hourly" style="width: 100%; border-radius: 8px;" onerror="this.style.display='none'; this.nextElementSibling.style.display='block';">
                        <div style="display: none; padding: 20px; text-align: center; color: #888; background: rgba(42, 46, 57, 0.5); border-radius: 8px;">
                            <p style="font-size: 0.9em;">Graphique non disponible</p>
                        </div>
                    </div>
                    
                    <!-- Profit Factor -->
                    <div style="margin-bottom: 30px;">
                        <h4 style="color: #26a69a; margin-bottom: 10px;">Profit Factor</h4>
                        <img src="expectancy_hourly_pf.png" alt="PF Hourly" style="width: 100%; border-radius: 8px;" onerror="this.style.display='none'; this.nextElementSibling.style.display='block';">
                        <div style="display: none; padding: 20px; text-align: center; color: #888; background: rgba(42, 46, 57, 0.5); border-radius: 8px;">
                            <p style="font-size: 0.9em;">Graphique non disponible</p>
                        </div>
                    </div>
                    
                    <!-- Drawdown -->
                    <div style="margin-bottom: 30px;">
                        <h4 style="color: #ef5350; margin-bottom: 10px;">Max Drawdown</h4>
                        <img src="expectancy_hourly_drawdown.png" alt="Drawdown Hourly" style="width: 100%; border-radius: 8px;" onerror="this.style.display='none'; this.nextElementSibling.style.display='block';">
                        <div style="display: none; padding: 20px; text-align: center; color: #888; background: rgba(42, 46, 57, 0.5); border-radius: 8px;">
                            <p style="font-size: 0.9em;">Graphique non disponible</p>
                        </div>
                    </div>
                    
                    <!-- Variance -->
                    <div style="margin-bottom: 30px;">
                        <h4 style="color: #9C27B0; margin-bottom: 10px;">Variance</h4>
                        <img src="expectancy_hourly_variance.png" alt="Variance Hourly" style="width: 100%; border-radius: 8px;" onerror="this.style.display='none'; this.nextElementSibling.style.display='block';">
                        <div style="display: none; padding: 20px; text-align: center; color: #888; background: rgba(42, 46, 57, 0.5); border-radius: 8px;">
                            <p style="font-size: 0.9em;">Graphique non disponible</p>
                        </div>
                    </div>
                </div>
                
                <!-- Tableau détaillé par SL size -->
                <div style="margin-top: 30px;">
                    <h3 style="color: #4dd0e1; margin-bottom: 15px;">Expectancy par Taille de SL</h3>
                    <table style="width: 100%; border-collapse: collapse; background: rgba(42, 46, 57, 0.5);">
                        <thead>
                            <tr style="background: rgba(77, 208, 225, 0.1); border-bottom: 1px solid rgba(77, 208, 225, 0.3);">
                                <th style="padding: 12px; text-align: left;">SL Range (pips)</th>
                                <th style="padding: 12px; text-align: right;">Trades</th>
                                <th style="padding: 12px; text-align: right;">Win Rate</th>
                                <th style="padding: 12px; text-align: right;">Expectancy ($)</th>
                                <th style="padding: 12px; text-align: right;">Expectancy (R)</th>
                            </tr>
                        </thead>
                        <tbody>
                            {"".join([f'''
                            <tr style="border-bottom: 1px solid rgba(77, 208, 225, 0.1);">
                                <td style="padding: 12px;">{s.get("sl_range", f"{s['sl_size']:.0f}")}</td>
                                <td style="padding: 12px; text-align: right;">{s["count"]}</td>
                                <td style="padding: 12px; text-align: right;">{s["win_rate"]:.1f}%</td>
                                <td style="padding: 12px; text-align: right; color: {'#26a69a' if s['expectancy'] > 0 else '#ef5350'};">${s["expectancy"]:.2f}</td>
                                <td style="padding: 12px; text-align: right; color: {'#26a69a' if s['expectancy_R'] > 0 else '#ef5350'};">{s["expectancy_R"]:.2f}R</td>
                            </tr>
                            ''' for s in sorted(sl_stats, key=lambda x: x['expectancy_R'], reverse=True) if len(sl_stats) > 0])}
                        </tbody>
                    </table>
                    {f'<p style="text-align: center; color: #888; margin-top: 20px;">Aucune donnée SL disponible</p>' if len(sl_stats) == 0 else ''}
                </div>
            </div>
        </div>
    </div>
    
    <div class="modal" id="statsModal">
        <div class="modal-content">
            <div class="modal-header">
                <div class="modal-title">📊 Statistiques Détaillées</div>
                <button class="close-btn" onclick="closeStats()">✕ Fermer</button>
            </div>
            <div class="stats-details">
                <div class="stats-section">
                    <h3>🎯 Performance Globale</h3>
                    <div class="stats-row">
                        <span>Total Trades:</span>
                        <span class="stat-value-large">{total_trades}</span>
                    </div>
                    <div class="stats-row">
                        <span>Win Rate:</span>
                        <span class="stat-value-large {'stat-green' if win_rate >= 50 else 'stat-red'}">{win_rate:.1f}%</span>
                    </div>
                    <div class="stats-row">
                        <span>Profit Factor:</span>
                        <span class="stat-value-large {'stat-green' if profit_factor > 1 else 'stat-red'}">{profit_factor:.2f}</span>
                    </div>
                    <div class="stats-row">
                        <span>PnL Total {'(net)' if portfolio_pnl_with_commissions is not None else '(brut)'}:</span>
                        <span class="stat-value-large {'stat-green' if total_pnl > 0 else 'stat-red'}">${total_pnl:+.2f}</span>
                    </div>
                    {'<div class="stats-row" style="font-size: 0.85em; color: #888;"><span>Brut (avant comm.):</span><span class="stat-value-large">$' + f"{total_pnl_brut:+.2f}" + '</span></div>' if portfolio_pnl_with_commissions is not None else ''}
                    <div class="stats-row">
                        <span>Return Stratégie:</span>
                        <span class="stat-value-large {'stat-green' if strategy_return_pct > 0 else 'stat-red'}">{strategy_return_pct:+.2f}%</span>
                    </div>
                </div>
                
                <div class="stats-section">
                    <h3>📈 Benchmark vs Marché</h3>
                    <div class="stats-row">
                        <span>Return Buy & Hold:</span>
                        <span class="stat-value-large {'stat-green' if market_return_pct > 0 else 'stat-red'}">{market_return_pct:+.2f}%</span>
                    </div>
                    <div class="stats-row">
                        <span>Outperformance:</span>
                        <span class="stat-value-large {'stat-green' if outperformance > 0 else 'stat-red'}">{outperformance:+.2f}%</span>
                    </div>
                    <div class="stats-info">
                        {'✅ Stratégie surperforme le marché' if outperformance > 0 else '⚠️ Marché surperforme la stratégie'}
                    </div>
                </div>
                
                <div class="stats-section">
                    <h3>🔥 Séries de Gains/Pertes</h3>
                    <div class="stats-row">
                        <span>Plus longue série de wins:</span>
                        <span class="stat-value-large stat-green">{max_win_streak} trades</span>
                    </div>
                    <div class="stats-row">
                        <span>Plus longue série de losses:</span>
                        <span class="stat-value-large stat-red">{max_loss_streak} trades</span>
                    </div>
                </div>
                
                <div class="stats-section">
                    <h3>🚫 Filtres de Trade</h3>
                    <div class="stats-row">
                        <span>SL Min configuré:</span>
                        <span class="stat-value-large">{min_sl_pips} pips</span>
                    </div>
                    <div class="stats-row">
                        <span>SL Max configuré:</span>
                        <span class="stat-value-large">{max_sl_pips if max_sl_pips > 0 else 'Aucun'} {'pips' if max_sl_pips > 0 else ''}</span>
                    </div>
                    <div class="stats-info">
                        Note: Taux de rejet précis disponible dans la console lors du backtest
                    </div>
                </div>
                
                <div class="stats-section">
                    <h3>💰 Détails PnL</h3>
                    <div class="stats-row">
                        <span>Avg Win:</span>
                        <span class="stat-value-large stat-green">+{avg_win:.2f}</span>
                    </div>
                    <div class="stats-row">
                        <span>Avg Loss:</span>
                        <span class="stat-value-large stat-red">{avg_loss:.2f}</span>
                    </div>
                </div>
            </div>
        </div>
    </div>
    
    <script>
        const candlesData = {json.dumps(candles)};
        const rectanglesData = {json.dumps(rectangles)};
        const bbUpperData = {json.dumps(bb_upper)};
        const bbMiddleData = {json.dumps(bb_middle)};
        const bbLowerData = {json.dumps(bb_lower)};
        const rsiData = {json.dumps(rsi_data)};
        const tradesData = {json.dumps(trade_times)};
        
        let chart, candlestickSeries, rsiChart, rsiSeries;
        let overlay, ctx;
        let boxesVisible = true;
        let currentTradeIndex = -1;
        let hoveredRect = null;  // NOUVEAU: Pour tooltip
        
        function initCharts() {{
            const mainContainer = document.querySelector('.main-chart-container');
            const rsiContainer = document.querySelector('.rsi-chart-container');
            
            // Main chart
            chart = LightweightCharts.createChart(document.getElementById('chart'), {{
                layout: {{ background: {{ color: '#1a1d29' }}, textColor: '#d1d4dc' }},
                grid: {{ vertLines: {{ color: 'rgba(43, 43, 67, 0.2)' }}, horzLines: {{ color: 'rgba(43, 43, 67, 0.2)' }} }},
                width: mainContainer.clientWidth,
                height: mainContainer.clientHeight,
                timeScale: {{ timeVisible: true, secondsVisible: true, borderColor: 'rgba(77, 208, 225, 0.2)' }},
                rightPriceScale: {{ borderColor: 'rgba(77, 208, 225, 0.2)' }},
                crosshair: {{ mode: LightweightCharts.CrosshairMode.Normal }}
            }});
            
            candlestickSeries = chart.addCandlestickSeries({{
                upColor: '#26a69a',
                downColor: '#ef5350',
                borderVisible: true,
                borderUpColor: '#26a69a',
                borderDownColor: '#ef5350',
                wickUpColor: '#26a69a',
                wickDownColor: '#ef5350'
            }});
            candlestickSeries.setData(candlesData);
            
            // Bollinger Bands
            const bbUpperSeries = chart.addLineSeries({{ color: '#2196F3', lineWidth: 1, priceLineVisible: false, lastValueVisible: false }});
            bbUpperSeries.setData(bbUpperData);
            
            const bbMiddleSeries = chart.addLineSeries({{ color: '#9C27B0', lineWidth: 2, priceLineVisible: false, lastValueVisible: false }});
            bbMiddleSeries.setData(bbMiddleData);
            
            const bbLowerSeries = chart.addLineSeries({{ color: '#2196F3', lineWidth: 1, priceLineVisible: false, lastValueVisible: false }});
            bbLowerSeries.setData(bbLowerData);
            
            // Canvas overlay
            overlay = document.getElementById('overlay');
            overlay.width = mainContainer.clientWidth;
            overlay.height = mainContainer.clientHeight;
            ctx = overlay.getContext('2d');
            
            setTimeout(drawRectangles, 100);
            chart.timeScale().subscribeVisibleLogicalRangeChange(drawRectangles);
            
            // RSI chart
            rsiChart = LightweightCharts.createChart(document.getElementById('rsiChart'), {{
                layout: {{ background: {{ color: '#1a1d29' }}, textColor: '#d1d4dc' }},
                grid: {{ vertLines: {{ color: 'rgba(43, 43, 67, 0.2)' }}, horzLines: {{ color: 'rgba(43, 43, 67, 0.2)' }} }},
                width: rsiContainer.clientWidth,
                height: rsiContainer.clientHeight,
                timeScale: {{ timeVisible: true, secondsVisible: true, borderColor: 'rgba(77, 208, 225, 0.2)' }},
                rightPriceScale: {{ borderColor: 'rgba(77, 208, 225, 0.2)' }}
            }});
            
            rsiSeries = rsiChart.addLineSeries({{ color: '#9C27B0', lineWidth: 2 }});
            rsiSeries.setData(rsiData);
            
            // RSI levels
            rsiChart.addLineSeries({{ color: 'rgba(239, 83, 80, 0.5)', lineWidth: 1, priceLineVisible: false, lastValueVisible: false }})
                .setData([{{ time: rsiData[0].time, value: 70 }}, {{ time: rsiData[rsiData.length - 1].time, value: 70 }}]);
            
            rsiChart.addLineSeries({{ color: 'rgba(76, 175, 80, 0.5)', lineWidth: 1, priceLineVisible: false, lastValueVisible: false }})
                .setData([{{ time: rsiData[0].time, value: 30 }}, {{ time: rsiData[rsiData.length - 1].time, value: 30 }}]);
            
            // Sync timeScale
            chart.timeScale().subscribeVisibleLogicalRangeChange((range) => {{
                if (range) rsiChart.timeScale().setVisibleLogicalRange(range);
            }});
            
            rsiChart.timeScale().subscribeVisibleLogicalRangeChange((range) => {{
                if (range) chart.timeScale().setVisibleLogicalRange(range);
            }});
            
            // Resize
            window.addEventListener('resize', () => {{
                chart.applyOptions({{ width: mainContainer.clientWidth, height: mainContainer.clientHeight }});
                rsiChart.applyOptions({{ width: rsiContainer.clientWidth, height: rsiContainer.clientHeight }});
                overlay.width = mainContainer.clientWidth;
                overlay.height = mainContainer.clientHeight;
                drawRectangles();
            }});
            
            // NOUVEAU: Tooltip au survol des boxes
            overlay.addEventListener('mousemove', handleMouseMove);
            overlay.addEventListener('mouseleave', () => {{
                hoveredRect = null;
                drawRectangles();
            }});
            
            chart.timeScale().fitContent();
            
            console.log('✅ Charts initialisés');
            console.log(`📊 ${{candlesData.length}} chandelles`);
            console.log(`📦 ${{rectanglesData.length}} rectangles`);
            console.log(`📈 Bollinger Bands & RSI ajoutés`);
        }}
        
        function handleMouseMove(event) {{
            if (!boxesVisible) return;
            
            const rect = overlay.getBoundingClientRect();
            const x = event.clientX - rect.left;
            const y = event.clientY - rect.top;
            
            const timeScale = chart.timeScale();
            hoveredRect = null;
            
            // Trouver si la souris est sur une box
            for (const boxRect of rectanglesData) {{
                const x1 = timeScale.timeToCoordinate(boxRect.time1);
                const x2 = timeScale.timeToCoordinate(boxRect.time2);
                const y1 = candlestickSeries.priceToCoordinate(boxRect.price1);
                const y2 = candlestickSeries.priceToCoordinate(boxRect.price2);
                
                if (x1 !== null && y1 !== null && x2 !== null && y2 !== null) {{
                    const left = Math.min(x1, x2);
                    const top = Math.min(y1, y2);
                    const width = Math.abs(x2 - x1);
                    const height = Math.abs(y2 - y1);
                    
                    if (x >= left && x <= left + width && y >= top && y <= top + height) {{
                        hoveredRect = {{ ...boxRect, x, y }};
                        break;
                    }}
                }}
            }}
            
            drawRectangles();
        }}
        
        function drawTradeMarkers() {{
            if (!boxesVisible) return;
            
            const timeScale = chart.timeScale();
            
            // Grouper rectangles par trade_id
            const tradeGroups = {{}};
            rectanglesData.forEach(rect => {{
                if (!tradeGroups[rect.trade_id]) {{
                    tradeGroups[rect.trade_id] = [];
                }}
                tradeGroups[rect.trade_id].push(rect);
            }});
            
            // Pour chaque trade, dessiner les markers
            Object.entries(tradeGroups).forEach(([tradeId, rects]) => {{
                if (rects.length === 0) return;
                
                // Trouver le trade correspondant
                const trade = tradesData.find(t => t.id === parseInt(tradeId));
                if (!trade) return;
                
                const entryX = timeScale.timeToCoordinate(trade.time);
                const entryY = candlestickSeries.priceToCoordinate(trade.price);
                
                if (entryX === null || entryY === null) return;
                
                // Triangle ENTRY (haut=LONG jaune, bas=SHORT bleu)
                const entrySize = 10;
                ctx.fillStyle = trade.direction === 'LONG' ? '#FFD700' : '#87CEEB';
                ctx.beginPath();
                if (trade.direction === 'LONG') {{
                    // Triangle pointant vers le haut
                    ctx.moveTo(entryX, entryY + entrySize);
                    ctx.lineTo(entryX - entrySize, entryY + entrySize * 2);
                    ctx.lineTo(entryX + entrySize, entryY + entrySize * 2);
                }} else {{
                    // Triangle pointant vers le bas
                    ctx.moveTo(entryX, entryY - entrySize);
                    ctx.lineTo(entryX - entrySize, entryY - entrySize * 2);
                    ctx.lineTo(entryX + entrySize, entryY - entrySize * 2);
                }}
                ctx.closePath();
                ctx.fill();
                ctx.strokeStyle = trade.direction === 'LONG' ? '#DAA520' : '#4682B4';
                ctx.lineWidth = 1;
                ctx.stroke();
                
                // NOUVEAU: Triangles SL et TP sur la même ligne temporelle (entryX)
                rects.forEach(rect => {{
                    // Skip SL_INITIAL boxes (juste pour info, pas de triangle)
                    if (rect.type === 'SL_INITIAL') {{
                        // Dessiner quand même un petit marker pour SL initial
                        const slPrice = rect.metadata && rect.metadata.sl_price ? rect.metadata.sl_price : 
                                       (trade.direction === 'LONG' ? rect.price1 : rect.price2);
                        const slY = candlestickSeries.priceToCoordinate(slPrice);
                        
                        if (slY !== null) {{
                            // Petit triangle orange transparent pour SL initial
                            const markerSize = 6;
                            ctx.fillStyle = 'rgba(255, 100, 0, 0.5)';
                            ctx.strokeStyle = 'rgba(255, 100, 0, 0.8)';
                            ctx.beginPath();
                            ctx.moveTo(entryX + markerSize * 1.5, slY);
                            ctx.lineTo(entryX, slY - markerSize);
                            ctx.lineTo(entryX, slY + markerSize);
                            ctx.closePath();
                            ctx.fill();
                            ctx.lineWidth = 1;
                            ctx.stroke();
                        }}
                        return;
                    }}
                    
                    // Utiliser entryX au lieu de exitX (tous alignés verticalement)
                    let targetPrice;
                    
                    if (rect.type === 'SL') {{
                        // SL = le prix opposé à l'entry
                        targetPrice = trade.direction === 'LONG' ? rect.price1 : rect.price2;
                    }} else {{
                        // TP = le prix opposé à l'entry
                        targetPrice = trade.direction === 'LONG' ? rect.price2 : rect.price1;
                    }}
                    
                    const targetY = candlestickSeries.priceToCoordinate(targetPrice);
                    
                    if (targetY === null) return;
                    
                    const markerSize = 8;
                    
                    if (rect.type === 'SL') {{
                        // Triangle SL rouge pointant droite
                        ctx.fillStyle = 'rgba(255, 0, 0, 0.8)';
                        ctx.strokeStyle = '#8B0000';
                    }} else {{
                        // Triangle TP vert pointant droite
                        ctx.fillStyle = rect.type === 'TP2' ? 'rgba(0, 200, 0, 0.8)' : 'rgba(0, 255, 0, 0.7)';
                        ctx.strokeStyle = rect.type === 'TP2' ? '#006400' : '#228B22';
                    }}
                    
                    ctx.beginPath();
                    // CHANGEMENT: Utiliser entryX au lieu de exitX
                    ctx.moveTo(entryX + markerSize * 1.5, targetY);
                    ctx.lineTo(entryX, targetY - markerSize);
                    ctx.lineTo(entryX, targetY + markerSize);
                    ctx.closePath();
                    ctx.fill();
                    ctx.lineWidth = 1;
                    ctx.stroke();
                }});
            }});
        }}
        
        function drawRectangles() {{
            if (!ctx) {{
                console.log('❌ Pas de contexte canvas');
                return;
            }}
            
            if (!boxesVisible) {{
                ctx.clearRect(0, 0, overlay.width, overlay.height);
                return;
            }}
            
            ctx.clearRect(0, 0, overlay.width, overlay.height);
            
            const timeScale = chart.timeScale();
            const layerOrder = ['TP2', 'TP1', 'SL', 'SL_INITIAL'];  // SL_INITIAL en dernier (plus transparent)
            
            let drawnCount = 0;
            
            layerOrder.forEach(type => {{
                rectanglesData.filter(r => r.type === type).forEach(rect => {{
                    const x1 = timeScale.timeToCoordinate(rect.time1);
                    const x2 = timeScale.timeToCoordinate(rect.time2);
                    const y1 = candlestickSeries.priceToCoordinate(rect.price1);
                    const y2 = candlestickSeries.priceToCoordinate(rect.price2);
                    
                    if (x1 !== null && y1 !== null && x2 !== null && y2 !== null) {{
                        const left = Math.min(x1, x2);
                        const top = Math.min(y1, y2);
                        const width = Math.abs(x2 - x1);
                        const height = Math.abs(y2 - y1);
                        
                        ctx.fillStyle = rect.fillColor;
                        ctx.fillRect(left, top, width, height);
                        ctx.strokeStyle = rect.borderColor;
                        ctx.lineWidth = 2;
                        ctx.strokeRect(left, top, width, height);
                        drawnCount++;
                    }}
                }});
            }});
            
            // NOUVEAU: Dessiner les triangles pour les trades
            drawTradeMarkers();
            
            // NOUVEAU: Dessiner tooltip si hoveredRect existe
            if (hoveredRect) {{
                const trade = tradesData.find(t => t.id === hoveredRect.trade_id);
                if (trade) {{
                    const tooltipPadding = 10;
                    const tooltipWidth = 200;
                    const tooltipHeight = 100;
                    
                    // Position du tooltip (éviter les bords)
                    let tooltipX = hoveredRect.x + 15;
                    let tooltipY = hoveredRect.y - tooltipHeight - 10;
                    
                    if (tooltipX + tooltipWidth > overlay.width) {{
                        tooltipX = hoveredRect.x - tooltipWidth - 15;
                    }}
                    if (tooltipY < 0) {{
                        tooltipY = hoveredRect.y + 15;
                    }}
                    
                    // Fond tooltip
                    ctx.fillStyle = 'rgba(26, 29, 41, 0.95)';
                    ctx.strokeStyle = hoveredRect.type === 'SL' ? 'rgba(255, 0, 0, 0.8)' : 'rgba(0, 255, 0, 0.8)';
                    ctx.lineWidth = 2;
                    ctx.fillRect(tooltipX, tooltipY, tooltipWidth, tooltipHeight);
                    ctx.strokeRect(tooltipX, tooltipY, tooltipWidth, tooltipHeight);
                    
                    // Texte tooltip
                    ctx.font = '14px monospace';
                    ctx.fillStyle = '#d1d4dc';
                    ctx.textAlign = 'left';
                    
                    const textX = tooltipX + tooltipPadding;
                    let textY = tooltipY + tooltipPadding + 15;
                    
                    ctx.fillText(`Trade #${{hoveredRect.trade_id}}`, textX, textY);
                    textY += 20;
                    
                    ctx.fillStyle = trade.direction === 'LONG' ? '#26a69a' : '#ef5350';
                    ctx.fillText(`${{trade.direction}}`, textX, textY);
                    textY += 20;
                    
                    ctx.fillStyle = '#d1d4dc';
                    ctx.fillText(`Type: ${{hoveredRect.type}}`, textX, textY);
                    textY += 20;
                    
                    const typeColors = {{ 'SL': '#ef5350', 'TP1': '#4caf50', 'TP2': '#2e7d32' }};
                    ctx.fillStyle = typeColors[hoveredRect.type] || '#d1d4dc';
                    const exitPrice = trade.direction === 'LONG' ? 
                        (hoveredRect.type === 'SL' ? hoveredRect.price1 : hoveredRect.price2) :
                        (hoveredRect.type === 'SL' ? hoveredRect.price2 : hoveredRect.price1);
                    ctx.fillText(`Prix: ${{exitPrice.toFixed(2)}}`, textX, textY);
                }}
            }}
            
            if (drawnCount === 0 && rectanglesData.length > 0) {{
                console.log('⚠️  Aucune box dessinée malgré', rectanglesData.length, 'rectangles dans les données');
                console.log('Premier rectangle:', rectanglesData[0]);
            }}
        }}
        
        function previousTrade() {{
            if (currentTradeIndex > 0) {{
                currentTradeIndex--;
                goToTrade(currentTradeIndex);
            }}
        }}
        
        function nextTrade() {{
            if (currentTradeIndex < tradesData.length - 1) {{
                currentTradeIndex++;
                goToTrade(currentTradeIndex);
            }}
        }}
        
        function goToTrade(index) {{
            const trade = tradesData[index];
            
            // Trouver la box SL de ce trade pour déterminer la durée
            const tradeBoxes = rectanglesData.filter(r => r.trade_id === trade.id);
            
            let tradeDuration = 3600; // 1h par défaut
            if (tradeBoxes.length > 0) {{
                // Trouver la durée max des boxes
                const maxEndTime = Math.max(...tradeBoxes.map(b => b.time2));
                tradeDuration = maxEndTime - trade.time;
            }}
            
            // NOUVEAU: Box prend 20% de l'écran (5x la durée du trade)
            const totalDuration = tradeDuration * 5;
            const margin = (totalDuration - tradeDuration) / 2;
            const from = trade.time - margin;
            const to = trade.time + tradeDuration + margin;
            
            // Centrer verticalement sur le prix d'entrée
            // Trouver min/max prix des boxes pour calculer le range
            let minPrice = trade.price;
            let maxPrice = trade.price;
            
            tradeBoxes.forEach(box => {{
                minPrice = Math.min(minPrice, box.price1, box.price2);
                maxPrice = Math.max(maxPrice, box.price1, box.price2);
            }});
            
            // Calculer range vertical centré sur entry price
            const priceRange = maxPrice - minPrice || 50; // Au moins 50 points si pas de boxes
            const halfRange = priceRange * 1.5; // 1.5x pour avoir de la marge
            
            // IMPORTANT: Réactiver autoScale puis le désactiver pour forcer le reset
            chart.priceScale('right').applyOptions({{
                autoScale: true,
            }});
            
            // Set la plage visible (temps)
            chart.timeScale().setVisibleRange({{ from, to }});
            
            // Attendre un instant puis appliquer le range de prix personnalisé
            setTimeout(() => {{
                // Désactiver autoScale
                chart.priceScale('right').applyOptions({{
                    autoScale: false,
                }});
                
                // Forcer le range de prix centré sur entry
                const minVisible = trade.price - halfRange;
                const maxVisible = trade.price + halfRange;
                
                // Utiliser scaleMargins pour forcer le centrage
                candlestickSeries.applyOptions({{
                    autoscaleInfoProvider: () => ({{
                        priceRange: {{
                            minValue: minVisible,
                            maxValue: maxVisible,
                        }},
                        margins: {{
                            above: 0,
                            below: 0,
                        }},
                    }}),
                }});
                
                // Redessiner les boxes pour qu'elles apparaissent
                drawRectangles();
            }}, 50);
            
            // Afficher info avec SL et TP
            document.getElementById('tradeInfo').style.display = 'block';
            document.getElementById('tradeId').textContent = trade.id;
            document.getElementById('tradeDirection').textContent = trade.direction;
            document.getElementById('tradeDirection').style.color = trade.direction === 'LONG' ? '#26a69a' : '#ef5350';
            document.getElementById('tradeEntry').textContent = trade.price.toFixed(2);
            document.getElementById('tradeTime').textContent = new Date(trade.time * 1000).toLocaleString();
            
            // NOUVEAU: Afficher SL et TP
            const slBox = tradeBoxes.find(b => b.type === 'SL');
            const tp1Box = tradeBoxes.find(b => b.type === 'TP1');
            const tp2Box = tradeBoxes.find(b => b.type === 'TP2');
            
            if (slBox) {{
                const slPrice = trade.direction === 'LONG' ? slBox.price1 : slBox.price2;
                document.getElementById('tradeSL').textContent = slPrice.toFixed(2);
            }} else {{
                document.getElementById('tradeSL').textContent = 'N/A';
            }}
            
            if (tp1Box) {{
                const tp1Price = trade.direction === 'LONG' ? tp1Box.price2 : tp1Box.price1;
                document.getElementById('tradeTP1').textContent = tp1Price.toFixed(2);
            }} else {{
                document.getElementById('tradeTP1').textContent = 'N/A';
            }}
            
            if (tp2Box) {{
                const tp2Price = trade.direction === 'LONG' ? tp2Box.price2 : tp2Box.price1;
                document.getElementById('tradeTP2').textContent = tp2Price.toFixed(2);
            }} else {{
                document.getElementById('tradeTP2').textContent = 'N/A';
            }}
            
            // Calculer RR (Risk/Reward)
            // Chercher SL_INITIAL pour avoir le SL d'origine (même si BE après)
            const slInitialBox = tradeBoxes.find(b => b.type === 'SL_INITIAL');
            const slBoxForRR = slInitialBox || slBox;  // Fallback sur SL si pas de SL_INITIAL
            
            if (slBoxForRR && (tp1Box || tp2Box)) {{
                const entryPrice = trade.price;
                const slPrice = slBoxForRR.metadata && slBoxForRR.metadata.sl_price 
                    ? slBoxForRR.metadata.sl_price 
                    : (trade.direction === 'LONG' ? slBoxForRR.price1 : slBoxForRR.price2);
                
                // Risk = distance entry -> SL
                const risk = Math.abs(entryPrice - slPrice);
                
                // Reward = moyenne pondérée des TP (50% TP1 + 50% TP2)
                let reward = 0;
                if (tp1Box && tp2Box) {{
                    const tp1Price = trade.direction === 'LONG' ? tp1Box.price2 : tp1Box.price1;
                    const tp2Price = trade.direction === 'LONG' ? tp2Box.price2 : tp2Box.price1;
                    const reward1 = Math.abs(tp1Price - entryPrice);
                    const reward2 = Math.abs(tp2Price - entryPrice);
                    reward = (reward1 * 0.5) + (reward2 * 0.5);  // 50% chaque
                }} else if (tp1Box) {{
                    const tp1Price = trade.direction === 'LONG' ? tp1Box.price2 : tp1Box.price1;
                    reward = Math.abs(tp1Price - entryPrice) * 0.5;  // 50% seulement
                }}
                
                const rr = risk > 0 ? reward / risk : 0;
                document.getElementById('tradeRR').textContent = `1:${{rr.toFixed(2)}}`;
            }} else {{
                document.getElementById('tradeRR').textContent = 'N/A';
            }}
        }}
        
        function fitContent() {{ chart.timeScale().fitContent(); }}
        function scrollToEnd() {{ chart.timeScale().scrollToRealTime(); }}
        
        function toggleBoxes() {{
            boxesVisible = !boxesVisible;
            drawRectangles();
            document.getElementById('toggleIcon').textContent = boxesVisible ? '👁️' : '🚫';
            document.getElementById('toggleText').textContent = boxesVisible ? 'Cacher' : 'Montrer';
        }}
        
        function showHeatmaps() {{
            document.getElementById('heatmapsModal').classList.add('active');
        }}
        
        function closeHeatmaps() {{
            document.getElementById('heatmapsModal').classList.remove('active');
        }}
        
        function showExpectancy() {{
            document.getElementById('expectancyModal').classList.add('active');
        }}
        
        function closeExpectancy() {{
            document.getElementById('expectancyModal').classList.remove('active');
        }}
        
        function showStats() {{
            document.getElementById('statsModal').classList.add('active');
        }}
        
        function closeStats() {{
            document.getElementById('statsModal').classList.remove('active');
        }}
        
        // Toggle legend collapse
        document.querySelectorAll('.legend').forEach(legend => {{
            legend.addEventListener('click', function() {{
                this.classList.toggle('collapsed');
            }});
        }});
        
        // Fermer modals avec Escape
        document.addEventListener('keydown', (e) => {{
            if (e.key === 'Escape') {{
                closeHeatmaps();
                closeStats();
            }}
        }});
        
        window.addEventListener('load', initCharts);
    </script>
</body>
</html>'''
    
    output_file = Path('output/visualization_complete.html')
    output_file.write_text(html, encoding='utf-8')
    
    print(f"\n✅ HTML complet: {output_file}")
    print(f"\n🎯 Fonctionnalités:")
    print(f"   ✅ Bollinger Bands (std 1.5)")
    print(f"   ✅ RSI (14) en panneau séparé")
    print(f"   ✅ Stats backtest complètes")
    print(f"   ✅ Navigation entre trades (⬅️/➡️)")
    print(f"   ✅ Modal heatmaps (4 images)")
    print(f"   ✅ Info trade au survol")
    print(f"   ✅ Boxes avec z-ordering")
    print(f"   ✅ TimeScale synchronisé")
    
    print(f"\n📊 Stats:")
    print(f"   Total Trades: {total_trades}")
    print(f"   Wins: {wins} (trades that reached TP1)")
    print(f"   Losses: {losses} (trades that hit SL)")
    print(f"   Scratches: {scratches} (if any)")
    print(f"   Win Rate: {win_rate:.1f}%")
    print(f"\n   📍 Final Exits:")
    print(f"      SL: {num_final_sl}")
    print(f"      BE: {num_final_be} (came from TP1)")
    print(f"      TP1 only: {num_final_tp1} (stopped at TP1, didn't reach TP2)")
    print(f"      TP2: {num_final_tp2} (came from TP1)")
    print(f"      Total: {num_final_sl + num_final_be + num_final_tp1 + num_final_tp2}")
    print(f"\n   🎯 Levels Reached:")
    print(f"      TP1: {num_reached_tp1}")
    print(f"      TP2: {num_reached_tp2}")
    print(f"\n   ✅ Coherence:")
    print(f"      Wins ({wins}) = TP1 reached ({num_reached_tp1}): {'✅' if wins == num_reached_tp1 else '❌'}")
    print(f"      Losses ({losses}) = SL ({num_final_sl}): {'✅' if losses == num_final_sl else '❌'}")
    print(f"      TP1 ({num_reached_tp1}) >= TP2 ({num_reached_tp2}): {'✅' if num_reached_tp2 <= num_reached_tp1 else '❌'}")
    print(f"      TP1 reached = TP1_final + TP2 + BE: {num_final_tp1} + {num_final_tp2} + {num_final_be} = {num_final_tp1 + num_final_tp2 + num_final_be} (actual: {num_reached_tp1})")
    print(f"\n   💰 PnL:")
    print(f"      Total: {total_pnl:.2f}")
    print(f"      Avg Win: {avg_win:.2f}")
    print(f"      Avg Loss: {avg_loss:.2f}")
    print(f"      Profit Factor: {profit_factor:.2f}")
    print(f"      Expectancy: ${expectancy_dollars:.2f} per trade ({expectancy_R:.2f}R)")
    
    # Expectancy breakdown
    if len(hourly_stats) > 0:
        print(f"\n   📈 Top 5 Hours by Expectancy:")
        sorted_hours = sorted(hourly_stats, key=lambda x: x['expectancy'], reverse=True)[:5]
        for h in sorted_hours:
            print(f"      {h['hour']:02d}h: ${h['expectancy']:>7.2f} (WR: {h['win_rate']:.1f}%, n={h['count']})")
    
    if len(sl_stats) > 0:
        print(f"\n   📏 Top 5 SL Ranges by Expectancy (R):")
        sorted_sl = sorted(sl_stats, key=lambda x: x['expectancy_R'], reverse=True)[:5]
        for s in sorted_sl:
            sl_label = s.get('sl_range', f"{s['sl_size']:.0f}")
            print(f"      {sl_label:>12s} pips: {s['expectancy_R']:>6.2f}R (${s['expectancy']:>7.2f}, WR: {s['win_rate']:.1f}%, n={s['count']})")
    
    print("\n" + "="*70 + "\n")
    
    return output_file


if __name__ == "__main__":
    import sys
    config_file = sys.argv[1] if len(sys.argv) > 1 else 'config_rsi_amplitude.yaml'
    generate_complete_html(config_file)
