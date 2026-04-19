"""
ui/app.py — Main Tkinter application
Tabs: Data Entry | History (CRUD) | Regression | Graphs
"""
from __future__ import annotations
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import tkinter as tk
from tkinter import ttk, messagebox, simpledialog
import threading
import pandas as pd
from typing import Optional, Dict, Any, List

from core.models import FleetInputs
from core.engine import solve
from data.repository import (
    create, read_all, read_dataframe, delete, update,
    COL_LABELS, NUMERIC_COLS, ALL_COLS, INPUT_COLS, RESULT_COLS
)
from analysis.regression import run_regression, filter_by_matching_inputs
from analysis.graphs import (
    scatter_with_regression, bar_chart,
    production_dashboard, haul_distance_analysis,
    productivity_vs_production, correlation_heatmap,
)

# ─────────────────────────── Theme ───────────────────────────────────
BG       = "#0D1117"
SURFACE  = "#161B22"
SURFACE2 = "#21262D"
BORDER   = "#30363D"
ACCENT   = "#F78166"
ACCENT2  = "#79C0FF"
ACCENT3  = "#56D364"
ACCENT4  = "#E3B341"
TEXT     = "#E6EDF3"
SUBTEXT  = "#8B949E"
RED      = "#FF7B72"

FONT_HEAD  = ("Consolas", 13, "bold")
FONT_LABEL = ("Consolas", 9)
FONT_VALUE = ("Consolas", 9, "bold")
FONT_SMALL = ("Consolas", 8)
FONT_TITLE = ("Consolas", 11, "bold")

# ─────────────────────────── Widget helpers ───────────────────────────

def _frame(parent, **kw) -> tk.Frame:
    kw.setdefault("bg", SURFACE)
    return tk.Frame(parent, **kw)

def _label(parent, text, **kw) -> tk.Label:
    kw.setdefault("bg", SURFACE)
    kw.setdefault("fg", TEXT)
    kw.setdefault("font", FONT_LABEL)
    return tk.Label(parent, text=text, **kw)

def _entry(parent, textvariable=None, width=14, **kw) -> tk.Entry:
    kw.setdefault("bg", SURFACE2)
    kw.setdefault("fg", TEXT)
    kw.setdefault("insertbackground", ACCENT2)
    kw.setdefault("relief", "flat")
    kw.setdefault("font", FONT_LABEL)
    kw.setdefault("highlightthickness", 1)
    kw.setdefault("highlightbackground", BORDER)
    kw.setdefault("highlightcolor", ACCENT2)
    return tk.Entry(parent, textvariable=textvariable, width=width, **kw)

def _btn(parent, text, cmd, color=ACCENT2, **kw) -> tk.Button:
    kw.setdefault("bg", color)
    kw.setdefault("fg", BG)
    kw.setdefault("font", FONT_LABEL)
    kw.setdefault("relief", "flat")
    kw.setdefault("cursor", "hand2")
    kw.setdefault("padx", 10)
    kw.setdefault("pady", 4)
    kw.setdefault("activebackground", TEXT)
    kw.setdefault("activeforeground", BG)
    return tk.Button(parent, text=text, command=cmd, **kw)

def _combo(parent, values, textvariable=None, width=12, **kw) -> ttk.Combobox:
    style = ttk.Style()
    style.theme_use("clam")
    style.configure("Dark.TCombobox",
                    fieldbackground=SURFACE2, background=SURFACE2,
                    foreground=TEXT, bordercolor=BORDER,
                    arrowcolor=ACCENT2, selectbackground=SURFACE2,
                    selectforeground=TEXT)
    return ttk.Combobox(parent, values=values, textvariable=textvariable,
                        width=width, style="Dark.TCombobox", **kw)

def _separator(parent) -> tk.Frame:
    return tk.Frame(parent, bg=BORDER, height=1)

def _section_header(parent, text: str) -> tk.Label:
    lbl = tk.Label(parent, text=f"  {text}  ", bg=ACCENT, fg=BG,
                   font=FONT_TITLE, padx=6, pady=3, anchor="w")
    return lbl

# ─────────────────────────── Scrollable Frame ─────────────────────────

class ScrollFrame(tk.Frame):
    def __init__(self, parent, **kw):
        kw.setdefault("bg", SURFACE)
        super().__init__(parent, **kw)
        canvas = tk.Canvas(self, bg=SURFACE, highlightthickness=0)
        sb = ttk.Scrollbar(self, orient="vertical", command=canvas.yview)
        self.inner = tk.Frame(canvas, bg=SURFACE)
        self.inner.bind("<Configure>",
                        lambda e: canvas.configure(scrollregion=canvas.bbox("all")))
        canvas.create_window((0, 0), window=self.inner, anchor="nw")
        canvas.configure(yscrollcommand=sb.set)
        canvas.pack(side="left", fill="both", expand=True)
        sb.pack(side="right", fill="y")
        canvas.bind_all("<MouseWheel>",
                        lambda e: canvas.yview_scroll(-1*(e.delta//120), "units"))


# ─────────────────────────── Main App ────────────────────────────────

class FleetApp(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("⛏  Shovel–Dumper Fleet Optimiser")
        self.configure(bg=BG)
        self.geometry("1100x780")
        self.resizable(True, True)

        self._build_header()
        self._build_notebook()
        self._build_status_bar()

        # Tabs
        self.entry_tab  = DataEntryTab(self.nb, self)
        self.history_tab = HistoryTab(self.nb, self)
        self.reg_tab    = RegressionTab(self.nb, self)
        self.graph_tab  = GraphsTab(self.nb, self)

        self.nb.add(self.entry_tab,   text="  ✚  Data Entry  ")
        self.nb.add(self.history_tab, text="  📋  History / CRUD  ")
        self.nb.add(self.reg_tab,     text="  📈  Regression  ")
        self.nb.add(self.graph_tab,   text="  📊  Graphs  ")

        self.nb.bind("<<NotebookTabChanged>>", self._on_tab_change)

    def _build_header(self):
        hdr = tk.Frame(self, bg=SURFACE, pady=8)
        hdr.pack(fill="x")
        tk.Label(hdr, text="⛏  SHOVEL–DUMPER FLEET OPTIMISATION SYSTEM",
                 bg=SURFACE, fg=ACCENT, font=("Consolas", 14, "bold")).pack(side="left", padx=20)
        tk.Label(hdr, text="B.Tech Mining Engineering Project",
                 bg=SURFACE, fg=SUBTEXT, font=FONT_SMALL).pack(side="right", padx=20)

    def _build_notebook(self):
        style = ttk.Style()
        style.theme_use("clam")
        style.configure("Custom.TNotebook",
                        background=BG, borderwidth=0, tabmargins=[0, 0, 0, 0])
        style.configure("Custom.TNotebook.Tab",
                        background=SURFACE2, foreground=SUBTEXT,
                        font=("Consolas", 9, "bold"), padding=[12, 6],
                        borderwidth=0)
        style.map("Custom.TNotebook.Tab",
                  background=[("selected", ACCENT)],
                  foreground=[("selected", BG)])
        self.nb = ttk.Notebook(self, style="Custom.TNotebook")
        self.nb.pack(fill="both", expand=True, padx=0, pady=0)

    def _build_status_bar(self):
        self.status_var = tk.StringVar(value="Ready.")
        sb = tk.Label(self, textvariable=self.status_var, bg=SURFACE2, fg=SUBTEXT,
                      font=FONT_SMALL, anchor="w", pady=3, padx=10)
        sb.pack(fill="x", side="bottom")

    def set_status(self, msg: str, color: str = SUBTEXT):
        self.status_var.set(msg)

    def _on_tab_change(self, _event):
        tab = self.nb.index(self.nb.select())
        if tab == 1:
            self.history_tab.refresh()
        elif tab == 2:
            self.reg_tab.refresh_ids()
        elif tab == 3:
            self.graph_tab.refresh()


# ─────────────────────────── Data Entry Tab ───────────────────────────

class DataEntryTab(tk.Frame):
    """Tab 1: Enter all fleet parameters and compute results."""

    HAUL_PRESETS   = [0.5, 1.0, 1.5, 2.0]
    SHIFT_PRESETS  = [5, 6, 7]
    CYCLE_PRESETS  = [80, 85, 90, 95, 100]

    def __init__(self, parent, app: FleetApp):
        super().__init__(parent, bg=BG)
        self.app = app
        self._vars: Dict[str, tk.Variable] = {}
        self._result_labels: Dict[str, tk.Label] = {}
        self._build()

    # ── Build ─────────────────────────────────────────────────────────

    def _build(self):
        # Left panel: inputs
        left = tk.Frame(self, bg=BG, padx=10, pady=10)
        left.pack(side="left", fill="y")

        # Right panel: results
        right = tk.Frame(self, bg=BG, padx=10, pady=10)
        right.pack(side="left", fill="both", expand=True)

        self._build_input_panel(left)
        self._build_result_panel(right)

    def _build_input_panel(self, parent):
        sf = ScrollFrame(parent)
        sf.pack(fill="both", expand=True)
        f = sf.inner

        # ── Section: Fleet ──
        _section_header(f, "FLEET CONFIGURATION").pack(fill="x", pady=(4, 2))
        self._row(f, "Number of Shovels", "n_shovels", "int", default=1, unit="units")
        self._row(f, "Number of Dumpers (assigned)", "n_dumpers", "int", default=5, unit="units",
                  hint="Required dumpers shown in results →")

        # ── Section: Equipment ──
        _section_header(f, "EQUIPMENT SPECIFICATIONS").pack(fill="x", pady=(10, 2))
        self._row(f, "Shovel Bucket Capacity", "shovel_bucket_m3", "float", default=10.0, unit="m³")
        self._row(f, "Dumper Capacity", "dumper_capacity_t", "float", default=50.0, unit="tonnes")
        self._row(f, "Bucket Fill Factor", "bucket_fill_factor", "float", default=0.80, unit="0–1")
        self._row(f, "Swing Factor", "swing_factor", "float", default=0.80, unit="0–1")
        self._row(f, "Material Density", "material_density_t_per_m3", "float", default=1.40, unit="t/m³")

        # ── Section: Shovel Cycle Time (preset + custom) ──
        _section_header(f, "SHOVEL CYCLE TIME").pack(fill="x", pady=(10, 2))
        self._preset_row(f, "shovel_cycle_time_sec",
                         [str(v) for v in self.CYCLE_PRESETS],
                         custom_label="Custom (sec)",
                         unit="sec", default=90)

        # ── Section: Haul Distance ──
        _section_header(f, "HAUL DISTANCE (ONE-WAY)").pack(fill="x", pady=(10, 2))
        self._preset_row(f, "distance_km_one_way",
                         ["500 m → 0.5", "1000 m → 1.0", "1500 m → 1.5", "2000 m → 2.0"],
                         custom_label="Custom (km)",
                         unit="km", default=2.0,
                         parse_fn=lambda s: float(s.split("→")[-1]) if "→" in s else float(s))

        # ── Section: Shift Duration ──
        _section_header(f, "SHIFT DURATION").pack(fill="x", pady=(10, 2))
        self._preset_row(f, "shift_hours",
                         ["5 hrs", "6 hrs", "7 hrs"],
                         custom_label="Custom (hrs)",
                         unit="hrs", default=6,
                         parse_fn=lambda s: float(s.split()[0]) if "hrs" in s else float(s))

        # ── Section: Transport & Ops ──
        _section_header(f, "TRANSPORT & OPERATIONS").pack(fill="x", pady=(10, 2))
        self._row(f, "Dumper Speed", "dumper_speed_kmph", "float", default=30.0, unit="km/h")
        self._row(f, "Dumper Unload Time", "dumper_unload_time_min", "float", default=2.0, unit="min")
        self._row(f, "Shifts per Day", "shifts_per_day", "int", default=3, unit="shifts")
        self._row(f, "Days per Month", "days_per_month", "int", default=30, unit="days")

        # ── Action buttons ──
        btn_row = _frame(f)
        btn_row.pack(fill="x", pady=14)
        _btn(btn_row, "  ▶  CALCULATE  ", self._on_calculate,
             color=ACCENT3).pack(side="left", padx=6)
        _btn(btn_row, "  💾  SAVE TO CSV  ", self._on_save,
             color=ACCENT4).pack(side="left", padx=6)
        _btn(btn_row, "  ↺  RESET  ", self._on_reset,
             color=SURFACE2).pack(side="left", padx=6)

    def _row(self, parent, label, key, typ, default, unit="", hint=""):
        """A single labelled entry row."""
        row = _frame(parent)
        row.pack(fill="x", pady=2, padx=4)
        # Label column (fixed width)
        lbl_txt = f"{label}"
        _label(row, lbl_txt, width=32, anchor="w").pack(side="left")
        # Unit hint
        _label(row, f"[{unit}]", fg=SUBTEXT, width=9, anchor="w").pack(side="left")
        # Entry
        var = tk.StringVar(value=str(default))
        self._vars[key] = var
        ent = _entry(row, textvariable=var, width=12)
        ent.pack(side="left", padx=4)
        if hint:
            _label(row, hint, fg=SUBTEXT).pack(side="left", padx=4)

    def _preset_row(self, parent, key, presets, custom_label, unit, default,
                    parse_fn=None):
        """Row with preset buttons + custom entry."""
        row1 = _frame(parent)
        row1.pack(fill="x", pady=2, padx=4)
        _label(row1, f"Select preset:", width=14, fg=SUBTEXT).pack(side="left")

        var = tk.StringVar(value=str(default))
        self._vars[key] = var

        # Store parse function
        if parse_fn is None:
            parse_fn = float
        self._vars[f"_parse_{key}"] = parse_fn  # store as attribute trick

        for p in presets:
            val = parse_fn(p)
            b = tk.Button(row1, text=p,
                          bg=SURFACE2, fg=ACCENT2, font=FONT_SMALL,
                          relief="flat", cursor="hand2", padx=6, pady=3,
                          activebackground=ACCENT2, activeforeground=BG,
                          command=lambda v=val: var.set(str(v)))
            b.pack(side="left", padx=3)

        row2 = _frame(parent)
        row2.pack(fill="x", pady=1, padx=4)
        _label(row2, f"{custom_label}:", width=16, fg=SUBTEXT, anchor="w").pack(side="left")
        _label(row2, f"[{unit}]", fg=SUBTEXT, width=6).pack(side="left")
        _entry(row2, textvariable=var, width=12).pack(side="left", padx=4)

    def _build_result_panel(self, parent):
        hdr = _frame(parent, bg=SURFACE)
        hdr.pack(fill="x", pady=(0, 6))
        _label(hdr, "CALCULATION RESULTS", bg=SURFACE, fg=ACCENT,
               font=FONT_HEAD).pack(side="left", padx=8, pady=6)

        # Result grid
        res_frame = _frame(parent, bg=SURFACE)
        res_frame.pack(fill="both", expand=True, padx=4, pady=4)

        result_items = [
            ("─── BUCKET & LOAD ─────────────────",),
            ("Effective Bucket Load",        "effective_bucket_tons",        "t"),
            ("Buckets Needed per Dumper",    "buckets_per_dumper",           ""),
            ("Load Time per Dumper",         "load_time_per_dumper_min",     "min"),
            ("─── TRAVEL ────────────────────────",),
            ("One-way Travel Time",          "travel_time_one_way_min",      "min"),
            ("Round-trip Time (incl. unload)","round_trip_time_min",         "min"),
            ("─── FLEET MATCHING ────────────────",),
            ("Required Dumpers per Shovel ✔", "required_dumpers_per_shovel", ""),
            ("Actual Trucks per Shovel",     "trucks_per_shovel_actual",     ""),
            ("Idle Party",                   "who_idles",                    ""),
            ("Shovel Idle Gap / Cycle",      "shovel_idle_gap_min_per_cycle","min"),
            ("Dumper Wait / Cycle",          "truck_wait_min_per_cycle",     "min"),
            ("Fleet Match Ratio",            "match_ratio",                  ""),
            ("Fleet Efficiency",             "fleet_efficiency_pct",         "%"),
            ("─── PRODUCTION ────────────────────",),
            ("Production per Shovel",        "tph_per_shovel",               "t/h"),
            ("Total Fleet Production",       "tph_total",                    "t/h"),
            ("Production per Shift",         "production_per_shift_t",       "t"),
            ("Production per Day",           "production_per_day_t",         "t"),
            ("Production per Month",         "production_per_month_t",       "t"),
        ]

        for item in result_items:
            if len(item) == 1:
                # Section divider
                row = _frame(res_frame, bg=SURFACE)
                row.pack(fill="x", pady=(8, 2))
                _label(row, item[0], bg=SURFACE, fg=SUBTEXT,
                       font=FONT_SMALL).pack(side="left", padx=6)
            else:
                label_txt, key, unit = item
                row = _frame(res_frame, bg=SURFACE2)
                row.pack(fill="x", pady=1, padx=2)
                _label(row, label_txt, bg=SURFACE2, width=36, anchor="w").pack(side="left", padx=6)
                val_lbl = _label(row, "—", bg=SURFACE2, fg=ACCENT2,
                                 font=FONT_VALUE, width=14, anchor="e")
                val_lbl.pack(side="left")
                _label(row, f"  {unit}", bg=SURFACE2, fg=SUBTEXT).pack(side="left")
                self._result_labels[key] = val_lbl

    # ── Actions ───────────────────────────────────────────────────────

    def _collect_inputs(self) -> Optional[FleetInputs]:
        """Read all vars and return FleetInputs, or show error."""
        try:
            return FleetInputs(
                n_shovels=int(self._vars["n_shovels"].get()),
                n_dumpers=int(self._vars["n_dumpers"].get()),
                shovel_bucket_m3=float(self._vars["shovel_bucket_m3"].get()),
                dumper_capacity_t=float(self._vars["dumper_capacity_t"].get()),
                bucket_fill_factor=float(self._vars["bucket_fill_factor"].get()),
                swing_factor=float(self._vars["swing_factor"].get()),
                material_density_t_per_m3=float(self._vars["material_density_t_per_m3"].get()),
                shovel_cycle_time_sec=float(self._vars["shovel_cycle_time_sec"].get()),
                dumper_speed_kmph=float(self._vars["dumper_speed_kmph"].get()),
                distance_km_one_way=float(self._vars["distance_km_one_way"].get()),
                dumper_unload_time_min=float(self._vars["dumper_unload_time_min"].get()),
                shift_hours=float(self._vars["shift_hours"].get()),
                shifts_per_day=int(self._vars["shifts_per_day"].get()),
                days_per_month=int(self._vars["days_per_month"].get()),
            )
        except (ValueError, KeyError) as e:
            messagebox.showerror("Input Error", f"Invalid input: {e}")
            return None

    def _on_calculate(self):
        inp = self._collect_inputs()
        if inp is None:
            return
        record = solve(inp)
        self._last_record = record
        res = record.results
        for key, lbl in self._result_labels.items():
            val = getattr(res, key, None)
            if val is not None:
                if isinstance(val, float):
                    lbl.config(text=f"{val:.3f}")
                else:
                    lbl.config(text=str(val))
                # Colour coding
                if key == "who_idles":
                    color = RED if val == "Shovel idle" else (ACCENT4 if val == "Dumpers idle" else ACCENT3)
                    lbl.config(fg=color)
                elif key == "fleet_efficiency_pct":
                    v = float(val)
                    color = ACCENT3 if v >= 90 else (ACCENT4 if v >= 70 else RED)
                    lbl.config(fg=color)
                else:
                    lbl.config(fg=ACCENT2)
        self.app.set_status(
            f"✔  Calculated — Fleet TPH: {res.tph_total:.1f}  |  "
            f"Efficiency: {res.fleet_efficiency_pct:.1f}%  |  "
            f"Required dumpers/shovel: {res.required_dumpers_per_shovel}"
        )

    def _on_save(self):
        if not hasattr(self, "_last_record"):
            # Auto-calculate first
            self._on_calculate()
            if not hasattr(self, "_last_record"):
                return
        create(self._last_record)
        messagebox.showinfo(
            "Saved",
            f"Record saved!\nSession ID: {self._last_record.inputs.session_id}"
        )
        self.app.set_status(f"💾  Saved record {self._last_record.inputs.session_id}")

    def _on_reset(self):
        defaults = {
            "n_shovels": "1", "n_dumpers": "5",
            "shovel_bucket_m3": "10.0", "dumper_capacity_t": "50.0",
            "bucket_fill_factor": "0.80", "swing_factor": "0.80",
            "material_density_t_per_m3": "1.40",
            "shovel_cycle_time_sec": "90.0",
            "dumper_speed_kmph": "30.0", "distance_km_one_way": "2.0",
            "dumper_unload_time_min": "2.0",
            "shift_hours": "6.0", "shifts_per_day": "3", "days_per_month": "30",
        }
        for k, v in defaults.items():
            if k in self._vars:
                self._vars[k].set(v)
        for lbl in self._result_labels.values():
            lbl.config(text="—", fg=ACCENT2)
        if hasattr(self, "_last_record"):
            del self._last_record
        self.app.set_status("Reset to defaults.")


# ─────────────────────────── History / CRUD Tab ───────────────────────

class HistoryTab(tk.Frame):
    def __init__(self, parent, app: FleetApp):
        super().__init__(parent, bg=BG)
        self.app = app
        self._build()

    def _build(self):
        # Toolbar
        toolbar = _frame(self, bg=SURFACE)
        toolbar.pack(fill="x")
        _label(toolbar, "SIMULATION HISTORY", bg=SURFACE, fg=ACCENT,
               font=FONT_HEAD).pack(side="left", padx=10, pady=8)
        _btn(toolbar, "↺ Refresh", self.refresh, color=ACCENT2).pack(side="left", padx=6, pady=6)
        _btn(toolbar, "🗑  Delete Selected", self._on_delete, color=RED).pack(side="left", padx=6)
        _btn(toolbar, "📂  Open CSV folder", self._open_csv_folder, color=SURFACE2).pack(side="right", padx=10)

        # Treeview
        cols = ["session_id", "timestamp",
                "n_shovels", "n_dumpers", "distance_km_one_way",
                "shovel_cycle_time_sec", "shift_hours",
                "tph_total", "fleet_efficiency_pct",
                "required_dumpers_per_shovel", "who_idles",
                "production_per_shift_t"]

        tree_frame = _frame(self, bg=BG)
        tree_frame.pack(fill="both", expand=True, padx=8, pady=8)

        style = ttk.Style()
        style.configure("Dark.Treeview",
                        background=SURFACE2, foreground=TEXT,
                        fieldbackground=SURFACE2, bordercolor=BORDER,
                        rowheight=22, font=FONT_SMALL)
        style.configure("Dark.Treeview.Heading",
                        background=SURFACE, foreground=ACCENT,
                        font=("Consolas", 8, "bold"), relief="flat")
        style.map("Dark.Treeview",
                  background=[("selected", ACCENT)],
                  foreground=[("selected", BG)])

        sb_y = ttk.Scrollbar(tree_frame, orient="vertical")
        sb_x = ttk.Scrollbar(tree_frame, orient="horizontal")
        self.tree = ttk.Treeview(tree_frame, columns=cols, show="headings",
                                 style="Dark.Treeview",
                                 yscrollcommand=sb_y.set,
                                 xscrollcommand=sb_x.set)
        sb_y.config(command=self.tree.yview)
        sb_x.config(command=self.tree.xview)

        widths = {"session_id": 90, "timestamp": 140, "n_shovels": 70,
                  "n_dumpers": 70, "distance_km_one_way": 120,
                  "shovel_cycle_time_sec": 120, "shift_hours": 80,
                  "tph_total": 100, "fleet_efficiency_pct": 110,
                  "required_dumpers_per_shovel": 130,
                  "who_idles": 100, "production_per_shift_t": 130}

        for c in cols:
            self.tree.heading(c, text=COL_LABELS.get(c, c),
                              command=lambda _c=c: self._sort_by(_c))
            self.tree.column(c, width=widths.get(c, 100), anchor="center")

        self.tree.pack(side="left", fill="both", expand=True)
        sb_y.pack(side="right", fill="y")
        sb_x.pack(side="bottom", fill="x")

        self.tree.bind("<Double-1>", self._on_view_detail)

    def refresh(self):
        for row in self.tree.get_children():
            self.tree.delete(row)
        df = read_dataframe()
        if df.empty:
            return
        display_cols = [c for c in self.tree["columns"]]
        for _, row in df.iterrows():
            vals = []
            for c in display_cols:
                v = row.get(c, "")
                if isinstance(v, float):
                    v = f"{v:.3f}"
                vals.append(str(v) if v is not None else "")
            self.tree.insert("", "end", values=vals)
        self.app.set_status(f"Loaded {len(df)} records.")

    def _on_delete(self):
        sel = self.tree.selection()
        if not sel:
            messagebox.showwarning("No selection", "Select a row first.")
            return
        item = self.tree.item(sel[0])
        sid = item["values"][0]
        if messagebox.askyesno("Confirm Delete", f"Delete record {sid}?"):
            delete(str(sid))
            self.refresh()
            self.app.set_status(f"Deleted record {sid}.")

    def _on_view_detail(self, _event):
        sel = self.tree.selection()
        if not sel:
            return
        item = self.tree.item(sel[0])
        sid = str(item["values"][0])
        record = None
        for r in read_all():
            if r.inputs.session_id == sid:
                record = r
                break
        if not record:
            return
        # Popup detail window
        win = tk.Toplevel(self)
        win.title(f"Record Detail — {sid}")
        win.configure(bg=SURFACE)
        win.geometry("520x600")
        sf = ScrollFrame(win)
        sf.pack(fill="both", expand=True)
        f = sf.inner
        _label(f, f"Session ID: {sid}", fg=ACCENT,
               font=FONT_TITLE, bg=SURFACE).pack(anchor="w", padx=12, pady=6)
        for key in INPUT_COLS + RESULT_COLS:
            val = getattr(record.inputs, key, None) or getattr(record.results, key, None)
            row = _frame(f, bg=SURFACE2)
            row.pack(fill="x", pady=1, padx=6)
            _label(row, COL_LABELS.get(key, key), bg=SURFACE2,
                   width=36, anchor="w").pack(side="left", padx=6)
            _label(row, str(val) if val is not None else "—",
                   bg=SURFACE2, fg=ACCENT2,
                   font=FONT_VALUE).pack(side="right", padx=6)

    def _sort_by(self, col):
        data = [(self.tree.set(k, col), k) for k in self.tree.get_children("")]
        try:
            data.sort(key=lambda t: float(t[0]))
        except ValueError:
            data.sort()
        for i, (_, k) in enumerate(data):
            self.tree.move(k, "", i)

    def _open_csv_folder(self):
        import subprocess, platform
        from data.repository import CSV_PATH
        folder = os.path.dirname(CSV_PATH)
        if platform.system() == "Windows":
            os.startfile(folder)
        elif platform.system() == "Darwin":
            subprocess.Popen(["open", folder])
        else:
            subprocess.Popen(["xdg-open", folder])


# ─────────────────────────── Regression Tab ───────────────────────────

class RegressionTab(tk.Frame):
    def __init__(self, parent, app: FleetApp):
        super().__init__(parent, bg=BG)
        self.app = app
        self._build()

    def _build(self):
        left = tk.Frame(self, bg=BG, padx=10, pady=10, width=340)
        left.pack(side="left", fill="y")
        left.pack_propagate(False)

        right = tk.Frame(self, bg=SURFACE, padx=12, pady=12)
        right.pack(side="left", fill="both", expand=True)

        self._build_controls(left)
        self._build_output(right)

    def _build_controls(self, parent):
        _section_header(parent, "REGRESSION SETTINGS").pack(fill="x", pady=(4, 8))

        num_cols = [c for c in NUMERIC_COLS if c not in
                    ("session_id", "timestamp", "who_idles", "shifts_per_day",
                     "days_per_month", "buckets_per_dumper")]
        col_options = [f"{COL_LABELS.get(c, c)}  [{c}]" for c in num_cols]
        self._num_cols = num_cols
        self._col_options = col_options

        def _combo_row(lbl, var, row_no):
            row = _frame(parent)
            row.pack(fill="x", pady=3)
            _label(row, lbl, width=14, anchor="w").pack(side="left")
            cb = _combo(row, col_options, textvariable=var, width=34)
            cb.pack(side="left", padx=4)

        self._x_var = tk.StringVar()
        self._y_var = tk.StringVar()
        self._deg_var = tk.StringVar(value="1")
        self._n_var = tk.StringVar(value="5")

        _combo_row("X  (independent)", self._x_var, 0)
        _combo_row("Y  (dependent)",   self._y_var, 1)

        # Degree
        row = _frame(parent)
        row.pack(fill="x", pady=3)
        _label(row, "Polynomial degree", width=20, anchor="w").pack(side="left")
        _combo(row, ["1", "2", "3"], textvariable=self._deg_var, width=6).pack(side="left")

        # Last N or custom selection
        _separator(parent).pack(fill="x", pady=8)
        _label(parent, "DATA SELECTION", fg=ACCENT, font=FONT_TITLE).pack(anchor="w", pady=4)

        row = _frame(parent)
        row.pack(fill="x", pady=3)
        _label(row, "Use last N records:", width=22, anchor="w").pack(side="left")
        _entry(row, textvariable=self._n_var, width=6).pack(side="left", padx=4)

        # Priority matching columns
        _label(parent, "Priority match columns\n(choose to prefer records with\nsame values):",
               fg=SUBTEXT, justify="left").pack(anchor="w", pady=(6, 2))

        self._match_listbox = tk.Listbox(parent, bg=SURFACE2, fg=TEXT, font=FONT_SMALL,
                                         selectmode="multiple", height=7,
                                         relief="flat", highlightthickness=1,
                                         highlightbackground=BORDER,
                                         selectbackground=ACCENT, selectforeground=BG)
        match_options = ["distance_km_one_way", "shovel_cycle_time_sec",
                         "shift_hours", "n_shovels", "dumper_capacity_t",
                         "shovel_bucket_m3", "dumper_speed_kmph"]
        for opt in match_options:
            self._match_listbox.insert(tk.END, f"{COL_LABELS.get(opt, opt)}  [{opt}]")
        self._match_options = match_options
        self._match_listbox.pack(fill="x", pady=4)

        _separator(parent).pack(fill="x", pady=8)

        _btn(parent, "  ▶  RUN REGRESSION  ", self._on_run,
             color=ACCENT3).pack(fill="x", pady=6)
        _btn(parent, "  📊  PLOT RESULT  ", self._on_plot,
             color=ACCENT2).pack(fill="x", pady=4)

        self._last_result = None

    def _build_output(self, parent):
        _label(parent, "REGRESSION OUTPUT", bg=SURFACE, fg=ACCENT,
               font=FONT_HEAD).pack(anchor="w", pady=(0, 8))
        self._out_text = tk.Text(parent, bg=SURFACE2, fg=TEXT, font=("Consolas", 10),
                                 relief="flat", highlightthickness=0,
                                 state="disabled", wrap="word")
        self._out_text.pack(fill="both", expand=True)

    def _write_output(self, text: str):
        self._out_text.config(state="normal")
        self._out_text.delete("1.0", "end")
        self._out_text.insert("end", text)
        self._out_text.config(state="disabled")

    def refresh_ids(self):
        pass

    def _get_x_col(self):
        s = self._x_var.get()
        if "[" in s:
            return s.split("[")[-1].rstrip("]")
        return None

    def _get_y_col(self):
        s = self._y_var.get()
        if "[" in s:
            return s.split("[")[-1].rstrip("]")
        return None

    def _on_run(self):
        x_col = self._get_x_col()
        y_col = self._get_y_col()
        if not x_col or not y_col:
            messagebox.showerror("Error", "Select both X and Y columns.")
            return
        if x_col == y_col:
            messagebox.showerror("Error", "X and Y must be different columns.")
            return

        df = read_dataframe()
        if df.empty:
            messagebox.showwarning("No data", "No records found. Save some calculations first.")
            return

        # Priority matching
        sel_idx = list(self._match_listbox.curselection())
        match_cols = [self._match_options[i] for i in sel_idx]

        try:
            n = int(self._n_var.get())
        except ValueError:
            n = 5

        anchor = {}
        for col in match_cols:
            if col in df.columns:
                anchor[col] = df[col].iloc[-1]  # use last row's value as anchor

        if match_cols:
            df_sub = filter_by_matching_inputs(df, anchor, match_cols, n=n)
        else:
            df_sub = df.tail(n)

        degree = int(self._deg_var.get())
        result = run_regression(df_sub, x_col, y_col, degree=degree)

        if "error" in result:
            self._write_output(f"Error: {result['error']}")
            return

        self._last_result = result
        self._last_df = df_sub

        lines = [
            f"{'═'*52}",
            f"  REGRESSION REPORT",
            f"{'═'*52}",
            f"  X variable : {COL_LABELS.get(x_col, x_col)}",
            f"  Y variable : {COL_LABELS.get(y_col, y_col)}",
            f"  Degree     : {degree} ({'Linear' if degree==1 else 'Polynomial'})",
            f"  Data points: {result['n']}",
            f"{'─'*52}",
            f"  R²         : {result['r2']:.6f}",
            f"  Adj. R²    : {result['adj_r2']:.6f}",
            f"  RMSE       : {result['rmse']:.4f}",
            f"  Pearson r  : {result['pearson_r']:.4f}",
            f"  p-value    : {result['p_value']:.4e}",
            f"{'─'*52}",
            f"  Equation:",
            f"  Y = {result['equation']}",
            f"{'─'*52}",
        ]
        if match_cols:
            lines.append(f"  Priority match on: {', '.join(match_cols)}")
        lines += [
            f"  Selected from last {n} matching records.",
            f"{'═'*52}",
            "",
            "  RAW DATA (x, y, y_predicted):",
            f"  {'X':>12}  {'Y_actual':>12}  {'Y_pred':>12}  {'Residual':>12}",
            "  " + "─"*52,
        ]
        for x, y, yp in zip(result["x_data"], result["y_data"], result["y_pred"]):
            lines.append(f"  {x:>12.4f}  {y:>12.4f}  {yp:>12.4f}  {y-yp:>+12.4f}")

        self._write_output("\n".join(lines))
        self.app.set_status(
            f"Regression done. R²={result['r2']:.4f}, n={result['n']}")

    def _on_plot(self):
        if not self._last_result:
            messagebox.showwarning("No result", "Run regression first.")
            return
        x_col = self._get_x_col()
        y_col = self._get_y_col()
        threading.Thread(
            target=scatter_with_regression,
            args=(self._last_df, x_col, y_col, self._last_result),
            daemon=True
        ).start()


# ─────────────────────────── Graphs Tab ───────────────────────────────

class GraphsTab(tk.Frame):
    def __init__(self, parent, app: FleetApp):
        super().__init__(parent, bg=BG)
        self.app = app
        self._build()

    def _build(self):
        # Top controls
        ctrl = _frame(self, bg=SURFACE)
        ctrl.pack(fill="x")
        _label(ctrl, "GRAPHS & VISUALISATIONS", bg=SURFACE, fg=ACCENT,
               font=FONT_HEAD).pack(side="left", padx=10, pady=8)

        # Left: preset charts | Right: custom chart builder
        body = tk.Frame(self, bg=BG)
        body.pack(fill="both", expand=True, padx=8, pady=8)

        left = tk.Frame(body, bg=SURFACE, padx=10, pady=10, width=300)
        left.pack(side="left", fill="y", padx=(0, 6))
        left.pack_propagate(False)

        right = tk.Frame(body, bg=SURFACE, padx=10, pady=10)
        right.pack(side="left", fill="both", expand=True)

        self._build_presets(left)
        self._build_custom(right)

    def _build_presets(self, parent):
        _label(parent, "PRESET CHARTS", fg=ACCENT, font=FONT_TITLE).pack(anchor="w", pady=4)
        _separator(parent).pack(fill="x", pady=4)

        presets = [
            ("📊  Production Dashboard",        self._plot_dashboard),
            ("🚛  Haul Distance Analysis",      self._plot_haul),
            ("📈  Productivity vs Production",  self._plot_prod_vs),
            ("🌡  Correlation Heatmap",          self._plot_corr),
        ]
        for label, cmd in presets:
            _btn(parent, label, cmd, color=ACCENT).pack(fill="x", pady=4)

    def _build_custom(self, parent):
        _label(parent, "CUSTOM CHART BUILDER", fg=ACCENT, font=FONT_TITLE).pack(anchor="w", pady=4)
        _separator(parent).pack(fill="x", pady=4)

        num_cols = [c for c in NUMERIC_COLS if c not in
                    ("shifts_per_day", "days_per_month")]
        col_options = [f"{COL_LABELS.get(c, c)}  [{c}]" for c in num_cols]
        self._num_cols = num_cols
        self._col_options = col_options

        # X axis
        row = _frame(parent)
        row.pack(fill="x", pady=4)
        _label(row, "X axis:", width=12, anchor="w").pack(side="left")
        self._cx_var = tk.StringVar()
        _combo(row, col_options, textvariable=self._cx_var, width=38).pack(side="left", padx=4)

        # Y axis
        row = _frame(parent)
        row.pack(fill="x", pady=4)
        _label(row, "Y axis:", width=12, anchor="w").pack(side="left")
        self._cy_var = tk.StringVar()
        _combo(row, col_options, textvariable=self._cy_var, width=38).pack(side="left", padx=4)

        # Chart type
        row = _frame(parent)
        row.pack(fill="x", pady=4)
        _label(row, "Chart type:", width=12, anchor="w").pack(side="left")
        self._chart_type = tk.StringVar(value="Scatter + Regression")
        _combo(row, ["Scatter + Regression", "Bar Chart", "Scatter (no regression)"],
               textvariable=self._chart_type, width=24).pack(side="left", padx=4)

        # Colour-by
        row = _frame(parent)
        row.pack(fill="x", pady=4)
        _label(row, "Colour by:", width=12, anchor="w").pack(side="left")
        self._color_var = tk.StringVar(value="(none)")
        _combo(row, ["(none)"] + col_options,
               textvariable=self._color_var, width=38).pack(side="left", padx=4)

        _btn(parent, "  📊  GENERATE CHART  ", self._plot_custom,
             color=ACCENT3).pack(pady=10, anchor="w")

        # Info
        _separator(parent).pack(fill="x", pady=6)
        info = (
            "Tips:\n"
            "• Scatter + Regression: adds best-fit line + R²\n"
            "• Bar Chart: groups X values, shows mean Y\n"
            "• Colour by: adds a 3rd dimension via colour\n"
            "• Need ≥ 2 records saved for meaningful charts"
        )
        _label(parent, info, fg=SUBTEXT, justify="left", font=FONT_SMALL).pack(anchor="w")

    def refresh(self):
        pass  # nothing stateful to refresh

    def _get_col(self, var):
        s = var.get()
        if "[" in s:
            return s.split("[")[-1].rstrip("]")
        return None

    def _plot_dashboard(self):
        df = read_dataframe()
        if df.empty:
            messagebox.showwarning("No data", "No records to plot.")
            return
        threading.Thread(target=production_dashboard, args=(df,), daemon=True).start()

    def _plot_haul(self):
        df = read_dataframe()
        if df.empty:
            messagebox.showwarning("No data", "No records to plot.")
            return
        threading.Thread(target=haul_distance_analysis, args=(df,), daemon=True).start()

    def _plot_prod_vs(self):
        df = read_dataframe()
        if df.empty:
            messagebox.showwarning("No data", "No records to plot.")
            return
        threading.Thread(target=productivity_vs_production, args=(df,), daemon=True).start()

    def _plot_corr(self):
        df = read_dataframe()
        if df.empty:
            messagebox.showwarning("No data", "No records to plot.")
            return
        threading.Thread(target=correlation_heatmap, args=(df,), daemon=True).start()

    def _plot_custom(self):
        x_col = self._get_col(self._cx_var)
        y_col = self._get_col(self._cy_var)
        if not x_col or not y_col:
            messagebox.showerror("Error", "Select both X and Y axes.")
            return
        df = read_dataframe()
        if df.empty:
            messagebox.showwarning("No data", "No records to plot.")
            return

        color_raw = self._color_var.get()
        color_col = None
        if color_raw and color_raw != "(none)" and "[" in color_raw:
            color_col = color_raw.split("[")[-1].rstrip("]")

        ctype = self._chart_type.get()

        def _do():
            if ctype == "Bar Chart":
                bar_chart(df, x_col, y_col)
            elif ctype == "Scatter + Regression":
                reg = run_regression(df, x_col, y_col, degree=1)
                scatter_with_regression(df, x_col, y_col,
                                        reg_result=reg if "error" not in reg else None,
                                        color_col=color_col)
            else:
                scatter_with_regression(df, x_col, y_col, color_col=color_col)

        threading.Thread(target=_do, daemon=True).start()


# ─────────────────────────── Entry point ─────────────────────────────

def main():
    app = FleetApp()
    app.mainloop()

if __name__ == "__main__":
    main()
