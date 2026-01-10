#!/usr/bin/env python3
"""
Générateur HTML Complet - Architecture Refactorisée

Utilise:
- core/indicator_loader.py pour charger indicateurs
- core/models.py primitives
- visualization/primitive_serializer.py pour conversion
- visualization/trades_analyzer.py pour stats

Génère:
- Bollinger Bands via indicateur
- RSI via indicateur
- Trades overlay via indicateur
- Stats backtest via analyzer

- Navigation trades
"""

import pandas as pd

import json
import yaml
from pathlib import Path

# NEW: Import refactored helpers
from visualization.html_generation_helpers import (
    load_candles,
    build_candles_json,
    get_visualization_indicators,
    run_indicators,
    serialize_indicators
)
from visualization.trades_analyzer import TradesAnalyzer
from visualization.heatmaps_generator import generate_all as generate_heatmap_assets


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


# DEPRECATED: Old calculation functions kept for reference
# Now using indicators from visualization/indicators/







def generate_complete_html(config_file='config_rsi_amplitude.yaml'):
    """
    Génère HTML complet interactif - VERSION REFACTORISÉE

    Uses:
    - visualization/indicators/bollinger_bands.py
    - visualization/indicators/rsi.py
    - visualization/indicators/trades_overlay.py
    - visualization/trades_analyzer.py
    - visualization/primitive_serializer.py
    """

    print("\n" + "=" * 70)
    print("GÉNÉRATION HTML COMPLET INTERACTIF (REFACTORISÉ)")
    print("=" * 70 + "\n")

    # 1. Load config
    config = load_config(config_file)
    config_name = Path(config_file).stem

    symbol = config.get('data', {}).get('symbol', 'NAS100')
    timeframe = config.get('data', {}).get('timeframe', 'M3')
    strategy_name = config.get('strategy_name', 'Strategy')

    # 2. Load candles
    try:
        df = load_candles(config)
        print(f"   ✅ {len(df)} chandelles")
    except FileNotFoundError as e:
        print(f"❌ {e}")
        return

    # 3. Build candles JSON
    candles = build_candles_json(df)

    # 4. Get indicators config
    indicators_config = get_visualization_indicators(config)

    # 5. Run indicators
    results = run_indicators(df, indicators_config)

    # 6. Serialize
    serialized = serialize_indicators(candles, results)

    bb_upper = serialized['bb_upper']
    bb_middle = serialized['bb_middle']
    bb_lower = serialized['bb_lower']
    rsi_data = serialized['rsi']
    rectangles = serialized['rectangles']
    trade_times = serialized['trades_nav']

    print(f"\n📊 Sérialisé: {len(bb_upper)} BB, {len(rsi_data)} RSI, {len(rectangles)} boxes, {len(trade_times)} trades")

    # 7. Stats
    analyzer = TradesAnalyzer('output/trades_backtest.csv')
    df_trades = analyzer.trades  # Ajoute cette ligne

    portfolio_stats_file = Path('output/portfolio_stats.json')
    portfolio_pnl = None
    if portfolio_stats_file.exists():
        import json
        with open(portfolio_stats_file, 'r') as f:
            portfolio_stats = json.load(f)
        portfolio_pnl = portfolio_stats.get('total_pnl', None)

    stats = analyzer.compute_stats(portfolio_pnl)

    # DEBUG
    #trade_details = analyzer.get_trade_details()
    #print(f"DEBUG: type(trade_details) = {type(trade_details)}")
    #print(f"DEBUG: trade_details = {trade_details}")


    # Generate heatmap image assets (PNG) via dedicated module
    heatmap_assets = generate_heatmap_assets(analyzer, output_dir='output')


    # Extract stats
    total_trades = stats['total_trades']
    wins = stats['wins']
    losses = stats['losses']
    scratches = stats['scratches']
    win_rate = stats['win_rate']
    total_pnl = stats['total_pnl']
    avg_pnl = stats['avg_pnl']
    best_trade = stats['best_trade']
    worst_trade = stats['worst_trade']
    num_final_sl = stats['num_final_sl']
    num_final_be = stats['num_final_be']
    num_final_tp1 = stats['num_final_tp1']

    # Variables for template compatibility
    portfolio_pnl_with_commissions = portfolio_pnl
    total_pnl_brut = total_pnl  # Same in our simplified version
    num_final_tp2 = stats['num_final_tp2']
    num_forced_close = stats['num_forced_close']
    num_reached_tp1 = stats['num_reached_tp1']
    num_reached_tp2 = stats['num_reached_tp2']

    # Computed stats (now computed in TradesAnalyzer for consistency)
    avg_win = stats.get('avg_win', 0.0)
    avg_loss = stats.get('avg_loss', 0.0)
    profit_factor = stats.get('profit_factor', 0.0)
    expectancy_dollars = stats.get('expectancy_dollars', avg_pnl)
    # Calculate expectancy in R (risk-adjusted)

    # Calculate expectancy in R (risk-adjusted)
    # Calculate expectancy in R (risk-adjusted)
    try:
        boxes_df = pd.read_csv('output/boxes_log.csv')
        print(f"DEBUG: boxes_df columns = {list(boxes_df.columns)}")
        print(f"DEBUG: First 3 rows:")
        print(boxes_df.head(3))

        # Check column name (box_type or type)
        type_col = 'box_type' if 'box_type' in boxes_df.columns else 'type'
        sl_boxes = boxes_df[boxes_df[type_col] == 'SL']

        print(f"📊 Calcul expectancy_R: {len(sl_boxes)} SL boxes trouvées sur {len(boxes_df)} total")

        risks = []
        for idx, box in sl_boxes.iterrows():
            trade_id = box['trade_id']
            entry = df_trades[(df_trades['trade_id'] == trade_id) &
                              (df_trades['event_type'] == 'ENTRY')]
            if len(entry) > 0:
                entry_price = entry.iloc[0]['price']

                # Get SL price from metadata or calculate from box bounds
                if 'sl_price' in box and pd.notna(box['sl_price']):
                    sl_price = box['sl_price']
                else:
                    # Fallback: use price_low or price_high depending on direction
                    direction = entry.iloc[0].get('direction', 'LONG')
                    if direction == 'LONG':
                        sl_price = box['price_low']  # SL below entry for LONG
                    else:
                        sl_price = box['price_high']  # SL above entry for SHORT

                risk = abs(entry_price - sl_price)
                if risk > 0:
                    risks.append(risk)

        if len(risks) > 0:
            avg_risk = sum(risks) / len(risks)
            expectancy_R = expectancy_dollars / avg_risk
            print(f"✅ Expectancy: ${expectancy_dollars:.2f} / Risk moyen: ${avg_risk:.2f} = {expectancy_R:.2f}R")
        else:
            print(f"⚠️  Aucun risque calculé, expectancy_R = 0")
            expectancy_R = 0.0

    except Exception as e:
        print(f"⚠️  Erreur calcul expectancy_R: {e}")
        import traceback
        traceback.print_exc()
        expectancy_R = 0.0



    trade_results = []
    for trade_id in df_trades['trade_id'].unique():
        exits = df_trades[(df_trades['trade_id'] == trade_id) &
                          (df_trades['event_type'].isin(['SL', 'TP1', 'TP2', 'BE', 'FORCED_CLOSE']))]
        if len(exits) > 0:
            total_pnl = exits['pnl'].sum()
            trade_results.append(total_pnl)
    max_win_streak = 0
    max_loss_streak = 0
    current_win_streak = 0
    current_loss_streak = 0

    for pnl in trade_results:
        if pnl > 0:
            current_win_streak += 1
            current_loss_streak = 0
            max_win_streak = max(max_win_streak, current_win_streak)
        elif pnl < 0:
            current_loss_streak += 1
            current_win_streak = 0
            max_loss_streak = max(max_loss_streak, current_loss_streak)
        else:
            current_win_streak = 0
            current_loss_streak = 0
    min_sl_pips = 0
    max_sl_pips = 0

    # Expectancy breakdown (simplified)
    exp_tp1_pct = (num_final_tp1 / total_trades * 100) if total_trades > 0 else 0
    exp_tp1_R = 1.5
    exp_tp1_contrib = 0
    exp_tp2_pct = (num_final_tp2 / total_trades * 100) if total_trades > 0 else 0
    exp_tp2_R = 2.5
    exp_tp2_contrib = 0
    exp_sl_pct = (num_final_sl / total_trades * 100) if total_trades > 0 else 0
    exp_sl_R = -1.0
    exp_sl_contrib = 0



    # Trading windows (disabled for now - simplified version)
    tw_enabled = False
    tw_total_hours = 0
    tw_pct_of_week = 0
    tw_windows_count = 0

    # SL stats (disabled for now - complex feature)
    sl_stats = []

    # Portfolio return percentage (simplified)
    strategy_return_pct = (total_pnl / 10000 * 100) if total_pnl != 0 else 0  # Assuming 10k starting capital
    market_return_pct = 0  # Buy & Hold not computed in simplified version
    outperformance = strategy_return_pct - market_return_pct

    # Hourly/Daily stats (disabled for now - complex feature)
    hourly_stats = []
    daily_stats = []

    # 8. Generate HTML (template starts below)

    # 8. Generate HTML from external template (token replacement)
    template_file = Path('templates/visualization_complete.html.j2')
    if not template_file.exists():
        raise FileNotFoundError(f"Template not found: {template_file}")

    def _render_tokens(template_str: str, mapping: dict) -> str:
        for k, v in mapping.items():
            template_str = template_str.replace(k, str(v))
        return template_str

    # Build visualization payload (single contract passed to template)
    payload = {
        'candles': candles,
        'rectangles': rectangles,
        'markers': serialized.get('markers', []),
        'bb_upper': bb_upper,
        'bb_middle': bb_middle,
        'bb_lower': bb_lower,
        'rsi': rsi_data,
        'trades': trade_times,
        'heatmaps': heatmap_assets,
        'has_rsi': bool(rsi_data),
    }
    # JSON payload embedded in HTML (avoid </script> breakage)
    payload_json = json.dumps(payload, ensure_ascii=False)
    payload_json = payload_json.replace('</', '<\\/')


    # Template tokens
    pnl_net_brut_label = "(net)" if portfolio_pnl_with_commissions is not None else "(brut)"
    pnl_brut_line = ''
    pnl_brut_line_stats = ''
    net_info_line = ''
    if portfolio_pnl_with_commissions is not None:
        pnl_brut_line = f'<div style="font-size: 0.65em; color: #888; margin-top: 2px;">Brut: ${total_pnl_brut:.2f}</div>'
        pnl_brut_line_stats = f'<div class="stats-row" style="font-size: 0.85em; color: #888;"><span>Brut (avant comm.):</span><span class="stat-value-large">${total_pnl_brut:+.2f}</span></div>'
        net_info_line = '<div style="text-align: center; color: #888; font-size: 0.85em; margin-top: 10px; padding: 8px; background: rgba(0,0,0,0.2); border-radius: 4px;">ℹ️ Toutes les statistiques (Avg Win/Loss, Profit Factor, Expectancy) sont calculées avec le PnL NET (après commissions)</div>'

    tokens = {
        "@@SYMBOL@@": symbol,
        "@@TIMEFRAME@@": timeframe,
        "@@STRATEGY_NAME@@": strategy_name,

        "@@TOTAL_TRADES@@": total_trades,
        "@@WINS@@": wins,
        "@@LOSSES@@": losses,
        "@@SCRATCHES@@": scratches,
        "@@WIN_RATE@@": f"{win_rate:.1f}%",
        "@@WIN_RATE_CLASS@@": "green" if win_rate >= 50 else "red",
        "@@EXPECTANCY_CLASS@@": "green" if expectancy_R > 0 else "red",
        "@@TOTAL_PNL_CLASS@@": "green" if total_pnl > 0 else "red",

        "@@EXPECTANCY_R@@": f"{expectancy_R:.2f}R",
        "@@EXPECTANCY_DOLLARS@@": f"{expectancy_dollars:.2f} per trade",

        "@@PNL_NET_BRUT_LABEL@@": pnl_net_brut_label,
        "@@PNL_BRUT_LINE@@": pnl_brut_line,
        "@@PNL_BRUT_LINE_STATS@@": pnl_brut_line_stats,
        "@@NET_INFO_LINE@@": net_info_line,

        "@@TOTAL_PNL@@": f"{total_pnl:.2f}",
        # Tokens manquants pour les classes CSS
        "@@TOTAL_PNL_BRUT@@": f"{total_pnl_brut:.2f}",
        "@@WINRATE_CLASS@@": "stat-green" if win_rate >= 50 else "stat-red",
        "@@EXPECTANCY_CLASS@@": "stat-green" if expectancy_dollars > 0 else "stat-red",
        "@@PNL_CLASS@@": "stat-green" if total_pnl > 0 else "stat-red",
        "@@PF_CLASS@@": "stat-green" if profit_factor > 1 else "stat-red",
        "@@STRAT_RETURN_CLASS@@": "stat-green" if strategy_return_pct > 0 else "stat-red",
        "@@MKT_RETURN_CLASS@@": "stat-green" if market_return_pct > 0 else "stat-red",
        "@@OUTPERF_CLASS@@": "stat-green" if outperformance > 0 else "stat-red",

        # Tokens pour PnL signé
        "@@TOTAL_PNL_SIGNED@@": f"{total_pnl:+.2f}",
        "@@TOTAL_PNL_BRUT_SIGNED@@": f"{total_pnl_brut:+.2f}",

        # Tokens pour affichage conditionnel
        "@@BRUT_LINE_DISPLAY@@": "block" if portfolio_pnl_with_commissions is not None else "none",
        "@@NET_INFO_DISPLAY@@": "block" if portfolio_pnl_with_commissions is not None else "none",
        "@@RSI_PANEL_DISPLAY@@": "" if len(rsi_data) > 0 else "none",

        # Token pour message outperformance
        "@@OUTPERF_MSG@@": "✅ Stratégie surperforme le marché" if outperformance > 0 else "⚠️ Marché surperforme la stratégie",
        "@@PNL_NET_LABEL@@": "(net)" if portfolio_pnl_with_commissions is not None else "(brut)",
        "@@PNL_BRUT_BLOCK@@": (f"<div style=\"font-size: 0.65em; color: #888; margin-top: 2px;\">Brut: ${total_pnl_brut:.2f}</div>" if portfolio_pnl_with_commissions is not None else ""),
        "@@AVG_WIN@@": f"{avg_win:.2f}",
        "@@AVG_LOSS@@": f"{avg_loss:.2f}",
        "@@AVG_WIN_SIGNED@@": f"+{avg_win:.2f}",
        "@@PROFIT_FACTOR@@": f"{profit_factor:.2f}",

        "@@NUM_FINAL_SL@@": num_final_sl,
        "@@NUM_FINAL_BE@@": num_final_be,
        "@@NUM_REACHED_TP1@@": num_reached_tp1,
        "@@NUM_REACHED_TP2@@": num_reached_tp2,

        "@@STRATEGY_RETURN_PCT@@": f"{strategy_return_pct:+.2f}%",
        "@@MARKET_RETURN_PCT@@": f"{market_return_pct:+.2f}%",
        "@@OUTPERFORMANCE@@": f"{outperformance:+.2f}%",

        "@@OUTPERFORMANCE_LABEL@@": "✅ Stratégie surperforme le marché" if outperformance > 0 else "⚠️ Marché surperforme la stratégie",

        "@@WIN_RATE_STATCLASS@@": "stat-green" if win_rate >= 50 else "stat-red",
        "@@PF_STATCLASS@@": "stat-green" if profit_factor > 1 else "stat-red",
        "@@TOTAL_PNL_STATCLASS@@": "stat-green" if total_pnl > 0 else "stat-red",
        "@@STRAT_RETURN_STATCLASS@@": "stat-green" if strategy_return_pct > 0 else "stat-red",
        "@@MARKET_RETURN_STATCLASS@@": "stat-green" if market_return_pct > 0 else "stat-red",
        "@@OUTPERF_STATCLASS@@": "stat-green" if outperformance > 0 else "stat-red",

        "@@MAX_WIN_STREAK@@": max_win_streak,
        "@@MAX_LOSS_STREAK@@": max_loss_streak,
        "@@MIN_SL_PIPS@@": min_sl_pips,
        "@@MAX_SL_PIPS@@": max_sl_pips if max_sl_pips > 0 else "Aucun",

        # Data series JSON
        "@@CANDLES_JSON@@": json.dumps(candles),
        "@@RECTANGLES_JSON@@": json.dumps(rectangles),
        "@@MARKERS_JSON@@": json.dumps(serialized.get("markers", [])),
        "@@PAYLOAD_JSON@@": payload_json,
        "@@BB_UPPER_JSON@@": json.dumps(bb_upper),
        "@@BB_MIDDLE_JSON@@": json.dumps(bb_middle),
        "@@BB_LOWER_JSON@@": json.dumps(bb_lower),
        "@@RSI_JSON@@": json.dumps(rsi_data),
        "@@RSI_SECTION_STYLE@@": "" if len(rsi_data) > 0 else "display:none;",
        "@@TRADING_WINDOWS_CARD@@": "",  # (feature not wired in payload yet)
        "@@TRADES_JSON@@": json.dumps(trade_times),

        # SL table (disabled for now)
        "@@SL_STATS_ROWS@@": "",
        "@@SL_STATS_EMPTY@@": '<p style="text-align: center; color: #888; margin-top: 20px;">Aucune donnée SL disponible</p>',

        # Trading windows (disabled for now)
        "@@TRADING_WINDOWS_BLOCK@@": "",
    }

    template_str = template_file.read_text(encoding='utf-8')
    html = _render_tokens(template_str, tokens)
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
    print(
        f"      TP1 ({num_reached_tp1}) >= TP2 ({num_reached_tp2}): {'✅' if num_reached_tp2 <= num_reached_tp1 else '❌'}")
    print(
        f"      TP1 reached = TP1_final + TP2 + BE: {num_final_tp1} + {num_final_tp2} + {num_final_be} = {num_final_tp1 + num_final_tp2 + num_final_be} (actual: {num_reached_tp1})")
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
            print(
                f"      {sl_label:>12s} pips: {s['expectancy_R']:>6.2f}R (${s['expectancy']:>7.2f}, WR: {s['win_rate']:.1f}%, n={s['count']})")

    print("\n" + "=" * 70 + "\n")

    return output_file


if __name__ == "__main__":
    import sys

    config_file = sys.argv[1] if len(sys.argv) > 1 else 'config_rsi_amplitude.yaml'
    generate_complete_html(config_file)