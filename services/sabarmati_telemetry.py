"""
FloodGuard AI — Sabarmati Telemetry Loader
==========================================
Parses the official NWDP Gujarat SW GW Sabarmati River Water Level
Telemetry Hourly CSV and exposes the latest reading per station.

DATA SOURCE
-----------
File  : data/Sabarmati_River_Water_Level_Telemetry_2026_2030.csv.csv
Agency: Gujarat SW GW  (National Water Data Platform — NWDP)
River : Sabarmati Basin, Gujarat, India

IMPORTANT — WHAT THIS MODULE DOES AND DOES NOT DO
--------------------------------------------------
* Reads the static CSV as-is; does NOT call any external API.
* Does NOT invent, interpolate, or infer values beyond what is in the file.
* Does NOT modify or overwrite the existing ML training dataset.
* Clearly labels all returned data as "REAL TELEMETRY — NWDP / Gujarat SW GW".
* If the CSV cannot be read, returns a structured error result instead of
  raising so that the rest of the application continues to function.

WATER LEVEL FIELD
-----------------
Column used: "River Water Level Telemetry Hourly (meter)"
Timestamp  : "Data Acquisition Time"  (format: %d-%m-%Y %H:%M)
"""
from __future__ import annotations

import csv
import os
from collections import defaultdict
from datetime import datetime
from pathlib import Path
from typing import Any

# ──────────────────────────────────────────────
# Path resolution — works whether the app is run from the repo root
# or from inside the floodguard-ai/ sub-directory.
# ──────────────────────────────────────────────
_THIS_DIR = Path(__file__).parent          # floodguard-ai/services/
_APP_ROOT  = _THIS_DIR.parent              # floodguard-ai/
_CSV_NAME  = "Sabarmati_River_Water_Level_Telemetry_2026_2030.csv.csv"
_CSV_PATH  = _APP_ROOT / "data" / _CSV_NAME

# Column names exactly as they appear in the CSV header
_COL_SLNO      = "SlNo"
_COL_STATION   = "Station"
_COL_AGENCY    = "Agency"
_COL_LAT       = "Latitude"
_COL_LON       = "Longitude"
_COL_TS        = "Data Acquisition Time"
_COL_WL        = "River Water Level Telemetry Hourly (meter)"
_TS_FORMAT     = "%d-%m-%Y %H:%M"

DATA_SOURCE_LABEL = "REAL TELEMETRY — NWDP / Gujarat SW GW"
DATA_SOURCE_BADGE = "🛰️ REAL TELEMETRY — NWDP / Gujarat SW GW"


# ──────────────────────────────────────────────
# Core parsing
# ──────────────────────────────────────────────

def _parse_timestamp(ts_str: str) -> datetime | None:
    """Parse a timestamp string from the telemetry CSV. Returns None on failure."""
    try:
        return datetime.strptime(ts_str.strip(), _TS_FORMAT)
    except (ValueError, AttributeError):
        return None


def _safe_float(value: str) -> float | None:
    """Convert a string to float, returning None if invalid."""
    try:
        v = float(value.strip())
        return v if not (v != v) else None  # reject NaN
    except (ValueError, TypeError):
        return None


def load_latest_per_station(csv_path: Path = _CSV_PATH) -> dict[str, Any]:
    """
    Read the telemetry CSV and return the latest reading for each station.

    Returns a dict with the following structure:
    {
        "ok": bool,                  # True if CSV was read successfully
        "error": str | None,         # Error message if ok=False
        "csv_path": str,             # Path used
        "stations": [                # List of per-station dicts
            {
                "station":        str,   # Station name
                "agency":         str,   # e.g. "Gujarat SW GW"
                "latitude":       float,
                "longitude":      float,
                "timestamp_str":  str,   # Raw timestamp string from CSV
                "timestamp":      datetime | None,
                "water_level_m":  float | None,
                "row_count":      int,   # Total rows seen for this station
                "data_source":    str,   # DATA_SOURCE_LABEL
            },
            ...
        ],
        "station_count":   int,
        "latest_timestamp": datetime | None,   # Across all stations
        "latest_timestamp_str": str | None,
        "data_source":     str,
        "water_level_field": str,
        "data_mode":       "CSV",              # Never "API" — always CSV-based
        "is_live":         False,              # CSV is a static file, not streaming
    }
    """
    result: dict[str, Any] = {
        "ok": False,
        "error": None,
        "csv_path": str(csv_path),
        "stations": [],
        "station_count": 0,
        "latest_timestamp": None,
        "latest_timestamp_str": None,
        "data_source": DATA_SOURCE_LABEL,
        "water_level_field": _COL_WL,
        "data_mode": "CSV",
        "is_live": False,
    }

    if not csv_path.exists():
        result["error"] = (
            f"Telemetry CSV not found at: {csv_path}. "
            "Download from NWDP and place in data/ folder."
        )
        return result

    # Group all rows by station name
    station_rows: dict[str, list[dict]] = defaultdict(list)
    row_errors = 0
    total_rows = 0

    try:
        with open(csv_path, encoding="utf-8", newline="") as fh:
            reader = csv.DictReader(fh)
            for raw in reader:
                total_rows += 1
                station = (raw.get(_COL_STATION) or "").strip()
                if not station:
                    row_errors += 1
                    continue
                station_rows[station].append(raw)
    except Exception as exc:
        result["error"] = f"Failed to read CSV: {exc}"
        return result

    if not station_rows:
        result["error"] = "CSV parsed but contained no station rows."
        return result

    stations_out: list[dict[str, Any]] = []
    overall_latest: datetime | None = None

    for station_name, rows in station_rows.items():
        # Find the row with the latest timestamp for this station
        best_row: dict | None = None
        best_ts: datetime | None = None

        for row in rows:
            ts = _parse_timestamp(row.get(_COL_TS, ""))
            if ts is None:
                continue
            if best_ts is None or ts > best_ts:
                best_ts = ts
                best_row = row

        if best_row is None:
            # All rows had unparseable timestamps — use the physical last row
            best_row = rows[-1]
            best_ts = None

        wl = _safe_float(best_row.get(_COL_WL, ""))
        lat = _safe_float(best_row.get(_COL_LAT, ""))
        lon = _safe_float(best_row.get(_COL_LON, ""))
        agency = (best_row.get(_COL_AGENCY) or "Gujarat SW GW").strip()
        ts_str = (best_row.get(_COL_TS) or "").strip()

        stations_out.append({
            "station":        station_name,
            "agency":         agency,
            "latitude":       lat,
            "longitude":      lon,
            "timestamp_str":  ts_str,
            "timestamp":      best_ts,
            "water_level_m":  wl,
            "row_count":      len(rows),
            "data_source":    DATA_SOURCE_LABEL,
        })

        if best_ts and (overall_latest is None or best_ts > overall_latest):
            overall_latest = best_ts

    # Sort by station name for consistent ordering
    stations_out.sort(key=lambda s: s["station"])

    result["ok"] = True
    result["stations"] = stations_out
    result["station_count"] = len(stations_out)
    result["latest_timestamp"] = overall_latest
    result["latest_timestamp_str"] = (
        overall_latest.strftime(_TS_FORMAT) if overall_latest else None
    )

    return result


def get_primary_station_reading(
    loaded: dict[str, Any] | None = None,
    preferred_station: str = "Sabarmati_Gandhinagar",
) -> dict[str, Any]:
    """
    Return the single most relevant reading for use by the Flood Risk Agent.

    Strategy:
      1. Prefer the station named `preferred_station` (default: Sabarmati_Gandhinagar —
         nearest to Ahmedabad, the primary city in FloodGuard).
      2. Fall back to the station with the latest timestamp among all stations.
      3. If no valid reading exists, return a clearly-labelled unavailable record.

    Returns a flat dict suitable for passing directly to FloodRiskAgent.analyze_area().
    """
    if loaded is None:
        loaded = load_latest_per_station()

    empty = {
        "ok": False,
        "station": None,
        "water_level_m": None,
        "timestamp_str": None,
        "timestamp": None,
        "data_source": DATA_SOURCE_LABEL,
        "data_mode": "CSV",
        "is_live": False,
        "note": "No valid telemetry reading available.",
    }

    if not loaded.get("ok") or not loaded.get("stations"):
        empty["note"] = loaded.get("error") or "Telemetry unavailable."
        return empty

    stations = loaded["stations"]

    # Try preferred station first
    preferred = next(
        (s for s in stations if s["station"] == preferred_station), None
    )
    if preferred and preferred["water_level_m"] is not None:
        return {**preferred, "ok": True, "data_mode": "CSV", "is_live": False}

    # Fall back: station with latest timestamp that has a valid water level
    candidates = [
        s for s in stations
        if s.get("water_level_m") is not None and s.get("timestamp") is not None
    ]
    if candidates:
        best = max(candidates, key=lambda s: s["timestamp"])  # type: ignore[arg-type]
        return {**best, "ok": True, "data_mode": "CSV", "is_live": False}

    empty["note"] = "Stations found but all water level values are invalid."
    return empty


# ──────────────────────────────────────────────
# Module-level cache (loaded once per process;
# Streamlit's @st.cache_resource would also work
# but this avoids a Streamlit import here)
# ──────────────────────────────────────────────
_cached_load: dict[str, Any] | None = None


def get_telemetry(force_reload: bool = False) -> dict[str, Any]:
    """
    Return the loaded telemetry result, caching it for the process lifetime.

    Use `force_reload=True` only if the CSV file has been updated on disk.
    """
    global _cached_load
    if _cached_load is None or force_reload:
        _cached_load = load_latest_per_station()
    return _cached_load
