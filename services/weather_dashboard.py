"""
FloodGuard AI -- Weather Dashboard Service
==========================================
Per-city TTL caching layer for the Live Weather & Forecast page.

Each city has its own cache entry with a 10-minute TTL so that:
  - Switching locations does NOT share a single global cache slot.
  - A forced refresh only re-fetches the selected city, not all cities.
  - Repeated Streamlit reruns do NOT hit the API every time.
  - API failures are stored so the UI can show a clear error state.

Usage:
    from services.weather_dashboard import get_weather_for_city, GUJARAT_CITIES

    rec, error = get_weather_for_city("Vadodara")
    if error:
        st.error(error)
    else:
        st.write(rec["temperature"])

    # Force refresh (on button click):
    rec, error = get_weather_for_city("Ahmedabad", force_refresh=True)
"""
from __future__ import annotations

import time
from datetime import datetime, timezone
from typing import Any

from services.live_weather import (
    fetch_city_weather,
    WeatherFetchError,
    GUJARAT_CITY_COORDS,
)

# Ordered list for the location selector (most important cities first)
GUJARAT_CITIES: list[str] = [
    "Ahmedabad",
    "Surat",
    "Vadodara",
    "Rajkot",
    "Gandhinagar",
    "Bhavnagar",
    "Jamnagar",
    "Junagadh",
    "Anand",
    "Nadiad",
]

# Cache TTL in seconds (10 minutes -- same as LiveDataManager)
_CACHE_TTL = 600

# In-process per-city cache:
#   { city: {"record": dict, "fetched_at": float, "error": str|None} }
_cache: dict[str, dict[str, Any]] = {}


def _is_valid(city: str) -> bool:
    """Return True if this city has a fresh, error-free cache entry."""
    entry = _cache.get(city)
    if not entry:
        return False
    if entry.get("error"):
        return False
    if time.time() - entry.get("fetched_at", 0) > _CACHE_TTL:
        return False
    return bool(entry.get("record"))


def get_weather_for_city(
    city: str,
    force_refresh: bool = False,
    timeout: int = 10,
) -> tuple[dict[str, Any] | None, str | None]:
    """
    Return (WeatherRecord, None) for a valid live fetch,
    or (None, error_message) on failure.

    Caches per city for _CACHE_TTL seconds.
    force_refresh=True bypasses the cache and hits the API immediately.

    Never raises -- all errors are returned as the second tuple element.
    """
    if not force_refresh and _is_valid(city):
        return _cache[city]["record"], None

    try:
        record = fetch_city_weather(city, timeout=timeout)
        _cache[city] = {
            "record":     record,
            "fetched_at": time.time(),
            "error":      None,
        }
        return record, None
    except WeatherFetchError as exc:
        err = str(exc)
        # Keep stale data in place if available; report the error
        _cache.setdefault(city, {})["error"] = err
        stale = _cache[city].get("record")
        if stale:
            return stale, f"Live weather data temporarily unavailable ({err}). Showing last known data."
        return None, f"Live weather data temporarily unavailable: {err}"
    except Exception as exc:
        err = f"Unexpected error: {exc}"
        stale = _cache.get(city, {}).get("record")
        if stale:
            return stale, f"Live weather data temporarily unavailable. Showing last known data."
        return None, err


def cache_age_seconds(city: str) -> float | None:
    """Return how old the cached data is in seconds, or None if not cached."""
    entry = _cache.get(city)
    if not entry or not entry.get("fetched_at"):
        return None
    return round(time.time() - entry["fetched_at"], 0)


def clear_cache(city: str | None = None) -> None:
    """Clear cache for one city or all cities."""
    if city:
        _cache.pop(city, None)
    else:
        _cache.clear()
