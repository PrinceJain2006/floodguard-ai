"""
FloodGuard AI — Live Weather Service
=====================================
Fetches current and forecast weather/rainfall data for Ahmedabad and Surat
via the Open-Meteo public API (no API key required).

SCOPE: Ahmedabad & Surat only — per hackathon challenge
       "Smart Urban Flooding & Drainage Management System for Ahmedabad–Surat".

Design principles:
  • Never crashes Streamlit: every network/parsing failure is caught.
  • Returns a validated, normalised dict or raises WeatherFetchError.
  • Callers should ALWAYS use get_live_weather() via LiveDataManager,
    which handles DEMO fallback — never call fetch_* directly from the UI.
  • Clearly distinguishes LIVE weather evidence from flood predictions.
    Live weather = "Live Weather Evidence", NOT "Live Flood Location".

Open-Meteo endpoint:
    https://api.open-meteo.com/v1/forecast
    No authentication required. Free for non-commercial use.
    See: https://open-meteo.com/en/docs
"""
from __future__ import annotations

import time
from datetime import datetime, timezone
from typing import Any

import httpx

# ──────────────────────────────────────────────────────────────────────────────
# City geography — Ahmedabad & Surat only
# ──────────────────────────────────────────────────────────────────────────────
CITY_COORDS: dict[str, dict[str, float]] = {
    "Ahmedabad": {"lat": 23.0225, "lon": 72.5714},
    "Surat":     {"lat": 21.1702, "lon": 72.8311},
}

# WMO weather interpretation codes → human-readable label
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

# Open-Meteo hourly variables we request
_HOURLY_VARS = [
    "precipitation",
    "precipitation_probability",
    "rain",
    "windspeed_10m",
    "temperature_2m",
    "weathercode",
]

# Current-condition variables
_CURRENT_VARS = [
    "temperature_2m",
    "precipitation",
    "rain",
    "windspeed_10m",
    "weathercode",
]

# Reasonable numeric bounds for validation
_BOUNDS: dict[str, tuple[float, float]] = {
    "temperature_2m":            (-10.0, 55.0),   # °C — Gujarat range
    "precipitation":             (0.0, 300.0),    # mm/hr
    "rain":                      (0.0, 300.0),
    "windspeed_10m":             (0.0, 200.0),    # km/h
    "precipitation_probability": (0.0, 100.0),   # %
}


class WeatherFetchError(Exception):
    """Raised when live weather data cannot be fetched or validated."""


# ──────────────────────────────────────────────────────────────────────────────
# Low-level fetch
# ──────────────────────────────────────────────────────────────────────────────

def _fetch_open_meteo(city: str, timeout: int = 8) -> dict[str, Any]:
    """
    Fetch current + 24h hourly forecast from Open-Meteo for a single city.

    Returns raw API response dict.
    Raises WeatherFetchError on any network or HTTP error.
    """
    coords = CITY_COORDS.get(city)
    if coords is None:
        raise WeatherFetchError(
            f"City '{city}' is not in scope. Only Ahmedabad and Surat are supported."
        )

    params = {
        "latitude":              coords["lat"],
        "longitude":             coords["lon"],
        "current":               ",".join(_CURRENT_VARS),
        "hourly":                ",".join(_HOURLY_VARS),
        "forecast_days":         1,
        "timezone":              "Asia/Kolkata",
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
        raise WeatherFetchError(f"Open-Meteo request timed out after {timeout}s") from exc
    except httpx.HTTPStatusError as exc:
        raise WeatherFetchError(
            f"Open-Meteo returned HTTP {exc.response.status_code}"
        ) from exc
    except httpx.RequestError as exc:
        raise WeatherFetchError(f"Network error reaching Open-Meteo: {exc}") from exc
    except Exception as exc:
        raise WeatherFetchError(f"Unexpected error fetching Open-Meteo data: {exc}") from exc


# ──────────────────────────────────────────────────────────────────────────────
# Validation helpers
# ──────────────────────────────────────────────────────────────────────────────

def _validate_numeric(value: Any, field: str) -> float:
    """
    Validate a single numeric field against known reasonable bounds.
    Returns the float value if valid.
    Raises WeatherFetchError if invalid.
    """
    try:
        v = float(value)
    except (TypeError, ValueError) as exc:
        raise WeatherFetchError(
            f"Field '{field}' is not numeric: {value!r}"
        ) from exc

    lo, hi = _BOUNDS.get(field, (-1e9, 1e9))
    if not (lo <= v <= hi):
        raise WeatherFetchError(
            f"Field '{field}' value {v} is outside valid range [{lo}, {hi}]"
        )
    return v


def _wmo_to_condition(code: Any) -> str:
    """Convert WMO weather code to human-readable string."""
    try:
        return _WMO_CONDITIONS.get(int(code), f"Weather code {code}")
    except (TypeError, ValueError):
        return "Unknown"


# ──────────────────────────────────────────────────────────────────────────────
# Parsing + normalisation
# ──────────────────────────────────────────────────────────────────────────────

def _parse_response(city: str, raw: dict[str, Any]) -> dict[str, Any]:
    """
    Parse and validate an Open-Meteo response into a normalised WeatherRecord.

    Returns a dict with consistent keys used throughout FloodGuard AI:
        city, latitude, longitude,
        temperature, rainfall_1h, rainfall_6h, precipitation_probability,
        wind_speed, condition, weathercode,
        forecast_precip_next6h (list of 6 floats, one per hour),
        source, is_live, recorded_at, fetched_at

    Raises WeatherFetchError on missing required fields or out-of-range values.
    """
    if city not in CITY_COORDS:
        raise WeatherFetchError(
            f"City '{city}' is not in scope. Only Ahmedabad and Surat are supported."
        )
    coords = CITY_COORDS[city]

    # ── Current conditions ────────────────────────────────────────────────
    current = raw.get("current")
    if not isinstance(current, dict):
        raise WeatherFetchError("Response missing 'current' block")

    # Required fields in current block
    required_current = {"temperature_2m", "precipitation", "rain", "windspeed_10m", "weathercode"}
    missing = required_current - set(current.keys())
    if missing:
        raise WeatherFetchError(f"Current block missing fields: {missing}")

    temperature  = _validate_numeric(current["temperature_2m"],  "temperature_2m")
    precip_1h    = _validate_numeric(current["precipitation"],    "precipitation")
    rain_1h      = _validate_numeric(current["rain"],             "rain")
    wind_speed   = _validate_numeric(current["windspeed_10m"],   "windspeed_10m")
    weathercode  = current.get("weathercode", 0)
    condition    = _wmo_to_condition(weathercode)
    recorded_at  = current.get("time", datetime.now(timezone.utc).isoformat())

    # rainfall_1h = max of precipitation and rain (both are valid proxies)
    rainfall_1h = max(precip_1h, rain_1h)

    # ── Hourly forecast — next 6 hours ────────────────────────────────────
    hourly = raw.get("hourly", {})
    hourly_precip = hourly.get("precipitation", [])
    hourly_prob   = hourly.get("precipitation_probability", [])

    # Take first 6 hourly values for near-term forecast
    forecast_next6 = []
    for i in range(min(6, len(hourly_precip))):
        try:
            v = float(hourly_precip[i]) if hourly_precip[i] is not None else 0.0
            forecast_next6.append(max(0.0, min(300.0, v)))
        except (TypeError, ValueError):
            forecast_next6.append(0.0)

    # Derive 6h accumulated total from hourly forecast
    rainfall_6h = round(sum(forecast_next6), 1)

    # Current precipitation probability (first hourly value or 0)
    precip_prob = 0.0
    if hourly_prob:
        try:
            precip_prob = _validate_numeric(
                hourly_prob[0] if hourly_prob[0] is not None else 0,
                "precipitation_probability",
            )
        except WeatherFetchError:
            precip_prob = 0.0

    return {
        "city":                        city,
        "latitude":                    coords["lat"],
        "longitude":                   coords["lon"],
        "temperature":                 round(temperature, 1),
        "rainfall_1h":                 round(rainfall_1h, 1),
        "rainfall_6h":                 rainfall_6h,
        "rainfall_3h":                 round(sum(forecast_next6[:3]), 1),
        "precipitation_probability":   round(precip_prob, 0),
        "wind_speed":                  round(wind_speed, 1),
        "condition":                   condition,
        "weathercode":                 weathercode,
        "forecast_precip_next6h":      forecast_next6,
        "source":                      "Open-Meteo",
        "source_url":                  "https://open-meteo.com",
        "is_live":                     True,
        "data_mode":                   "LIVE",
        "recorded_at":                 str(recorded_at),
        "fetched_at":                  datetime.now(timezone.utc).isoformat(),
        # These keys align with the existing pipeline's rainfall record schema
        "area":                        city,   # city-level observation
        "rainfall_24h":                round(sum(forecast_next6) * 4, 1),  # rough 24h estimate
        "data_source":                 "Open-Meteo (live)",
        "recorded_at_label":           f"Open-Meteo — {str(recorded_at)[:16]} IST",
    }


# ──────────────────────────────────────────────────────────────────────────────
# Public API
# ──────────────────────────────────────────────────────────────────────────────

def fetch_city_weather(city: str, timeout: int = 8) -> dict[str, Any]:
    """
    Fetch, validate, and return a normalised weather record for one city.

    This is the main public function for live data.

    Returns a validated WeatherRecord dict.
    Raises WeatherFetchError if the fetch or validation fails for any reason.
    Callers MUST catch WeatherFetchError and fall back to DEMO data.
    """
    raw = _fetch_open_meteo(city, timeout=timeout)
    return _parse_response(city, raw)


def fetch_all_cities(timeout: int = 8) -> dict[str, dict[str, Any]]:
    """
    Fetch live weather for Ahmedabad and Surat.

    Returns:
        {
            "Ahmedabad": WeatherRecord | None,
            "Surat":     WeatherRecord | None,
            "errors":    {"Ahmedabad": str | None, "Surat": str | None},
        }

    Never raises — all errors are captured in the "errors" key.
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
