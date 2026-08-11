"""
FloodGuard AI — Agent 4: Real-Time Civic Response Coordination Agent
The main agentic component. Combines outputs from all agents
to generate prioritized incident response plans.
Includes human approval workflow for emergency actions.
"""
import uuid
from datetime import datetime
from typing import Any

try:
    from agents.granite_service import generate_recommendation_explanation, generate_situation_report
except ImportError:
    from granite_service import generate_recommendation_explanation, generate_situation_report


PRIORITY_ORDER = {"CRITICAL": 4, "HIGH": 3, "MEDIUM": 2, "LOW": 1}


class ResponseCoordinationAgent:
    """
    Agent 4 — Response Coordination Agent.
    Aggregates risk predictions, drain alerts, and citizen reports
    to produce a ranked, actionable incident response plan.
    """

    def __init__(self):
        self.name = "Response Coordination Agent"
        self.last_run = None
        self.activity_log: list[str] = []

    def _log(self, msg: str):
        ts = datetime.utcnow().strftime("%H:%M:%S")
        self.activity_log.append(f"[{ts}] {msg}")
        if len(self.activity_log) > 50:
            self.activity_log = self.activity_log[-50:]

    def coordinate(
        self,
        risk_predictions: list[dict],
        drain_analysis: dict,
        report_analysis: dict,
        response_teams: list[dict],
        city: str = "All",
    ) -> dict:
        """
        Main coordination function.
        Returns a structured incident response plan with ranked recommendations.
        """
        self._log(f"Coordinating response for city={city}")

        # 1. Identify high-priority areas from flood risk
        critical_areas = [p for p in risk_predictions if p.get("risk_level") in ("CRITICAL", "HIGH")]
        critical_areas.sort(key=lambda x: x.get("risk_score", 0), reverse=True)

        # 2. Critical drains
        critical_drains = drain_analysis.get("requires_immediate_action", [])
        top_drains = drain_analysis.get("top_5_critical", [])

        # 3. Report hotspots
        hotspots = report_analysis.get("hotspot_areas", [])
        open_reports = report_analysis.get("open_reports", 0)

        # 4. Available teams
        available_teams = [t for t in response_teams if t.get("status") == "AVAILABLE"]

        # 5. Generate incidents
        incidents = []
        incident_counter = 1

        for area_pred in critical_areas[:8]:
            area = area_pred.get("area", "Unknown")
            area_city = area_pred.get("city", city)
            risk_level = area_pred.get("risk_level", "HIGH")
            risk_score = area_pred.get("risk_score", 0)
            rainfall = area_pred.get("input_features", {}).get("rainfall_1h", 0)

            # Count reports in this area
            area_reports = next(
                (h["report_count"] for h in hotspots if h["area"] == area), 0
            )

            # Find nearby critical drain
            nearby_drain = next(
                (d for d in top_drains if d.get("area") == area and d.get("city") == area_city), None
            )

            # Generate action list
            actions = _generate_actions(area, area_city, risk_level, rainfall, nearby_drain, area_reports, available_teams)

            incident_id = f"INC-{datetime.utcnow().strftime('%Y%m%d')}-{incident_counter:03d}"
            incident = {
                "incident_id": incident_id,
                "city": area_city,
                "area": area,
                "risk_level": risk_level,
                "risk_score": risk_score,
                "rainfall_1h": round(rainfall, 1),
                "citizen_reports": area_reports,
                "drain_risk": "HIGH" if nearby_drain and nearby_drain.get("maintenance_priority") in ("CRITICAL", "HIGH") else "MEDIUM",
                "recommended_actions": actions,
                "requires_human_approval": risk_level == "CRITICAL",
                "status": "PENDING_APPROVAL" if risk_level == "CRITICAL" else "ACTIVE",
                "created_at": datetime.utcnow().isoformat(),
                "latitude": area_pred.get("latitude"),
                "longitude": area_pred.get("longitude"),
            }
            incidents.append(incident)
            incident_counter += 1

        # 6. Top 5 system-level recommendations
        top_recommendations = _generate_system_recommendations(
            critical_areas, critical_drains, open_reports, available_teams, city
        )

        # 7. Summary data for Granite report
        summary_data = {
            "critical_zones": sum(1 for p in risk_predictions if p.get("risk_level") == "CRITICAL"),
            "high_zones": sum(1 for p in risk_predictions if p.get("risk_level") == "HIGH"),
            "citizen_reports": report_analysis.get("total_reports", 0),
            "avg_rainfall_1h": (
                sum(p.get("input_features", {}).get("rainfall_1h", 0) for p in risk_predictions) /
                max(len(risk_predictions), 1)
            ),
            "top_actions": [r["recommendation"] for r in top_recommendations[:3]],
        }

        self._log(f"Generated {len(incidents)} incidents, {len(top_recommendations)} recommendations")
        self.last_run = datetime.utcnow().isoformat()

        return {
            "city": city,
            "incidents": incidents,
            "top_recommendations": top_recommendations,
            "summary": summary_data,
            "available_teams": len(available_teams),
            "total_teams": len(response_teams),
            "critical_drain_count": len(critical_drains),
            "coordinated_at": datetime.utcnow().isoformat(),
            "requires_emergency_protocol": any(inc["risk_level"] == "CRITICAL" for inc in incidents),
        }

    def approve_action(self, incident_id: str, action_idx: int, approver: str) -> dict:
        """
        Human approval step for a recommended action.
        Returns approval record.
        """
        rec_id = f"REC-{uuid.uuid4().hex[:8].upper()}"
        self._log(f"Action approved: incident={incident_id}, action={action_idx}, by={approver}")
        return {
            "rec_id": rec_id,
            "incident_id": incident_id,
            "action_index": action_idx,
            "approval_status": "APPROVED",
            "approved_by": approver,
            "approved_at": datetime.utcnow().isoformat(),
        }

    def reject_action(self, incident_id: str, action_idx: int, approver: str, reason: str) -> dict:
        rec_id = f"REC-{uuid.uuid4().hex[:8].upper()}"
        self._log(f"Action rejected: incident={incident_id}, action={action_idx}, by={approver}")
        return {
            "rec_id": rec_id,
            "incident_id": incident_id,
            "action_index": action_idx,
            "approval_status": "REJECTED",
            "rejected_by": approver,
            "rejection_reason": reason,
            "rejected_at": datetime.utcnow().isoformat(),
        }

    def get_status(self) -> dict:
        return {
            "agent": self.name,
            "status": "ACTIVE",
            "last_run": self.last_run,
            "recent_activity": self.activity_log[-5:],
        }


# ──────────────────────────────────────────────
# Helpers
# ──────────────────────────────────────────────

def _generate_actions(
    area: str,
    city: str,
    risk_level: str,
    rainfall: float,
    nearby_drain: dict | None,
    report_count: int,
    available_teams: list[dict],
) -> list[dict]:
    actions = []
    action_idx = 1

    def _find_team(team_type: str) -> str:
        team = next(
            (t for t in available_teams if t.get("team_type") == team_type and t.get("city") == city),
            None
        )
        return team["name"] if team else f"{team_type.replace('_',' ').title()} (assign manually)"

    if risk_level == "CRITICAL":
        actions.append({
            "index": action_idx, "action": f"Deploy Emergency Response Team to {area}",
            "team": _find_team("emergency"), "requires_approval": True, "priority": "CRITICAL",
        }); action_idx += 1
        actions.append({
            "index": action_idx, "action": f"Activate flood control pumps in {area}",
            "team": _find_team("pump_team"), "requires_approval": True, "priority": "CRITICAL",
        }); action_idx += 1
        actions.append({
            "index": action_idx, "action": f"Issue CRITICAL citizen alert for {area}, {city}",
            "team": "Alert System", "requires_approval": True, "priority": "CRITICAL",
        }); action_idx += 1
        actions.append({
            "index": action_idx, "action": "Escalate to Emergency Management Officer",
            "team": "Senior Officer", "requires_approval": True, "priority": "CRITICAL",
        }); action_idx += 1

    if risk_level in ("HIGH", "CRITICAL") and nearby_drain:
        actions.append({
            "index": action_idx,
            "action": f"Inspect and clear drain {nearby_drain.get('drain_id', 'nearby')} in {area}",
            "team": _find_team("drainage"),
            "requires_approval": False,
            "priority": "HIGH",
        }); action_idx += 1

    if report_count >= 10:
        actions.append({
            "index": action_idx, "action": f"Acknowledge and respond to {report_count} citizen reports in {area}",
            "team": "Citizen Services", "requires_approval": False, "priority": "HIGH",
        }); action_idx += 1

    if rainfall > 40:
        actions.append({
            "index": action_idx, "action": f"Alert traffic control for potential road closure in {area}",
            "team": _find_team("traffic"), "requires_approval": False, "priority": "HIGH" if rainfall > 60 else "MEDIUM",
        }); action_idx += 1

    if risk_level == "HIGH":
        actions.append({
            "index": action_idx, "action": f"Issue HIGH risk advisory to citizens in {area}",
            "team": "Alert System", "requires_approval": False, "priority": "HIGH",
        }); action_idx += 1

    return actions


def _generate_system_recommendations(
    critical_areas: list[dict],
    critical_drain_ids: list[str],
    open_reports: int,
    available_teams: list[dict],
    city: str,
) -> list[dict]:
    recs = []
    rec_counter = 1

    if critical_areas:
        top_area = critical_areas[0]
        recs.append({
            "rec_id": f"SYS-{rec_counter:03d}",
            "agent": "Response Coordination Agent",
            "recommendation": f"Deploy emergency resources to {top_area['area']}, {top_area['city']} — highest risk zone (score: {top_area['risk_score']:.0f})",
            "reasoning": f"Risk score {top_area['risk_score']:.0f}/100, level {top_area['risk_level']}. " +
                         ("; ".join(top_area.get("main_reasons", [])[:2])),
            "priority": top_area["risk_level"],
            "requires_approval": top_area["risk_level"] == "CRITICAL",
        })
        rec_counter += 1

    if critical_drain_ids:
        n = len(critical_drain_ids)
        recs.append({
            "rec_id": f"SYS-{rec_counter:03d}",
            "agent": "Drainage Agent",
            "recommendation": f"Dispatch drainage maintenance team to {n} CRITICAL drain(s): {', '.join(critical_drain_ids[:3])}",
            "reasoning": f"{n} drains classified as CRITICAL priority due to blockage/capacity issues.",
            "priority": "CRITICAL" if n >= 3 else "HIGH",
            "requires_approval": False,
        })
        rec_counter += 1

    if open_reports > 50:
        recs.append({
            "rec_id": f"SYS-{rec_counter:03d}",
            "agent": "Citizen Report Agent",
            "recommendation": f"Activate surge response protocol — {open_reports} open citizen reports",
            "reasoning": f"High volume of unresolved citizen reports indicates widespread impact.",
            "priority": "HIGH",
            "requires_approval": False,
        })
        rec_counter += 1

    available_count = len(available_teams)
    if available_count < 3:
        recs.append({
            "rec_id": f"SYS-{rec_counter:03d}",
            "agent": "Response Coordination Agent",
            "recommendation": "Request additional response teams — current availability critically low",
            "reasoning": f"Only {available_count} teams available for deployment.",
            "priority": "HIGH",
            "requires_approval": True,
        })
        rec_counter += 1

    recs.append({
        "rec_id": f"SYS-{rec_counter:03d}",
        "agent": "Response Coordination Agent",
        "recommendation": "Generate and broadcast municipal flood situation report to all departments",
        "reasoning": "Regular communication ensures coordinated response across all municipal teams.",
        "priority": "MEDIUM",
        "requires_approval": False,
    })

    for r in recs:
        r["created_at"] = datetime.utcnow().isoformat()
        r["approval_status"] = "PENDING"
    return recs


# Singleton
_response_agent: ResponseCoordinationAgent | None = None


def get_response_agent() -> ResponseCoordinationAgent:
    global _response_agent
    if _response_agent is None:
        _response_agent = ResponseCoordinationAgent()
    return _response_agent
