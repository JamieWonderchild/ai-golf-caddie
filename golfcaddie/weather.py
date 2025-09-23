from __future__ import annotations

import math
import time
from dataclasses import dataclass
from typing import Optional, Tuple

import httpx


_CACHE: dict[str, tuple[float, float, float]] = {}
_CACHE_TTL_SEC = 60.0


@dataclass
class Wind:
    speed_ms: float
    direction_deg: int  # meteorological: from which it blows
    headwind_ms: float
    crosswind_ms: float
    summary: str


def _cache_key(lat: float, lon: float) -> str:
    return f"{lat:.4f},{lon:.4f}"


def _from_cache(lat: float, lon: float) -> Optional[tuple[float, float]]:
    k = _cache_key(lat, lon)
    if k in _CACHE:
        ts, speed_ms, dir_deg = _CACHE[k]
        if time.time() - ts <= _CACHE_TTL_SEC:
            return speed_ms, dir_deg
    return None


def _store_cache(lat: float, lon: float, speed_ms: float, dir_deg: int) -> None:
    _CACHE[_cache_key(lat, lon)] = (time.time(), speed_ms, dir_deg)


def fetch_current_wind(lat: float, lon: float, *, timeout_sec: float = 2.0) -> tuple[float, int]:
    cached = _from_cache(lat, lon)
    if cached is not None:
        return cached[0], int(cached[1])

    url = (
        "https://api.open-meteo.com/v1/forecast"
        f"?latitude={lat}&longitude={lon}&current=wind_speed_10m,wind_direction_10m&timezone=UTC"
    )
    try:
        with httpx.Client(timeout=timeout_sec) as client:
            resp = client.get(url)
            resp.raise_for_status()
            data = resp.json()
            current = data.get("current", {})
            speed_ms = float(current.get("wind_speed_10m", 0.0))
            direction_deg = int(current.get("wind_direction_10m", 0))
            _store_cache(lat, lon, speed_ms, direction_deg)
            return speed_ms, direction_deg
    except Exception:
        # Fallback to stale cache if available
        if cached is not None:
            return cached[0], int(cached[1])
        # Unknown wind
        return 0.0, 0


def compute_components(speed_ms: float, direction_deg_from: int, target_bearing_deg_to: int) -> tuple[float, float]:
    """Return headwind_ms (positive=headwind) and crosswind_ms (positive pushes ball right-to-left).

    direction_deg_from: meteorological origin (0 = from north, 90 = from east)
    target_bearing_deg_to: azimuth toward target (0 = north, 90 = east)
    """
    # Wind vector blowing from direction_deg_from means it blows toward direction_deg_from + 180
    wind_to_deg = (direction_deg_from + 180) % 360
    # Angle between wind-to vector and target bearing
    theta = math.radians((wind_to_deg - target_bearing_deg_to) % 360)
    # Normalize to [-pi, pi]
    if theta > math.pi:
        theta -= 2 * math.pi
    # Positive headwind when wind opposes target (against ball flight)
    headwind_ms = -speed_ms * math.cos(theta)
    # Positive crosswind when pushing right-to-left relative to target direction
    crosswind_ms = -speed_ms * math.sin(theta)
    return headwind_ms, crosswind_ms


def summarize_wind(speed_ms: float, headwind_ms: float, crosswind_ms: float) -> str:
    mph = speed_ms * 2.23694
    parts = [f"{mph:.0f} mph"]
    if abs(headwind_ms) < 0.5:
        parts.append("neutral wind")
    elif headwind_ms > 0:
        parts.append("headwind")
    else:
        parts.append("tailwind")
    if abs(crosswind_ms) >= 0.5:
        parts.append("right-to-left" if crosswind_ms > 0 else "left-to-right")
    return ", ".join(parts)


def get_wind(lat: float, lon: float, target_bearing_deg_to: int) -> Wind:
    speed_ms, dir_from = fetch_current_wind(lat, lon)
    head, cross = compute_components(speed_ms, dir_from, target_bearing_deg_to)
    return Wind(
        speed_ms=speed_ms,
        direction_deg=dir_from,
        headwind_ms=head,
        crosswind_ms=cross,
        summary=summarize_wind(speed_ms, head, cross),
    )


