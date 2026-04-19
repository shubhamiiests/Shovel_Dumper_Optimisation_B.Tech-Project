"""
core/models.py — Data models (dataclasses) for Fleet Optimization
"""
from dataclasses import dataclass, field, asdict
from datetime import datetime
from math import ceil
from typing import Optional


@dataclass
class FleetInputs:
    """All user-supplied parameters for one simulation run."""
    # Identity
    session_id: str = ""
    timestamp: str = ""

    # Fleet
    n_shovels: int = 1
    n_dumpers: int = 5

    # Capacities
    shovel_bucket_m3: float = 10.0
    dumper_capacity_t: float = 50.0

    # Factors & material
    bucket_fill_factor: float = 0.80
    swing_factor: float = 0.80
    material_density_t_per_m3: float = 1.40

    # Times & speeds
    shovel_cycle_time_sec: float = 90.0
    dumper_speed_kmph: float = 30.0
    distance_km_one_way: float = 2.0
    dumper_unload_time_min: float = 2.0

    # Accounting horizon
    shift_hours: float = 6.0
    shifts_per_day: int = 3
    days_per_month: int = 30

    def to_dict(self) -> dict:
        return asdict(self)

    @classmethod
    def from_dict(cls, d: dict) -> "FleetInputs":
        valid = {k: v for k, v in d.items() if k in cls.__dataclass_fields__}
        return cls(**valid)


@dataclass
class FleetResults:
    """Computed outputs for one simulation run."""
    effective_bucket_tons: float = 0.0
    buckets_per_dumper: int = 0
    load_time_per_dumper_min: float = 0.0
    travel_time_one_way_min: float = 0.0
    round_trip_time_min: float = 0.0
    required_dumpers_per_shovel: int = 0
    trucks_per_shovel_actual: float = 0.0
    who_idles: str = ""
    shovel_idle_gap_min_per_cycle: float = 0.0
    truck_wait_min_per_cycle: float = 0.0
    tph_per_shovel: float = 0.0
    tph_total: float = 0.0
    production_per_shift_t: float = 0.0
    production_per_day_t: float = 0.0
    production_per_month_t: float = 0.0
    fleet_efficiency_pct: float = 0.0
    match_ratio: float = 0.0

    def to_dict(self) -> dict:
        return asdict(self)

    @classmethod
    def from_dict(cls, d: dict) -> "FleetResults":
        valid = {k: v for k, v in d.items() if k in cls.__dataclass_fields__}
        return cls(**valid)


@dataclass
class SimulationRecord:
    """One full record = inputs + results, stored to CSV."""
    inputs: FleetInputs
    results: FleetResults

    def to_flat_dict(self) -> dict:
        d = {}
        d.update(self.inputs.to_dict())
        d.update(self.results.to_dict())
        return d

    @classmethod
    def from_flat_dict(cls, d: dict) -> "SimulationRecord":
        inp = FleetInputs.from_dict(d)
        res = FleetResults.from_dict(d)
        return cls(inputs=inp, results=res)
