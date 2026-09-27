"""
FloodGuard AI — Sabarmati Telemetry Service
============================================
Provides Sabarmati River Water Level telemetry from the official
NWDP / Gujarat SW GW data source.

DATA RESOLUTION STRATEGY (priority order)
------------------------------------------
1.  LIVE API    — if NWDP_API_URL is configured in env/secrets, attempt
                  a live fetch from that endpoint.
2.  CSV FALLBACK — if API is not configured, unavailable, or returns bad
                  data, use the static NWDP CSV downloaded locally.
3.  ERROR        — if both sources fail, return a structured error result.

IMPORTANT — DESIGN CONSTRAINTS
--------------------------------
* No endpoint is hard-coded. The API URL comes entirely from
  environment variable NWDP_API_URL (or Streamlit secret).
* No API key is hard-coded. NWDP_API_KEY is optional — many government
  data portals use it in a query-param or header; some require none.
* The CSV fallback is NEVER deleted or disabled.
* The CSV-based result is NEVER labelled "LIVE". It always carries
  data_mode="CSV_FALLBACK" and is_live=False.
* The API-based result carries data_mode="LIVE_API" and is_live=True
  ONLY when the API fetch actually succeeded.
* The synthetic ML training dataset (data/ml_training_data.json and the
  seed generator) are never touched by this module.

ENVIRONMENT VARIABLES / STREAMLIT SECRETS
------------------------------------------
NWDP_API_URL
    Full URL of the NWDP / data.gov.in telemetry API endpoint.
    Example (data.gov.in pattern):
        https://api.data.gov.in/resource/{resource_id}?format=json&offset=0&limit=10
    If empty or unset: only the CSV fallback is used.

NWDP_API_KEY
    API key sent as the "api-key" request header.
    If empty or unset: requests are made without an API key.
    (Some government APIs are keyless; some require registration.)

NWDP_API_KEY_PARAM
    If set, the key is appended as a query parameter with this name
    instead of being sent as a header.
    Default: empty (sends as header "api-key").

NWDP_REFRESH_INTERVAL
    How often (seconds) to re-fetch from the API before using the cache.
    Default: 3600 (1 hour — matches NWDP hourly telemetry update frequency).

NWDP_API_TIMEOUT
    HTTP request timeout in seconds. Default: 10.

NWDP_STATION_NAME_FIELD
    JSON field name for the station identifier in the API response.
    Default: "Station"  (same as CSV column name).

NWDP_WL_FIELD
    JSON field name for the water-level value in the API response.
    Default: "River Water Level Telemetry Hourly (meter)"  (same as CSV).

NWDP_TS_FIELD
    JSON field name for the acquisition timestamp.
    Default: "Data Acquisition Time"

NWDP_TS_FORMAT
    strptime format for the timestamp field.
    Default: "%d-%m-%Y %H:%M"  (matches NWDP CSV format).

RESPONSE FORMAT ASSUMPTION
--------------------------
The module assumes the API returns JSON with a top-level list or a dict
containing a "records" / "data" / "result" key holding a list of records,
each record being a flat dict matching the CSV column structure.

If the target API has a different schema, extend _parse_api_response().
The CSV parser is unchanged and always available as a fallback.

UI LABELS (never interchangeable)
----------------------------------
LIVE API mode :  "🟢 LIVE API — NWDP / Gujarat SW GW"
CSV FALLBACK  :  "🟡 CSV FALLBACK — NWDP / Gujarat SW GW"
"""
from __future__ import annotations

import csv
import os
import time
from collections import defaultdict
from datetime import datetime
from pathlib import Path
from typing import Any

import httpx

# ──────────────────────────────────────────────
# Path resolution
# ──────────────────────────────────────────────
_THIS_DIR = Path(__file__).parent          # floodguard-ai/services/
_APP_ROOT  = _THIS_DIR.parent              # floodguard-ai/
_CSV_NAME  = "Sabarmati_River_Water_Level_Telemetry_2026_2030.csv.csv"
_CSV_PATH  = _APP_ROOT / "data" / _CSV_NAME

# ──────────────────────────────────────────────
# CSV column names (fixed — match actual file)
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
DATA_SOURCE_LABEL     = "REAL TELEMETRY \u2014 NWDP / Gujarat SW GW"
BADGE_LIVE_API        = "\U0001f7e2 LIVE API \u2014 NWDP / Gujarat SW GW"
BADGE_CSV_FALLBACK    = "\U0001f7e1 CSV FALLBACK \u2014 NWDP / Gujarat SW GW"
BADGE_UNAVAILABLE     = "\U0001f534 TELEMETRY UNAVAILABLE \u2014 NWDP / Gujarat SW GW"
DATA_MODE_LIVE_API    = "LIVE_API"
DATA_MODE_CSV_FALLBACK = "CSV_FALLBACK"
DATA_MODE_UNAVAILABLE  = "UNAVAILABLE"

# Preferred primary station (nearest to Ahmedabad)
_DEFAULT_PREFERRED_STATION = "Sabarmati_Gandhinagar"


# ──────────────────────────────────────────────
# Env-var helpers (read at call time, not module load)
# ──────────────────────────────────────────────

def _env(key: str, default: str = "") -> str:
    """
    Read a config value from Streamlit secrets (if available) or os.environ.
    Never raises. Always returns a string.
    """
    # Try Streamlit secrets first (only if inside a Streamlit run context)
    try:
        import sys
        _st = sys.modules.get("streamlit")
        if _st is not None:
            _scriptrunner = sys.modules.get("streamlit.runtime.scriptrunner")
            if _scriptrunner is not None:
                _get_ctx = getattr(_scriptrunner, "get_script_run_ctx", None)
                if _get_ctx is not None and _get_ctx() is not None:
                    val = _st.secrets.get(key, "")
                    if val:
                        return str(val)
    except Exception:
        pass
    return os.environ.get(key, default)


def _api_url() -> str:
    return _env("NWDP_API_URL", "").strip()

def _api_key() -> str:
    return _env("NWDP_API_KEY", "").strip()

def _api_key_param() -> str:
    return _env("NWDP_API_KEY_PARAM", "").strip()

def _refresh_interval() -> int:
    try:
        return int(_env("NWDP_REFRESH_INTERVAL", "3600"))
    except ValueError:
        return 3600

def _api_timeout() -> int:
    try:
        return int(_env("NWDP_API_TIMEOUT", "10"))
    except ValueError:
        return 10

def _station_name_field() -> str:
    return _env("NWDP_STATION_NAME_FIELD", _COL_STATION)

def _wl_field() -> str:
    return _env("NWDP_WL_FIELD", _COL_WL)

def _ts_field() -> str:
    return _env("NWDP_TS_FIELD", _COL_TS)

def _ts_format() -> str:
    return _env("NWDP_TS_FORMAT", _CSV_TS_FMT)


# ──────────────────────────────────────────────
# Shared parsing helpers
# ──────────────────────────────────────────────

def _parse_timestamp(ts_str: str, fmt: str = _CSV_TS_FMT) -> datetime | None:
    try:
        return datetime.strptime(ts_str.strip(), fmt)
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
    data_mode: str,
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
        "data_mode":     data_mode,
        "is_live":       data_mode == DATA_MODE_LIVE_API,
    }


def _build_result(
    ok: bool,
    stations: list[dict[str, Any]],
    data_mode: str,
    error: str | None = None,
    source_url: str = "",
    fetched_at: str | None = None,
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

    badge = (
        BADGE_LIVE_API       if data_mode == DATA_MODE_LIVE_API  else
        BADGE_CSV_FALLBACK   if data_mode == DATA_MODE_CSV_FALLBACK else
        BADGE_UNAVAILABLE
    )

    return {
        "ok":                   ok,
        "error":                error,
        "stations":             stations,
        "station_count":        len(stations),
        "latest_timestamp":     latest_ts,
        "latest_timestamp_str": latest_ts_str,
        "data_source":          DATA_SOURCE_LABEL,
        "water_level_field":    _COL_WL,
        "data_mode":            data_mode,
        "is_live":              data_mode == DATA_MODE_LIVE_API,
        "badge":                badge,
        "source_url":           source_url,
        "fetched_at":           fetched_at or now_iso,
        # CSV path (always set for transparency even in API mode)
        "csv_path":             str(_CSV_PATH),
    }


# ──────────────────────────────────────────────
# CSV loader (permanent fallback)
# ──────────────────────────────────────────────

def _load_csv() -> dict[str, Any]:
    """
    Parse the local NWDP CSV and return the latest reading per station.
    This is the permanent CSV_FALLBACK path.  It never modifies any file.
    """
    if not _CSV_PATH.exists():
        return _build_result(
            ok=False,
            stations=[],
            data_mode=DATA_MODE_UNAVAILABLE,
            error=(
                f"Telemetry CSV not found: {_CSV_PATH}. "
                "Download from NWDP and place in data/ folder."
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
            error=f"CSV read failed: {exc}",
        )

    if not station_rows:
        return _build_result(
            ok=False,
            stations=[],
            data_mode=DATA_MODE_UNAVAILABLE,
            error="CSV parsed but contained no station rows.",
        )

    stations_out: list[dict[str, Any]] = []

    for station_name, rows in station_rows.items():
        best_row: dict | None = None
        best_ts: datetime | None = None

        for row in rows:
            ts = _parse_timestamp(row.get(_COL_TS, ""), _CSV_TS_FMT)
            if ts is None:
                continue
            if best_ts is None or ts > best_ts:
                best_ts = ts
                best_row = row

        if best_row is None:
            best_row = rows[-1]

        wl  = _safe_float(best_row.get(_COL_WL, ""))
        lat = _safe_float(best_row.get(_COL_LAT, ""))
        lon = _safe_float(best_row.get(_COL_LON, ""))
        agency   = (best_row.get(_COL_AGENCY) or "Gujarat SW GW").strip()
        ts_str   = (best_row.get(_COL_TS) or "").strip()

        stations_out.append(_build_station_record(
            station=station_name,
            agency=agency,
            lat=lat, lon=lon,
            ts_str=ts_str, ts=best_ts,
            wl=wl,
            row_count=len(rows),
            data_mode=DATA_MODE_CSV_FALLBACK,
        ))

    stations_out.sort(key=lambda s: s["station"])
    return _build_result(
        ok=True,
        stations=stations_out,
        data_mode=DATA_MODE_CSV_FALLBACK,
    )


# ──────────────────────────────────────────────
# API response parser
# ──────────────────────────────────────────────

def _parse_api_response(
    payload: Any,
    station_field: str,
    wl_field: str,
    ts_field: str,
    ts_fmt: str,
    api_url: str,
    fetched_at: str,
) -> dict[str, Any]:
    """
    Parse a JSON payload from the NWDP / data.gov.in API into the standard
    telemetry result format.

    Supported response shapes:
      - A bare list of record dicts
      - {"records": [...]}
      - {"data": [...]}
      - {"result": {..., "records": [...]}}
      - {"fields": [...], "records": [...]}   (data.gov.in OGPL format)

    If the shape is unrecognised or no valid records are found, returns
    ok=False so the caller can fall back to CSV.
    """
    records: list[dict] = []

    if isinstance(payload, list):
        records = payload
    elif isinstance(payload, dict):
        for key in ("records", "data", "result", "features", "items", "rows"):
            val = payload.get(key)
            if isinstance(val, list):
                records = val
                break
            if isinstance(val, dict):
                # data.gov.in OGPL: {"result": {"records": [...]}}
                inner = val.get("records") or val.get("data") or []
                if isinstance(inner, list):
                    records = inner
                    break

    if not records:
        return _build_result(
            ok=False,
            stations=[],
            data_mode=DATA_MODE_UNAVAILABLE,
            error=(
                "API returned a response but no parseable record list was found. "
                f"Top-level keys: {list(payload.keys()) if isinstance(payload, dict) else type(payload).__name__}"
            ),
            source_url=api_url,
            fetched_at=fetched_at,
        )

    # Group by station and find latest per station
    station_rows: dict[str, list[dict]] = defaultdict(list)
    for rec in records:
        if not isinstance(rec, dict):
            continue
        name = str(rec.get(station_field, "") or "").strip()
        if name:
            station_rows[name].append(rec)

    if not station_rows:
        return _build_result(
            ok=False,
            stations=[],
            data_mode=DATA_MODE_UNAVAILABLE,
            error=f"API records found but no '{station_field}' field present.",
            source_url=api_url,
            fetched_at=fetched_at,
        )

    stations_out: list[dict[str, Any]] = []
    for station_name, rows in station_rows.items():
        best_row: dict | None = None
        best_ts: datetime | None = None

        for row in rows:
            ts = _parse_timestamp(str(row.get(ts_field, "") or ""), ts_fmt)
            if ts is None:
                continue
            if best_ts is None or ts > best_ts:
                best_ts = ts
                best_row = row

        if best_row is None:
            best_row = rows[-1]

        wl  = _safe_float(best_row.get(wl_field))
        lat = _safe_float(best_row.get("Latitude") or best_row.get("lat"))
        lon = _safe_float(best_row.get("Longitude") or best_row.get("lon"))
        agency = str(best_row.get("Agency") or best_row.get("agency") or "Gujarat SW GW").strip()
        ts_str = str(best_row.get(ts_field, "") or "").strip()

        stations_out.append(_build_station_record(
            station=station_name,
            agency=agency,
            lat=lat, lon=lon,
            ts_str=ts_str, ts=best_ts,
            wl=wl,
            row_count=len(rows),
            data_mode=DATA_MODE_LIVE_API,
        ))

    stations_out.sort(key=lambda s: s["station"])
    return _build_result(
        ok=True,
        stations=stations_out,
        data_mode=DATA_MODE_LIVE_API,
        source_url=api_url,
        fetched_at=fetched_at,
    )


# ──────────────────────────────────────────────
# Live API fetch
# ──────────────────────────────────────────────

def _fetch_api() -> dict[str, Any]:
    """
    Attempt a live fetch from the configured NWDP_API_URL.

    Returns a telemetry result dict.  On any failure returns ok=False
    with a clear error message — never raises.

    Authentication
    --------------
    * If NWDP_API_KEY_PARAM is set (e.g. "api-key"):
        appends ?{param}={key} to the request URL.
    * Otherwise, if NWDP_API_KEY is set:
        sends it as the "api-key" request header.
    * If neither is set: no authentication is added.
    """
    url = _api_url()
    if not url:
        return _build_result(
            ok=False,
            stations=[],
            data_mode=DATA_MODE_UNAVAILABLE,
            error=(
                "NWDP_API_URL is not configured. "
                "Set it in .env or Streamlit secrets to enable live API mode."
            ),
        )

    key      = _api_key()
    key_param = _api_key_param()
    timeout  = _api_timeout()
    now_iso  = datetime.utcnow().isoformat()

    headers: dict[str, str] = {"Accept": "application/json"}
    params:  dict[str, str] = {}

    if key:
        if key_param:
            params[key_param] = key
        else:
            headers["api-key"] = key

    try:
        response = httpx.get(url, headers=headers, params=params, timeout=timeout, follow_redirects=True)
        response.raise_for_status()
    except httpx.TimeoutException as exc:
        return _build_result(
            ok=False, stations=[],
            data_mode=DATA_MODE_UNAVAILABLE,
            error=f"NWDP API timed out after {timeout}s: {exc}",
            source_url=url, fetched_at=now_iso,
        )
    except httpx.HTTPStatusError as exc:
        return _build_result(
            ok=False, stations=[],
            data_mode=DATA_MODE_UNAVAILABLE,
            error=f"NWDP API returned HTTP {exc.response.status_code}: {exc.response.text[:200]}",
            source_url=url, fetched_at=now_iso,
        )
    except httpx.RequestError as exc:
        return _build_result(
            ok=False, stations=[],
            data_mode=DATA_MODE_UNAVAILABLE,
            error=f"Network error reaching NWDP API: {exc}",
            source_url=url, fetched_at=now_iso,
        )
    except Exception as exc:
        return _build_result(
            ok=False, stations=[],
            data_mode=DATA_MODE_UNAVAILABLE,
            error=f"Unexpected error fetching NWDP API: {exc}",
            source_url=url, fetched_at=now_iso,
        )

    try:
        payload = response.json()
    except Exception as exc:
        return _build_result(
            ok=False, stations=[],
            data_mode=DATA_MODE_UNAVAILABLE,
            error=f"NWDP API response is not valid JSON: {exc}",
            source_url=url, fetched_at=now_iso,
        )

    return _parse_api_response(
        payload=payload,
        station_field=_station_name_field(),
        wl_field=_wl_field(),
        ts_field=_ts_field(),
        ts_fmt=_ts_format(),
        api_url=url,
        fetched_at=now_iso,
    )


# ──────────────────────────────────────────────
# Primary public loader (API → CSV fallback)
# ──────────────────────────────────────────────

def load_telemetry() -> dict[str, Any]:
    """
    Load the latest Sabarmati telemetry using the configured source.

    Resolution order
    ----------------
    1.  If NWDP_API_URL is configured → attempt live API fetch.
        On success → return LIVE_API result.
        On failure → log error and fall through to CSV.
    2.  CSV fallback → parse local NWDP CSV file.
        Returns CSV_FALLBACK result.
    3.  If CSV also fails → return UNAVAILABLE result.

    The returned dict always includes:
        "data_mode"   : "LIVE_API" | "CSV_FALLBACK" | "UNAVAILABLE"
        "is_live"     : True only for LIVE_API
        "badge"       : human-readable UI badge string
        "api_attempted": True if LIVE_API fetch was attempted
        "api_error"   : error string if API failed and CSV was used
    """
    api_attempted = False
    api_error: str | None = None

    if _api_url():
        api_attempted = True
        api_result = _fetch_api()
        if api_result.get("ok"):
            api_result["api_attempted"] = True
            api_result["api_error"] = None
            return api_result
        # API failed — record error, fall through to CSV
        api_error = api_result.get("error", "Unknown API error")

    # CSV fallback
    csv_result = _load_csv()
    csv_result["api_attempted"] = api_attempted
    csv_result["api_error"] = api_error
    # If API was attempted but failed, add a clear note
    if api_attempted and api_error:
        csv_result["api_fallback_note"] = (
            f"API fetch failed ({api_error[:120]}). "
            "Serving CSV fallback — data is from the static NWDP download, "
            "NOT a live reading."
        )
    else:
        csv_result["api_fallback_note"] = None
    return csv_result


# ──────────────────────────────────────────────
# Primary station selection
# ──────────────────────────────────────────────

def get_primary_station_reading(
    loaded: dict[str, Any] | None = None,
    preferred_station: str = _DEFAULT_PREFERRED_STATION,
) -> dict[str, Any]:
    """
    Return the single most relevant reading for the Flood Risk Agent.

    Strategy:
      1. Prefer `preferred_station` (default: Sabarmati_Gandhinagar).
      2. Fall back to the station with the latest timestamp.
      3. If nothing valid: return a clearly-labelled unavailable record.

    The `data_mode` and `is_live` fields of the returned dict match
    those of the `loaded` result so downstream code always knows the source.
    """
    if loaded is None:
        loaded = get_telemetry()

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
        "is_live":       data_mode == DATA_MODE_LIVE_API,
        "badge":         badge,
        "note":          "No valid telemetry reading available.",
    }

    if not loaded.get("ok") or not loaded.get("stations"):
        empty["note"] = loaded.get("error") or "Telemetry unavailable."
        return empty

    stations = loaded["stations"]

    # Try preferred station
    preferred = next((s for s in stations if s["station"] == preferred_station), None)
    if preferred and preferred["water_level_m"] is not None:
        return {
            **preferred,
            "ok":      True,
            "badge":   badge,
            "note":    f"Source: {badge}",
        }

    # Fall back: station with latest valid timestamp + water level
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
            "note":  f"Source: {badge} (preferred station '{preferred_station}' not found, using latest available)",
        }

    empty["note"] = "Stations found but all water level values are invalid."
    return empty


# ──────────────────────────────────────────────
# Module-level TTL cache
# ──────────────────────────────────────────────
_cached_result: dict[str, Any] | None = None
_cached_at: float = 0.0


def get_telemetry(force_reload: bool = False) -> dict[str, Any]:
    """
    Return the telemetry result, using the TTL cache when fresh.

    Cache TTL is controlled by NWDP_REFRESH_INTERVAL (default: 3600 s).
    Set force_reload=True to bypass the cache (e.g. after a manual refresh).

    In LIVE_API mode the cache respects the refresh interval so the API is
    not called on every Streamlit rerun.
    In CSV_FALLBACK mode the cache is effectively permanent for the process
    lifetime (CSV content does not change without a restart).
    """
    global _cached_result, _cached_at
    ttl = _refresh_interval()
    age = time.time() - _cached_at

    if _cached_result is None or force_reload or age >= ttl:
        _cached_result = load_telemetry()
        _cached_at = time.time()

    return _cached_result


def get_telemetry_status() -> dict[str, Any]:
    """
    Return a concise status dict for UI display panels.

    Keys:
        data_mode         "LIVE_API" | "CSV_FALLBACK" | "UNAVAILABLE"
        is_live           bool
        badge             UI badge string (green / yellow / red)
        api_configured    bool — whether NWDP_API_URL is set
        api_url           str  — the configured URL (masked key)
        station_count     int
        latest_ts         str | None
        primary_station   str | None
        primary_wl_m      float | None
        api_attempted     bool
        api_error         str | None
        api_fallback_note str | None
        refresh_interval  int
        cache_age_s       float
        source_url        str
    """
    result = get_telemetry()
    primary = get_primary_station_reading(result)
    api_url_raw = _api_url()

    return {
        "data_mode":        result.get("data_mode", DATA_MODE_UNAVAILABLE),
        "is_live":          result.get("is_live", False),
        "badge":            result.get("badge", BADGE_UNAVAILABLE),
        "api_configured":   bool(api_url_raw),
        "api_url":          api_url_raw if api_url_raw else "(not configured)",
        "station_count":    result.get("station_count", 0),
        "latest_ts":        result.get("latest_timestamp_str"),
        "primary_station":  primary.get("station"),
        "primary_wl_m":     primary.get("water_level_m"),
        "api_attempted":    result.get("api_attempted", False),
        "api_error":        result.get("api_error"),
        "api_fallback_note": result.get("api_fallback_note"),
        "refresh_interval": _refresh_interval(),
        "cache_age_s":      round(time.time() - _cached_at, 1),
        "source_url":       result.get("source_url", ""),
    }
