"""
Heatmaps & charts generation for the HTML report.

Goal:
- Keep generate_html_complete.py focused on *payload + template rendering*
- Keep plotting code isolated here (matplotlib only; no seaborn dependency)

Inputs:
- TradesAnalyzer (visualization/trades_analyzer.py)
- Uses analyzer.get_trade_details() to build day/hour pivots

Outputs:
- PNG files in output_dir
- A dict of produced asset filenames for the HTML payload

PATCH: Ajout de 3 nouvelles heatmaps:
- Expectancy x Count (bulles proportionnelles au nombre de trades)
- Profit Factor par jour/heure
- Max Drawdown par jour/heure
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Dict, Optional, Tuple, Any

import numpy as np
import pandas as pd

# matplotlib only (Agg backend)
import matplotlib

matplotlib.use("Agg")  # noqa: E402
import matplotlib.pyplot as plt  # noqa: E402

DAY_LABELS_FR = ["Lun", "Mar", "Mer", "Jeu", "Ven", "Sam", "Dim"]


@dataclass(frozen=True)
class HeatmapAsset:
    key: str
    filename: str
    title: str


def _ensure_dir(path: Path) -> None:
    path.mkdir(parents=True, exist_ok=True)


def _annotate_cells(ax: Any, data: np.ndarray, fmt: str) -> None:
    # annotate each cell with its value (skip NaNs)
    nrows, ncols = data.shape
    for i in range(nrows):
        for j in range(ncols):
            v = data[i, j]
            if np.isnan(v):
                continue
            ax.text(j, i, format(v, fmt), ha="center", va="center", fontsize=7, color="black")


def _plot_heatmap(
        pivot: pd.DataFrame,
        *,
        title: str,
        cbar_label: str,
        cmap: str,
        center: Optional[float] = None,
        vmin: Optional[float] = None,
        vmax: Optional[float] = None,
        annotate_fmt: Optional[str] = None,
        output_file: Path,
) -> None:
    data = pivot.to_numpy(dtype=float)

    fig, ax = plt.subplots(figsize=(14, 7))
    if center is not None and (vmin is None or vmax is None):
        # symmetric bounds around center (commonly 0)
        finite = data[np.isfinite(data)]
        if finite.size:
            m = np.max(np.abs(finite - center))
            vmin = center - m
            vmax = center + m

    im = ax.imshow(data, aspect="auto", cmap=cmap, vmin=vmin, vmax=vmax)

    ax.set_title(title, fontsize=14, fontweight="bold", pad=15)
    ax.set_xlabel("Heure de la journée", fontsize=11)
    ax.set_ylabel("Jour de la semaine", fontsize=11)

    ax.set_xticks(range(pivot.shape[1]))
    ax.set_xticklabels([str(c) for c in pivot.columns], rotation=0, fontsize=8)

    ax.set_yticks(range(pivot.shape[0]))
    ax.set_yticklabels(DAY_LABELS_FR[: pivot.shape[0]], rotation=0, fontsize=10)

    # grid lines
    ax.set_xticks(np.arange(-0.5, pivot.shape[1], 1), minor=True)
    ax.set_yticks(np.arange(-0.5, pivot.shape[0], 1), minor=True)
    ax.grid(which="minor", color="white", linestyle="-", linewidth=0.5, alpha=0.2)
    ax.tick_params(which="minor", bottom=False, left=False)

    cbar = fig.colorbar(im, ax=ax)
    cbar.set_label(cbar_label)

    if annotate_fmt is not None:
        _annotate_cells(ax, data, annotate_fmt)

    fig.tight_layout()
    fig.savefig(output_file, dpi=150, bbox_inches="tight")
    plt.close(fig)


def _build_day_hour_grid(trade_details: pd.DataFrame) -> pd.DataFrame:
    # Ensure full grid 7x24 with NaNs when no trades
    rows = []
    for day in range(7):
        for hour in range(24):
            rows.append({"day": day, "hour": hour})
    base = pd.DataFrame(rows)
    return base.merge(trade_details, on=["day", "hour"], how="left")


def _plot_expectancy_count_heatmap(
        exp_pivot: pd.DataFrame,
        count_pivot: pd.DataFrame,
        *,
        title: str,
        output_file: Path,
) -> None:
    """
    Heatmap avec expectancy en couleur ET taille de bulle proportionnelle au nombre de trades
    """
    fig, ax = plt.subplots(figsize=(16, 8))

    exp_data = exp_pivot.to_numpy(dtype=float)
    count_data = count_pivot.to_numpy(dtype=float)

    # Color map basée sur expectancy
    finite_exp = exp_data[np.isfinite(exp_data)]
    if finite_exp.size:
        vmax = np.max(np.abs(finite_exp))
        vmin = -vmax
    else:
        vmax = 1.0
        vmin = -1.0

    # Background heatmap (expectancy)
    im = ax.imshow(exp_data, aspect="auto", cmap="RdYlGn", vmin=vmin, vmax=vmax, alpha=0.3)

    # Scatter avec taille proportionnelle au count
    max_count = np.nanmax(count_data) if np.isfinite(count_data).any() else 1
    for i in range(exp_pivot.shape[0]):
        for j in range(exp_pivot.shape[1]):
            exp_val = exp_data[i, j]
            count_val = count_data[i, j]
            if np.isnan(exp_val) or np.isnan(count_val):
                continue

            # Taille de bulle proportionnelle
            size = (count_val / max_count) * 2000 if max_count > 0 else 100

            # Couleur basée sur expectancy
            if exp_val > 0:
                color = plt.cm.RdYlGn(0.75)
            elif exp_val < 0:
                color = plt.cm.RdYlGn(0.25)
            else:
                color = plt.cm.RdYlGn(0.5)

            ax.scatter(j, i, s=size, c=[color], alpha=0.6, edgecolors='black', linewidths=1.5)

            # Annotation: expectancy
            ax.text(j, i - 0.15, f"{exp_val:.1f}", ha="center", va="center", fontsize=8, fontweight='bold',
                    color='black')
            # Annotation: count
            ax.text(j, i + 0.15, f"n={int(count_val)}", ha="center", va="center", fontsize=7, color='#555')

    ax.set_title(title, fontsize=14, fontweight="bold", pad=15)
    ax.set_xlabel("Heure de la journée", fontsize=11)
    ax.set_ylabel("Jour de la semaine", fontsize=11)

    ax.set_xticks(range(exp_pivot.shape[1]))
    ax.set_xticklabels([str(c) for c in exp_pivot.columns], rotation=0, fontsize=8)

    ax.set_yticks(range(exp_pivot.shape[0]))
    ax.set_yticklabels(DAY_LABELS_FR[: exp_pivot.shape[0]], rotation=0, fontsize=10)

    # Grid lines
    ax.set_xticks(np.arange(-0.5, exp_pivot.shape[1], 1), minor=True)
    ax.set_yticks(np.arange(-0.5, exp_pivot.shape[0], 1), minor=True)
    ax.grid(which="minor", color="white", linestyle="-", linewidth=0.5, alpha=0.3)
    ax.tick_params(which="minor", bottom=False, left=False)

    cbar = fig.colorbar(im, ax=ax)
    cbar.set_label("Expectancy ($)")

    fig.tight_layout()
    fig.savefig(output_file, dpi=150, bbox_inches="tight")
    plt.close(fig)


def generate_temporal_heatmaps(
        trade_details: pd.DataFrame,
        output_dir: Path,
) -> Dict[str, HeatmapAsset]:
    """
    Generates:
      - frequency (count)
      - winrate (%)
      - avg pnl
      - combined score
      - expectancy ($)

    Expects trade_details columns:
      - dayofweek (0=Mon)
      - hour (0-23)
      - pnl (float) : per-trade net PnL
    """
    _ensure_dir(output_dir)

    if trade_details.empty:
        return {}

    # normalize columns
    td = trade_details.copy()
    td["day"] = td["dayofweek"].astype(int)
    td["hour"] = td["hour"].astype(int)
    td["pnl"] = td["pnl"].astype(float)

    # aggregate per day/hour
    grp = td.groupby(["day", "hour"], as_index=False).agg(
        count=("pnl", "size"),
        winrate=("pnl", lambda s: float((s > 0).mean() * 100.0) if len(s) else np.nan),
        avg_pnl=("pnl", "mean"),
        expectancy=("pnl", "mean"),  # per-trade expectancy is mean pnl for that bucket
    )

    # full grid
    full = _build_day_hour_grid(grp)

    # pivots
    freq_pivot = full.pivot(index="day", columns="hour", values="count")
    wr_pivot = full.pivot(index="day", columns="hour", values="winrate")
    pnl_pivot = full.pivot(index="day", columns="hour", values="avg_pnl")
    exp_pivot = full.pivot(index="day", columns="hour", values="expectancy")

    # combined score: (winrate-50) + avg_pnl/10 (same heuristic as legacy script)
    score = full.copy()
    score["score"] = (score["winrate"] - 50.0) + (score["avg_pnl"] / 10.0)
    score_pivot = score.pivot(index="day", columns="hour", values="score")

    assets: Dict[str, HeatmapAsset] = {}

    # 1) Frequency
    f1 = output_dir / "heatmap_1_frequency.png"
    _plot_heatmap(
        freq_pivot,
        title="Fréquence des Trades par Jour et Heure",
        cbar_label="Nombre de trades",
        cmap="YlOrRd",
        annotate_fmt=".0f",
        output_file=f1,
    )
    assets["frequency"] = HeatmapAsset("frequency", f1.name, "Fréquence des Trades")

    # 2) Winrate
    f2 = output_dir / "heatmap_2_winrate.png"
    _plot_heatmap(
        wr_pivot,
        title="Win Rate par Jour et Heure",
        cbar_label="Win Rate (%)",
        cmap="RdYlGn",
        center=50,
        vmin=0,
        vmax=100,
        annotate_fmt=".0f",
        output_file=f2,
    )
    assets["winrate"] = HeatmapAsset("winrate", f2.name, "Taux de Réussite (%)")

    # 3) Avg PnL
    f3 = output_dir / "heatmap_3_pnl.png"
    finite = pnl_pivot.to_numpy(dtype=float)
    finite = finite[np.isfinite(finite)]
    vmax = float(np.max(np.abs(finite))) if finite.size else 1.0
    _plot_heatmap(
        pnl_pivot,
        title="PnL Moyen par Jour et Heure",
        cbar_label="PnL Moyen ($)",
        cmap="RdYlGn",
        center=0,
        vmin=-vmax,
        vmax=vmax,
        annotate_fmt=".1f",
        output_file=f3,
    )
    assets["pnl"] = HeatmapAsset("pnl", f3.name, "PnL Moyen")

    # 4) Combined score
    f4 = output_dir / "heatmap_4_combined.png"
    finite = score_pivot.to_numpy(dtype=float)
    finite = finite[np.isfinite(finite)]
    vmax = float(np.max(np.abs(finite))) if finite.size else 1.0
    _plot_heatmap(
        score_pivot,
        title="Score Combiné (WR + PnL) par Jour et Heure",
        cbar_label="Score Combiné",
        cmap="RdYlGn",
        center=0,
        vmin=-vmax,
        vmax=vmax,
        annotate_fmt=".1f",
        output_file=f4,
    )
    assets["combined"] = HeatmapAsset("combined", f4.name, "Vue d'Ensemble")

    # 5) Expectancy
    f5 = output_dir / "heatmap_5_expectancy.png"
    finite = exp_pivot.to_numpy(dtype=float)
    finite = finite[np.isfinite(finite)]
    vmax = float(np.max(np.abs(finite))) if finite.size else 1.0
    _plot_heatmap(
        exp_pivot,
        title="Expectancy par Jour et Heure",
        cbar_label="Expectancy ($)",
        cmap="RdYlGn",
        center=0,
        vmin=-vmax,
        vmax=vmax,
        annotate_fmt=".1f",
        output_file=f5,
    )
    assets["expectancy"] = HeatmapAsset("expectancy", f5.name, "Expectancy")

    return assets


def generate_advanced_heatmaps(
        trade_details: pd.DataFrame,
        output_dir: Path,
) -> Dict[str, HeatmapAsset]:
    """
    Génère 3 heatmaps additionnelles:
    - Expectancy x Count (scatter avec taille de bulle = nb trades)
    - Profit Factor par jour/heure
    - Max Drawdown par jour/heure
    """
    _ensure_dir(output_dir)

    if trade_details.empty:
        return {}

    # Normalize columns
    td = trade_details.copy()
    td["day"] = td["dayofweek"].astype(int)
    td["hour"] = td["hour"].astype(int)
    td["pnl"] = td["pnl"].astype(float)

    # Aggregate per day/hour
    grp = td.groupby(["day", "hour"], as_index=False).agg(
        count=("pnl", "size"),
        total_pnl=("pnl", "sum"),
        expectancy=("pnl", "mean"),
        wins=("pnl", lambda s: (s > 0).sum()),
        losses=("pnl", lambda s: (s < 0).sum()),
        gross_profit=("pnl", lambda s: s[s > 0].sum() if (s > 0).any() else 0.0),
        gross_loss=("pnl", lambda s: abs(s[s < 0].sum()) if (s < 0).any() else 0.0),
    )

    # Calculate Profit Factor
    grp["profit_factor"] = grp.apply(
        lambda row: row["gross_profit"] / row["gross_loss"] if row["gross_loss"] > 0 else np.nan,
        axis=1
    )

    # Calculate Max Drawdown per day/hour (running cumulative)
    grp["max_drawdown"] = 0.0
    for idx, row in grp.iterrows():
        # Get all trades for this day/hour
        trades = td[(td["day"] == row["day"]) & (td["hour"] == row["hour"])].sort_values("pnl")
        cumsum = trades["pnl"].cumsum()
        running_max = cumsum.expanding().max()
        drawdown = running_max - cumsum
        grp.at[idx, "max_drawdown"] = drawdown.max() if len(drawdown) > 0 else 0.0

    # Full grid
    full = _build_day_hour_grid(grp)

    # Pivots
    exp_pivot = full.pivot(index="day", columns="hour", values="expectancy")
    count_pivot = full.pivot(index="day", columns="hour", values="count")
    pf_pivot = full.pivot(index="day", columns="hour", values="profit_factor")
    dd_pivot = full.pivot(index="day", columns="hour", values="max_drawdown")

    assets: Dict[str, HeatmapAsset] = {}

    # 1) Expectancy x Count (scatter avec bulles)
    f1 = output_dir / "heatmap_6_expectancy_count.png"
    _plot_expectancy_count_heatmap(
        exp_pivot,
        count_pivot,
        title="Expectancy x Nombre de Trades (Jour/Heure)",
        output_file=f1,
    )
    assets["expectancy_count"] = HeatmapAsset("expectancy_count", f1.name, "Expectancy x Count")

    # 2) Profit Factor
    f2 = output_dir / "heatmap_7_profit_factor.png"
    finite = pf_pivot.to_numpy(dtype=float)
    finite = finite[np.isfinite(finite)]
    vmax = float(np.max(finite)) if finite.size else 3.0
    _plot_heatmap(
        pf_pivot,
        title="Profit Factor par Jour et Heure",
        cbar_label="Profit Factor",
        cmap="RdYlGn",
        center=1.0,
        vmin=0,
        vmax=vmax,
        annotate_fmt=".2f",
        output_file=f2,
    )
    assets["profit_factor"] = HeatmapAsset("profit_factor", f2.name, "Profit Factor")

    # 3) Max Drawdown
    f3 = output_dir / "heatmap_8_max_drawdown.png"
    finite = dd_pivot.to_numpy(dtype=float)
    finite = finite[np.isfinite(finite)]
    vmax = float(np.max(finite)) if finite.size else 100.0
    _plot_heatmap(
        dd_pivot,
        title="Max Drawdown par Jour et Heure",
        cbar_label="Max Drawdown ($)",
        cmap="Reds",
        vmin=0,
        vmax=vmax,
        annotate_fmt=".1f",
        output_file=f3,
    )
    assets["max_drawdown"] = HeatmapAsset("max_drawdown", f3.name, "Max Drawdown")

    return assets


def generate_all(analyzer: Any, output_dir: str | Path = "output") -> Dict[str, Any]:
    """
    Main entry point used by generate_html_complete.py

    Returns a payload-ready dict:
      {
        "assets": {key: {"filename": "...", "title": "..."}},
      }
    """
    out = Path(output_dir)
    trade_details = analyzer.get_trade_details()

    # Génère les 5 heatmaps de base
    assets = generate_temporal_heatmaps(trade_details, out)

    # Génère les 3 nouvelles heatmaps avancées
    advanced_assets = generate_advanced_heatmaps(trade_details, out)
    assets.update(advanced_assets)

    return {
        "assets": {k: {"filename": v.filename, "title": v.title} for k, v in assets.items()}
    }