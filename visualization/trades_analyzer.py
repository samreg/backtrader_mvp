"""
Trades Analyzer Helper

Calcule statistiques et heatmaps depuis trades_backtest.csv
(Pas un indicateur - juste helper pour generate_html_complete.py)
"""

import pandas as pd
import numpy as np
from pathlib import Path
from typing import Dict, Any, Optional


class TradesAnalyzer:
    """
    Analyze trades and compute statistics/heatmaps

    Usage:
        analyzer = TradesAnalyzer('output/trades_backtest.csv')
        stats = analyzer.compute_stats()
        heatmaps = analyzer.compute_heatmaps()
    """

    def __init__(self, trades_file: str = 'output/trades_backtest.csv'):
        """
        Initialize analyzer

        Args:
            trades_file: Path to trades CSV
        """
        self.trades_file = trades_file
        self.trades = None

        if Path(trades_file).exists():
            self.trades = pd.read_csv(trades_file, parse_dates=['datetime'])

            self.df = self.trades  # backward-compat alias
        else:
            self.trades = pd.DataFrame()
            self.df = self.trades  # backward-compat alias

    def compute_stats(self, portfolio_pnl_with_commissions: Optional[float] = None) -> Dict[str, Any]:
        """
        Compute backtest statistics

        Args:
            portfolio_pnl_with_commissions: Real PnL including commissions (optional)

        Returns:
            Dict with stats
        """
        if self.trades is None or len(self.trades) == 0:
            return self._empty_stats()

        trades = self.trades

        # Total trades
        total_trades = len(trades['trade_id'].unique())

        # Exit events
        exit_events = trades[trades['event_type'].isin(['SL', 'BE', 'TP1', 'TP2', 'FORCED_CLOSE'])]

        # Final exit per trade
        final_exit = exit_events.groupby('trade_id')['event_type'].last()
        num_final_sl = (final_exit == 'SL').sum()
        num_final_be = (final_exit == 'BE').sum()
        num_final_tp1 = (final_exit == 'TP1').sum()
        num_final_tp2 = (final_exit == 'TP2').sum()
        num_forced_close = (final_exit == 'FORCED_CLOSE').sum()

        # Trades that reached each level
        num_reached_tp1 = exit_events[exit_events['event_type'] == 'TP1'].groupby('trade_id').size().shape[0]
        num_reached_tp2 = exit_events[exit_events['event_type'] == 'TP2'].groupby('trade_id').size().shape[0]

        # Wins/Losses logic
        # PnL stats
        trade_pnl = exit_events.groupby('trade_id')['pnl'].sum().reset_index()
        total_pnl_brut = trade_pnl['pnl'].sum()

        # Adjust for commissions if provided
        if portfolio_pnl_with_commissions is not None:
            total_commissions = total_pnl_brut - portfolio_pnl_with_commissions

            # Distribute commissions proportionally
            trade_pnl['abs_pnl'] = trade_pnl['pnl'].abs()
            total_abs_pnl = trade_pnl['abs_pnl'].sum()

            if total_abs_pnl > 0:
                trade_pnl['commission'] = (trade_pnl['abs_pnl'] / total_abs_pnl) * total_commissions
                trade_pnl['pnl_net'] = trade_pnl['pnl'] - trade_pnl['commission']
            else:
                trade_pnl['pnl_net'] = trade_pnl['pnl']

            avg_pnl = trade_pnl['pnl_net'].mean()
            total_pnl = portfolio_pnl_with_commissions
        else:
            avg_pnl = trade_pnl['pnl'].mean()
            total_pnl = total_pnl_brut

        # Wins/Losses/Scratches based on final PnL (net if commissions are available)
        pnl_col = "pnl_net" if "pnl_net" in trade_pnl.columns else "pnl"
        pnl_series = trade_pnl[pnl_col].astype(float)

        wins = int((pnl_series > 0).sum())
        losses = int((pnl_series < 0).sum())
        scratches = int((pnl_series == 0).sum())
        win_rate = (wins / total_trades * 100) if total_trades > 0 else 0.0

        # Best/worst trades
        best_trade = trade_pnl['pnl'].max() if len(trade_pnl) > 0 else 0
        worst_trade = trade_pnl['pnl'].min() if len(trade_pnl) > 0 else 0

        # Derived performance metrics (consistent with wins/losses definition)
        avg_win = float(pnl_series[pnl_series > 0].mean()) if wins > 0 else 0.0
        avg_loss = float(abs(pnl_series[pnl_series < 0].mean())) if losses > 0 else 0.0
        gross_profit = float(pnl_series[pnl_series > 0].sum()) if wins > 0 else 0.0
        gross_loss = float(abs(pnl_series[pnl_series < 0].sum())) if losses > 0 else 0.0
        profit_factor = (gross_profit / gross_loss) if gross_loss > 0 else 0.0
        expectancy_dollars = float(pnl_series.mean()) if total_trades > 0 else 0.0

        return {
            'total_trades': total_trades,
            'wins': wins,
            'losses': losses,
            'scratches': scratches,
            'win_rate': round(win_rate, 2),
            'total_pnl': round(total_pnl, 2),
            'avg_pnl': round(avg_pnl, 2),
                        'expectancy_dollars': round(expectancy_dollars, 2),
            'avg_win': round(avg_win, 2),
            'avg_loss': round(avg_loss, 2),
            'profit_factor': round(profit_factor, 2),
'best_trade': round(best_trade, 2),
            'worst_trade': round(worst_trade, 2),
            'num_final_sl': num_final_sl,
            'num_final_be': num_final_be,
            'num_final_tp1': num_final_tp1,
            'num_final_tp2': num_final_tp2,
            'num_forced_close': num_forced_close,
            'num_reached_tp1': num_reached_tp1,
            'num_reached_tp2': num_reached_tp2
        }

    def get_trade_details(self) -> pd.DataFrame:
        """Returns a per-trade table used by heatmaps.

        Columns:
          - trade_id
          - entry_dt (datetime64)
          - dayofweek (Mon=0..Sun=6)
          - hour (0..23)
          - pnl (float): per-trade PnL (derived from EXIT rows in trades_backtest.csv)
        """
        df = self.trades.copy()

        # Entry time per trade (first ENTRY)
        entries = df[df["event_type"] == "ENTRY"].copy()
        if entries.empty:
            return pd.DataFrame(columns=["trade_id", "entry_dt", "dayofweek", "hour", "pnl"])

        entries.sort_values("datetime", inplace=True)
        entry_time = entries.groupby("trade_id", as_index=False).first()[["trade_id", "datetime"]]
        entry_time = entry_time.rename(columns={"datetime": "entry_dt"})

        # Per-trade pnl from exits (sum of pnl on EXIT rows)
        exits = df[df["event_type"].isin(["SL", "TP1", "TP2", "BE", "FORCED_CLOSE"])].copy()
        if exits.empty:
            entry_time["pnl"] = 0.0
        else:
            pnl = exits.groupby("trade_id", as_index=False)["pnl"].sum()
            entry_time = entry_time.merge(pnl, on="trade_id", how="left")
            entry_time["pnl"] = entry_time["pnl"].fillna(0.0)

        entry_time["dayofweek"] = entry_time["entry_dt"].dt.dayofweek.astype(int)
        entry_time["hour"] = entry_time["entry_dt"].dt.hour.astype(int)
        return entry_time


    def _empty_stats(self) -> Dict[str, Any]:
        """Return empty stats structure"""
        return {
            'total_trades': 0,
            'wins': 0,
            'losses': 0,
            'scratches': 0,
            'win_rate': 0.0,
            'total_pnl': 0.0,
            'avg_pnl': 0.0,
            'best_trade': 0.0,
            'worst_trade': 0.0,
            'num_final_sl': 0,
            'num_final_be': 0,
            'num_final_tp1': 0,
            'num_final_tp2': 0,
            'num_forced_close': 0,
            'num_reached_tp1': 0,
            'num_reached_tp2': 0
        }

    def _empty_heatmaps(self) -> Dict[str, Any]:
        """Return empty heatmaps structure"""
        hour_heatmap = [{'hour': h, 'count': 0, 'pnl': 0.0} for h in range(24)]
        day_names = ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday', 'Sunday']
        day_heatmap = [{'day': d, 'count': 0, 'pnl': 0.0} for d in day_names]

        return {
            'hour_heatmap': hour_heatmap,
            'day_heatmap': day_heatmap
        }