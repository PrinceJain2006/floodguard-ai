"""
FloodGuard AI — Open-Meteo Global Flood API (GloFAS) Client
============================================================
Fetches modelled river-discharge forecasts from the Open-Meteo Flood API,
which is powered by the GloFAS (Global Flood Awareness System) model.

ENDPOINT
--------
    https://flood-api.open-meteo.com/v1/flood
    No API key required. Free for non-commercial use.
    Documentation: https://open-meteo.com/en/docs/flood-api

IMPORTANT DISTINCTIONS — READ BEFORE USE
-----------------------------------------
1.  River discharge (m³/s) is a MODELLED quantity produced by a hydrological
    model (GloFAS). It is NOT a measured water-level reading.
    → Labelled: "MODELLED RIVER DISCHARGE — Open-Meteo / GloFAS"

2.  The Sabarmati NWDP CSV remains the authoritative REAL TELEMETRY source.
    → Labelled: "REAL TELEMETRY — NWDP / Gujarat SW GW"

3.  River discharge feeds the Flood Risk Agent as a supplementary input ONLY.
    It does NOT replace the rainfall-based water_level feature; instead it
    adjusts a separate `discharge_factor` that moderates the risk score.

4.  The synthetic 30K ML training dataset is never modified.

5.  No fake API keys or fake endpoints are used.

LOCATIONS QUERIED
-----------------
Ahmedabad  — Sabarmati river  — 23.0225°N, 72.5714°E
Surat      — Tapi river       — 21.1702°N, 72.8311°E

VARIABLES RETRIEVED
-------------------
river_discharge   — Daily mean river discharge (m³/s), 7-day forecast

FALLBACK
--------
If the API is unavailable, every public function returns a structured error
result with `ok=False` and a human-readable `error` string.  All consumers
must check `ok` before using data values.
"""
from __future__ import annotations

import time
from datetime import datetime, timezone
from typing import Any

import httpx

# ──────────────────────────────────────────────
# Constants
# ──────────────────────────────────────────────
_FLOOD_API_URL = "https://flood-api.open-meteo.com/v1/flood"
_TIMEOUT = 10          # seconds per request
_CACHE_TTL = 3600      # 1 hour — discharge changes slowly

DATA_SOURCE_LABEL = "MODELLED RIVER DISCHARGE — Open-Meteo / GloFAS"
DATA_SOURCE_URL   = "https://open-meteo.com/en/docs/flood-api"

# Per-city configuration: city → (latitude, longitude, river_name)
_CITY_CONFIG: dict[str, dict[str, Any]] = {
    "Ahmedabad": {
        "latitude":  23.0225,
        "longitude": 72.5714,
        "river":     "Sabarmati",
        # Rough bankfull discharge thresholds for Sabarmati at Ahmedabad (m³/s)
        # Based on published CWC figures; used for tier classification only.
        "threshold_warning":  200.0,
        "threshold_danger":   500.0,
        "threshold_extreme": 1200.0,
    },
    "Surat": {
        "latitude":  21.1702,
        "longitude": 72.8311,
        "river":     "Tapi",
        # Rough thresholds for Tapi at Surat (m³/s)
        "threshold_warning":  300.0,
        "threshold_danger":   700.0,
        "threshold_extreme": 1500.0,
    },
}

# Scale factor used in the Flood Risk Agent:
# river discharge is normalised to a 0.0–1.0 "discharge_factor"
# at the extreme threshold of each city.
# The agent caps this at 1.0 and blends it with the rainfall proxy.
_MAX_DISCHARGE_SCALE: dict[str, float] = {
    city: cfg["threshold_extreme"]
    for city, cfg in _CITY_CONFIG.items()
}


# ──────────────────────────────────────────────
# Tier classification
# ──────────────────────────────────────────────

def _discharge_tier(discharge_m3s: float, city: str) -> str:
    cfg = _CITY_CONFIG.get(city, {})
    if discharge_m3s >= cfg.get("threshold_extreme", 1200.0):
        return "EXTREME"
    if discharge_m3s >= cfg.get("threshold_danger", 500.0):
        return "DANGER"
    if discharge_m3s >= cfg.get("threshold_warning", 200.0):
        return "WARNING"
    return "NORMAL"


# ──────────────────────────────────────────────
# Raw API fetch
# ──────────────────────────────────────────────

def _fetch_discharge(
    latitude: float,
    longitude: float,
    forecast_days: int = 7,
    timeout: int = _TIMEOUT,
) -> dict[str, Any]:
    """
    Call the Open-Meteo Flood API and return the raw JSON.
    Raises httpx.HTTPError / httpx.RequestError on failure.
    """
    params = {
        "latitude":      latitude,
        "longitude":     longitude,
        "daily":         "river_discharge",
        "forecast_days": forecast_days,
    }
    response = httpx.get(_FLOOD_API_URL, params=params, timeout=timeout)
    response.raise_for_status()
    return response.json()


# ──────────────────────────────────────────────
# Per-city fetch + parse
# ──────────────────────────────────────────────

def _safe_float(val: Any) -> float | None:
    try:
        v = float(val)
        return None if (v != v) else v   # NaN guard
    except (TypeError, ValueError):
        return None


def fetch_city_discharge(
    city: str,
    forecast_days: int = 7,
    timeout: int = _TIMEOUT,
) -> dict[str, Any]:
    """
    Fetch the river-discharge forecast for a single city.

    Returns
    -------
    {
        "ok":                  bool,
        "error":               str | None,
        "city":                str,
        "river":               str,
        "latitude":            float,
        "longitude":           float,
        "times":               list[str],       # ISO date strings
        "discharge_m3s":       list[float],     # m³/s per day (None = missing)
        "current_discharge":   float | None,    # today's value
        "peak_discharge":      float | None,    # max in forecast window
        "peak_date":           str | None,      # date of peak
        "discharge_tier":      str,             # NORMAL / WARNING / DANGER / EXTREME
        "discharge_factor":    float,           # 0.0–1.0 normalised (for agent)
        "data_source":         str,             # DATA_SOURCE_LABEL
        "data_source_url":     str,
        "data_mode":           "API",
        "is_live":             bool,            # True = fetched from API
        "fetched_at":          str,             # ISO UTC
        "note":                str,             # human-readable caveat
    }
    """
    empty = {
        "ok":               False,
        "error":            "Not attempted",
        "city":             city,
        "river":            _CITY_CONFIG.get(city, {}).get("river", "Unknown"),
        "latitude":         _CITY_CONFIG.get(city, {}).get("latitude", 0.0),
        "longitude":        _CITY_CONFIG.get(city, {}).get("longitude", 0.0),
        "times":            [],
        "discharge_m3s":    [],
        "current_discharge": None,
        "peak_discharge":   None,
        "peak_date":        None,
        "discharge_tier":   "NORMAL",
        "discharge_factor": 0.0,
        "data_source":      DATA_SOURCE_LABEL,
        "data_source_url":  DATA_SOURCE_URL,
        "data_mode":        "API",
        "is_live":          False,
        "fetched_at":       datetime.now(timezone.utc).isoformat(),
        "note": (
            "MODELLED — GloFAS hydrological model output. "
            "NOT a measured water-level reading. "
            "Do not use as a substitute for official gauge data."
        ),
    }

    cfg = _CITY_CONFIG.get(city)
    if cfg is None:
        empty["error"] = f"City '{city}' not configured in GloFAS client."
        return empty

    try:
        raw = _fetch_discharge(
            cfg["latitude"], cfg["longitude"],
            forecast_days=forecast_days,
            timeout=timeout,
        )
    except httpx.TimeoutException as exc:
        empty["error"] = f"Open-Meteo Flood API timed out after {timeout}s: {exc}"
        return empty
    except httpx.HTTPStatusError as exc:
        empty["error"] = (
            f"Open-Meteo Flood API returned HTTP {exc.response.status_code}: "
            f"{exc.response.text[:200]}"
        )
        return empty
    except httpx.RequestError as exc:
        empty["error"] = f"Network error reaching Open-Meteo Flood API: {exc}"
        return empty
    except Exception as exc:
        empty["error"] = f"Unexpected error fetching GloFAS data: {exc}"
        return empty

    # Parse daily block
    daily = raw.get("daily", {})
    times = daily.get("time", [])
    raw_q = daily.get("river_discharge", [])

    discharge: list[float | None] = [_safe_float(v) for v in raw_q]
    valid_vals = [v for v in discharge if v is not None]

    current = discharge[0] if discharge else None
    peak = max(valid_vals) if valid_vals else None
    peak_idx = discharge.index(peak) if (peak is not None and peak in discharge) else None
    peak_date = times[peak_idx] if (peak_idx is not None and peak_idx < len(times)) else None

    # discharge_factor: 0.0 (none) → 1.0 (at/above extreme threshold)
    max_scale = _MAX_DISCHARGE_SCALE.get(city, 1200.0)
    ref_val = peak if peak is not None else (current if current is not None else 0.0)
    discharge_factor = min(1.0, max(0.0, ref_val / max_scale)) if max_scale > 0 else 0.0

    tier = _discharge_tier(ref_val, city)

    return {
        "ok":                True,
        "error":             None,
        "city":              city,
        "river":             cfg["river"],
        "latitude":          raw.get("latitude", cfg["latitude"]),
        "longitude":         raw.get("longitude", cfg["longitude"]),
        "times":             times,
        "discharge_m3s":     [v if v is not None else 0.0 for v in discharge],
        "current_discharge": current,
        "peak_discharge":    peak,
        "peak_date":         peak_date,
        "discharge_tier":    tier,
        "discharge_factor":  round(discharge_factor, 4),
        "data_source":       DATA_SOURCE_LABEL,
        "data_source_url":   DATA_SOURCE_URL,
        "data_mode":         "API",
        "is_live":           True,
        "fetched_at":        datetime.now(timezone.utc).isoformat(),
        "note": (
            "MODELLED — GloFAS hydrological model output via Open-Meteo Flood API. "
            "NOT a measured water-level reading. "
            "Do not use as a substitute for official gauge or telemetry data."
        ),
    }


# ──────────────────────────────────────────────
# Multi-city fetch
# ──────────────────────────────────────────────

def fetch_all_cities(
    forecast_days: int = 7,
    timeout: int = _TIMEOUT,
) -> dict[str, Any]:
    """
    Fetch river-discharge forecasts for Ahmedabad and Surat.

    Returns
    -------
    {
        "ok":              bool,    # True if at least one city succeeded
        "cities": {
            "Ahmedabad": { per-city dict },
            "Surat":     { per-city dict },
        },
        "errors": {
            "Ahmedabad": str | None,
            "Surat":     str | None,
        },
        "fetched_at":      str,
        "data_source":     str,
        "data_source_url": str,
    }
    Never raises.
    """
    results: dict[str, Any] = {
        "ok": False,
        "cities": {},
        "errors": {},
        "fetched_at":      datetime.now(timezone.utc).isoformat(),
        "data_source":     DATA_SOURCE_LABEL,
        "data_source_url": DATA_SOURCE_URL,
    }

    any_ok = False
    for city in _CITY_CONFIG:
        rec = fetch_city_discharge(city, forecast_days=forecast_days, timeout=timeout)
        results["cities"][city] = rec
        results["errors"][city] = rec.get("error")
        if rec.get("ok"):
            any_ok = True

    results["ok"] = any_ok
    return results


# ──────────────────────────────────────────────
# Module-level cache
# ──────────────────────────────────────────────
_cache: dict[str, Any] = {}
_cache_ts: float = 0.0


def get_flood_discharge(force_reload: bool = False) -> dict[str, Any]:
    """
    Return the cached multi-city discharge result, refreshing if stale.

    Cache TTL: 1 hour (discharge forecasts change slowly).
    Thread-safety: single-threaded Streamlit processes — no lock needed.
    """
    global _cache, _cache_ts
    age = time.time() - _cache_ts
    if not _cache or force_reload or age > _CACHE_TTL:
        _cache = fetch_all_cities()
        _cache_ts = time.time()
    return _cache


def get_city_discharge(city: str, glofas_data: dict | None = None) -> dict[str, Any]:
    """
    Return the per-city discharge record from a pre-fetched glofas_data result,
    or fetch fresh if glofas_data is None.
    """
    if glofas_data is None:
        glofas_data = get_flood_discharge()
    return glofas_data.get("cities", {}).get(city, {
        "ok": False,
        "error": f"City '{city}' not in GloFAS result.",
        "city": city,
        "discharge_factor": 0.0,
        "discharge_tier": "NORMAL",
        "current_discharge": None,
        "data_source": DATA_SOURCE_LABEL,
        "is_live": False,
    })
