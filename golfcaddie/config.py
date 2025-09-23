from __future__ import annotations

import os
from dataclasses import dataclass
from typing import Optional

from dotenv import load_dotenv


@dataclass
class AppConfig:
    speechmatics_api_key: str
    db_path: str = "./app.db"
    course_lat: Optional[float] = None
    course_lon: Optional[float] = None
    use_llm_humor: bool = False
    tts_enabled: bool = False
    log_level: str = "INFO"
    bins_distance_yards: int = 10
    wind_head_bands_ms: str = "0,2,4,6,8"
    go_to_min_attempts: int = 4
    go_to_min_hitrate: float = 0.6
    go_to_max_prox_ft: float = 20.0


_cached_config: Optional[AppConfig] = None


def _env_bool(name: str, default: bool) -> bool:
    val = os.getenv(name)
    if val is None:
        return default
    return val.lower() in {"1", "true", "yes", "on"}


def load_config() -> AppConfig:
    global _cached_config
    if _cached_config is not None:
        return _cached_config

    load_dotenv(override=False)

    api_key = os.getenv("SPEECHMATICS_API_KEY")
    if not api_key:
        raise RuntimeError(
            "SPEECHMATICS_API_KEY is required. Set it in environment or .env"
        )

    def _get_float(name: str) -> Optional[float]:
        val = os.getenv(name)
        if val is None or val == "":
            return None
        try:
            return float(val)
        except ValueError:
            raise RuntimeError(f"Invalid float for {name}: {val}")

    cfg = AppConfig(
        speechmatics_api_key=api_key,
        db_path=os.getenv("DB_PATH", "./app.db"),
        course_lat=_get_float("COURSE_LAT"),
        course_lon=_get_float("COURSE_LON"),
        use_llm_humor=_env_bool("USE_LLM_HUMOR", False),
        tts_enabled=_env_bool("TTS_ENABLED", False),
        log_level=os.getenv("LOG_LEVEL", "INFO"),
        bins_distance_yards=int(os.getenv("BINS_DISTANCE_YARDS", "10")),
        wind_head_bands_ms=os.getenv("WIND_HEAD_BANDS_MS", "0,2,4,6,8"),
        go_to_min_attempts=int(os.getenv("GO_TO_MIN_ATTEMPTS", "4")),
        go_to_min_hitrate=float(os.getenv("GO_TO_MIN_HITRATE", "0.6")),
        go_to_max_prox_ft=float(os.getenv("GO_TO_MAX_PROX_FT", "20")),
    )

    _cached_config = cfg
    return cfg


def reload_config() -> AppConfig:
    global _cached_config
    _cached_config = None
    return load_config()


