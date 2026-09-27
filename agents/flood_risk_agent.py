"""
FloodGuard AI — Agent 1: Flood Risk Prediction Agent
Analyzes rainfall, drainage, historical data, and citizen reports
to calculate per-area flood risk scores and classifications.
"""
import uuid
from datetime import datetime, timezone
from typing import Any

try:
    from ml.flood_risk_model import get_model
    from agents.granite_service import explain_flood_risk
except ImportError:
    from flood_risk_model import get_model
    from granite_service import explain_flood_risk


RISK_COLORS = {
    "LOW":      "#22c55e",
    "MEDIUM":   "#eab308",
    "HIGH":     "#f97316",
    "CRITICAL": "#ef4444",
}

RISK_WEIGHTS = {
    "rainfall_1h": 0.30,
    "drainage_capacity": 0.20,
    "historical_flood_freq": 0.15,
    "water_level": 0.15,
    "citizen_reports": 0.10,
    "elevation_factor": 0.10,
}


class FloodRiskAgent:
    """
    Agent 1 — Flood Risk Prediction Agent.

    Combines ML model predictions with domain logic to produce
    per-area risk assessments.
    """

    def __init__(self):
        self.name = "Flood Risk Agent"
        self.model = None
        self.last_run = None
        self.activity_log: list[str] = []
        self._load_model()

    def _load_model(self):
        try:
            self.model = get_model()
            self._log("ML model loaded successfully")
        except Exception as e:
            self._log(f"ML model load failed: {e} — using rule-based fallback")

    def _log(self, msg: str):
        ts = datetime.now(timezone.utc).strftime("%H:%M:%S")
        self.activity_log.append(f"[{ts}] {msg}")
        if len(self.activity_log) > 50:
            self.activity_log = self.activity_log[-50:]

    def analyze_area(
        self,
        area: str,
        city: str,
        latitude: float,
        longitude: float,
        rainfall_data: dict,
        drain_data: list[dict],
        citizen_reports: list[dict],
        historical_incidents: list[dict],
        elevation: float = 50.0,
        real_water_level: dict | None = None,
        river_discharge: dict | None = None,
    ) -> dict:
        """
        Full risk analysis for a single area.
        Returns a structured risk assessment dict.

        Parameters
        ----------
        real_water_level : dict | None
            If provided, a reading dict from services.sabarmati_telemetry
            (keys: station, water_level_m, timestamp_str, data_source, …).
            When present its water_level_m value replaces the rainfall-
            derived water_level estimate in the feature vector, and the
            assessment result carries explicit REAL TELEMETRY labels.
            The synthetic ML training dataset is NOT affected.

        river_discharge : dict | None
            If provided, a per-city record from services.glofas_flood_api
            (keys: ok, city, discharge_factor, discharge_tier,
                   current_discharge, peak_discharge, peak_date, …).
            Labelled: "MODELLED RIVER DISCHARGE — Open-Meteo / GloFAS".
            River discharge is NOT treated as a measured water level.
            It is used as a supplementary `discharge_factor` (0.0–1.0)
            that adds a bounded bonus to the risk score, separate from the
            water_level feature.  This is clearly documented in the result.
            The synthetic ML training dataset is NOT affected.
        """
        # Aggregate drain capacity
        if drain_data:
            avg_drain_capacity = sum(d.get("capacity_rating", 50) for d in drain_data) / len(drain_data)
            blocked_drains = sum(1 for d in drain_data if d.get("status") == "BLOCKED")
        else:
            avg_drain_capacity = 50.0
            blocked_drains = 0

        # Historical flood frequency
        hist_freq = len(historical_incidents)

        # Citizen report count (last 2 hours approx)
        report_count = len(citizen_reports)

        r1h = rainfall_data.get("rainfall_1h", 0)
        r6h = rainfall_data.get("rainfall_6h", 0)

        # Water level: use real telemetry when available; otherwise derive from rainfall.
        _telemetry_used = False
        _telemetry_station: str | None = None
        _telemetry_ts: str | None = None
        _telemetry_raw_m: float | None = None

        if (
            real_water_level
            and real_water_level.get("ok")
            and real_water_level.get("water_level_m") is not None
        ):
            raw_m = float(real_water_level["water_level_m"])
            # Normalise to a 0–5 m scale comparable to the rainfall-proxy.
            # The CSV records absolute gauge heights (e.g. 52.961 m MSL for
            # Sabarmati_Gandhinagar).  We cap at 5.0 to stay within the
            # training-data range used by the ML model.
            water_level = min(5.0, max(0.0, raw_m / 100.0))
            _telemetry_used = True
            _telemetry_station = real_water_level.get("station")
            _telemetry_ts = real_water_level.get("timestamp_str")
            _telemetry_raw_m = raw_m
        else:
            water_level = min(5.0, r6h / 80.0 + (blocked_drains * 0.3))

        features = {
            "rainfall_1h":          r1h,
            "rainfall_3h":          rainfall_data.get("rainfall_3h", r1h * 2.8),
            "rainfall_6h":          r6h,
            "rainfall_24h":         rainfall_data.get("rainfall_24h", r1h * 18),
            "drainage_capacity":    avg_drain_capacity,
            "historical_flood_freq": hist_freq,
            "water_level":          water_level,
            "elevation":            elevation,
            "road_density":         0.7,   # default if not provided
            "citizen_reports":      report_count,
        }

        # ML prediction
        if self.model:
            pred = self.model.predict(features)
        else:
            pred = _rule_based_predict(features)

        risk_score = pred["risk_score"]
        risk_level = pred["risk_level"]

        # ── River-discharge advisory adjustment (GloFAS) ──────────────────────
        # River discharge is MODELLED (not measured). It is NOT substituted for
        # water_level. Instead, a bounded bonus (≤ 8 points) is added to the
        # risk score when GloFAS signals elevated discharge.
        # This preserves the integrity of the ML training data and clearly
        # separates modelled discharge from the telemetry water-level input.
        _discharge_used = False
        _discharge_city: str | None = None
        _discharge_m3s: float | None = None
        _discharge_tier: str = "NORMAL"
        _discharge_factor: float = 0.0
        _discharge_fetched_at: str | None = None
        _discharge_peak: float | None = None
        _discharge_peak_date: str | None = None

        if river_discharge and river_discharge.get("ok"):
            _discharge_used      = True
            _discharge_city      = river_discharge.get("city")
            _discharge_m3s       = river_discharge.get("current_discharge")
            _discharge_tier      = river_discharge.get("discharge_tier", "NORMAL")
            _discharge_factor    = float(river_discharge.get("discharge_factor", 0.0))
            _discharge_fetched_at = river_discharge.get("fetched_at")
            _discharge_peak      = river_discharge.get("peak_discharge")
            _discharge_peak_date = river_discharge.get("peak_date")
            # Additive bonus: up to 8 points at discharge_factor=1.0
            # Capped so a single-source GloFAS signal cannot alone push to CRITICAL.
            _discharge_bonus = round(_discharge_factor * 8.0, 2)
            risk_score = min(100.0, risk_score + _discharge_bonus)
            # Re-derive risk_level from adjusted score
            risk_level = (
                "CRITICAL" if risk_score >= 75 else
                "HIGH"     if risk_score >= 50 else
                "MEDIUM"   if risk_score >= 25 else
                "LOW"
            )

        # Time window estimation
        if r1h > 60:
            time_window = "Next 0-1 hours"
        elif r1h > 30:
            time_window = "Next 1-3 hours"
        elif r1h > 10:
            time_window = "Next 3-6 hours"
        else:
            time_window = "Next 6-12 hours"

        # Action recommendation
        action_map = {
            "CRITICAL": (
                "IMMEDIATE ACTION: Deploy emergency response teams. "
                f"Evacuate low-lying areas in {area}. Activate flood control command."
            ),
            "HIGH": (
                f"Deploy pump team to {area}. "
                "Inspect and clear blocked drains. Issue public advisory."
            ),
            "MEDIUM": (
                f"Pre-position response team near {area}. "
                "Monitor rainfall progression. Inspect high-risk drains."
            ),
            "LOW": (
                "Continue routine monitoring. "
                "Ensure response teams are on standby. No immediate action required."
            ),
        }

        # Build data labels — reflect all active sources
        if _telemetry_used and _discharge_used:
            _data_label = (
                "REAL TELEMETRY — NWDP / Gujarat SW GW + "
                "MODELLED RIVER DISCHARGE — Open-Meteo / GloFAS"
            )
        elif _telemetry_used:
            _data_label = "REAL TELEMETRY — NWDP / Gujarat SW GW"
        elif _discharge_used:
            _data_label = "MODELLED RIVER DISCHARGE — Open-Meteo / GloFAS"
        else:
            _data_label = "DEMO/SIMULATED"

        if _telemetry_used:
            _telemetry_note = (
                f"Water level from NWDP telemetry station '{_telemetry_station}' "
                f"at {_telemetry_ts} (raw: {_telemetry_raw_m} m gauge height). "
                "Normalised to 0–5 m model input range."
            )
        else:
            _telemetry_note = "Water level derived from rainfall estimate (no live telemetry injected)."

        if _discharge_used:
            _discharge_note = (
                f"MODELLED — GloFAS via Open-Meteo Flood API. "
                f"City: {_discharge_city}. "
                f"Current discharge: {_discharge_m3s} m\u00b3/s. "
                f"Peak: {_discharge_peak} m\u00b3/s on {_discharge_peak_date}. "
                f"Tier: {_discharge_tier}. "
                f"Discharge factor: {_discharge_factor:.4f}. "
                "NOT a measured water level. Treated as supplementary advisory input only."
            )
        else:
            _discharge_note = (
                "GloFAS river discharge unavailable or not injected. "
                "Risk score based on rainfall, telemetry, and historical data only."
            )

        result = {
            "prediction_id": f"PRED-{uuid.uuid4().hex[:8].upper()}",
            "city": city,
            "area": area,
            "latitude": latitude,
            "longitude": longitude,
            "risk_score": risk_score,
            "risk_level": risk_level,
            "risk_color": RISK_COLORS[risk_level],
            "confidence": pred.get("confidence", 0.75),
            "predicted_time_window": time_window,
            "main_reasons": pred.get("main_reasons", []),
            "recommended_action": action_map[risk_level],
            "feature_importance": pred.get("feature_importance", {}),
            "probabilities": pred.get("probabilities", {}),
            "input_features": features,
            "blocked_drains": blocked_drains,
            "active_reports": report_count,
            "historical_incidents": hist_freq,
            "created_at": datetime.now(timezone.utc).isoformat(),
            "model_version": "v1.0-synthetic",
            "data_label": _data_label,
            # Real telemetry provenance fields (NWDP CSV)
            "telemetry_used":      _telemetry_used,
            "telemetry_station":   _telemetry_station,
            "telemetry_timestamp": _telemetry_ts,
            "telemetry_raw_m":     _telemetry_raw_m,
            "telemetry_note":      _telemetry_note,
            # River discharge provenance fields (GloFAS / Open-Meteo Flood API)
            "discharge_used":       _discharge_used,
            "discharge_city":       _discharge_city,
            "discharge_m3s":        _discharge_m3s,
            "discharge_tier":       _discharge_tier,
            "discharge_factor":     _discharge_factor,
            "discharge_peak_m3s":   _discharge_peak,
            "discharge_peak_date":  _discharge_peak_date,
            "discharge_fetched_at": _discharge_fetched_at,
            "discharge_note":       _discharge_note,
        }

        self._log(f"Analyzed {area}, {city} → {risk_level} ({risk_score:.0f})")
        self.last_run = datetime.now(timezone.utc).isoformat()
        return result

    def analyze_all_areas(
        self,
        rainfall_records: list[dict],
        drain_records: list[dict],
        report_records: list[dict],
        incident_records: list[dict],
        area_meta: dict,
        real_water_level: dict | None = None,
        glofas_data: dict | None = None,
        water_level_by_city: dict[str, dict] | None = None,
    ) -> list[dict]:
        """
        Run risk analysis for all areas across cities.
        Returns sorted list of risk assessments.

        Parameters
        ----------
        real_water_level : dict | None
            Legacy single-city reading (Sabarmati / Ahmedabad).
            Used when water_level_by_city is not supplied or has no entry
            for the area's city.  Kept for backward compatibility.

        water_level_by_city : dict[str, dict] | None
            Optional city-keyed map of telemetry readings, e.g.:
                {
                    "Ahmedabad": <Sabarmati primary station reading>,
                    "Surat":     <Tapi primary station reading>,
                }
            When present, the correct river's reading is selected per area
            so that Sabarmati values are NEVER injected into Surat areas and
            Tapi values are NEVER injected into Ahmedabad areas.
            Takes priority over the legacy real_water_level argument.

        glofas_data : dict | None
            Multi-city result from services.glofas_flood_api.get_flood_discharge().
            Contains per-city river-discharge forecasts.
            The correct city record is selected per area and passed as
            river_discharge to analyze_area().
        """
        self._log(f"Starting batch analysis — {len(rainfall_records)} areas")
        # Log telemetry sources that will be injected
        if water_level_by_city:
            for _city, _reading in water_level_by_city.items():
                if _reading and _reading.get("ok"):
                    self._log(
                        f"Real telemetry injected for {_city}: "
                        f"station={_reading.get('station')}, "
                        f"wl={_reading.get('water_level_m')} m, "
                        f"ts={_reading.get('timestamp_str')}"
                    )
        elif real_water_level and real_water_level.get("ok"):
            self._log(
                f"Real telemetry injected: station={real_water_level.get('station')}, "
                f"wl={real_water_level.get('water_level_m')} m, "
                f"ts={real_water_level.get('timestamp_str')}"
            )
        _glofas_cities = (glofas_data or {}).get("cities", {})
        if _glofas_cities:
            _active = [c for c, r in _glofas_cities.items() if r.get("ok")]
            if _active:
                self._log(
                    f"GloFAS discharge injected for cities: {_active} "
                    f"[MODELLED — Open-Meteo Flood API, not measured water level]"
                )
        results = []

        for rf in rainfall_records:
            city = rf.get("city", "")
            area_name = rf.get("area", "")

            # Get area metadata
            area_info = next(
                (a for a in area_meta.get(city, []) if a["name"] == area_name),
                {"lat": rf["latitude"], "lon": rf["longitude"], "elevation": 50}
            )
            elevation = area_info.get("elevation", 50)

            # Filter related data
            area_drains = [d for d in drain_records if d["area"] == area_name and d["city"] == city]
            area_reports = [r for r in report_records if r["area"] == area_name and r["city"] == city]
            area_incidents = [i for i in incident_records if i["area"] == area_name and i["city"] == city]

            # Select per-city GloFAS discharge record (or None if unavailable)
            city_discharge = _glofas_cities.get(city) if _glofas_cities else None

            # Select the correct river telemetry for this area's city.
            # water_level_by_city takes priority; legacy real_water_level is
            # the fallback so existing callers without the new map still work.
            if water_level_by_city is not None:
                area_water_level = water_level_by_city.get(city)
            else:
                area_water_level = real_water_level

            assessment = self.analyze_area(
                area=area_name,
                city=city,
                latitude=rf["latitude"],
                longitude=rf["longitude"],
                rainfall_data=rf,
                drain_data=area_drains,
                citizen_reports=area_reports,
                historical_incidents=area_incidents,
                elevation=elevation,
                real_water_level=area_water_level,
                river_discharge=city_discharge,
            )
            results.append(assessment)

        # Sort by risk score descending
        results.sort(key=lambda x: x["risk_score"], reverse=True)
        self._log(f"Batch analysis complete — {len(results)} areas assessed")

        critical = sum(1 for r in results if r["risk_level"] == "CRITICAL")
        high = sum(1 for r in results if r["risk_level"] == "HIGH")
        self._log(f"Risk summary: {critical} CRITICAL, {high} HIGH")

        return results

    def get_status(self) -> dict:
        return {
            "agent": self.name,
            "status": "ACTIVE",
            "model_loaded": self.model is not None and getattr(self.model, "is_trained", False),
            "last_run": self.last_run,
            "recent_activity": self.activity_log[-5:],
        }


# ──────────────────────────────────────────────
# Rule-based fallback
# ──────────────────────────────────────────────
def _rule_based_predict(features: dict) -> dict:
    r1h = features.get("rainfall_1h", 0)
    dc  = features.get("drainage_capacity", 50)
    hff = features.get("historical_flood_freq", 0)
    cr  = features.get("citizen_reports", 0)
    wl  = features.get("water_level", 0)
    el  = features.get("elevation", 50)

    score = (
        r1h * 0.35 +
        (100 - dc) * 0.25 +
        hff * 3.0 +
        cr * 0.3 +
        wl * 8.0 +
        max(0, 60 - el) * 0.4
    ) * 0.85

    score = max(0, min(100, score))
    level = (
        "CRITICAL" if score >= 75 else
        "HIGH"     if score >= 50 else
        "MEDIUM"   if score >= 25 else
        "LOW"
    )
    reasons = []
    if r1h > 40: reasons.append(f"High rainfall: {r1h:.0f} mm/hr")
    if dc < 40:  reasons.append(f"Low drainage capacity: {dc:.0f}%")
    if hff > 3:  reasons.append(f"Historical flooding: {hff} events/year")
    if cr > 20:  reasons.append(f"Citizen reports: {int(cr)}")

    return {
        "risk_score": round(score, 1),
        "risk_level": level,
        "confidence": 0.70,
        "main_reasons": reasons or ["Multiple risk factors contributing."],
        "feature_importance": {},
        "probabilities": {},
    }


# ──────────────────────────────────────────────
# Singleton
# ──────────────────────────────────────────────
_flood_risk_agent: FloodRiskAgent | None = None


def get_flood_risk_agent() -> FloodRiskAgent:
    global _flood_risk_agent
    if _flood_risk_agent is None:
        _flood_risk_agent = FloodRiskAgent()
    return _flood_risk_agent
