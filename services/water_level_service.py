"""
FloodGuard AI — Water Level Service
=====================================
Abstraction for water level / river gauge data.

Current status (as of 2025):
  - No free, reliable, real-time river/drainage water-level API is
    publicly available for Ahmedabad / Surat at city-zone granularity.
  - India's CWC (Central Water Commission) publishes flood forecasts
    at https://ffs.india.gov.in but it is a web portal, not a machine-
    readable API, and scraping it is not appropriate.
  - GloFAS (Copernicus) provides river discharge forecasts at global
    resolution (~0.1°), usable for major rivers only.

Architecture decision:
  - This service implements the full interface contract so the rest of
    the system can consume water-level data cleanly.
  - When a live source is configured/available it is used transparently.
  - When no live source is available the service returns clearly-labelled
    FALLBACK / ESTIMATED data with explicit limitations shown in the UI.
  - The architecture allows future IoT/sensor integration without
    rewriting any consuming code.

Status labels used:
  LIVE        — actual sensor/API reading
  ESTIMATED   — derived from rainfall/runoff model (not a direct measurement)
  STATIC      — configured baseline, not updated
  FALLBACK    — no data available, last known or default used
  UNAVAILABLE — source not configured
"""
from __future__ import annotations

import math
import time
from datetime import datetime, timezone
from typing import Any

# Water level thresholds per location (configurable)
# All levels in metres above baseline / channel datum.
# These are illustrative values — replace with official CWC/municipal data.
_LOCATION_CONFIG: dict[str, dict] = {
    "Sabarmati @ Ahmedabad": {
        "city": "Ahmedabad",
        "latitude": 23.0225,
        "longitude": 72.5714,
        "normal_level":   5.0,
        "warning_level":  7.5,
        "danger_level":   9.0,
        "extreme_level":  11.0,
        "source_note":    "Illustrative threshold — official CWC thresholds should be used in production.",
    },
    "Tapi @ Surat": {
        "city": "Surat",
        "latitude": 21.1702,
        "longitude": 72.8311,
        "normal_level":   4.0,
        "warning_level":  6.5,
        "danger_level":   8.5,
        "extreme_level":  10.5,
        "source_note":    "Illustrative threshold — official CWC/SMP thresholds should be used in production.",
    },
}


def _estimate_water_level(
    location_key: str,
    rainfall_1h: float,
    rainfall_6h: float,
    rainfall_24h: float,
) -> dict[str, Any]:
    """
    Estimate water level from rainfall using a simple runoff proxy.

    THIS IS NOT A HYDROLOGICAL MODEL.
    This is a rough heuristic only, used when no direct measurement exists.
    The estimate provides a relative indication of risk and must NOT be
    presented as an actual measured water level.
    """
    cfg = _LOCATION_CONFIG.get(location_key, {})
    normal = cfg.get("normal_level", 5.0)
    danger = cfg.get("danger_level", 9.0)

    # Simple heuristic: combine rainfall signals
    # Each term represents a rough contribution to water-level rise.
    rain_proxy = (
        rainfall_1h  * 0.05 +    # immediate intense rainfall
        rainfall_6h  * 0.02 +    # accumulated over 6h
        rainfall_24h * 0.008      # catchment saturation proxy
    )
    rain_proxy = min(rain_proxy, danger - normal)
    estimated = round(normal + rain_proxy, 2)

    # Determine status tier
    warning  = cfg.get("warning_level", normal + 2.5)
    danger_l = cfg.get("danger_level", normal + 4.0)
    extreme  = cfg.get("extreme_level", normal + 6.0)

    if estimated >= extreme:
        tier = "EXTREME"
    elif estimated >= danger_l:
        tier = "DANGER"
    elif estimated >= warning:
        tier = "WARNING"
    else:
        tier = "NORMAL"

    return {
        "level_m":           estimated,
        "tier":              tier,
        "normal_level_m":    normal,
        "warning_level_m":   warning,
        "danger_level_m":    danger_l,
        "extreme_level_m":   extreme,
        "above_normal_m":    round(max(0.0, estimated - normal), 2),
    }


class WaterLevelService:
    """
    Provides water level data for monitored locations.

    Data priority:
      1. Live sensor feed (if IoT_SENSOR_ENABLED and endpoint configured)
      2. GloFAS API (future integration point)
      3. Rainfall-derived estimate (clearly labelled ESTIMATED)
    """

    def __init__(self):
        self._cache: dict[str, Any] = {}
        self._cache_ts: float = 0.0
        self._cache_ttl: int = 600   # 10 minutes

    def _cache_valid(self) -> bool:
        return bool(self._cache) and (time.time() - self._cache_ts) < self._cache_ttl

    def get_all_locations(
        self,
        rainfall_by_city: dict[str, dict] | None = None,
    ) -> list[dict[str, Any]]:
        """
        Return water level data for all monitored locations.

        Parameters
        ----------
        rainfall_by_city : dict mapping city → {rainfall_1h, rainfall_6h, rainfall_24h}
            Used to compute ESTIMATED water levels when no live sensor exists.

        Returns
        -------
        List of water level records.
        Each record contains:
            location, city, latitude, longitude,
            level_m, tier, source, data_mode,
            warning_level_m, danger_level_m,
            above_normal_m, timestamp, limitations
        """
        rainfall_by_city = rainfall_by_city or {}
        now = datetime.now(timezone.utc).isoformat()
        records: list[dict[str, Any]] = []

        for loc_key, cfg in _LOCATION_CONFIG.items():
            city = cfg["city"]
            rain = rainfall_by_city.get(city, {})

            # Try live source first — placeholder for future IoT integration
            live_level = self._try_live_source(loc_key)

            if live_level is not None:
                level_data = live_level
                data_mode = "LIVE"
                source = "Sensor Feed"
                limitations = ""
            else:
                # Rainfall-derived estimate
                level_data = _estimate_water_level(
                    loc_key,
                    rainfall_1h=float(rain.get("rainfall_1h", 0.0)),
                    rainfall_6h=float(rain.get("rainfall_6h", 0.0)),
                    rainfall_24h=float(rain.get("rainfall_24h", 0.0)),
                )
                data_mode = "ESTIMATED"
                source = "Rainfall-Derived Estimate"
                limitations = (
                    "⚠️ ESTIMATED — No live river/drainage sensor available for this location. "
                    "Value derived from rainfall data via a simple runoff proxy and is NOT a "
                    "measured water level. Do not use for official flood management decisions."
                )

            records.append({
                "location":       loc_key,
                "city":           city,
                "latitude":       cfg["latitude"],
                "longitude":      cfg["longitude"],
                "level_m":        level_data.get("level_m", cfg.get("normal_level", 5.0)),
                "tier":           level_data.get("tier", "NORMAL"),
                "normal_level_m": level_data.get("normal_level_m"),
                "warning_level_m": level_data.get("warning_level_m"),
                "danger_level_m": level_data.get("danger_level_m"),
                "extreme_level_m": level_data.get("extreme_level_m"),
                "above_normal_m": level_data.get("above_normal_m", 0.0),
                "source":         source,
                "data_mode":      data_mode,
                "timestamp":      now,
                "source_note":    cfg.get("source_note", ""),
                "limitations":    limitations,
            })

        return records

    def _try_live_source(self, location_key: str) -> dict | None:
        """
        Attempt to fetch from a live sensor endpoint.
        Currently returns None (no live source configured).
        Future: read from IoT endpoint or GloFAS API.
        """
        # Placeholder — wire up real sensor API here:
        # endpoint = os.getenv(f"SENSOR_URL_{location_key.replace(' ', '_').upper()}")
        # if endpoint: ... fetch ...
        return None

    def get_status_summary(self) -> dict[str, Any]:
        """Return a status summary for the observability panel."""
        return {
            "available": True,  # service itself is always available
            "data_mode": "ESTIMATED",
            "source": "Rainfall-Derived Estimate",
            "live_sensor": False,
            "note": (
                "Real-time river/drainage sensor data is not currently available "
                "for Ahmedabad/Surat. Water level values are estimates derived from "
                "Open-Meteo rainfall data."
            ),
            "monitored_locations": list(_LOCATION_CONFIG.keys()),
        }


# Module-level singleton
_wl_service: WaterLevelService | None = None


def get_water_level_service() -> WaterLevelService:
    global _wl_service
    if _wl_service is None:
        _wl_service = WaterLevelService()
    return _wl_service
