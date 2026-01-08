"""
Moteur de backtest générique
Charge dynamiquement la stratégie depuis le config
"""

import backtrader as bt
import pandas as pd
import yaml
from datetime import datetime
import sys
import os
import importlib

from costs import SimpleCosts


def load_config(config_path='config_rsi_amplitude.yaml'):
    """Charge la configuration"""
    with open(config_path, 'r', encoding='utf-8') as f:
        config = yaml.safe_load(f)
    return config


def load_data(filepath):
    """Charge les données depuis CSV"""
    try:
        df = pd.read_csv(filepath)
        df.columns = df.columns.str.lower()
        
        # Identifier la colonne de temps
        time_col = None
        for col in ['datetime', 'time', 'timestamp', 'date']:
            if col in df.columns:
                time_col = col
                break
        
        if time_col is None:
            raise ValueError("No time column found")
        
        if time_col != 'datetime':
            df = df.rename(columns={time_col: 'datetime'})
        
        df['datetime'] = pd.to_datetime(df['datetime'])
        df = df.set_index('datetime')
        df = df.sort_index()
        
        required_cols = ['open', 'high', 'low', 'close', 'volume']
        for col in required_cols:
            if col not in df.columns:
                raise ValueError(f"Missing required column: {col}")
        
        return df
        
    except Exception as e:
        print(f"Error loading data: {e}")
        raise


def export_trades_to_csv(strategy, config=None, output_path='output/trades_backtest.csv'):
    """Exporte les trades dans un CSV"""
    
    # Créer le répertoire si nécessaire
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    
    if not hasattr(strategy, 'trades_log'):
        print("❌ Strategy has no trades_log attribute")
        return
    
    if not strategy.trades_log:
        print("⚠️  No trades to export (trades_log is empty)")
        return
    
    trades_df = pd.DataFrame(strategy.trades_log)
    trades_df.to_csv(output_path, index=False)
    print(f"✅ Trades exported to: {output_path}")
    print(f"   Total events logged: {len(trades_df)}")
    print(f"   Columns: {list(trades_df.columns)}")
    
    # Debug: show event types
    if 'event_type' in trades_df.columns:
        print(f"   Event types: {dict(trades_df['event_type'].value_counts())}")


def export_boxes_to_csv(strategy, output_path='output/boxes_log.csv'):
    """Exporte les boxes dans un CSV pour visualisation"""
    
    # Créer le répertoire si nécessaire
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    
    if not hasattr(strategy, 'boxes_log'):
        print("❌ Strategy has no boxes_log attribute")
        return
    
    if not strategy.boxes_log:
        print("⚠️  No boxes to export (boxes_log is empty)")
        return
    
    boxes_df = pd.DataFrame(strategy.boxes_log)
    boxes_df.to_csv(output_path, index=False)
    print(f"✅ Boxes exported to: {output_path}")
    print(f"   Total boxes: {len(boxes_df)}")
    
    # Debug: show box types
    if 'type' in boxes_df.columns:
        print(f"   Box types: {dict(boxes_df['type'].value_counts())}")


def run_backtest(config_file='config_rsi_amplitude.yaml'):
    """Lance le backtest avec chargement dynamique de stratégie"""
    
    print("="*60)
    print("BACKTEST GÉNÉRIQUE - STRATÉGIES MULTIPLES")
    print("="*60)
    
    # 0. Créer et nettoyer output/
    os.makedirs('output', exist_ok=True)
    
    print("\n🧹 Nettoyage output/...")
    for file in os.listdir('output'):
        file_path = os.path.join('output', file)
        try:
            if os.path.isfile(file_path):
                os.unlink(file_path)
        except Exception as e:
            pass
    
    # 1. Charger configuration
    print("\n[1] Loading configuration...")
    config = load_config(config_file)
    print(f"Capital: ${config['capital']}")
    
    # Déterminer stratégie
    strategy_name = config.get('strategy_name', 'RSIAmplitudeStrategy')
    strategy_module = config.get('strategy_module', 'strategy_rsi_amplitude')
    
    print(f"📊 Stratégie: {strategy_name}")
    print(f"📦 Module: strategies.{strategy_module}")
    
    # 2. Importer stratégie dynamiquement
    try:
        # Toujours importer depuis strategies/
        module = importlib.import_module(f'strategies.{strategy_module}')
        StrategyClass = getattr(module, strategy_name)
        
        print(f"✅ Stratégie chargée: {StrategyClass.__name__}\n")
    except Exception as e:
        print(f"❌ Impossible de charger la stratégie: {e}")
        print(f"   Module: strategies.{strategy_module}")
        print(f"   Classe: {strategy_name}")
        sys.exit(1)
    
    # 3. Charger données
    print("[2] Loading data...")
    
    if 'data' in config:
        use_specific = config['data'].get('use_specific_csv_file', False)
        
        if use_specific:
            data_file = config['data'].get('file', 'data/NAS100_3min.csv')
        else:
            symbol = config['data'].get('symbol', 'NAS100')
            timeframe = config['data'].get('timeframe', '3min')
            data_file = f"data/{symbol}_{timeframe}.csv"
    else:
        data_file = config.get('data_file', 'data/NAS100_3min.csv')
    
    print(f"Fichier données: {data_file}")
    
    if not os.path.exists(data_file):
        print(f"❌ Fichier données non trouvé: {data_file}")
        print("\n💡 Lancez: python run_backtest.py")
        sys.exit(1)
    
    df = load_data(data_file)
    
    # 4. Créer Cerebro
    print("\n[3] Initializing Backtrader...")
    cerebro = bt.Cerebro()
    
    # 5. Ajouter données
    df_for_bt = df.reset_index()
    data = bt.feeds.PandasData(
        dataname=df_for_bt,
        datetime='datetime',
        open='open',
        high='high',
        low='low',
        close='close',
        volume='volume',
        openinterest=-1
    )
    cerebro.adddata(data)
    
    # 6. Ajouter stratégie avec params depuis config
    # Gérer ancien format (params à la racine) ET nouveau format (strategy_params)
    if 'strategy_params' in config:
        # Nouveau format
        strategy_params = config['strategy_params']
    else:
        # Ancien format - extraire params connus
        strategy_params = {}
        param_keys = [
            'rsi_period', 'rsi_long_threshold', 'rsi_short_threshold', 'sl_lookback',
            'tp1_rr', 'tp2_rr', 'tp1_ratio', 'tp2_ratio',
            'enable_breakeven', 'breakeven_offset', 'risk_per_trade',
            'min_sl_distance_pips', 'max_sl_distance_pips', 'pip_value',  # ← Ajouté pip_value
            # MACD params
            'macd_fast', 'macd_slow', 'macd_signal', 'ema_period', 'sl_atr_multiplier', 'atr_period',
            # Bollinger params
            'bb_period', 'bb_std', 'volume_ma_period', 'volume_threshold'
        ]
        for key in param_keys:
            if key in config:
                strategy_params[key] = config[key]
    
    print(f"📋 Params stratégie: {len(strategy_params)} paramètres")
    print(f"🔍 DEBUG Params extraits:")
    for k, v in sorted(strategy_params.items()):
        print(f"   {k}: {v}")
    print()
    
    # Ajouter le config complet pour que trading_windows soit accessible
    cerebro.addstrategy(StrategyClass, config=config, **strategy_params)
    
    # 7. Configuration broker
    cerebro.broker.setcash(config['capital'])
    cerebro.broker.set_coc(True)
    cerebro.broker.set_shortcash(True)
    
    # 8. Coûts
    commission = SimpleCosts(commission=config.get('cost_rate', 0.0001))
    cerebro.broker.addcommissioninfo(commission)
    
    # 9. Analyzers
    cerebro.addanalyzer(bt.analyzers.TradeAnalyzer, _name='trades')
    cerebro.addanalyzer(bt.analyzers.DrawDown, _name='drawdown')
    cerebro.addanalyzer(bt.analyzers.Returns, _name='returns')
    cerebro.addanalyzer(bt.analyzers.SharpeRatio, _name='sharpe')
    
    # 10. Lancer
    print("\n[4] Running backtest...")
    print("-"*60)
    
    start_value = cerebro.broker.getvalue()
    print(f'Starting Portfolio Value: ${start_value:.2f}\n')
    
    results = cerebro.run()
    strat = results[0]
    
    end_value = cerebro.broker.getvalue()
    
    print("\n" + "-"*60)
    print(f'Final Portfolio Value: ${end_value:.2f}')
    print(f'Total PnL: ${end_value - start_value:.2f}')
    
    # 11. Analyser résultats
    drawdown_analysis = strat.analyzers.drawdown.get_analysis()
    returns_analysis = strat.analyzers.returns.get_analysis()
    
    print("\n--- Trade Analysis (from strategy logs) ---")
    if hasattr(strat, 'trades_log') and len(strat.trades_log) > 0:
        import pandas as pd
        events_df = pd.DataFrame(strat.trades_log)
        
        # Calculer stats comme dans HTML
        total_trades = len(events_df['trade_id'].unique())
        exit_events = events_df[events_df['event_type'].isin(['SL', 'BE', 'TP1', 'TP2', 'FORCED_CLOSE'])]
        
        # Final exits
        final_exits = exit_events.groupby('trade_id')['event_type'].last()
        num_sl = (final_exits == 'SL').sum()
        num_be = (final_exits == 'BE').sum()
        num_tp1_final = (final_exits == 'TP1').sum()
        num_tp2_final = (final_exits == 'TP2').sum()
        num_forced = (final_exits == 'FORCED_CLOSE').sum()
        
        # Levels reached (wins/losses comme HTML)
        num_tp1_reached = exit_events[exit_events['event_type'] == 'TP1'].groupby('trade_id').size().shape[0]
        num_tp2_reached = exit_events[exit_events['event_type'] == 'TP2'].groupby('trade_id').size().shape[0]
        
        # Wins = trades ayant atteint TP1, Losses = trades fermés au SL
        wins = num_tp1_reached
        losses = num_sl
        win_rate = (wins / total_trades * 100) if total_trades > 0 else 0
        
        # Calculer PnL moyen
        entry_data = events_df[events_df['event_type'] == 'ENTRY'][['trade_id', 'price']].copy()
        entry_data.columns = ['trade_id', 'entry_price']
        exit_data = exit_events.groupby('trade_id').agg({'pnl': 'sum'}).reset_index()
        trade_pnl = entry_data.merge(exit_data, on='trade_id', how='inner')
        
        winning_trades = trade_pnl[trade_pnl['pnl'] > 0]
        losing_trades = trade_pnl[trade_pnl['pnl'] <= 0]
        
        avg_win = winning_trades['pnl'].mean() if len(winning_trades) > 0 else 0
        avg_loss = losing_trades['pnl'].mean() if len(losing_trades) > 0 else 0
        
        print(f"Total trades: {total_trades}")
        print(f"Won: {wins} ({win_rate:.1f}%)")
        print(f"Lost: {losses}")
        if avg_win > 0:
            print(f"Average win: ${avg_win:.2f}")
        if avg_loss < 0:
            print(f"Average loss: ${avg_loss:.2f}")
    else:
        print("No trade data available")
    
    # Exit type stats from strategy logs
    print("\n--- Exit Types ---")
    if hasattr(strat, 'trades_log') and len(strat.trades_log) > 0:
        print(f"SL: {num_sl}")
        print(f"BE: {num_be}")
        print(f"TP1 reached: {num_tp1_reached} (of which {num_tp2_reached} continued to TP2)")
        print(f"TP2 reached: {num_tp2_reached}")
        print(f"TP1 only (no TP2): {num_tp1_final}")
        if num_forced > 0:
            print(f"Forced close: {num_forced}")
    else:
        print("No exit type data available")
    
    print("\n--- Drawdown ---")
    print(f"Max drawdown: ${drawdown_analysis.max.moneydown:.2f} ({drawdown_analysis.max.drawdown:.2f}%)")
    
    print("\n--- Returns ---")
    # returns_analysis est un dict, pas un objet
    if 'rtot' in returns_analysis:
        print(f"Total return: {returns_analysis['rtot'] * 100:.2f}%")
    elif 'rnorm100' in returns_analysis:
        print(f"Total return: {returns_analysis['rnorm100']:.2f}%")
    else:
        print(f"Total return: N/A")
    
    # 12. Export trades
    print("\n[5] Exporting trades...")
    export_trades_to_csv(strat, config)
    
    # Export portfolio stats
    print("\n[5.1] Exporting portfolio stats...")
    portfolio_stats = {
        'start_value': start_value,
        'end_value': end_value,
        'total_pnl': end_value - start_value
    }
    import json
    with open('output/portfolio_stats.json', 'w') as f:
        json.dump(portfolio_stats, f)
    print(f"✅ Portfolio stats exported")
    print(f"   Start: ${start_value:.2f}")
    print(f"   End: ${end_value:.2f}")
    print(f"   PnL (with commissions): ${end_value - start_value:.2f}")
    
    # Export boxes
    print("\n[6] Exporting boxes...")
    export_boxes_to_csv(strat)
    
    # 13. Plot
    print("\n[6] Generating plot...")
    try:
        cerebro.plot(style='candlestick', barup='green', bardown='red')
        print("Plot generated successfully")
    except Exception as e:
        print(f"Could not generate plot: {e}")
    
    print("\n" + "="*60)
    print("BACKTEST COMPLETED")
    print("="*60)


if __name__ == '__main__':
    config_file = sys.argv[1] if len(sys.argv) > 1 else 'config_rsi_amplitude.yaml'
    run_backtest(config_file)
