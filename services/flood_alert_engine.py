"""
FloodGuard AI — Flood Alert Engine
=====================================
Combines multi-source evidence into structured flood risk alerts.

Pipeline:
    Live weather (rainfall)
    + Water level estimates
    + Drainage stress
    + ML risk predictions
    + Citizen reports
    + Historical flood frequency
    ↓
    Risk score (0–100)
    Risk level (GREEN / YELLOW / ORANGE / RED)
    Expected flood-risk window
    Evidence summary
    Confidence estimate
    ↓
    Alert record with de-duplication / cooldown
    ↓
    Notification dispatch

IMPORTANT:
  - Risk levels map: GREEN = LOW, YELLOW = MEDIUM, ORANGE = HIGH, RED = CRITICAL
  - "Expected Flood-Risk Window" is an ESTIMATE based on forecast data.
    It is NOT a precise hydrological prediction.
  - The system never claims "flood will definitely occur at X time."
  - All thresholds are configurable via environment variables.
  - Simulation alerts are clearly labelled and never trigger real notifications.
"""
from __future__ import annotations

import os
import time
import uuid
from datetime import datetime, timezone
from typing import Any

# ─────────────────────────────────────────────────────────────────────────────
# Configurable thresholds
# ─────────────────────────────────────────────────────────────────────────────

def _float_env(key: str, default: float) -> float:
    try:
        return float(os.getenv(key, str(default)))
    except (ValueError, TypeError):
        return default


# Risk score thresholds (0–100)
THRESHOLD_GREEN  = _float_env("ALERT_THRESHOLD_GREEN",  25.0)
THRESHOLD_YELLOW = _float_env("ALERT_THRESHOLD_YELLOW", 40.0)
THRESHOLD_ORANGE = _float_env("ALERT_THRESHOLD_ORANGE", 60.0)
THRESHOLD_RED    = _float_env("ALERT_THRESHOLD_RED",    75.0)

# Evidence fusion weights — labelled as PROTOTYPE weights
# Calibrate with real historical data before operational use.
FUSION_WEIGHTS = {
    "ml_risk_score":            0.35,  # Random Forest prediction
    "rainfall_intensity":       0.20,  # Current rainfall (normalised)
    "water_level_stress":       0.15,  # Water level vs thresholds
    "drainage_stress":          0.15,  # Drainage capacity/blockage
    "citizen_report_signals":   0.10,  # Report volume and severity
    "historical_vulnerability": 0.05,  # Historical flood frequency
}
FUSION_WEIGHT_LABEL = "⚠️ Prototype decision-fusion weights — not yet calibrated with historical data"

# Alert cooldown: avoid re-alerting for the same area within this window
ALERT_COOLDOWN_SECONDS = int(os.getenv("ALERT_COOLDOWN_SECONDS", "1800"))  # 30 min


# ─────────────────────────────────────────────────────────────────────────────
# In-memory alert state (persisted via database.py)
# ─────────────────────────────────────────────────────────────────────────────
_active_alerts: dict[str, dict] = {}   # event_id → alert record
_cooldown_map:  dict[str, float] = {}  # location_key → last_alert_epoch


# ─────────────────────────────────────────────────────────────────────────────
# Evidence normalisation helpers
# ─────────────────────────────────────────────────────────────────────────────

def _norm_ml_risk(risk_predictions: list[dict], location: str) -> tuple[float, str]:
    """Extract ML risk score for a location (0–100)."""
    for p in risk_predictions:
        if location.lower() in f"{p.get('area','')}, {p.get('city','')}".lower():
            score = float(p.get("risk_score", 0))
            level = p.get("risk_level", "LOW")
            conf  = p.get("confidence", 0.75)
            return min(100, max(0, score)), f"ML flood risk: {score:.0f}/100 ({level}, conf {conf:.0%})"
    # Use aggregate max if specific match not found
    if risk_predictions:
        max_p = max(risk_predictions, key=lambda x: x.get("risk_score", 0))
        score = float(max_p.get("risk_score", 0))
        return min(100, score), f"ML flood risk (aggregate max): {score:.0f}/100"
    return 0.0, "ML risk: no prediction available"


def _norm_rainfall(rainfall_1h: float, rainfall_6h: float) -> tuple[float, str]:
    """Normalise rainfall to 0–100. 120 mm/hr = 100."""
    score = min(100, (rainfall_1h / 120) * 100)
    # Boost for sustained rainfall
    if rainfall_6h > 50:
        score = min(100, score * 1.15)
    note = f"Rainfall: {rainfall_1h:.1f} mm/hr current, {rainfall_6h:.1f} mm/6h"
    return round(score, 1), note


def _norm_water_level(water_records: list[dict], city: str) -> tuple[float, str]:
    """Normalise water level stress 0–100."""
    for rec in water_records:
        if rec.get("city", "").lower() == city.lower():
            tier = rec.get("tier", "NORMAL")
            above_normal = float(rec.get("above_normal_m", 0))
            # Map tier to score
            tier_scores = {"NORMAL": 10, "WARNING": 45, "DANGER": 75, "EXTREME": 95}
            score = tier_scores.get(tier, 10)
            mode  = rec.get("data_mode", "ESTIMATED")
            note  = f"Water level: {tier} ({above_normal:.2f}m above normal) [{mode}]"
            return float(score), note
    return 10.0, "Water level: no data available (UNAVAILABLE)"


def _norm_drainage(drain_analysis: dict, city: str | None) -> tuple[float, str]:
    """Normalise drainage stress 0–100."""
    summary = drain_analysis.get("priority_summary", {})
    critical_drains = int(summary.get("CRITICAL", 0))
    high_drains     = int(summary.get("HIGH", 0))
    total_drains    = int(drain_analysis.get("total_drains", 1) or 1)
    blocked_count   = int(drain_analysis.get("blocked_drains", 0))

    stress = min(100, (critical_drains * 20 + high_drains * 10) / max(total_drains, 1) * 100)
    score  = min(100, stress + blocked_count * 5)
    note   = f"Drainage: {critical_drains} critical, {high_drains} high-priority, {blocked_count} blocked"
    return round(score, 1), note


def _norm_citizen_reports(report_analysis: dict) -> tuple[float, str]:
    """Normalise citizen report signal 0–100."""
    total    = int(report_analysis.get("total_reports", 0))
    by_sev   = report_analysis.get("by_severity", {})
    critical = int(by_sev.get("CRITICAL", 0))
    high_r   = int(by_sev.get("HIGH", 0))
    score    = min(100, total * 0.5 + critical * 10 + high_r * 5)
    note     = f"Citizen reports: {total} total, {critical} critical, {high_r} high severity"
    return round(score, 1), note


def _norm_historical(risk_predictions: list[dict], location: str) -> tuple[float, str]:
    """Extract historical flood frequency as risk signal."""
    for p in risk_predictions:
        if location.lower() in f"{p.get('area','')}, {p.get('city','')}".lower():
            freq = float(p.get("input_features", {}).get("historical_flood_freq", 0))
            score = min(100, freq * 10)
            return round(score, 1), f"Historical flood frequency: {freq:.1f} events/year"
    return 0.0, "Historical frequency: no data"


# ─────────────────────────────────────────────────────────────────────────────
# Expected risk window calculator
# ─────────────────────────────────────────────────────────────────────────────

def _estimate_risk_window(
    risk_score: float,
    rainfall_forecast_6h: float,
    water_level_tier: str,
    drainage_stress: float,
) -> tuple[str, str]:
    """
    Estimate an expected flood-risk window using available forecast signals.

    Returns (window_string, reason_string).

    IMPORTANT: This is a HEURISTIC estimate, NOT a physically accurate
    hydrological/hydraulic prediction. It should be clearly labelled as such.
    The label "Expected Flood-Risk Window" is used, never "Flood will occur at X."
    """
    now = datetime.now(timezone.utc)

    if risk_score < THRESHOLD_YELLOW:
        return "LOW RISK — No imminent risk window", "Risk score below threshold"

    # Estimate window onset based on severity signals
    # These time offsets are heuristic only.
    if risk_score >= THRESHOLD_RED:
        onset_hours  = 0.5   # Immediate threat
        duration_hrs = 3.0
        reason_parts = [f"Critical ML risk score ({risk_score:.0f}/100)"]
    elif risk_score >= THRESHOLD_ORANGE:
        onset_hours  = 1.5
        duration_hrs = 4.0
        reason_parts = [f"High ML risk score ({risk_score:.0f}/100)"]
    else:
        onset_hours  = 3.0
        duration_hrs = 3.0
        reason_parts = [f"Moderate risk score ({risk_score:.0f}/100)"]

    # Rainfall forecast adjustment
    if rainfall_forecast_6h > 60:
        onset_hours  = max(0.25, onset_hours - 1.0)
        reason_parts.append(f"Heavy forecast rainfall ({rainfall_forecast_6h:.0f}mm/6h)")
    elif rainfall_forecast_6h > 30:
        reason_parts.append(f"Moderate forecast rainfall ({rainfall_forecast_6h:.0f}mm/6h)")

    # Water level adjustment
    if water_level_tier in ("DANGER", "EXTREME"):
        onset_hours = max(0.25, onset_hours - 0.5)
        reason_parts.append(f"River/water level at {water_level_tier}")

    # Drainage adjustment
    if drainage_stress > 70:
        onset_hours = max(0.25, onset_hours - 0.5)
        reason_parts.append("High drainage stress")

    from datetime import timedelta
    t_start = now + timedelta(hours=onset_hours)
    t_end   = t_start + timedelta(hours=duration_hrs)

    # Format in IST (UTC+5:30)
    from datetime import timezone as tz
    ist_offset = tz(timedelta(hours=5, minutes=30))
    t_start_ist = t_start.astimezone(ist_offset)
    t_end_ist   = t_end.astimezone(ist_offset)

    window_str = (
        f"{t_start_ist.strftime('%H:%M')}–{t_end_ist.strftime('%H:%M')} IST "
        f"(+{onset_hours:.1f}h to +{onset_hours + duration_hrs:.1f}h from now)"
    )
    reason_str = "; ".join(reason_parts)

    return window_str, reason_str


# ─────────────────────────────────────────────────────────────────────────────
# Core alert calculation
# ─────────────────────────────────────────────────────────────────────────────

def compute_risk_alert(
    location: str,
    city: str,
    latitude: float,
    longitude: float,
    risk_predictions: list[dict],
    drain_analysis: dict,
    report_analysis: dict,
    water_records: list[dict],
    rainfall_1h: float,
    rainfall_6h: float,
    rainfall_24h: float,
    rainfall_forecast_6h: float = 0.0,
    scenario: str = "NORMAL",
    is_simulation: bool = False,
) -> dict[str, Any]:
    """
    Compute a structured risk alert for a given location.

    Returns a fully structured alert record or None if risk is below threshold.
    """
    # --- Evidence fusion ---
    scores: dict[str, float] = {}
    notes:  dict[str, str]   = {}

    scores["ml_risk_score"],            notes["ml_risk"] = _norm_ml_risk(risk_predictions, location)
    scores["rainfall_intensity"],       notes["rainfall"] = _norm_rainfall(rainfall_1h, rainfall_6h)
    scores["water_level_stress"],       notes["water_level"] = _norm_water_level(water_records, city)
    scores["drainage_stress"],          notes["drainage"] = _norm_drainage(drain_analysis, city)
    scores["citizen_report_signals"],   notes["reports"] = _norm_citizen_reports(report_analysis)
    scores["historical_vulnerability"], notes["history"] = _norm_historical(risk_predictions, location)

    # Weighted composite score
    composite = sum(
        FUSION_WEIGHTS.get(k, 0) * v for k, v in scores.items()
    )
    composite = round(min(100, max(0, composite)), 1)

    # Confidence estimate — based on data availability
    data_quality_signals = [
        scores["ml_risk_score"] > 0,
        rainfall_1h > 0,
        scores["water_level_stress"] > 10,
        scores["drainage_stress"] > 0,
    ]
    confidence = round(0.50 + 0.10 * sum(data_quality_signals), 2)

    # Risk level mapping
    if composite >= THRESHOLD_RED:
        risk_level  = "RED"
        alert_color = "#ef4444"
        severity    = "CRITICAL"
    elif composite >= THRESHOLD_ORANGE:
        risk_level  = "ORANGE"
        alert_color = "#f97316"
        severity    = "HIGH"
    elif composite >= THRESHOLD_YELLOW:
        risk_level  = "YELLOW"
        alert_color = "#eab308"
        severity    = "MODERATE"
    else:
        risk_level  = "GREEN"
        alert_color = "#22c55e"
        severity    = "LOW"

    # Determine water level tier for window calculation
    wl_tier = "NORMAL"
    for rec in water_records:
        if rec.get("city", "").lower() == city.lower():
            wl_tier = rec.get("tier", "NORMAL")
            break

    drain_stress_val = scores.get("drainage_stress", 0)

    # Expected risk window
    risk_window, window_reason = _estimate_risk_window(
        composite, rainfall_forecast_6h, wl_tier, drain_stress_val
    )

    # Build evidence list for display
    evidence = [
        notes["rainfall"],
        notes["water_level"],
        notes["drainage"],
        notes["reports"],
        notes["history"],
    ]
    evidence = [e for e in evidence if e]

    # Recommended action
    if risk_level == "RED":
        recommended_action = (
            "CRITICAL: Deploy emergency response resources immediately. "
            "Issue area flood warning. Pre-position rescue equipment. "
            "Consider evacuation advisory for lowest-lying zones. "
            "Requires authorized human approval before public notification."
        )
    elif risk_level == "ORANGE":
        recommended_action = (
            "HIGH: Pre-position response teams. Clear critical drainage blockages. "
            "Monitor situation continuously. Prepare for potential escalation."
        )
    elif risk_level == "YELLOW":
        recommended_action = (
            "MONITOR: Increase monitoring frequency. Inspect drainage at risk points. "
            "Brief response teams for standby."
        )
    else:
        recommended_action = "Continue routine monitoring."

    # Data sources
    data_sources = ["Open-Meteo (weather/rainfall)"]
    if scores["ml_risk_score"] > 0:
        data_sources.append("Random Forest ML model")
    if scores["water_level_stress"] > 10:
        data_sources.append("Water Level Estimate (rainfall-derived)")
    if scores["citizen_report_signals"] > 0:
        data_sources.append("Citizen Reports (USER SUBMITTED)")

    # Per-factor data status labels for display
    data_status_map = {
        "Rainfall":           "LIVE" if rainfall_1h > 0 else "ESTIMATED",
        "ML Risk Score":      "MODEL",
        "Water Level":        "ESTIMATED",   # derived from rainfall, not live sensor
        "Drainage":           "DEMO",         # synthetic infrastructure data
        "Citizen Reports":    "USER SUBMITTED",
        "Historical":         "DEMO",
    }
    # Derive overall alert data status
    _has_live_rain = rainfall_1h > 0
    data_status_summary = "LIVE+MODEL" if _has_live_rain else "MODEL+DEMO"

    # Trigger text (what caused this alert to fire)
    if composite >= THRESHOLD_RED:
        trigger_text = f"Risk score {composite:.0f}/100 crossed RED threshold ({THRESHOLD_RED})"
    elif composite >= THRESHOLD_ORANGE:
        trigger_text = f"Risk score {composite:.0f}/100 crossed ORANGE threshold ({THRESHOLD_ORANGE})"
    elif composite >= THRESHOLD_YELLOW:
        trigger_text = f"Risk score {composite:.0f}/100 crossed YELLOW threshold ({THRESHOLD_YELLOW})"
    else:
        trigger_text = f"Risk score {composite:.0f}/100 — below alert threshold"

    now_iso = datetime.now(timezone.utc).isoformat()

    alert = {
        "event_id":          f"FGA-{uuid.uuid4().hex[:8].upper()}",
        "location":          location,
        "city":              city,
        "latitude":          latitude,
        "longitude":         longitude,
        "risk_level":        risk_level,
        "risk_score":        composite,
        "severity":          severity,
        "confidence":        confidence,
        "expected_window":   risk_window,
        "window_reason":     window_reason,
        "evidence":          evidence,
        "evidence_scores":   scores,
        "evidence_notes":    notes,
        "fusion_weights":    FUSION_WEIGHTS,
        "fusion_weight_note": FUSION_WEIGHT_LABEL,
        "recommended_action": recommended_action,
        "data_sources":      data_sources,
        "data_status_map":   data_status_map,
        "data_status":       data_status_summary,
        "trigger":           trigger_text,
        "scenario":          scenario,
        "is_simulation":     is_simulation,
        "alert_state":       "NEW",
        "alert_color":       alert_color,
        "timestamp":         now_iso,
        "created_at":        now_iso,
        # Freshness metadata
        "rainfall_1h":       rainfall_1h,
        "rainfall_6h":       rainfall_6h,
        "notification_status": {},
    }

    return alert


# ─────────────────────────────────────────────────────────────────────────────
# Alert engine — de-duplication and dispatch
# ─────────────────────────────────────────────────────────────────────────────

class FloodAlertEngine:
    """
    Main alert engine for FloodGuard AI.
    Processes pipeline output and generates de-duplicated, structured alerts.
    """

    def __init__(self):
        self._active_alerts: dict[str, dict] = {}
        self._last_alert_time: dict[str, float] = {}

    def _cooldown_ok(self, location_key: str) -> bool:
        """True if enough time has passed since the last alert for this location."""
        last = self._last_alert_time.get(location_key, 0)
        return (time.time() - last) > ALERT_COOLDOWN_SECONDS

    def _dedup_key(self, location: str, risk_level: str) -> str:
        return f"{location.lower()}|{risk_level}"

    def process_pipeline_output(
        self,
        state: dict,
        is_simulation: bool = False,
    ) -> list[dict]:
        """
        Generate alerts from a full pipeline state dict.

        Parameters
        ----------
        state        : orchestrator current_state dict
        is_simulation: if True, marks alerts as simulation and blocks real notifications

        Returns
        -------
        List of alert dicts (may be empty if risk is low or cooldown active)
        """
        if not state:
            return []

        risk_predictions = state.get("risk_predictions", [])
        drain_analysis   = state.get("drain_analysis", {})
        report_analysis  = state.get("report_analysis", {})
        rainfall_data    = state.get("rainfall_data", [])
        scenario         = state.get("scenario", "NORMAL")

        # Get water level data
        try:
            from services.water_level_service import get_water_level_service
            # Build rainfall lookup by city
            rain_lookup: dict[str, dict] = {}
            for r in rainfall_data:
                city = r.get("city", "")
                if city not in rain_lookup or r.get("rainfall_1h", 0) > rain_lookup[city].get("rainfall_1h", 0):
                    rain_lookup[city] = r
            wl_service = get_water_level_service()
            water_records = wl_service.get_all_locations(rainfall_by_city={
                c: {"rainfall_1h": v.get("rainfall_1h", 0),
                    "rainfall_6h": v.get("rainfall_6h", 0),
                    "rainfall_24h": v.get("rainfall_24h", 0)}
                for c, v in rain_lookup.items()
            })
        except Exception:
            water_records = []

        # Determine top-risk areas (process up to 5 highest-risk)
        sorted_preds = sorted(
            risk_predictions,
            key=lambda p: p.get("risk_score", 0),
            reverse=True,
        )[:5]

        new_alerts: list[dict] = []

        for pred in sorted_preds:
            area      = pred.get("area", "Unknown Area")
            city      = pred.get("city", "")
            location  = f"{area}, {city}"
            lat       = float(pred.get("latitude", 0))
            lon       = float(pred.get("longitude", 0))

            # Find matching rainfall
            rain_rec = {}
            for r in rainfall_data:
                if r.get("city") == city:
                    rain_rec = r
                    break

            rainfall_1h          = float(rain_rec.get("rainfall_1h", 0))
            rainfall_6h          = float(rain_rec.get("rainfall_6h", 0))
            rainfall_24h         = float(rain_rec.get("rainfall_24h", 0))
            forecast_precip_next6 = sum(rain_rec.get("forecast_precip_next6h") or [0] * 6)

            alert = compute_risk_alert(
                location=location,
                city=city,
                latitude=lat,
                longitude=lon,
                risk_predictions=risk_predictions,
                drain_analysis=drain_analysis,
                report_analysis=report_analysis,
                water_records=water_records,
                rainfall_1h=rainfall_1h,
                rainfall_6h=rainfall_6h,
                rainfall_24h=rainfall_24h,
                rainfall_forecast_6h=forecast_precip_next6,
                scenario=scenario,
                is_simulation=is_simulation,
            )

            # Only surface YELLOW or above
            if alert["risk_level"] == "GREEN":
                continue

            # De-duplication / cooldown
            dedup_key = self._dedup_key(location, alert["risk_level"])
            if not self._cooldown_ok(dedup_key):
                # Update existing alert rather than creating new one
                if dedup_key in self._active_alerts:
                    self._active_alerts[dedup_key]["timestamp"] = alert["timestamp"]
                continue

            # Record alert
            self._active_alerts[dedup_key] = alert
            self._last_alert_time[dedup_key] = time.time()
            new_alerts.append(alert)

            # Persist to database
            try:
                from services.database import save_alert
                save_alert(alert)
            except Exception:
                pass

        return new_alerts

    def get_active_alerts(self) -> list[dict]:
        """Return currently active alerts sorted by risk score descending."""
        return sorted(
            list(self._active_alerts.values()),
            key=lambda a: a.get("risk_score", 0),
            reverse=True,
        )

    def acknowledge_alert(self, event_id: str, operator: str = "operator") -> bool:
        """Mark an alert as acknowledged."""
        for alert in self._active_alerts.values():
            if alert.get("event_id") == event_id:
                alert["alert_state"] = "ACKNOWLEDGED"
                alert["acknowledged_at"] = datetime.now(timezone.utc).isoformat()
                alert["acknowledged_by"] = operator
                try:
                    from services.database import update_alert_state
                    update_alert_state(event_id, "ACKNOWLEDGED", {
                        "acknowledged_at": alert["acknowledged_at"]
                    })
                except Exception:
                    pass
                return True
        return False

    def resolve_alert(self, event_id: str, outcome: str = "") -> bool:
        """Mark an alert as resolved."""
        for key, alert in list(self._active_alerts.items()):
            if alert.get("event_id") == event_id:
                alert["alert_state"] = "RESOLVED"
                alert["resolved_at"] = datetime.now(timezone.utc).isoformat()
                alert["final_outcome"] = outcome
                try:
                    from services.database import update_alert_state
                    update_alert_state(event_id, "RESOLVED", {
                        "resolved_at": alert["resolved_at"],
                        "final_outcome": outcome,
                    })
                except Exception:
                    pass
                del self._active_alerts[key]
                return True
        return False

    def generate_test_alert(self, location: str = "Limbayat, Surat") -> dict:
        """
        Generate a TEST alert for demonstration purposes.
        Only dispatches notifications if TEST_NOTIFICATION_MODE=true.
        """
        now = datetime.now(timezone.utc).isoformat()
        return {
            "event_id":          f"TEST-{uuid.uuid4().hex[:6].upper()}",
            "location":          location,
            "city":              "Surat",
            "latitude":          21.2,
            "longitude":         72.85,
            "risk_level":        "RED",
            "risk_score":        87.0,
            "severity":          "CRITICAL",
            "confidence":        0.78,
            "expected_window":   "TEST WINDOW — +1h to +4h from now",
            "window_reason":     "TEST ALERT — not derived from real data",
            "evidence":          [
                "TEST: Heavy rainfall signal",
                "TEST: Rising water level indicator",
                "TEST: Drainage stress",
                "TEST: Multiple citizen reports",
            ],
            "recommended_action": "TEST ALERT — Deploy local response resources.",
            "data_sources":      ["TEST"],
            "scenario":          "TEST",
            "is_simulation":     True,
            "is_test":           True,
            "test_label":        "⚠️ TEST ALERT — NOT A REAL EMERGENCY",
            "alert_state":       "NEW",
            "alert_color":       "#ef4444",
            "timestamp":         now,
            "created_at":        now,
            "notification_status": {},
        }


# Module-level singleton
_alert_engine: FloodAlertEngine | None = None


def get_alert_engine() -> FloodAlertEngine:
    global _alert_engine
    if _alert_engine is None:
        _alert_engine = FloodAlertEngine()
    return _alert_engine
