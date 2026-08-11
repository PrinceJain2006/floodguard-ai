"""
FloodGuard AI — Agent 1: Flood Risk Prediction Agent
Analyzes rainfall, drainage, historical data, and citizen reports
to calculate per-area flood risk scores and classifications.
"""
import uuid
from datetime import datetime
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
        ts = datetime.utcnow().strftime("%H:%M:%S")
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
    ) -> dict:
        """
        Full risk analysis for a single area.
        Returns a structured risk assessment dict.
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

        # Water level estimate from rainfall
        r1h = rainfall_data.get("rainfall_1h", 0)
        r6h = rainfall_data.get("rainfall_6h", 0)
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
            "created_at": datetime.utcnow().isoformat(),
            "model_version": "v1.0-synthetic",
            "data_label": "DEMO/SIMULATED",
        }

        self._log(f"Analyzed {area}, {city} → {risk_level} ({risk_score:.0f})")
        self.last_run = datetime.utcnow().isoformat()
        return result

    def analyze_all_areas(
        self,
        rainfall_records: list[dict],
        drain_records: list[dict],
        report_records: list[dict],
        incident_records: list[dict],
        area_meta: dict,
    ) -> list[dict]:
        """
        Run risk analysis for all areas across cities.
        Returns sorted list of risk assessments.
        """
        self._log(f"Starting batch analysis — {len(rainfall_records)} areas")
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
