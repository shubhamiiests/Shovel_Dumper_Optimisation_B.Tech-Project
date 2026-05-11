#!/usr/bin/env python3
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import matplotlib
matplotlib.use("TkAgg")

from data.repository import read_dataframe
from analysis.regression import run_regression
from analysis.graphs import (
    production_dashboard, haul_distance_analysis,
    productivity_vs_production, correlation_heatmap,
    scatter_with_regression, bar_chart,
)

def main():
    args = sys.argv[1:]
    if not args:
        return

    plot_type = args[0]
    df = read_dataframe()

    if df.empty:
        import tkinter as tk
        from tkinter import messagebox
        root = tk.Tk(); root.withdraw()
        messagebox.showwarning("No Data", "No records found.")
        return

    if plot_type == "dashboard":
        production_dashboard(df)
    elif plot_type == "haul":
        haul_distance_analysis(df)
    elif plot_type == "prod_vs":
        productivity_vs_production(df)
    elif plot_type == "corr":
        correlation_heatmap(df)
    elif plot_type == "scatter":
        x_col     = args[1]
        y_col     = args[2]
        degree    = int(args[3]) if len(args) > 3 else -1
        color_col = args[4] if len(args) > 4 and args[4] != "none" else None
        if degree == 0:
            reg = None
        elif degree == -1:
            # Auto: try degree 1,2,3 and pick best Adjusted R²
            best, best_adj_r2 = None, -999
            for d in [1, 2, 3]:
                r = run_regression(df, x_col, y_col, degree=d)
                if "error" not in r and r["adj_r2"] > best_adj_r2:
                    best, best_adj_r2 = r, r["adj_r2"]
            reg = best
        else:
            reg = run_regression(df, x_col, y_col, degree=degree)
        scatter_with_regression(df, x_col, y_col,
                                reg_result=reg if reg and "error" not in reg else None,
                                color_col=color_col)
    elif plot_type == "bar":
        bar_chart(df, args[1], args[2])
    elif plot_type == "reg_plot":
        x_col  = args[1]
        y_col  = args[2]
        degree = int(args[3]) if len(args) > 3 else -1
        import pandas as pd
        from analysis.regression import auto_best_degree
        subset_json = os.environ.get("FLEET_SUBSET")
        sub_df = pd.read_json(subset_json) if subset_json else df
        if degree == -1:
            reg = auto_best_degree(sub_df, x_col, y_col)
        else:
            reg = run_regression(sub_df, x_col, y_col, degree=degree)
        scatter_with_regression(sub_df, x_col, y_col,
                                reg_result=reg if "error" not in reg else None)


if __name__ == "__main__":
    main()
