"""
FloodGuard AI — Live Data Manager
===================================
Central orchestrator for the live-data intelligence layer.

Responsibilities:
  1. Attempt to fetch live weather from Open-Meteo for Ahmedabad & Surat.
  2. Validate freshness of the cached result.
  3. Serve live data when available; fall back to DEMO automatically.
  4. Expose a clear LIVE / DEMO status that the UI can display.
  5. Convert live weather records into the same schema as the existing
     seed_generator rainfall records so the pipeline receives them seamlessly.
  6. Never crash — all failures are caught and result in DEMO mode.

IMPORTANT DISTINCTION (do not conflate these):
  LIVE WEATHER EVIDENCE   — actual observed rainfall / weather from Open-Meteo
  MODEL FLOOD PREDICTION  — ML/rule-based risk zones (always labeled as DEMO/MODEL)
  DEMO SYNTHETIC DATA     — fallback data from data/seed_generator.py

Usage:
    manager = get_live_data_manager()
    status  = manager.get_status()          # LIVE / DEMO with metadata
    weather = manager.get_city_weather("Ahmedabad")   # WeatherRecord or None
    rf_recs = manager.get_rainfall_records("All")     # pipeline-compatible list
    manager.refresh()                       # force a new fetch (respects TTL)
"""
from __future__ import annotations

import time
from datetime import datetime, timezone
from typing import Any

# Config imports with graceful fallback for direct module execution
try:
    from backend.config import (
        LIVE_WEATHER_ENABLED,
        LIVE_DATA_CACHE_TTL,
        LIVE_DATA_REQUEST_TIMEOUT,
        LIVE_DATA_STALE_THRESHOLD,
        DEMO_MODE,
    )
except ImportError:
    try:
        from config import (
            LIVE_WEATHER_ENABLED,
            LIVE_DATA_CACHE_TTL,
            LIVE_DATA_REQUEST_TIMEOUT,
            LIVE_DATA_STALE_THRESHOLD,
            DEMO_MODE,
        )
    except ImportError:
        LIVE_WEATHER_ENABLED    = True
        LIVE_DATA_CACHE_TTL     = 600
        LIVE_DATA_REQUEST_TIMEOUT = 8
        LIVE_DATA_STALE_THRESHOLD = 1800
        DEMO_MODE               = True

try:
    from services.live_weather import fetch_all_cities, WeatherFetchError, CITY_COORDS
except ImportError:
    from live_weather import fetch_all_cities, WeatherFetchError, CITY_COORDS


# ──────────────────────────────────────────────────────────────────────────────
# Data mode constants
# ──────────────────────────────────────────────────────────────────────────────
DATA_MODE_LIVE = "LIVE"
DATA_MODE_DEMO = "DEMO"


class LiveDataManager:
    """
    Manages live vs DEMO weather data for Ahmedabad & Surat.

    Cache structure:
        _cache = {
            "fetched_at":  float (epoch),
            "data":        {"Ahmedabad": record, "Surat": record},
            "errors":      {"Ahmedabad": str|None, "Surat": str|None},
        }
    """

    def __init__(
        self,
        enabled: bool = True,
        cache_ttl: int = 600,
        request_timeout: int = 8,
        stale_threshold: int = 1800,
    ):
        self._enabled        = enabled and not DEMO_MODE
        self._cache_ttl      = cache_ttl
        self._request_timeout = request_timeout
        self._stale_threshold = stale_threshold

        self._cache: dict[str, Any] = {}
        self._last_error: str       = ""

    # ──────────────────────────────────────────────────────────────────────
    # Internal helpers
    # ──────────────────────────────────────────────────────────────────────

    def _cache_age(self) -> float:
        """Seconds since the last successful fetch, or infinity if never fetched."""
        fetched_at = self._cache.get("fetched_at", 0)
        return time.time() - fetched_at if fetched_at else float("inf")

    def _cache_valid(self) -> bool:
        """True if cached data exists and is within TTL."""
        return bool(self._cache.get("data")) and self._cache_age() < self._cache_ttl

    def _cache_stale(self) -> bool:
        """True if cached data is older than the stale threshold."""
        return self._cache_age() >= self._stale_threshold

    def _do_fetch(self) -> None:
        """Attempt a live fetch and update the cache. Silently swallows all errors."""
        try:
            result = fetch_all_cities(timeout=self._request_timeout)
            self._cache = {
                "fetched_at": time.time(),
                "data":  {
                    "Ahmedabad": result.get("Ahmedabad"),
                    "Surat":     result.get("Surat"),
                },
                "errors": result.get("errors", {}),
            }
            self._last_error = ""
        except Exception as exc:
            self._last_error = str(exc)
            # Keep stale cache in place if it exists

    # ──────────────────────────────────────────────────────────────────────
    # Public API
    # ──────────────────────────────────────────────────────────────────────

    def refresh(self, force: bool = False) -> None:
        """
        Refresh live data if the cache is stale or force=True.
        Always safe to call — never raises.
        """
        if not self._enabled:
            return
        if force or not self._cache_valid():
            self._do_fetch()

    def get_city_weather(self, city: str) -> dict[str, Any] | None:
        """
        Return the live weather record for a city, or None if unavailable.

        Automatically refreshes if the cache has expired.
        """
        if not self._enabled:
            return None
        if not self._cache_valid():
            self._do_fetch()
        data = self._cache.get("data", {})
        return data.get(city) if isinstance(data, dict) else None

    def get_all_weather(self) -> dict[str, dict[str, Any] | None]:
        """Return weather records for all in-scope cities."""
        return {city: self.get_city_weather(city) for city in CITY_COORDS}

    def get_rainfall_records(self, city_filter: str = "All") -> list[dict[str, Any]]:
        """
        Convert live weather records into the pipeline-compatible rainfall
        schema used by seed_generator.generate_rainfall_data().

        Returns [] if live data is unavailable — callers should fall back
        to seed_generator output in that case.

        Pipeline schema keys used:
            city, area, latitude, longitude,
            rainfall_1h, rainfall_3h, rainfall_6h, rainfall_24h,
            recorded_at, data_source
        """
        records: list[dict[str, Any]] = []

        cities = list(CITY_COORDS.keys()) if city_filter == "All" else [city_filter]
        for city in cities:
            if city not in CITY_COORDS:
                continue
            record = self.get_city_weather(city)
            if record is None:
                continue
            # Map to pipeline schema
            records.append({
                "city":         city,
                "area":         city,               # city-level observation
                "latitude":     record["latitude"],
                "longitude":    record["longitude"],
                "rainfall_1h":  record.get("rainfall_1h", 0.0),
                "rainfall_3h":  record.get("rainfall_3h", 0.0),
                "rainfall_6h":  record.get("rainfall_6h", 0.0),
                "rainfall_24h": record.get("rainfall_24h", 0.0),
                "recorded_at":  record.get("recorded_at", ""),
                "data_source":  "Open-Meteo (LIVE)",
                # Extra metadata (not used by pipeline but useful for UI)
                "temperature":              record.get("temperature"),
                "precipitation_probability": record.get("precipitation_probability"),
                "wind_speed":               record.get("wind_speed"),
                "condition":                record.get("condition"),
                "is_live":                  True,
                "fetched_at":               record.get("fetched_at", ""),
            })
        return records

    def get_status(self) -> dict[str, Any]:
        """
        Return a structured status dict for UI display.

        Keys:
            data_mode:      "LIVE" | "DEMO"
            is_live:        bool
            source:         str
            source_url:     str
            last_updated:   str (ISO timestamp or "Never")
            cache_age_sec:  float | None
            is_stale:       bool
            fallback_reason: str (empty if LIVE)
            cities:         {"Ahmedabad": {...}, "Surat": {...}}
        """
        now_iso = datetime.now(timezone.utc).isoformat()

        if not self._enabled:
            reason = "DEMO_MODE=true in config" if DEMO_MODE else "LIVE_WEATHER_ENABLED=false"
            return self._demo_status(reason)

        data = self._cache.get("data", {})
        errors = self._cache.get("errors", {})
        fetched_at = self._cache.get("fetched_at", 0)

        ahm_ok = isinstance(data.get("Ahmedabad"), dict)
        srt_ok = isinstance(data.get("Surat"), dict)
        any_live = ahm_ok or srt_ok

        if not any_live:
            reason = self._last_error or "No live data fetched yet"
            return self._demo_status(reason)

        last_updated = (
            datetime.fromtimestamp(fetched_at, tz=timezone.utc).isoformat()
            if fetched_at else "Unknown"
        )

        def _city_info(city: str) -> dict:
            rec = data.get(city)
            err = errors.get(city)
            if rec:
                return {
                    "available":    True,
                    "rainfall_1h":  rec.get("rainfall_1h"),
                    "condition":    rec.get("condition"),
                    "temperature":  rec.get("temperature"),
                    "precip_prob":  rec.get("precipitation_probability"),
                    "wind_speed":   rec.get("wind_speed"),
                    "recorded_at":  rec.get("recorded_at", ""),
                    "is_stale":     self._cache_stale(),
                }
            return {"available": False, "error": err}

        return {
            "data_mode":     DATA_MODE_LIVE,
            "is_live":       True,
            "source":        "Open-Meteo",
            "source_url":    "https://open-meteo.com",
            "last_updated":  last_updated,
            "cache_age_sec": round(self._cache_age(), 0) if fetched_at else None,
            "is_stale":      self._cache_stale(),
            "fallback_reason": "",
            "cities": {
                "Ahmedabad": _city_info("Ahmedabad"),
                "Surat":     _city_info("Surat"),
            },
        }

    def _demo_status(self, reason: str) -> dict[str, Any]:
        return {
            "data_mode":       DATA_MODE_DEMO,
            "is_live":         False,
            "source":          "Synthetic (seed_generator.py)",
            "source_url":      "",
            "last_updated":    "N/A — using DEMO data",
            "cache_age_sec":   None,
            "is_stale":        False,
            "fallback_reason": reason,
            "cities": {
                "Ahmedabad": {"available": False, "error": reason},
                "Surat":     {"available": False, "error": reason},
            },
        }

    def weather_to_map_points(self, city_filter: str = "All") -> list[dict[str, Any]]:
        """
        Convert live weather records to the map_component weather_data schema.

        Map schema keys:
            city, area, latitude, longitude,
            rainfall_1h, rainfall_6h, condition, source, is_live, recorded_at
        """
        points = []
        cities = list(CITY_COORDS.keys()) if city_filter == "All" else [city_filter]
        for city in cities:
            if city not in CITY_COORDS:
                continue
            rec = self.get_city_weather(city)
            if rec is None:
                continue
            points.append({
                "city":         city,
                "area":         city,
                "latitude":     rec["latitude"],
                "longitude":    rec["longitude"],
                "rainfall_1h":  rec.get("rainfall_1h", 0.0),
                "rainfall_6h":  rec.get("rainfall_6h", 0.0),
                "condition":    rec.get("condition", ""),
                "source":       "Open-Meteo",
                "is_live":      True,
                "recorded_at":  rec.get("recorded_at", ""),
                "temperature":  rec.get("temperature"),
                "precip_prob":  rec.get("precipitation_probability"),
                "wind_speed":   rec.get("wind_speed"),
            })
        return points


# ──────────────────────────────────────────────────────────────────────────────
# Module-level singleton
# ──────────────────────────────────────────────────────────────────────────────
_manager: LiveDataManager | None = None


def get_live_data_manager() -> LiveDataManager:
    """
    Return the module-level singleton LiveDataManager.

    The first call creates the instance and triggers an initial fetch
    (if live mode is enabled).
    """
    global _manager
    if _manager is None:
        _manager = LiveDataManager(
            enabled=LIVE_WEATHER_ENABLED,
            cache_ttl=LIVE_DATA_CACHE_TTL,
            request_timeout=LIVE_DATA_REQUEST_TIMEOUT,
            stale_threshold=LIVE_DATA_STALE_THRESHOLD,
        )
        # Eagerly populate cache on first access
        _manager.refresh()
    return _manager


def reset_live_data_manager() -> None:
    """Reset the singleton (useful for testing)."""
    global _manager
    _manager = None
