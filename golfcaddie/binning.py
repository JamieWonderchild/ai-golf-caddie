from __future__ import annotations

from dataclasses import dataclass
from typing import Optional


@dataclass(frozen=True)
class ContextBins:
    distance_bin: int
    wind_bin: str
    handicap_bin: Optional[str] = None
    performance_expectation: Optional[str] = None


def bin_distance_yards(distance_yards: int, bin_size: int = 10) -> int:
    if bin_size <= 0:
        raise ValueError("bin_size must be positive")
    # Round to nearest lower multiple of bin_size
    return (max(0, int(distance_yards)) // bin_size) * bin_size


def bin_wind_components(headwind_ms: float, crosswind_ms: float) -> str:
    """Create a compact wind bin label.

    - Headwind/tailwind magnitude bucketed to nearest 2 m/s.
    - Crosswind bucketed similarly with side encoded (L/R)
    """
    def bucket(v: float, step: int = 2) -> int:
        return int(abs(v) // step * step)

    head_bucket = bucket(headwind_ms)
    cross_bucket = bucket(crosswind_ms)
    head_dir = "head" if headwind_ms >= 0 else "tail"
    cross_dir = "R" if crosswind_ms > 0 else ("L" if crosswind_ms < 0 else "0")
    return f"{head_dir}_{head_bucket}|cross_{cross_bucket}{cross_dir}"


def bin_handicap(handicap: int) -> str:
    """Bin handicap into skill categories."""
    if handicap == 0:
        return "scratch"
    elif 1 <= handicap <= 5:
        return "low_single"
    elif 6 <= handicap <= 9:
        return "high_single"
    elif 10 <= handicap <= 15:
        return "low_double"
    elif 16 <= handicap <= 20:
        return "high_double"
    else:
        return "high_handicap"


def get_performance_expectation(distance_yards: int, handicap: int) -> str:
    """Get performance expectation string for distance/handicap combination."""
    try:
        from .statistics import get_golf_statistics
        golf_stats = get_golf_statistics()
        stats = golf_stats.get_stats(handicap)
        if not stats:
            return "unknown"
        
        gir_pct = stats.greens_in_regulation.get_gir_percentage(distance_yards)
        proximity = stats.proximity_to_target.get_expected_proximity(distance_yards)
        
        if gir_pct >= 50:
            return f"high_gir_{gir_pct}pct_{proximity}ft"
        elif gir_pct >= 25:
            return f"med_gir_{gir_pct}pct_{proximity}ft"
        else:
            return f"low_gir_{gir_pct}pct_{proximity}ft"
    except Exception:
        return "unknown"


def compute_context_bins(distance_yards: int, headwind_ms: float, crosswind_ms: float, 
                        handicap: Optional[int] = None, bin_size: int = 10) -> ContextBins:
    handicap_bin = bin_handicap(handicap) if handicap is not None else None
    performance_expectation = get_performance_expectation(distance_yards, handicap) if handicap is not None else None
    
    return ContextBins(
        distance_bin=bin_distance_yards(distance_yards, bin_size),
        wind_bin=bin_wind_components(headwind_ms, crosswind_ms),
        handicap_bin=handicap_bin,
        performance_expectation=performance_expectation,
    )


