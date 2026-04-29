"""
analysis/graphs.py — All matplotlib/seaborn plotting functions
"""
from __future__ import annotations
import matplotlib
import os as _os
if not _os.environ.get("MPLBACKEND"):
    try:
        matplotlib.use("TkAgg")
    except Exception:
        matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.gridspec as gridspec
import seaborn as sns
import numpy as np
import pandas as pd
from typing import Optional, List, Dict, Any

from data.repository import COL_LABELS

# ── Style ──────────────────────────────────────────────────────────────
PALETTE = {
    "bg":        "#0D1117",
    "surface":   "#161B22",
    "border":    "#30363D",
    "accent1":   "#F78166",
    "accent2":   "#79C0FF",
    "accent3":   "#56D364",
    "accent4":   "#E3B341",
    "text":      "#E6EDF3",
    "subtext":   "#8B949E",
}

def _apply_dark_style():
    plt.rcParams.update({
        "figure.facecolor":  PALETTE["bg"],
        "axes.facecolor":    PALETTE["surface"],
        "axes.edgecolor":    PALETTE["border"],
        "axes.labelcolor":   PALETTE["text"],
        "axes.titlecolor":   PALETTE["text"],
        "text.color":        PALETTE["text"],
        "xtick.color":       PALETTE["subtext"],
        "ytick.color":       PALETTE["subtext"],
        "grid.color":        PALETTE["border"],
        "grid.linestyle":    "--",
        "grid.alpha":        0.5,
        "legend.facecolor":  PALETTE["surface"],
        "legend.edgecolor":  PALETTE["border"],
        "font.family":       "monospace",
        "axes.spines.top":   False,
        "axes.spines.right": False,
    })

_apply_dark_style()

_lbl = lambda col: COL_LABELS.get(col, col)


# ──────────────────────────────────────────────────────────────────────
# 1. Custom X-Y scatter + regression overlay
# ──────────────────────────────────────────────────────────────────────

def scatter_with_regression(
    df: pd.DataFrame,
    x_col: str,
    y_col: str,
    reg_result: Optional[Dict[str, Any]] = None,
    color_col: Optional[str] = None,
    title: Optional[str] = None,
):
    fig, ax = plt.subplots(figsize=(9, 5))
    fig.patch.set_facecolor(PALETTE["bg"])

    if color_col and color_col in df.columns:
        vals = pd.to_numeric(df[color_col], errors="coerce")
        sc = ax.scatter(
            df[x_col], df[y_col],
            c=vals, cmap="plasma", s=80, zorder=3, edgecolors="none", alpha=0.9
        )
        cbar = fig.colorbar(sc, ax=ax)
        cbar.set_label(_lbl(color_col), color=PALETTE["text"])
        cbar.ax.yaxis.set_tick_params(color=PALETTE["subtext"])
    else:
        ax.scatter(df[x_col], df[y_col],
                   color=PALETTE["accent2"], s=80, zorder=3, edgecolors="none", alpha=0.9)

    if reg_result and "error" not in reg_result:
        ax.plot(
            reg_result["x_curve"], reg_result["y_curve"],
            color=PALETTE["accent1"], lw=2, label=f"Fit (R²={reg_result['r2']:.3f})",
            zorder=4
        )
        ax.legend()
        # Annotation box
        stats_txt = (
            f"R² = {reg_result['r2']:.4f}\n"
            f"Adj R² = {reg_result['adj_r2']:.4f}\n"
            f"RMSE = {reg_result['rmse']:.3f}\n"
            f"n = {reg_result['n']}"
        )
        ax.text(0.97, 0.05, stats_txt, transform=ax.transAxes,
                fontsize=8, verticalalignment="bottom", horizontalalignment="right",
                bbox=dict(boxstyle="round,pad=0.4", facecolor=PALETTE["surface"],
                          edgecolor=PALETTE["border"], alpha=0.9),
                color=PALETTE["text"])

    ax.set_xlabel(_lbl(x_col))
    ax.set_ylabel(_lbl(y_col))
    ax.set_title(title or f"{_lbl(y_col)}  vs  {_lbl(x_col)}", pad=12, fontsize=12)
    ax.grid(True)
    fig.tight_layout()
    plt.show()


# ──────────────────────────────────────────────────────────────────────
# 2. Bar chart — categorical X (e.g. haul distance) vs numeric Y
# ──────────────────────────────────────────────────────────────────────

def bar_chart(
    df: pd.DataFrame,
    x_col: str,
    y_col: str,
    title: Optional[str] = None,
    group_col: Optional[str] = None,
):
    fig, ax = plt.subplots(figsize=(10, 5))
    fig.patch.set_facecolor(PALETTE["bg"])

    if group_col and group_col in df.columns:
        groups = df[group_col].unique()
        width = 0.8 / len(groups)
        x_vals = sorted(df[x_col].unique())
        x_pos = np.arange(len(x_vals))
        colors = [PALETTE["accent1"], PALETTE["accent2"], PALETTE["accent3"], PALETTE["accent4"]]
        for i, g in enumerate(groups):
            sub = df[df[group_col] == g]
            means = [sub[sub[x_col] == xv][y_col].mean() for xv in x_vals]
            ax.bar(x_pos + i * width, means, width=width * 0.9,
                   color=colors[i % len(colors)], label=str(g), alpha=0.9)
        ax.set_xticks(x_pos + (len(groups) - 1) * width / 2)
        ax.set_xticklabels([str(v) for v in x_vals])
        ax.legend(title=_lbl(group_col))
    else:
        grp = df.groupby(x_col)[y_col].mean().reset_index().sort_values(x_col)
        colors = [PALETTE["accent2"]] * len(grp)
        bars = ax.bar(grp[x_col].astype(str), grp[y_col],
                      color=colors, width=0.55, alpha=0.9, edgecolor="none")
        # Value labels on bars
        for bar, val in zip(bars, grp[y_col]):
            ax.text(bar.get_x() + bar.get_width() / 2,
                    bar.get_height() + 0.01 * grp[y_col].max(),
                    f"{val:.1f}", ha="center", va="bottom",
                    fontsize=8, color=PALETTE["text"])

    ax.set_xlabel(_lbl(x_col))
    ax.set_ylabel(_lbl(y_col))
    ax.set_title(title or f"{_lbl(y_col)}  by  {_lbl(x_col)}", pad=12, fontsize=12)
    ax.grid(True, axis="y")
    fig.tight_layout()
    plt.show()


# ──────────────────────────────────────────────────────────────────────
# 3. Production overview dashboard (multi-panel)
# ──────────────────────────────────────────────────────────────────────

def production_dashboard(df: pd.DataFrame):
    if df.empty:
        return
    fig = plt.figure(figsize=(14, 8))
    fig.patch.set_facecolor(PALETTE["bg"])
    gs = gridspec.GridSpec(2, 3, figure=fig, hspace=0.45, wspace=0.38)

    panels = [
        (0, 0, "distance_km_one_way", "tph_total", "Haul Distance vs Fleet TPH", "scatter"),
        (0, 1, "shovel_cycle_time_sec", "tph_per_shovel", "Cycle Time vs TPH/Shovel", "scatter"),
        (0, 2, "n_dumpers", "tph_total", "No. of Dumpers vs Fleet TPH", "bar"),
        (1, 0, "distance_km_one_way", "production_per_shift_t", "Haul Distance vs Shift Prod.", "bar"),
        (1, 1, "fleet_efficiency_pct", "tph_total", "Fleet Efficiency vs Total TPH", "scatter"),
        (1, 2, "match_ratio", "production_per_shift_t", "Match Ratio vs Shift Production", "scatter"),
    ]

    accent_cycle = [PALETTE["accent1"], PALETTE["accent2"],
                    PALETTE["accent3"], PALETTE["accent4"]]

    for row, col, xcol, ycol, ttl, kind in panels:
        ax = fig.add_subplot(gs[row, col])
        ax.set_facecolor(PALETTE["surface"])
        for spine in ax.spines.values():
            spine.set_edgecolor(PALETTE["border"])
        ax.tick_params(colors=PALETTE["subtext"], labelsize=7)
        ax.xaxis.label.set_color(PALETTE["text"])
        ax.yaxis.label.set_color(PALETTE["text"])
        ax.title.set_color(PALETTE["text"])
        ax.grid(True, color=PALETTE["border"], linestyle="--", alpha=0.5)

        sub = df[[xcol, ycol]].dropna()
        if sub.empty:
            ax.set_title(ttl, fontsize=8)
            continue

        c = accent_cycle[row * 3 + col % 3]
        if kind == "scatter":
            ax.scatter(sub[xcol], sub[ycol], color=c, s=40, alpha=0.85, edgecolors="none")
            # Trend line
            if len(sub) >= 2:
                m, b, *_ = np.polyfit(sub[xcol], sub[ycol], 1), 0
                xs = np.linspace(sub[xcol].min(), sub[xcol].max(), 100)
                ax.plot(xs, np.polyval(m, xs), color=PALETTE["accent4"], lw=1.2, alpha=0.7)
        else:
            grp = sub.groupby(xcol)[ycol].mean().reset_index()
            ax.bar(grp[xcol].astype(str), grp[ycol], color=c, alpha=0.85, width=0.55)

        ax.set_xlabel(_lbl(xcol), fontsize=7)
        ax.set_ylabel(_lbl(ycol), fontsize=7)
        ax.set_title(ttl, fontsize=8, pad=6)

    fig.suptitle("Fleet Production Dashboard", fontsize=14,
                 color=PALETTE["text"], y=0.98, fontweight="bold")
    plt.show()


# ──────────────────────────────────────────────────────────────────────
# 4. Haul distance bar chart suite
# ──────────────────────────────────────────────────────────────────────

def haul_distance_analysis(df: pd.DataFrame):
    if df.empty:
        return
    y_cols = ["tph_total", "production_per_shift_t",
              "fleet_efficiency_pct", "round_trip_time_min"]
    titles = [
        "Haul Distance vs Fleet Production Rate",
        "Haul Distance vs Shift Production",
        "Haul Distance vs Fleet Efficiency",
        "Haul Distance vs Round-trip Time",
    ]
    fig, axes = plt.subplots(2, 2, figsize=(12, 7))
    fig.patch.set_facecolor(PALETTE["bg"])
    fig.suptitle("Haul Distance Impact Analysis", fontsize=13,
                 color=PALETTE["text"], fontweight="bold")
    colors = [PALETTE["accent1"], PALETTE["accent2"], PALETTE["accent3"], PALETTE["accent4"]]

    for ax, ycol, ttl, clr in zip(axes.ravel(), y_cols, titles, colors):
        ax.set_facecolor(PALETTE["surface"])
        for sp in ax.spines.values():
            sp.set_edgecolor(PALETTE["border"])
        ax.tick_params(colors=PALETTE["subtext"], labelsize=8)
        ax.grid(True, axis="y", color=PALETTE["border"], linestyle="--", alpha=0.4)

        sub = df[["distance_km_one_way", ycol]].dropna()
        if not sub.empty:
            grp = sub.groupby("distance_km_one_way")[ycol].mean().reset_index()
            bars = ax.bar(grp["distance_km_one_way"].astype(str), grp[ycol],
                          color=clr, alpha=0.88, width=0.5)
            for bar, v in zip(bars, grp[ycol]):
                ax.text(bar.get_x() + bar.get_width() / 2,
                        bar.get_height() * 1.01, f"{v:.1f}",
                        ha="center", va="bottom", fontsize=7, color=PALETTE["text"])

        ax.set_xlabel("Haul Distance One-way (km)", fontsize=8, color=PALETTE["text"])
        ax.set_ylabel(_lbl(ycol), fontsize=8, color=PALETTE["text"])
        ax.set_title(ttl, fontsize=9, color=PALETTE["text"], pad=6)

    plt.tight_layout()
    plt.show()


# ──────────────────────────────────────────────────────────────────────
# 5. Productivity vs Production line + scatter
# ──────────────────────────────────────────────────────────────────────

def productivity_vs_production(df: pd.DataFrame):
    if df.empty:
        return
    sub = df[["tph_per_shovel", "tph_total", "production_per_shift_t"]].dropna()
    if sub.empty:
        return

    fig, axes = plt.subplots(1, 2, figsize=(11, 5))
    fig.patch.set_facecolor(PALETTE["bg"])
    fig.suptitle("Productivity vs Production Analysis", fontsize=13,
                 color=PALETTE["text"], fontweight="bold")

    for ax in axes:
        ax.set_facecolor(PALETTE["surface"])
        for sp in ax.spines.values():
            sp.set_edgecolor(PALETTE["border"])
        ax.tick_params(colors=PALETTE["subtext"])
        ax.grid(True, color=PALETTE["border"], linestyle="--", alpha=0.5)

    # Panel 1: TPH per shovel vs total TPH
    ax = axes[0]
    ax.scatter(sub["tph_per_shovel"], sub["tph_total"],
               color=PALETTE["accent2"], s=70, zorder=3, edgecolors="none", alpha=0.9)
    if len(sub) >= 2:
        z = np.polyfit(sub["tph_per_shovel"], sub["tph_total"], 1)
        xs = np.linspace(sub["tph_per_shovel"].min(), sub["tph_per_shovel"].max(), 100)
        ax.plot(xs, np.polyval(z, xs), PALETTE["accent1"], lw=2)
    ax.set_xlabel("Productivity per Shovel (t/h)", color=PALETTE["text"])
    ax.set_ylabel("Total Fleet Production (t/h)", color=PALETTE["text"])
    ax.set_title("Shovel Productivity → Fleet Production", color=PALETTE["text"], fontsize=10)

    # Panel 2: TPH total vs production per shift
    ax = axes[1]
    ax.scatter(sub["tph_total"], sub["production_per_shift_t"],
               color=PALETTE["accent3"], s=70, zorder=3, edgecolors="none", alpha=0.9)
    if len(sub) >= 2:
        z = np.polyfit(sub["tph_total"], sub["production_per_shift_t"], 1)
        xs = np.linspace(sub["tph_total"].min(), sub["tph_total"].max(), 100)
        ax.plot(xs, np.polyval(z, xs), PALETTE["accent4"], lw=2)
    ax.set_xlabel("Total Fleet Production (t/h)", color=PALETTE["text"])
    ax.set_ylabel("Production per Shift (t)", color=PALETTE["text"])
    ax.set_title("Fleet Rate → Shift Production", color=PALETTE["text"], fontsize=10)

    plt.tight_layout()
    plt.show()


# ──────────────────────────────────────────────────────────────────────
# 6. Correlation heat-map
# ──────────────────────────────────────────────────────────────────────

def correlation_heatmap(df: pd.DataFrame, cols: Optional[List[str]] = None):
    if df.empty:
        return
    if cols is None:
        cols = [
            "distance_km_one_way", "shovel_cycle_time_sec", "n_dumpers",
            "dumper_capacity_t", "tph_per_shovel", "tph_total",
            "fleet_efficiency_pct", "round_trip_time_min",
            "production_per_shift_t", "match_ratio"
        ]
    sub = df[[c for c in cols if c in df.columns]].dropna()
    if sub.empty or len(sub) < 2:
        return

    corr = sub.rename(columns=COL_LABELS).corr()

    fig, ax = plt.subplots(figsize=(10, 8))
    fig.patch.set_facecolor(PALETTE["bg"])
    ax.set_facecolor(PALETTE["bg"])

    cmap = sns.diverging_palette(220, 10, as_cmap=True)
    sns.heatmap(
        corr, ax=ax, cmap=cmap, center=0,
        annot=True, fmt=".2f", annot_kws={"size": 7},
        linewidths=0.5, linecolor=PALETTE["border"],
        cbar_kws={"shrink": 0.8}
    )
    ax.set_title("Correlation Heatmap — Fleet Parameters",
                 color=PALETTE["text"], fontsize=12, pad=12)
    ax.tick_params(colors=PALETTE["text"], labelsize=7)
    plt.xticks(rotation=30, ha="right")
    plt.yticks(rotation=0)
    fig.tight_layout()
    plt.show()
