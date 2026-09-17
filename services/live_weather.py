"""
FloodGuard AI -- Live Weather Service
=====================================
Fetches current + hourly + 7-day forecast weather data for Gujarat cities
via the Open-Meteo public API (no API key required).

Supported cities: Ahmedabad, Surat, Vadodara, Rajkot, Gandhinagar,
                  Bhavnagar, Jamnagar, Junagadh, Anand, Nadiad.

Primary scope for flood pipeline: Ahmedabad & Surat.
Additional cities: available for the Live Weather & Forecast dashboard only.

Design principles:
  - Never crashes Streamlit: every network/parsing failure is caught.
  - Returns a validated, normalised dict or raises WeatherFetchError.
  - Callers should use LiveDataManager / WeatherDashboard for caching.
  - Clearly distinguishes LIVE weather evidence from flood predictions.
    Live weather = "Live Weather Evidence", NOT "Live Flood Location".

Open-Meteo endpoint:
    https://api.open-meteo.com/v1/forecast
    No authentication required. Free for non-commercial use.
    See: https://open-meteo.com/en/docs
"""
from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

import httpx

# ──────────────────────────────────────────────────────────────────────────────
# City geography
# Primary (flood pipeline): Ahmedabad, Surat
# Extended (weather dashboard): additional Gujarat cities
# ──────────────────────────────────────────────────────────────────────────────
CITY_COORDS: dict[str, dict[str, float]] = {
    "Ahmedabad": {"lat": 23.0225, "lon": 72.5714},
    "Surat":     {"lat": 21.1702, "lon": 72.8311},
}

# Full Gujarat city list for the weather dashboard
GUJARAT_CITY_COORDS: dict[str, dict[str, float]] = {
    "Ahmedabad":   {"lat": 23.0225, "lon": 72.5714},
    "Surat":       {"lat": 21.1702, "lon": 72.8311},
    "Vadodara":    {"lat": 22.3072, "lon": 73.1812},
    "Rajkot":      {"lat": 22.3039, "lon": 70.8022},
    "Gandhinagar": {"lat": 23.2156, "lon": 72.6369},
    "Bhavnagar":   {"lat": 21.7645, "lon": 72.1519},
    "Jamnagar":    {"lat": 22.4707, "lon": 70.0577},
    "Junagadh":    {"lat": 21.5222, "lon": 70.4579},
    "Anand":       {"lat": 22.5645, "lon": 72.9289},
    "Nadiad":      {"lat": 22.6942, "lon": 72.8634},
}

# WMO weather interpretation codes -> human-readable label
# Reference: https://open-meteo.com/en/docs#weathervariables
_WMO_CONDITIONS: dict[int, str] = {
    0:  "Clear Sky",
    1:  "Mainly Clear",
    2:  "Partly Cloudy",
    3:  "Overcast",
    45: "Foggy",
    48: "Icy Fog",
    51: "Light Drizzle",
    53: "Moderate Drizzle",
    55: "Heavy Drizzle",
    61: "Slight Rain",
    63: "Moderate Rain",
    65: "Heavy Rain",
    71: "Slight Snowfall",
    73: "Moderate Snowfall",
    75: "Heavy Snowfall",
    80: "Slight Rain Shower",
    81: "Moderate Rain Shower",
    82: "Violent Rain Shower",
    95: "Thunderstorm",
    96: "Thunderstorm with Hail",
    99: "Thunderstorm with Heavy Hail",
}

# WMO code -> emoji
WMO_EMOJI: dict[int, str] = {
    0: "\u2600\ufe0f", 1: "\U0001f324\ufe0f", 2: "\u26c5", 3: "\u2601\ufe0f",
    45: "\U0001f32b\ufe0f", 48: "\U0001f32b\ufe0f",
    51: "\U0001f326\ufe0f", 53: "\U0001f326\ufe0f", 55: "\U0001f327\ufe0f",
    61: "\U0001f327\ufe0f", 63: "\U0001f327\ufe0f", 65: "\U0001f327\ufe0f",
    71: "\U0001f328\ufe0f", 73: "\U0001f328\ufe0f", 75: "\u2744\ufe0f",
    80: "\U0001f326\ufe0f", 81: "\U0001f327\ufe0f", 82: "\u26c8\ufe0f",
    95: "\u26c8\ufe0f", 96: "\u26c8\ufe0f", 99: "\u26c8\ufe0f",
}

# Open-Meteo hourly variables (full set for weather dashboard)
_HOURLY_VARS = [
    "temperature_2m",
    "precipitation",
    "precipitation_probability",
    "rain",
    "windspeed_10m",
    "winddirection_10m",
    "weathercode",
]

# Current-condition variables (extended: adds humidity + wind direction)
_CURRENT_VARS = [
    "temperature_2m",
    "precipitation",
    "rain",
    "windspeed_10m",
    "winddirection_10m",
    "relativehumidity_2m",
    "weathercode",
]

# 7-day daily forecast variables
_DAILY_VARS = [
    "temperature_2m_max",
    "temperature_2m_min",
    "precipitation_sum",
    "precipitation_probability_max",
    "windspeed_10m_max",
    "weathercode",
]

# Reasonable numeric bounds for validation
_BOUNDS: dict[str, tuple[float, float]] = {
    "temperature_2m":            (-10.0, 55.0),
    "precipitation":             (0.0, 300.0),
    "rain":                      (0.0, 300.0),
    "windspeed_10m":             (0.0, 200.0),
    "winddirection_10m":         (0.0, 360.0),
    "relativehumidity_2m":       (0.0, 100.0),
    "precipitation_probability": (0.0, 100.0),
}


def wmo_emoji(code: Any) -> str:
    """Return weather emoji for a WMO code."""
    try:
        return WMO_EMOJI.get(int(code), "\U0001f321\ufe0f")
    except (TypeError, ValueError):
        return "\U0001f321\ufe0f"


class WeatherFetchError(Exception):
    """Raised when live weather data cannot be fetched or validated."""


# ──────────────────────────────────────────────────────────────────────────────
# Low-level fetch
# ──────────────────────────────────────────────────────────────────────────────

def _fetch_open_meteo(
    city: str,
    timeout: int = 8,
    forecast_days: int = 7,
) -> dict[str, Any]:
    """
    Fetch current + hourly + 7-day daily from Open-Meteo for any Gujarat city.

    Returns raw API response dict.
    Raises WeatherFetchError on any network or HTTP error.
    """
    coords = GUJARAT_CITY_COORDS.get(city)
    if coords is None:
        raise WeatherFetchError(
            f"City '{city}' is not in the Gujarat city list."
        )

    params = {
        "latitude":      coords["lat"],
        "longitude":     coords["lon"],
        "current":       ",".join(_CURRENT_VARS),
        "hourly":        ",".join(_HOURLY_VARS),
        "daily":         ",".join(_DAILY_VARS),
        "forecast_days": forecast_days,
        "timezone":      "Asia/Kolkata",
    }

    try:
        response = httpx.get(
            "https://api.open-meteo.com/v1/forecast",
            params=params,
            timeout=timeout,
        )
        response.raise_for_status()
        return response.json()
    except httpx.TimeoutException as exc:
        raise WeatherFetchError(f"Open-Meteo timed out after {timeout}s") from exc
    except httpx.HTTPStatusError as exc:
        raise WeatherFetchError(
            f"Open-Meteo returned HTTP {exc.response.status_code}"
        ) from exc
    except httpx.RequestError as exc:
        raise WeatherFetchError(f"Network error reaching Open-Meteo: {exc}") from exc
    except Exception as exc:
        raise WeatherFetchError(f"Unexpected error: {exc}") from exc


# ──────────────────────────────────────────────────────────────────────────────
# Validation helpers
# ──────────────────────────────────────────────────────────────────────────────

def _validate_numeric(value: Any, field: str) -> float:
    try:
        v = float(value)
    except (TypeError, ValueError) as exc:
        raise WeatherFetchError(f"Field '{field}' not numeric: {value!r}") from exc
    lo, hi = _BOUNDS.get(field, (-1e9, 1e9))
    if not (lo <= v <= hi):
        raise WeatherFetchError(
            f"Field '{field}' value {v} outside [{lo}, {hi}]"
        )
    return v


def _wmo_to_condition(code: Any) -> str:
    try:
        return _WMO_CONDITIONS.get(int(code), f"Weather code {code}")
    except (TypeError, ValueError):
        return "Unknown"


def _safe_float(value: Any, default: float = 0.0) -> float:
    try:
        v = float(value)
        return v if v == v else default  # NaN guard
    except (TypeError, ValueError):
        return default


# ──────────────────────────────────────────────────────────────────────────────
# Wind direction helper
# ──────────────────────────────────────────────────────────────────────────────

def wind_direction_label(degrees: float | None) -> str:
    """Convert wind direction degrees to compass label (N, NE, E ...)."""
    if degrees is None:
        return "--"
    try:
        deg = float(degrees) % 360
    except (TypeError, ValueError):
        return "--"
    dirs = ["N", "NNE", "NE", "ENE", "E", "ESE", "SE", "SSE",
            "S", "SSW", "SW", "WSW", "W", "WNW", "NW", "NNW"]
    idx = int((deg + 11.25) / 22.5) % 16
    return dirs[idx]


# ──────────────────────────────────────────────────────────────────────────────
# Parsing + normalisation
# ──────────────────────────────────────────────────────────────────────────────

def _parse_response(city: str, raw: dict[str, Any]) -> dict[str, Any]:
    """
    Parse and validate an Open-Meteo response into a full WeatherRecord.

    Keys in returned dict:
        city, latitude, longitude,
        temperature, humidity, rainfall_1h, rainfall_3h, rainfall_6h, rainfall_24h,
        precipitation_probability, wind_speed, wind_direction, wind_direction_label,
        condition, weathercode, condition_emoji,
        hourly_times, hourly_temp, hourly_precip, hourly_precip_prob,
        hourly_windspeed, hourly_winddir,
        forecast_precip_next6h,
        daily_times, daily_temp_max, daily_temp_min, daily_precip_sum,
        daily_precip_prob_max, daily_windspeed_max, daily_weathercode,
        source, is_live, recorded_at, fetched_at,
        area, data_source, recorded_at_label
    """
    coords = GUJARAT_CITY_COORDS.get(city)
    if coords is None:
        raise WeatherFetchError(f"City '{city}' not in Gujarat city list.")

    # -- Current conditions ---------------------------------------------------
    current = raw.get("current")
    if not isinstance(current, dict):
        raise WeatherFetchError("Response missing 'current' block")

    required = {"temperature_2m", "precipitation", "rain", "windspeed_10m", "weathercode"}
    missing = required - set(current.keys())
    if missing:
        raise WeatherFetchError(f"Current block missing: {missing}")

    temperature = _validate_numeric(current["temperature_2m"], "temperature_2m")
    precip_1h   = _validate_numeric(current["precipitation"],  "precipitation")
    rain_1h     = _validate_numeric(current["rain"],           "rain")
    wind_speed  = _validate_numeric(current["windspeed_10m"],  "windspeed_10m")
    weathercode = current.get("weathercode", 0)
    condition   = _wmo_to_condition(weathercode)
    recorded_at = current.get("time", datetime.now(timezone.utc).isoformat())

    wind_dir_deg = _safe_float(current.get("winddirection_10m"), 0.0)
    humidity     = _safe_float(current.get("relativehumidity_2m"), 0.0)
    rainfall_1h  = max(precip_1h, rain_1h)

    # -- Hourly data ----------------------------------------------------------
    hourly = raw.get("hourly", {})
    h_times   = hourly.get("time", [])
    h_temp    = hourly.get("temperature_2m", [])
    h_precip  = hourly.get("precipitation", [])
    h_prob    = hourly.get("precipitation_probability", [])
    h_wind    = hourly.get("windspeed_10m", [])
    h_winddir = hourly.get("winddirection_10m", [])

    def _safe_list(lst: list, n: int = 48) -> list[float]:
        out = []
        for v in lst[:n]:
            out.append(_safe_float(v, 0.0))
        return out

    h_temp_f    = _safe_list(h_temp)
    h_precip_f  = _safe_list(h_precip)
    h_prob_f    = _safe_list(h_prob)
    h_wind_f    = _safe_list(h_wind)
    h_winddir_f = _safe_list(h_winddir)

    # Near-term 6h precip forecast (for pipeline compatibility)
    forecast_next6 = h_precip_f[:6]
    rainfall_6h    = round(sum(forecast_next6), 1)
    precip_prob    = h_prob_f[0] if h_prob_f else 0.0

    # -- 7-day daily forecast -------------------------------------------------
    daily = raw.get("daily", {})
    d_times       = daily.get("time", [])
    d_temp_max    = [_safe_float(v, 0.0) for v in daily.get("temperature_2m_max", [])]
    d_temp_min    = [_safe_float(v, 0.0) for v in daily.get("temperature_2m_min", [])]
    d_precip_sum  = [_safe_float(v, 0.0) for v in daily.get("precipitation_sum", [])]
    d_precip_prob = [_safe_float(v, 0.0) for v in daily.get("precipitation_probability_max", [])]
    d_wind_max    = [_safe_float(v, 0.0) for v in daily.get("windspeed_10m_max", [])]
    d_weathercode = daily.get("weathercode", [])

    return {
        # Identity
        "city":                      city,
        "latitude":                  coords["lat"],
        "longitude":                 coords["lon"],
        # Current conditions
        "temperature":               round(temperature, 1),
        "humidity":                  round(humidity, 0),
        "rainfall_1h":               round(rainfall_1h, 1),
        "rainfall_3h":               round(sum(h_precip_f[:3]), 1),
        "rainfall_6h":               rainfall_6h,
        "rainfall_24h":              round(sum(h_precip_f[:24]), 1),
        "precipitation_probability": round(precip_prob, 0),
        "wind_speed":                round(wind_speed, 1),
        "wind_direction":            round(wind_dir_deg, 0),
        "wind_direction_label":      wind_direction_label(wind_dir_deg),
        "condition":                 condition,
        "weathercode":               weathercode,
        "condition_emoji":           wmo_emoji(weathercode),
        # Hourly arrays (48 h max)
        "hourly_times":              h_times[:48],
        "hourly_temp":               h_temp_f[:48],
        "hourly_precip":             h_precip_f[:48],
        "hourly_precip_prob":        h_prob_f[:48],
        "hourly_windspeed":          h_wind_f[:48],
        "hourly_winddir":            h_winddir_f[:48],
        # Near-term 6h (pipeline compat)
        "forecast_precip_next6h":    forecast_next6,
        # 7-day daily
        "daily_times":               d_times,
        "daily_temp_max":            d_temp_max,
        "daily_temp_min":            d_temp_min,
        "daily_precip_sum":          d_precip_sum,
        "daily_precip_prob_max":     d_precip_prob,
        "daily_windspeed_max":       d_wind_max,
        "daily_weathercode":         d_weathercode,
        # Metadata / labels
        "source":                    "Open-Meteo",
        "source_url":                "https://open-meteo.com",
        "is_live":                   True,
        "data_mode":                 "LIVE",
        "recorded_at":               str(recorded_at),
        "fetched_at":                datetime.now(timezone.utc).isoformat(),
        # Pipeline compatibility aliases
        "area":                      city,
        "data_source":               "Open-Meteo (live)",
        "recorded_at_label":         f"Open-Meteo -- {str(recorded_at)[:16]} IST",
    }


# ──────────────────────────────────────────────────────────────────────────────
# Public API
# ──────────────────────────────────────────────────────────────────────────────

def fetch_city_weather(city: str, timeout: int = 8) -> dict[str, Any]:
    """
    Fetch, validate, and return a full WeatherRecord for any Gujarat city.

    Raises WeatherFetchError on any failure -- callers must catch.
    """
    raw = _fetch_open_meteo(city, timeout=timeout, forecast_days=7)
    return _parse_response(city, raw)


def fetch_all_cities(timeout: int = 8) -> dict[str, dict[str, Any]]:
    """
    Fetch live weather for Ahmedabad and Surat (pipeline scope).

    Returns:
        {
            "Ahmedabad": WeatherRecord | None,
            "Surat":     WeatherRecord | None,
            "errors":    {"Ahmedabad": str | None, "Surat": str | None},
        }
    Never raises.
    """
    results: dict[str, Any] = {"errors": {}}
    for city in CITY_COORDS:
        try:
            results[city] = fetch_city_weather(city, timeout=timeout)
            results["errors"][city] = None
        except WeatherFetchError as exc:
            results[city] = None
            results["errors"][city] = str(exc)
    return results
