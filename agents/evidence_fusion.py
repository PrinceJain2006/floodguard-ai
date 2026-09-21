"""
FloodGuard AI — Evidence Fusion & Decision Intelligence Layer
=============================================================
Combines outputs from all existing agents into a transparent
zone-priority score, WHY THIS ZONE explanation, WHY NOW insight,
agent decision trace, and human-in-the-loop approval workflow.

All data is DEMO/SIMULATED. This is a decision-support tool only.
Labels are application priority scores — NOT scientifically validated
emergency-response scores.
"""
from __future__ import annotations

from datetime import datetime, timezone
from typing import Optional
import uuid

# ──────────────────────────────────────────────────────────────────────────────
# Evidence weights (must sum to 1.0)
# ──────────────────────────────────────────────────────────────────────────────
EVIDENCE_WEIGHTS = {
    "ml_risk_score":          0.35,   # Flood Risk Agent ML prediction
    "rainfall_intensity":     0.20,   # Rainfall 1h normalised
    "drainage_status":        0.18,   # Drainage capacity / blockage
    "citizen_reports":        0.12,   # Citizen report volume & severity
    "historical_vulnerability": 0.10, # Historical flood frequency
    "water_level_proxy":      0.05,   # Water level estimate
}

PRIORITY_LEVELS = {
    "CRITICAL": {"min": 75, "color": "#ef4444", "emoji": "🔴"},
    "HIGH":     {"min": 50, "color": "#f97316", "emoji": "🟠"},
    "MEDIUM":   {"min": 25, "color": "#eab308", "emoji": "🟡"},
    "LOW":      {"min": 0,  "color": "#22c55e", "emoji": "🟢"},
}


# ──────────────────────────────────────────────────────────────────────────────
# Evidence Normalizer
# Each normalise_* function returns a value in [0, 100] and a human text note.
# ──────────────────────────────────────────────────────────────────────────────

def _norm_ml_risk(risk_prediction: dict) -> tuple[float, str]:
    """Use ML risk score directly (already 0-100)."""
    score = float(risk_prediction.get("risk_score", 0))
    level = risk_prediction.get("risk_level", "LOW")
    conf  = risk_prediction.get("confidence", 0.75)
    note  = f"ML flood risk: {score:.0f}/100 ({level}, confidence {conf:.0%})"
    return min(100, max(0, score)), note


def _norm_rainfall(rain_1h: float) -> tuple[float, str]:
    """Normalise 1h rainfall to 0-100. 0=0mm, 100=120+mm."""
    score = min(100, (rain_1h / 120) * 100)
    if rain_1h >= 80:
        note = f"Extreme rainfall: {rain_1h:.1f} mm/hr"
    elif rain_1h >= 40:
        note = f"Heavy rainfall: {rain_1h:.1f} mm/hr"
    elif rain_1h >= 15:
        note = f"Moderate rainfall: {rain_1h:.1f} mm/hr"
    else:
        note = f"Light rainfall: {rain_1h:.1f} mm/hr"
    return score, note


def _norm_drainage(avg_capacity: float, blocked_count: int, total_drains: int) -> tuple[float, str]:
    """
    Low capacity and blocked drains → high score (high risk).
    Score = (100 - avg_capacity) weighted up by blocked fraction.
    """
    base = 100 - avg_capacity
    blocked_frac = (blocked_count / max(total_drains, 1)) * 100
    score = min(100, base * 0.7 + blocked_frac * 0.3)

    if blocked_count > 0:
        note = f"Drainage: {avg_capacity:.0f}% capacity, {blocked_count}/{total_drains} drains blocked"
    else:
        note = f"Drainage capacity: {avg_capacity:.0f}% (no blocked drains)"
    return score, note


def _norm_citizen_reports(report_count: int, critical_reports: int) -> tuple[float, str]:
    """
    Normalise citizen report density. 50+ reports = 100.
    Critical reports carry extra weight.
    """
    base_score = min(100, (report_count / 50) * 100)
    critical_bonus = min(30, critical_reports * 5)
    score = min(100, base_score + critical_bonus)
    note = f"Citizen reports: {report_count} total, {critical_reports} critical"
    return score, note


def _norm_historical(incident_count: int) -> tuple[float, str]:
    """
    Historical flood frequency: 10+ events/year = 100.
    """
    score = min(100, (incident_count / 10) * 100)
    if incident_count >= 7:
        note = f"High historical vulnerability: {incident_count} past flood events"
    elif incident_count >= 3:
        note = f"Moderate historical flooding: {incident_count} past events"
    else:
        note = f"Low historical flooding: {incident_count} past events"
    return score, note


def _norm_water_level(water_level: float) -> tuple[float, str]:
    """
    Water level 0–5m → 0–100.
    """
    score = min(100, (water_level / 5.0) * 100)
    note = f"Estimated water level: {water_level:.2f} m"
    return score, note


# ──────────────────────────────────────────────────────────────────────────────
# Evidence Fusion Engine
# ──────────────────────────────────────────────────────────────────────────────

def fuse_zone_evidence(
    risk_prediction: dict,
    drain_records: list[dict],
    area_reports: list[dict],
    historical_incidents: list[dict],
    live_weather_record: dict | None = None,
) -> dict:
    """
    Fuse all available evidence for a single zone into a priority score.

    Parameters:
        live_weather_record: Optional live weather dict (from LiveDataManager).
            When provided, the rainfall evidence is sourced from Open-Meteo
            (labeled LIVE) rather than from synthetic data (labeled DEMO).

    Returns a structured evidence fusion result including:
    - priority_score (0–100)
    - priority_level (CRITICAL / HIGH / MEDIUM / LOW)
    - contributing_factors (list of named factors with scores, each with data_source)
    - why_this_zone (explanation text)
    - evidence_breakdown (dict of normalised scores)
    - evidence_sources (dict: factor_key → data_source label)
    """
    area = risk_prediction.get("area", "Unknown")
    city = risk_prediction.get("city", "Unknown")
    features = risk_prediction.get("input_features", {})

    # ── Normalise each evidence source ──
    ml_score,   ml_note   = _norm_ml_risk(risk_prediction)

    # Rainfall: prefer live weather when available for this city
    city = risk_prediction.get("city", "Unknown")
    if live_weather_record and live_weather_record.get("city") == city:
        rain_1h = float(live_weather_record.get("rainfall_1h", 0))
        rain_source = "Open-Meteo (LIVE)"
        rain_is_live = True
    else:
        rain_1h = features.get("rainfall_1h", 0)
        rain_source = "Synthetic DEMO"
        rain_is_live = False

    rain_score,  rain_note = _norm_rainfall(rain_1h)
    if rain_is_live:
        rain_note += " [LIVE — Open-Meteo]"
    else:
        rain_note += " [DEMO — synthetic]"

    # Drain stats for this area
    area_drains = [d for d in drain_records if d.get("area") == area and d.get("city") == city]
    if area_drains:
        avg_cap   = sum(d.get("capacity_rating", 50) for d in area_drains) / len(area_drains)
        blocked   = sum(1 for d in area_drains if d.get("status") == "BLOCKED")
    else:
        avg_cap   = features.get("drainage_capacity", 50)
        blocked   = risk_prediction.get("blocked_drains", 0)
    drain_score, drain_note = _norm_drainage(avg_cap, blocked, max(len(area_drains), 1))

    # Citizen reports
    total_rpts   = len(area_reports)
    critical_rpts = sum(1 for r in area_reports if r.get("severity") == "CRITICAL")
    # Also pull from risk_prediction if direct area reports not yet broken out
    if total_rpts == 0:
        total_rpts = risk_prediction.get("active_reports", 0)
    report_score, report_note = _norm_citizen_reports(total_rpts, critical_rpts)

    # Historical
    hist_count  = len(historical_incidents) if historical_incidents else risk_prediction.get("historical_incidents", 0)
    hist_score,  hist_note  = _norm_historical(int(hist_count))

    # Water level
    water_level = features.get("water_level", 0)
    wl_score,    wl_note    = _norm_water_level(water_level)

    # ── Weighted fusion ──
    raw_scores = {
        "ml_risk_score":          ml_score,
        "rainfall_intensity":     rain_score,
        "drainage_status":        drain_score,
        "citizen_reports":        report_score,
        "historical_vulnerability": hist_score,
        "water_level_proxy":      wl_score,
    }
    notes = {
        "ml_risk_score":          ml_note,
        "rainfall_intensity":     rain_note,
        "drainage_status":        drain_note,
        "citizen_reports":        report_note,
        "historical_vulnerability": hist_note,
        "water_level_proxy":      wl_note,
    }
    # Evidence source labels — shown in the Decision Intelligence UI
    evidence_sources = {
        "ml_risk_score":            "FloodGuard ML Model",
        "rainfall_intensity":       rain_source,
        "drainage_status":          "Synthetic DEMO",
        "citizen_reports":          "Synthetic DEMO",
        "historical_vulnerability": "Synthetic DEMO",
        "water_level_proxy":        "Estimated (DEMO)",
    }

    fused_score = sum(
        raw_scores[k] * EVIDENCE_WEIGHTS[k]
        for k in EVIDENCE_WEIGHTS
    )
    fused_score = round(min(100, max(0, fused_score)), 1)

    # ── Priority level ──
    if fused_score >= 75:
        priority_level = "CRITICAL"
    elif fused_score >= 50:
        priority_level = "HIGH"
    elif fused_score >= 25:
        priority_level = "MEDIUM"
    else:
        priority_level = "LOW"

    # ── Contributing factors (sorted by weighted contribution) ──
    factors = []
    for key, weight in EVIDENCE_WEIGHTS.items():
        raw = raw_scores[key]
        contribution = raw * weight
        src = evidence_sources.get(key, "DEMO")
        is_live_factor = "LIVE" in src.upper() or "OPEN-METEO" in src.upper()
        factors.append({
            "factor_key":   key,
            "label":        _factor_label(key),
            "raw_score":    round(raw, 1),
            "weight":       weight,
            "contribution": round(contribution, 2),
            "note":         notes[key],
            "significant":  raw >= 60,
            "data_source":  src,
            "is_live":      is_live_factor,
        })
    factors.sort(key=lambda x: x["contribution"], reverse=True)

    # ── WHY THIS ZONE explanation ──
    why_factors = [f for f in factors if f["significant"]]
    why_this_zone = _build_why_this_zone(area, city, fused_score, priority_level, why_factors, risk_prediction)

    return {
        "area":            area,
        "city":            city,
        "priority_score":  fused_score,
        "priority_level":  priority_level,
        "priority_color":  PRIORITY_LEVELS[priority_level]["color"],
        "priority_emoji":  PRIORITY_LEVELS[priority_level]["emoji"],
        "evidence_breakdown": raw_scores,
        "evidence_sources": evidence_sources,
        "contributing_factors": factors,
        "why_this_zone":   why_this_zone,
        "notes":           notes,
        "fused_at":        datetime.now(timezone.utc).isoformat(),
        "rainfall_is_live": rain_is_live,
        "data_label":      "DEMO/SIMULATED — Application decision-support priority score only",
    }


def _factor_label(key: str) -> str:
    labels = {
        "ml_risk_score":          "ML Flood Risk Prediction",
        "rainfall_intensity":     "Rainfall Intensity",
        "drainage_status":        "Drainage Capacity/Blockage",
        "citizen_reports":        "Citizen Reports",
        "historical_vulnerability": "Historical Flood Vulnerability",
        "water_level_proxy":      "Estimated Water Level",
    }
    return labels.get(key, key)


def _build_why_this_zone(
    area: str,
    city: str,
    score: float,
    level: str,
    significant_factors: list[dict],
    risk_prediction: dict,
) -> str:
    """Build a structured WHY THIS ZONE explanation with all available evidence."""
    features = risk_prediction.get("input_features", {})
    r1h = features.get("rainfall_1h", 0)
    dc  = features.get("drainage_capacity", 50)
    wl  = features.get("water_level", 0)
    elev = features.get("elevation", 50)
    hff  = features.get("historical_flood_freq", 0)
    cr   = features.get("citizen_reports", 0)
    conf = risk_prediction.get("confidence", 0)
    ml_score = risk_prediction.get("risk_score", 0)

    lines = [f"WHY {area.upper()} ({city})?", ""]
    lines.append(f"Fused Priority Score: {score:.0f}/100 — {level}")
    lines.append(f"ML Flood Risk: {ml_score:.0f}/100 (confidence: {conf:.0%})")
    lines.append("")
    lines.append("📊 Evidence Snapshot:")

    # Rainfall evidence
    if r1h >= 50:
        lines.append(f"  🌧️ EXTREME rainfall: {r1h:.1f} mm/hr  [HIGH IMPACT]")
    elif r1h >= 25:
        lines.append(f"  🌧️ Heavy rainfall: {r1h:.1f} mm/hr  [ELEVATED]")
    elif r1h > 0:
        lines.append(f"  🌧️ Rainfall: {r1h:.1f} mm/hr  [MODERATE]")

    # Water level
    if wl >= 3:
        lines.append(f"  💧 CRITICAL water level: {wl:.1f} m above baseline  [DANGER]")
    elif wl >= 1.5:
        lines.append(f"  💧 Elevated water level: {wl:.1f} m  [WATCH]")

    # Drainage
    if dc < 30:
        lines.append(f"  🔧 CRITICALLY low drainage capacity: {dc:.0f}%  [DANGER]")
    elif dc < 60:
        lines.append(f"  🔧 Reduced drainage capacity: {dc:.0f}%  [ELEVATED]")

    # Citizen reports
    if cr >= 30:
        lines.append(f"  📱 HIGH citizen reports: {int(cr)}  [CONFIRMED FLOODING]")
    elif cr >= 10:
        lines.append(f"  📱 Multiple citizen reports: {int(cr)}  [ELEVATED]")

    # Historical
    if hff >= 5:
        lines.append(f"  📅 High historical flood frequency: {hff:.0f} events/year  [VULNERABLE]")
    elif hff >= 2:
        lines.append(f"  📅 Moderate historical flooding: {hff:.0f} events/year")

    # Elevation
    if elev < 15:
        lines.append(f"  ⛰️ Very low elevation: {elev:.0f} m — high inundation risk  [STRUCTURAL]")
    elif elev < 30:
        lines.append(f"  ⛰️ Low elevation zone: {elev:.0f} m  [ELEVATED]")

    # Top ML features
    top_feats = risk_prediction.get("top_features", [])
    if top_feats:
        lines.append("")
        lines.append("🤖 Top ML Feature Contributions (Random Forest):")
        for feat_name, importance in top_feats[:3]:
            label = feat_name.replace("_", " ").title()
            lines.append(f"  → {label}: {importance:.1%} model importance")

    # Significant fused factors
    if significant_factors:
        lines.append("")
        lines.append("🔀 Evidence Fusion Drivers:")
        for f in significant_factors[:4]:
            src_badge = "[LIVE]" if f.get("is_live") else "[DEMO]"
            lines.append(f"  ✓ {f['label']} ({f['raw_score']:.0f}/100) {src_badge}")

    lines.append("")
    action = risk_prediction.get("recommended_action", "")
    if action:
        lines.append(f"📋 Recommended: {action}")
    lines.append("")
    lines.append(
        "⚠ DEMO/SIMULATED — decision-support score only. "
        "Not a validated emergency-response score."
    )
    return "\n".join(lines)


# ──────────────────────────────────────────────────────────────────────────────
# WHY NOW — Temporal Comparison
# ──────────────────────────────────────────────────────────────────────────────

def build_why_now(
    current_fusion: dict,
    previous_fusion: Optional[dict],
) -> dict:
    """
    Compare current priority with previous (if available).
    Returns a WHY NOW insight dict.
    """
    area  = current_fusion["area"]
    city  = current_fusion["city"]
    curr_score = current_fusion["priority_score"]
    curr_level = current_fusion["priority_level"]

    if previous_fusion is None:
        return {
            "area":    area,
            "city":    city,
            "available": False,
            "message": "Insufficient historical comparison data for this zone.",
        }

    prev_score = previous_fusion["priority_score"]
    prev_level = previous_fusion["priority_level"]

    score_delta = curr_score - prev_score
    level_change = curr_level != prev_level

    # Identify what changed
    changes = []
    curr_ev = current_fusion.get("evidence_breakdown", {})
    prev_ev = previous_fusion.get("evidence_breakdown", {})
    for key in EVIDENCE_WEIGHTS:
        c = curr_ev.get(key, 0)
        p = prev_ev.get(key, 0)
        delta = c - p
        label = _factor_label(key)
        if abs(delta) >= 10:
            direction = "increased" if delta > 0 else "decreased"
            changes.append(f"{label} {direction} ({p:.0f} → {c:.0f})")

    if not changes:
        changes.append("Minor changes across multiple factors.")

    narrative = _build_why_now_narrative(
        area, curr_score, prev_score, curr_level, prev_level, score_delta, changes
    )

    return {
        "area":          area,
        "city":          city,
        "available":     True,
        "prev_score":    prev_score,
        "curr_score":    curr_score,
        "prev_level":    prev_level,
        "curr_level":    curr_level,
        "score_delta":   round(score_delta, 1),
        "level_changed": level_change,
        "changes":       changes,
        "narrative":     narrative,
    }


def _build_why_now_narrative(
    area, curr_score, prev_score, curr_level, prev_level, delta, changes
):
    direction = "increased" if delta >= 0 else "decreased"
    arrow = "↑" if delta > 0 else "↓" if delta < 0 else "→"
    urgency = ""
    if abs(delta) >= 20:
        urgency = "  ⚡ RAPID change — immediate review required."
    elif abs(delta) >= 10:
        urgency = "  ⚠ Significant change — monitor closely."

    lines = [
        f"WHY NOW — {area.upper()}?",
        "",
        f"Priority score {direction}: {prev_score:.0f} → {curr_score:.0f}  ({arrow}{abs(delta):.0f} pts)",
    ]
    if curr_level != prev_level:
        lines.append(f"🔺 Level escalated: {prev_level} → {curr_level}")
    if urgency:
        lines.append(urgency)
    lines.append("")
    lines.append("📈 What changed:")
    for c in changes:
        lines.append(f"  • {c}")
    lines.append("")
    lines.append(
        "⚠ DEMO/SIMULATED — comparison of application priority scores across scenario runs."
    )
    return "\n".join(lines)


# ──────────────────────────────────────────────────────────────────────────────
# Batch Fusion
# ──────────────────────────────────────────────────────────────────────────────

def fuse_all_zones(
    risk_predictions: list[dict],
    drain_records: list[dict],
    report_records: list[dict],
    incident_records: list[dict],
    live_weather_records: list[dict] | None = None,
) -> list[dict]:
    """
    Run evidence fusion for all zones and return sorted list.

    live_weather_records: optional list of live WeatherRecord dicts (one per city).
        When provided, the rainfall evidence for each zone uses the live
        observation for its city (labeled LIVE). Other evidence remains DEMO.
    """
    # Build a city → live weather record lookup for fast per-zone lookup
    live_by_city: dict[str, dict] = {}
    if live_weather_records:
        for rec in live_weather_records:
            city_key = rec.get("city", "")
            if city_key:
                live_by_city[city_key] = rec

    results = []
    for pred in risk_predictions:
        area = pred.get("area", "")
        city = pred.get("city", "")
        area_drains    = [d for d in drain_records  if d.get("area") == area and d.get("city") == city]
        area_reports   = [r for r in report_records if r.get("area") == area and r.get("city") == city]
        area_incidents = [i for i in incident_records if i.get("area") == area and i.get("city") == city]
        live_rec = live_by_city.get(city)  # None if no live data for this city
        fusion = fuse_zone_evidence(pred, area_drains, area_reports, area_incidents, live_rec)
        results.append(fusion)

    results.sort(key=lambda x: x["priority_score"], reverse=True)
    return results


# ──────────────────────────────────────────────────────────────────────────────
# Agent Decision Trace
# ──────────────────────────────────────────────────────────────────────────────

def build_agent_decision_trace(
    fusion_result: dict,
    risk_prediction: dict,
    drain_analysis: dict,
    report_analysis: dict,
    response_plan: dict,
    action_plan: dict,
) -> list[dict]:
    """
    Build a visible agent decision trace for a zone.
    Shows which agent contributed what evidence and how it feeds the final priority.
    """
    area  = fusion_result["area"]
    city  = fusion_result["city"]
    score = fusion_result["priority_score"]
    level = fusion_result["priority_level"]

    # ── Flood Risk Agent ──
    ml_score = risk_prediction.get("risk_score", 0)
    ml_level = risk_prediction.get("risk_level", "LOW")
    ml_reasons = risk_prediction.get("main_reasons", [])
    trace = [
        {
            "agent": "Flood Risk Agent",
            "emoji": "🌊",
            "mode": "ML + Rule-based (DEMO/SIMULATED)",
            "contribution": f"Flood probability score {ml_score:.0f}/100 — {ml_level}",
            "details": "; ".join(ml_reasons[:3]) if ml_reasons else "ML model evaluated rainfall and drainage features.",
            "output_label": f"Risk Score: {ml_score:.0f}",
        },
    ]

    # ── Drainage Agent ──
    drain_summary = drain_analysis.get("priority_summary", {})
    critical_drains = len(drain_analysis.get("requires_immediate_action", []))
    area_drain_data = [
        d for d in drain_analysis.get("scored_drains", [])
        if d.get("area") == area and d.get("city") == city
    ]
    drain_scores  = [d.get("computed_risk_score", 0) for d in area_drain_data]
    max_drain_score = max(drain_scores) if drain_scores else 0
    trace.append({
        "agent": "Drainage Agent",
        "emoji": "🔧",
        "mode": "Rule-based scoring (DEMO/SIMULATED)",
        "contribution": (
            f"Area drainage risk: {max_drain_score:.0f}/100. "
            f"System-wide critical drains: {critical_drains}."
        ),
        "details": (
            f"CRITICAL: {drain_summary.get('CRITICAL', 0)}, "
            f"HIGH: {drain_summary.get('HIGH', 0)}, "
            f"MEDIUM: {drain_summary.get('MEDIUM', 0)} — system total"
        ),
        "output_label": f"Drain Risk: {'HIGH' if max_drain_score >= 60 else 'MEDIUM' if max_drain_score >= 30 else 'LOW'}",
    })

    # ── Citizen Report Agent ──
    total_reports  = report_analysis.get("total_reports", 0)
    open_reports   = report_analysis.get("open_reports", 0)
    critical_rpts  = report_analysis.get("critical_count", 0)
    hotspots       = report_analysis.get("hotspot_areas", [])
    is_hotspot     = any(h["area"] == area for h in hotspots)
    trace.append({
        "agent": "Citizen Intelligence Agent",
        "emoji": "📱",
        "mode": "Pattern analysis (DEMO/SIMULATED)",
        "contribution": (
            f"Analyzed {total_reports} citizen reports; {open_reports} open, "
            f"{critical_rpts} critical. {'Zone is a HOTSPOT.' if is_hotspot else 'Zone not in top hotspot list.'}"
        ),
        "details": f"Top hotspot areas: {', '.join(h['area'] for h in hotspots[:3])}",
        "output_label": f"Reports: {total_reports} | Hotspot: {'YES' if is_hotspot else 'NO'}",
    })

    # ── Response Coordination Agent ──
    incidents = response_plan.get("incidents", [])
    zone_incident = next(
        (i for i in incidents if i.get("area") == area and i.get("city") == city), None
    )
    actions_for_zone = len(zone_incident.get("recommended_actions", [])) if zone_incident else 0
    trace.append({
        "agent": "Response Coordination Agent",
        "emoji": "⚡",
        "mode": "Priority queue (DEMO/SIMULATED)",
        "contribution": (
            f"Generated {actions_for_zone} recommended actions for {area}."
            if zone_incident
            else f"Area not in top-priority incident list (lower priority zone)."
        ),
        "details": (
            f"Incident status: {zone_incident.get('status', 'N/A')} | "
            f"Requires human approval: {zone_incident.get('requires_human_approval', False)}"
            if zone_incident
            else "No specific incident plan generated for this zone under current scenario."
        ),
        "output_label": f"Actions: {actions_for_zone}",
    })

    # ── Evidence Fusion Layer ──
    trace.append({
        "agent": "Evidence Fusion Layer",
        "emoji": "🔀",
        "mode": "Weighted fusion (deterministic, DEMO/SIMULATED)",
        "contribution": (
            f"Combined all agent evidence into priority score: {score:.0f}/100."
        ),
        "details": (
            "Weights: ML Risk 35%, Rainfall 20%, Drainage 18%, "
            "Citizen Reports 12%, Historical 10%, Water Level 5%."
        ),
        "output_label": f"Fused Score: {score:.0f}",
    })

    # ── Final Priority ──
    trace.append({
        "agent": "Final Decision",
        "emoji": "🎯",
        "mode": "Deterministic threshold",
        "contribution": f"PRIORITY: {level}",
        "details": (
            f"Score {score:.0f} → {level} "
            f"(CRITICAL≥75, HIGH≥50, MEDIUM≥25, LOW<25)"
        ),
        "output_label": level,
    })

    return trace


# ──────────────────────────────────────────────────────────────────────────────
# Recommended Action
# ──────────────────────────────────────────────────────────────────────────────

def get_recommended_action(fusion_result: dict, risk_prediction: dict) -> dict:
    """
    Produce a structured recommended action for human approval.
    """
    area  = fusion_result["area"]
    city  = fusion_result["city"]
    level = fusion_result["priority_level"]
    score = fusion_result["priority_score"]

    action_templates = {
        "CRITICAL": {
            "title":       f"CRITICAL: Inspect and prepare emergency response for {area}",
            "description": (
                f"{area}, {city} has a CRITICAL application priority score of {score:.0f}/100. "
                "Evidence: high ML flood risk, elevated rainfall, drainage constraints, "
                "and/or citizen report activity. "
                "Recommended: Deploy response resources, inspect critical drains, "
                "prepare evacuation routes, and issue public advisory."
            ),
            "urgency": "Immediate — within 0–2 hours",
            "requires_approval": True,
        },
        "HIGH": {
            "title":       f"HIGH: Pre-position response resources near {area}",
            "description": (
                f"{area}, {city} has a HIGH application priority score of {score:.0f}/100. "
                "Recommended: Pre-position drainage maintenance team, inspect high-risk drains, "
                "and monitor rainfall progression."
            ),
            "urgency": "Within 2–6 hours",
            "requires_approval": False,
        },
        "MEDIUM": {
            "title":       f"MEDIUM: Monitor {area} and prepare standby response",
            "description": (
                f"{area}, {city} has a MEDIUM application priority score of {score:.0f}/100. "
                "Recommended: Continue monitoring. Ensure response team is on standby."
            ),
            "urgency": "Within 6–12 hours",
            "requires_approval": False,
        },
        "LOW": {
            "title":       f"LOW: Routine monitoring for {area}",
            "description": (
                f"{area}, {city} has a LOW application priority score of {score:.0f}/100. "
                "No immediate action required. Continue standard monitoring."
            ),
            "urgency": "Routine",
            "requires_approval": False,
        },
    }

    template = action_templates[level]
    return {
        "action_id":          f"EF-{uuid.uuid4().hex[:8].upper()}",
        "area":               area,
        "city":               city,
        "priority_level":     level,
        "priority_score":     score,
        "title":              template["title"],
        "description":        template["description"],
        "urgency":            template["urgency"],
        "requires_approval":  template["requires_approval"],
        "ai_status":          "PENDING_HUMAN_APPROVAL" if template["requires_approval"] else "READY_FOR_EXECUTION",
        "human_decision":     None,
        "decided_by":         None,
        "decided_at":         None,
        "created_at":         datetime.now(timezone.utc).isoformat(),
        "data_label":         "DEMO/SIMULATED",
    }


# ──────────────────────────────────────────────────────────────────────────────
# Audit Trail
# ──────────────────────────────────────────────────────────────────────────────

class AuditTrail:
    """
    Lightweight in-memory audit trail for human decisions.
    Stores approve/modify/reject decisions for the session.
    All entries are DEMO only — no real-world actions are triggered.
    """

    def __init__(self):
        self._entries: list[dict] = []

    def record(
        self,
        action: dict,
        human_decision: str,      # "APPROVED" | "MODIFIED" | "REJECTED"
        decided_by: str = "Operator",
        modification_note: str = "",
    ) -> dict:
        entry = {
            "audit_id":        f"AUDIT-{uuid.uuid4().hex[:8].upper()}",
            "zone":            f"{action.get('area', '')}, {action.get('city', '')}",
            "area":            action.get("area", ""),
            "city":            action.get("city", ""),
            "priority_level":  action.get("priority_level", ""),
            "priority_score":  action.get("priority_score", 0),
            "ai_recommendation": action.get("title", ""),
            "human_decision":  human_decision,
            "decided_by":      decided_by,
            "modification_note": modification_note,
            "timestamp":       datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC"),
            "status":          "Demo Action Recorded",
            "data_label":      "DEMO/SIMULATED",
        }
        self._entries.append(entry)
        return entry

    def get_all(self) -> list[dict]:
        return list(reversed(self._entries))   # Most recent first

    def clear(self):
        self._entries.clear()


# ──────────────────────────────────────────────────────────────────────────────
# Singleton audit trail (session-scoped via Streamlit cache)
# ──────────────────────────────────────────────────────────────────────────────
_audit_trail: AuditTrail | None = None


def get_audit_trail() -> AuditTrail:
    global _audit_trail
    if _audit_trail is None:
        _audit_trail = AuditTrail()
    return _audit_trail
