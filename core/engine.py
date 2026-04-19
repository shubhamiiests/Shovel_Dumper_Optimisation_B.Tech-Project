"""
core/engine.py — Pure calculation functions (no I/O, no UI)
"""
from math import ceil
from typing import Tuple
from datetime import datetime
import uuid

from core.models import FleetInputs, FleetResults, SimulationRecord


# ─────────────────────────────────────────────
# 1. Individual calculation helpers
# ─────────────────────────────────────────────

def effective_bucket_tons(inp: FleetInputs) -> float:
    """Effective material moved per shovel bucket cycle (tonnes)."""
    effective_m3 = inp.shovel_bucket_m3 * inp.bucket_fill_factor * inp.swing_factor
    return effective_m3 * inp.material_density_t_per_m3


def buckets_per_dumper(inp: FleetInputs, bucket_tons: float) -> int:
    """Integer number of bucket fills needed to load one dumper."""
    return max(1, ceil(inp.dumper_capacity_t / bucket_tons))


def load_time_min(buckets: int, cycle_sec: float) -> float:
    """Total shovel loading time for one dumper (minutes)."""
    return buckets * cycle_sec / 60.0


def travel_times(inp: FleetInputs) -> Tuple[float, float]:
    """Returns (one_way_min, round_trip_min) including unload time."""
    one_way = (inp.distance_km_one_way / max(inp.dumper_speed_kmph, 1e-9)) * 60.0
    rt = 2.0 * one_way + inp.dumper_unload_time_min
    return one_way, rt


def required_dumpers_no_shovel_idle(load_t: float, rt: float) -> int:
    """
    Minimum dumpers per shovel so the shovel never waits:
    (N-1)*LoadTime >= RoundTrip  =>  N >= RoundTrip/LoadTime + 1
    """
    return max(1, ceil(rt / max(load_t, 1e-9) + 1.0))


def idle_analysis(
    trucks_per_shovel: float, load_t: float, rt: float
) -> Tuple[str, float, float]:
    """
    Returns (who_idles, shovel_gap_min, truck_wait_min).
    """
    n = max(1, round(trucks_per_shovel))
    covered = (n - 1) * load_t
    if covered < rt - 1e-9:
        return "Shovel idle", rt - covered, 0.0
    elif covered > rt + 1e-9:
        return "Dumpers idle", 0.0, covered - rt
    else:
        return "Balanced", 0.0, 0.0


def production_tph(
    dumper_cap_t: float, load_t: float, rt: float, trucks_per_shovel: float
) -> float:
    """
    Production per shovel (t/h). Conservative: min(transport-limited, shovel-cadence-limited).
    """
    N = max(1.0, trucks_per_shovel)
    transport_tph = (N * dumper_cap_t) / max(rt, 1e-9) * 60.0

    if N >= 2.0:
        interval = max(load_t, rt / (N - 1.0))
    else:
        interval = load_t + rt

    cadence_tph = dumper_cap_t / max(interval, 1e-9) * 60.0
    return min(transport_tph, cadence_tph)


# ─────────────────────────────────────────────
# 2. Main solver
# ─────────────────────────────────────────────

def solve(inp: FleetInputs) -> SimulationRecord:
    """Compute all outputs for a given FleetInputs and return a SimulationRecord."""

    # Assign identity if missing
    if not inp.session_id:
        inp.session_id = str(uuid.uuid4())[:8].upper()
    if not inp.timestamp:
        inp.timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    bt = effective_bucket_tons(inp)
    bpd = buckets_per_dumper(inp, bt)
    lt = load_time_min(bpd, inp.shovel_cycle_time_sec)
    one_way, rt = travel_times(inp)
    n_req = required_dumpers_no_shovel_idle(lt, rt)
    tps = inp.n_dumpers / max(inp.n_shovels, 1)
    who, s_gap, t_wait = idle_analysis(tps, lt, rt)
    tph_each = production_tph(inp.dumper_capacity_t, lt, rt, tps)
    tph_tot = tph_each * inp.n_shovels

    prod_shift = tph_tot * inp.shift_hours
    prod_day = prod_shift * inp.shifts_per_day
    prod_month = prod_day * inp.days_per_month

    # Fleet efficiency = actual / theoretical_max
    tph_max = production_tph(inp.dumper_capacity_t, lt, rt, float(n_req))
    fleet_eff = (tph_each / max(tph_max, 1e-9)) * 100.0

    # Match ratio (actual dumpers vs required)
    match_ratio = tps / max(n_req, 1)

    res = FleetResults(
        effective_bucket_tons=round(bt, 4),
        buckets_per_dumper=bpd,
        load_time_per_dumper_min=round(lt, 3),
        travel_time_one_way_min=round(one_way, 3),
        round_trip_time_min=round(rt, 3),
        required_dumpers_per_shovel=n_req,
        trucks_per_shovel_actual=round(tps, 3),
        who_idles=who,
        shovel_idle_gap_min_per_cycle=round(s_gap, 3),
        truck_wait_min_per_cycle=round(t_wait, 3),
        tph_per_shovel=round(tph_each, 3),
        tph_total=round(tph_tot, 3),
        production_per_shift_t=round(prod_shift, 1),
        production_per_day_t=round(prod_day, 1),
        production_per_month_t=round(prod_month, 1),
        fleet_efficiency_pct=round(fleet_eff, 2),
        match_ratio=round(match_ratio, 3),
    )

    return SimulationRecord(inputs=inp, results=res)
