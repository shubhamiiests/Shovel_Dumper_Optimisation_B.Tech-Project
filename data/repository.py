"""
data/repository.py — CRUD operations for SimulationRecord ↔ CSV
"""
from __future__ import annotations
import os
import csv
from typing import List, Optional
import pandas as pd
from datetime import datetime

from core.models import FleetInputs, FleetResults, SimulationRecord

CSV_PATH = os.path.join(os.path.dirname(__file__), "fleet_data.csv")

# All columns in the flat CSV (inputs first, then results)
INPUT_COLS = [
    "session_id", "timestamp",
    "n_shovels", "n_dumpers",
    "shovel_bucket_m3", "dumper_capacity_t",
    "bucket_fill_factor", "swing_factor", "material_density_t_per_m3",
    "shovel_cycle_time_sec", "dumper_speed_kmph",
    "distance_km_one_way", "dumper_unload_time_min",
    "shift_hours", "shifts_per_day", "days_per_month",
]

RESULT_COLS = [
    "effective_bucket_tons", "buckets_per_dumper",
    "load_time_per_dumper_min", "travel_time_one_way_min", "round_trip_time_min",
    "required_dumpers_per_shovel", "trucks_per_shovel_actual",
    "who_idles",
    "shovel_idle_gap_min_per_cycle", "truck_wait_min_per_cycle",
    "tph_per_shovel", "tph_total",
    "production_per_shift_t", "production_per_day_t", "production_per_month_t",
    "fleet_efficiency_pct", "match_ratio",
]

ALL_COLS = INPUT_COLS + RESULT_COLS

# Human-friendly labels (for UI / graphs)
COL_LABELS = {
    "session_id": "Session ID",
    "timestamp": "Timestamp",
    "n_shovels": "No. of Shovels",
    "n_dumpers": "No. of Dumpers",
    "shovel_bucket_m3": "Shovel Bucket (m³)",
    "dumper_capacity_t": "Dumper Capacity (t)",
    "bucket_fill_factor": "Bucket Fill Factor",
    "swing_factor": "Swing Factor",
    "material_density_t_per_m3": "Material Density (t/m³)",
    "shovel_cycle_time_sec": "Shovel Cycle Time (s)",
    "dumper_speed_kmph": "Dumper Speed (km/h)",
    "distance_km_one_way": "Haul Distance One-way (km)",
    "dumper_unload_time_min": "Dumper Unload Time (min)",
    "shift_hours": "Shift Length (h)",
    "shifts_per_day": "Shifts per Day",
    "days_per_month": "Days per Month",
    "effective_bucket_tons": "Effective Bucket Load (t)",
    "buckets_per_dumper": "Buckets per Dumper Load",
    "load_time_per_dumper_min": "Load Time per Dumper (min)",
    "travel_time_one_way_min": "Travel Time One-way (min)",
    "round_trip_time_min": "Round-trip Time (min)",
    "required_dumpers_per_shovel": "Required Dumpers per Shovel",
    "trucks_per_shovel_actual": "Actual Trucks per Shovel",
    "who_idles": "Idle Party",
    "shovel_idle_gap_min_per_cycle": "Shovel Idle Gap (min/cycle)",
    "truck_wait_min_per_cycle": "Truck Wait Time (min/cycle)",
    "tph_per_shovel": "Production per Shovel (t/h)",
    "tph_total": "Total Fleet Production (t/h)",
    "production_per_shift_t": "Production per Shift (t)",
    "production_per_day_t": "Production per Day (t)",
    "production_per_month_t": "Production per Month (t)",
    "fleet_efficiency_pct": "Fleet Efficiency (%)",
    "match_ratio": "Fleet Match Ratio",
}

# Numeric columns only (for graphs / regression)
NUMERIC_COLS = [c for c in ALL_COLS if c not in ("session_id", "timestamp", "who_idles")]


def _ensure_file():
    if not os.path.exists(CSV_PATH):
        with open(CSV_PATH, "w", newline="") as f:
            writer = csv.DictWriter(f, fieldnames=ALL_COLS)
            writer.writeheader()


def create(record: SimulationRecord) -> SimulationRecord:
    """Append a record to CSV. Returns the record (with session_id / timestamp filled)."""
    _ensure_file()
    row = record.to_flat_dict()
    # Fill any missing keys with empty string
    for col in ALL_COLS:
        row.setdefault(col, "")
    with open(CSV_PATH, "a", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=ALL_COLS)
        writer.writerow({k: row[k] for k in ALL_COLS})
    return record


def read_all() -> List[SimulationRecord]:
    """Read all records from CSV."""
    _ensure_file()
    df = pd.read_csv(CSV_PATH, dtype=str)
    records = []
    for _, row in df.iterrows():
        try:
            r = SimulationRecord.from_flat_dict(_cast_row(row.to_dict()))
            records.append(r)
        except Exception:
            continue
    return records


def read_dataframe() -> pd.DataFrame:
    """Return full CSV as a typed pandas DataFrame."""
    _ensure_file()
    if os.path.getsize(CSV_PATH) == 0:
        return pd.DataFrame(columns=ALL_COLS)
    df = pd.read_csv(CSV_PATH)
    for col in NUMERIC_COLS:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors="coerce")
    return df


def read_by_id(session_id: str) -> Optional[SimulationRecord]:
    """Fetch a single record by session_id."""
    for r in read_all():
        if r.inputs.session_id == session_id:
            return r
    return None


def update(session_id: str, record: SimulationRecord) -> bool:
    """Replace a record matching session_id. Returns True if found."""
    records = read_all()
    found = False
    for i, r in enumerate(records):
        if r.inputs.session_id == session_id:
            records[i] = record
            found = True
            break
    if found:
        _write_all(records)
    return found


def delete(session_id: str) -> bool:
    """Delete a record by session_id. Returns True if found."""
    records = read_all()
    new_records = [r for r in records if r.inputs.session_id != session_id]
    if len(new_records) < len(records):
        _write_all(new_records)
        return True
    return False


def _write_all(records: List[SimulationRecord]):
    _ensure_file()
    with open(CSV_PATH, "w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=ALL_COLS)
        writer.writeheader()
        for r in records:
            row = r.to_flat_dict()
            writer.writerow({k: row.get(k, "") for k in ALL_COLS})


def _cast_row(row: dict) -> dict:
    """Cast CSV string values to appropriate Python types."""
    int_cols = {"n_shovels", "n_dumpers", "buckets_per_dumper",
                "required_dumpers_per_shovel", "shifts_per_day", "days_per_month"}
    float_cols = set(NUMERIC_COLS) - int_cols
    out = {}
    for k, v in row.items():
        if k in int_cols:
            try:
                out[k] = int(float(v))
            except (ValueError, TypeError):
                out[k] = 0
        elif k in float_cols:
            try:
                out[k] = float(v)
            except (ValueError, TypeError):
                out[k] = 0.0
        else:
            out[k] = str(v) if v is not None else ""
    return out
