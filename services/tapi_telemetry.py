"""
FloodGuard AI — Tapi River Telemetry Service
=============================================
Provides Tapi River Water Level telemetry from the official
NWDP / Gujarat SW GW CSV snapshot.

DATA SOURCE
-----------
File : data/Tapi_River_Water_Level_Telemetry_2026_2030.csv.csv
Agency: Gujarat Surface Water & Ground Water Department (Gujarat SW GW)
River : Tapi
Basin : Tapi
City  : Surat (primary coverage area)

DESIGN CONSTRAINTS (identical to Sabarmati service)
----------------------------------------------------
* This is a CSV SNAPSHOT — it is NOT a live API feed.
* data_mode is always "CSV_FALLBACK" (never "LIVE_API").
* is_live is always False.
* The badge always reads "🟡 CSV SNAPSHOT — NWDP / Gujarat SW GW · Tapi".
* The synthetic ML training dataset is NEVER modified by this module.
* Sabarmati telemetry is NEVER mixed with Tapi telemetry.
* Each river's reading is only injected into areas of the matching city
  (Tapi → Surat; Sabarmati → Ahmedabad).

STATIONS IN DATASET
-------------------
Baldeva   — Bharuch district  — 21.6156°N, 73.4061°E
Ukai dam  — Tapi district     — 21.2475°N, 73.5897°E
Ver-II    — Surat district    — 21.3925°N, 73.3858°E

The preferred primary station for the Flood Risk Agent is "Ver-II",
as it is the closest gauge to Surat city.  Falls back to the station
with the most recent valid reading if Ver-II is absent.

CSV COLUMNS (all identical to Sabarmati CSV)
--------------------------------------------
SlNo, Station, Agency, State LGD Code, State,
District LGD Code, District, Tehsil, Block, Village,
River, Basin, Tributary, Subtributary, SubSubtributary, Local River,
Latitude, Longitude, Is_DischargeDataAvailable, RL_of_zeroGauge,
MeanSeaLevel, Data Acquisition Time,
River Water Level Telemetry Hourly (meter)

UI LABELS (never interchangeable with Sabarmati labels)
-------------------------------------------------------
CSV SNAPSHOT : "🟡 CSV SNAPSHOT — NWDP / Gujarat SW GW · Tapi"
UNAVAILABLE  : "🔴 TELEMETRY UNAVAILABLE — NWDP / Gujarat SW GW · Tapi"
"""
from __future__ import annotations

import csv
import time
from collections import defaultdict
from datetime import datetime
from pathlib import Path
from typing import Any

# ──────────────────────────────────────────────
# Paths
# ──────────────────────────────────────────────
_THIS_DIR = Path(__file__).parent           # floodguard-ai/services/
_APP_ROOT  = _THIS_DIR.parent               # floodguard-ai/
_CSV_NAME  = "Tapi_River_Water_Level_Telemetry_2026_2030.csv.csv"
_CSV_PATH  = _APP_ROOT / "data" / _CSV_NAME

# ──────────────────────────────────────────────
# CSV column names (identical to Sabarmati CSV)
# ──────────────────────────────────────────────
_COL_STATION = "Station"
_COL_AGENCY  = "Agency"
_COL_LAT     = "Latitude"
_COL_LON     = "Longitude"
_COL_TS      = "Data Acquisition Time"
_COL_WL      = "River Water Level Telemetry Hourly (meter)"
_CSV_TS_FMT  = "%d-%m-%Y %H:%M"

# ──────────────────────────────────────────────
# Public label constants
# ──────────────────────────────────────────────
DATA_SOURCE_LABEL = "REAL TELEMETRY \u2014 NWDP / Gujarat SW GW \u00b7 Tapi River"
BADGE_CSV         = "\U0001f7e1 CSV SNAPSHOT \u2014 NWDP / Gujarat SW GW \u00b7 Tapi"
BADGE_UNAVAILABLE = "\U0001f534 TELEMETRY UNAVAILABLE \u2014 NWDP / Gujarat SW GW \u00b7 Tapi"
DATA_MODE_CSV         = "CSV_FALLBACK"
DATA_MODE_UNAVAILABLE = "UNAVAILABLE"

# Preferred primary station (nearest to Surat city)
_DEFAULT_PREFERRED_STATION = "Ver-II"


# ──────────────────────────────────────────────
# Parsing helpers
# ──────────────────────────────────────────────

def _parse_timestamp(ts_str: str) -> datetime | None:
    try:
        return datetime.strptime(ts_str.strip(), _CSV_TS_FMT)
    except (ValueError, AttributeError):
        return None


def _safe_float(value: Any) -> float | None:
    try:
        v = float(str(value).strip())
        return None if (v != v) else v   # NaN guard
    except (ValueError, TypeError):
        return None


def _build_station_record(
    station: str,
    agency: str,
    lat: float | None,
    lon: float | None,
    ts_str: str,
    ts: datetime | None,
    wl: float | None,
    row_count: int,
) -> dict[str, Any]:
    return {
        "station":       station,
        "agency":        agency,
        "latitude":      lat,
        "longitude":     lon,
        "timestamp_str": ts_str,
        "timestamp":     ts,
        "water_level_m": wl,
        "row_count":     row_count,
        "data_source":   DATA_SOURCE_LABEL,
        "data_mode":     DATA_MODE_CSV,
        "is_live":       False,
        "river":         "Tapi",
    }


def _build_result(
    ok: bool,
    stations: list[dict[str, Any]],
    data_mode: str,
    error: str | None = None,
) -> dict[str, Any]:
    """Build the standard top-level result dict."""
    now_iso = datetime.utcnow().isoformat()
    latest_ts: datetime | None = None
    latest_ts_str: str | None = None

    for s in stations:
        ts = s.get("timestamp")
        if ts and (latest_ts is None or ts > latest_ts):
            latest_ts = ts
            latest_ts_str = s.get("timestamp_str")

    badge = BADGE_CSV if data_mode == DATA_MODE_CSV else BADGE_UNAVAILABLE

    return {
        "ok":                   ok,
        "error":                error,
        "river":                "Tapi",
        "stations":             stations,
        "station_count":        len(stations),
        "latest_timestamp":     latest_ts,
        "latest_timestamp_str": latest_ts_str,
        "data_source":          DATA_SOURCE_LABEL,
        "water_level_field":    _COL_WL,
        "data_mode":            data_mode,
        "is_live":              False,
        "badge":                badge,
        "csv_path":             str(_CSV_PATH),
        "fetched_at":           now_iso,
        # Explicit note — never silently claim live status
        "source_note":          "CSV SNAPSHOT \u2014 NOT a live feed. Timestamps reflect the last record in the static NWDP download.",
    }


# ──────────────────────────────────────────────
# CSV loader
# ──────────────────────────────────────────────

def _load_csv() -> dict[str, Any]:
    """
    Parse the Tapi NWDP CSV and return the latest reading per station.
    Never modifies any file. Never raises.
    """
    if not _CSV_PATH.exists():
        return _build_result(
            ok=False,
            stations=[],
            data_mode=DATA_MODE_UNAVAILABLE,
            error=(
                f"Tapi telemetry CSV not found: {_CSV_PATH}. "
                "Place Tapi_River_Water_Level_Telemetry_2026_2030.csv.csv in data/ folder."
            ),
        )

    station_rows: dict[str, list[dict]] = defaultdict(list)

    try:
        with open(_CSV_PATH, encoding="utf-8", newline="") as fh:
            reader = csv.DictReader(fh)
            for raw in reader:
                name = (raw.get(_COL_STATION) or "").strip()
                if name:
                    station_rows[name].append(raw)
    except Exception as exc:
        return _build_result(
            ok=False,
            stations=[],
            data_mode=DATA_MODE_UNAVAILABLE,
            error=f"Tapi CSV read failed: {exc}",
        )

    if not station_rows:
        return _build_result(
            ok=False,
            stations=[],
            data_mode=DATA_MODE_UNAVAILABLE,
            error="Tapi CSV parsed but contained no station rows.",
        )

    stations_out: list[dict[str, Any]] = []

    for station_name, rows in station_rows.items():
        best_row: dict | None = None
        best_ts:  datetime | None = None

        for row in rows:
            ts = _parse_timestamp(row.get(_COL_TS, ""))
            if ts is None:
                continue
            if best_ts is None or ts > best_ts:
                best_ts  = ts
                best_row = row

        if best_row is None:
            best_row = rows[-1]

        wl     = _safe_float(best_row.get(_COL_WL, ""))
        lat    = _safe_float(best_row.get(_COL_LAT, ""))
        lon    = _safe_float(best_row.get(_COL_LON, ""))
        agency = (best_row.get(_COL_AGENCY) or "Gujarat SW GW").strip()
        ts_str = (best_row.get(_COL_TS) or "").strip()

        stations_out.append(_build_station_record(
            station=station_name,
            agency=agency,
            lat=lat, lon=lon,
            ts_str=ts_str, ts=best_ts,
            wl=wl,
            row_count=len(rows),
        ))

    stations_out.sort(key=lambda s: s["station"])
    return _build_result(ok=True, stations=stations_out, data_mode=DATA_MODE_CSV)


# ──────────────────────────────────────────────
# Primary station selection
# ──────────────────────────────────────────────

def get_primary_station_reading(
    loaded: dict[str, Any] | None = None,
    preferred_station: str = _DEFAULT_PREFERRED_STATION,
) -> dict[str, Any]:
    """
    Return the single most relevant Tapi reading for the Flood Risk Agent.

    Strategy:
      1. Prefer `preferred_station` (default: Ver-II, nearest to Surat).
      2. Fall back to the station with the latest valid timestamp.
      3. If nothing valid: return a clearly-labelled unavailable record.

    The returned dict is structurally identical to the Sabarmati equivalent
    so the Flood Risk Agent can consume it without any code changes.
    """
    if loaded is None:
        loaded = get_tapi_telemetry()

    data_mode = loaded.get("data_mode", DATA_MODE_UNAVAILABLE)
    badge     = loaded.get("badge", BADGE_UNAVAILABLE)

    empty: dict[str, Any] = {
        "ok":            False,
        "station":       None,
        "water_level_m": None,
        "timestamp_str": None,
        "timestamp":     None,
        "data_source":   DATA_SOURCE_LABEL,
        "data_mode":     data_mode,
        "is_live":       False,
        "badge":         badge,
        "river":         "Tapi",
        "note":          "No valid Tapi telemetry reading available.",
    }

    if not loaded.get("ok") or not loaded.get("stations"):
        empty["note"] = loaded.get("error") or "Tapi telemetry unavailable."
        return empty

    stations = loaded["stations"]

    # 1. Try preferred station
    preferred = next((s for s in stations if s["station"] == preferred_station), None)
    if preferred and preferred.get("water_level_m") is not None:
        return {**preferred, "ok": True, "badge": badge, "note": f"Source: {badge}"}

    # 2. Latest valid reading across all stations
    candidates = [
        s for s in stations
        if s.get("water_level_m") is not None and s.get("timestamp") is not None
    ]
    if candidates:
        best = max(candidates, key=lambda s: s["timestamp"])  # type: ignore[arg-type]
        return {
            **best,
            "ok":    True,
            "badge": badge,
            "note":  (
                f"Source: {badge} "
                f"(preferred station '{preferred_station}' not found; using latest available)"
            ),
        }

    empty["note"] = "Tapi stations found but all water level values are invalid."
    return empty


# ──────────────────────────────────────────────
# Module-level TTL cache
# ──────────────────────────────────────────────
_cached_result: dict[str, Any] | None = None
_cached_at: float = 0.0
_CACHE_TTL = 3600   # CSV content is static; 1-hour TTL is effectively permanent per process


def get_tapi_telemetry(force_reload: bool = False) -> dict[str, Any]:
    """
    Return the Tapi telemetry result, using the TTL cache when fresh.
    The CSV is static, so the cache is effectively permanent for the
    process lifetime unless force_reload=True.
    Never raises.
    """
    global _cached_result, _cached_at
    age = time.time() - _cached_at

    if _cached_result is None or force_reload or age >= _CACHE_TTL:
        _cached_result = _load_csv()
        _cached_at     = time.time()

    return _cached_result
