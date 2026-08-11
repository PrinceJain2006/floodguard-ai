"""
FloodGuard AI — Chief Response Agent
Combines all agent outputs and generates a prioritized emergency action plan
with human approval gate for critical actions.
All outputs are DEMO/SIMULATED.
"""
import random
from datetime import datetime
from typing import Any


# ──────────────────────────────────────────────
# Resource templates (SIMULATED)
# ──────────────────────────────────────────────
RESOURCE_TYPES = {
    "pump_team":   {"emoji": "💧", "label": "Pump Team",   "deploy_time": 15, "coverage_km": 2.0},
    "ambulance":   {"emoji": "🚑", "label": "Ambulance",   "deploy_time": 8,  "coverage_km": 5.0},
    "shelter":     {"emoji": "🏠", "label": "Shelter",     "deploy_time": 30, "coverage_km": 3.0},
    "rapid_team":  {"emoji": "⚡", "label": "Rapid Team",  "deploy_time": 10, "coverage_km": 3.0},
    "drain_crew":  {"emoji": "🔧", "label": "Drain Crew",  "deploy_time": 20, "coverage_km": 1.5},
    "traffic_unit":{"emoji": "🚦", "label": "Traffic Unit","deploy_time": 5,  "coverage_km": 2.5},
}


class ChiefResponseAgent:
    """
    Combines outputs of all agents into a unified emergency action plan.
    Prioritizes actions, assigns resources, and flags human approval gates.
    DEMO/SIMULATED data only.
    """

    def __init__(self):
        self._status = "INACTIVE"
        self._last_run = None
        self._activity_log: list[str] = []

    def _log(self, msg: str):
        self._activity_log.append(f"{datetime.utcnow().strftime('%H:%M:%S')} — {msg}")
        if len(self._activity_log) > 30:
            self._activity_log = self._activity_log[-30:]

    def generate_action_plan(
        self,
        risk_predictions: list[dict],
        drain_analysis: dict,
        report_analysis: dict,
        response_plan: dict,
        teams: list[dict],
        scenario: str = "NORMAL",
    ) -> dict:
        """
        Generate a prioritized emergency action plan combining all agent outputs.
        Returns actions with priority, resource needs, and human approval flags.
        """
        self._status = "ACTIVE"
        self._log(f"Chief Response Agent activated for {scenario} scenario")

        actions = []
        action_id = 1

        # ── Pull from risk predictions ──
        critical_zones = [p for p in risk_predictions if p["risk_level"] == "CRITICAL"]
        high_zones     = [p for p in risk_predictions if p["risk_level"] == "HIGH"]

        for zone in critical_zones[:4]:
            rf = zone.get("input_features", {}).get("rainfall_1h", 0)
            actions.append({
                "action_id": f"CRA-{action_id:03d}",
                "priority": "CRITICAL",
                "category": "FLOOD_RESPONSE",
                "title": f"Emergency Flood Response — {zone['area']}, {zone['city']}",
                "description": (
                    f"Deploy pump teams and rapid response unit to {zone['area']}. "
                    f"Risk score {zone['risk_score']:.0f}/100, rainfall {rf:.0f} mm/hr. "
                    "Establish dewatering operations immediately."
                ),
                "area": zone["area"],
                "city": zone["city"],
                "resources_needed": ["pump_team", "rapid_team"],
                "estimated_time_min": 20,
                "requires_human_approval": True,
                "approval_reason": "Critical flood zone — emergency resource deployment",
                "source_agent": "Flood Risk Agent",
                "confidence": zone.get("confidence", 0.85),
                "impact_score": zone["risk_score"],
            })
            action_id += 1
            self._log(f"Critical action created for {zone['area']}")

        for zone in high_zones[:3]:
            actions.append({
                "action_id": f"CRA-{action_id:03d}",
                "priority": "HIGH",
                "category": "PRE_POSITIONING",
                "title": f"Pre-position Resources — {zone['area']}, {zone['city']}",
                "description": (
                    f"Pre-position drain crew and standby pump team near {zone['area']}. "
                    f"Risk score {zone['risk_score']:.0f}/100. Monitor closely."
                ),
                "area": zone["area"],
                "city": zone["city"],
                "resources_needed": ["drain_crew", "pump_team"],
                "estimated_time_min": 30,
                "requires_human_approval": False,
                "approval_reason": None,
                "source_agent": "Flood Risk Agent",
                "confidence": zone.get("confidence", 0.75),
                "impact_score": zone["risk_score"],
            })
            action_id += 1

        # ── Pull from drain analysis ──
        # requires_immediate_action is a list of drain_ids (strings)
        critical_drain_ids = drain_analysis.get("requires_immediate_action", [])[:3]
        # Build lookup from scored_drains
        drain_lookup = {d["drain_id"]: d for d in drain_analysis.get("scored_drains", [])}
        for drain_id in critical_drain_ids:
            drain = drain_lookup.get(drain_id, {})
            actions.append({
                "action_id": f"CRA-{action_id:03d}",
                "priority": "HIGH",
                "category": "DRAIN_CLEARANCE",
                "title": f"Urgent Drain Clearance — {drain_id}",
                "description": (
                    f"Clear blocked drain {drain_id} in {drain.get('area','Unknown')}, {drain.get('city','Unknown')}. "
                    f"Condition: {drain.get('condition','UNKNOWN')}. Risk score: {drain.get('computed_risk_score', 50):.0f}."
                ),
                "area": drain.get("area", "Unknown"),
                "city": drain.get("city", "Unknown"),
                "resources_needed": ["drain_crew"],
                "estimated_time_min": 45,
                "requires_human_approval": False,
                "approval_reason": None,
                "source_agent": "Drainage Agent",
                "confidence": 0.90,
                "impact_score": drain.get("computed_risk_score", 50),
            })
            action_id += 1
        self._log(f"Drain clearance actions: {len(critical_drain_ids)}")

        # ── Pull from citizen reports ──
        critical_reports = report_analysis.get("critical_count", 0)
        if critical_reports > 0:
            actions.append({
                "action_id": f"CRA-{action_id:03d}",
                "priority": "HIGH",
                "category": "CITIZEN_RESPONSE",
                "title": f"Respond to {critical_reports} Critical Citizen Reports",
                "description": (
                    f"{critical_reports} citizens have reported critical flood situations. "
                    "Dispatch emergency team to verify and respond to highest-severity reports immediately."
                ),
                "area": "Multiple",
                "city": "All",
                "resources_needed": ["rapid_team", "ambulance"],
                "estimated_time_min": 15,
                "requires_human_approval": critical_reports >= 5,
                "approval_reason": "High volume of critical reports — verify before mass response",
                "source_agent": "Citizen Report Agent",
                "confidence": 0.80,
                "impact_score": min(90, critical_reports * 10),
            })
            action_id += 1
            self._log(f"Citizen response action for {critical_reports} critical reports")

        # ── Evacuation trigger (scenario-based) ──
        if scenario in ("EXTREME", "EMERGENCY") and critical_zones:
            top_zone = critical_zones[0]
            actions.append({
                "action_id": f"CRA-{action_id:03d}",
                "priority": "CRITICAL",
                "category": "EVACUATION",
                "title": f"Evaluate Evacuation — {top_zone['area']}",
                "description": (
                    f"Extreme flood conditions in {top_zone['area']}. Evaluate need for precautionary "
                    "evacuation of low-lying residential areas. Coordinate with shelter teams."
                ),
                "area": top_zone["area"],
                "city": top_zone["city"],
                "resources_needed": ["rapid_team", "shelter", "ambulance"],
                "estimated_time_min": 60,
                "requires_human_approval": True,
                "approval_reason": "EVACUATION — Requires senior officer authorization",
                "source_agent": "Chief Response Agent",
                "confidence": 0.70,
                "impact_score": 95,
            })
            action_id += 1
            self._log("Evacuation evaluation action created")

        # Sort by impact score descending
        actions.sort(key=lambda x: x["impact_score"], reverse=True)

        # Executive summary
        critical_count = sum(1 for a in actions if a["priority"] == "CRITICAL")
        approval_needed = sum(1 for a in actions if a["requires_human_approval"])

        summary = (
            f"Chief Response Agent has generated {len(actions)} prioritized actions for the {scenario} scenario. "
            f"{critical_count} actions are CRITICAL priority. "
            f"{approval_needed} actions require human approval before execution. "
            f"Immediate focus: {critical_zones[0]['area'] if critical_zones else 'No critical zones'}."
        )

        self._last_run = datetime.utcnow().isoformat()
        self._status = "COMPLETE"
        self._log(f"Plan complete: {len(actions)} actions, {approval_needed} need approval")

        return {
            "actions": actions,
            "total_actions": len(actions),
            "critical_actions": critical_count,
            "approval_needed": approval_needed,
            "executive_summary": summary,
            "scenario": scenario,
            "generated_at": self._last_run,
            "data_label": "DEMO/SIMULATED",
        }

    def get_resource_recommendations(
        self,
        risk_predictions: list[dict],
        teams: list[dict],
        scenario: str = "NORMAL",
    ) -> list[dict]:
        """
        Recommend specific resources (pumps, teams, ambulances, shelters)
        based on risk level, priority, and team availability.
        SIMULATED optimization — not real operational deployment.
        """
        self._log("Resource optimization started")
        recommendations = []
        available_teams = {t["team_type"]: [] for t in teams}
        for t in teams:
            available_teams.setdefault(t["team_type"], []).append(t)

        for zone in sorted(risk_predictions, key=lambda x: x["risk_score"], reverse=True)[:8]:
            level = zone["risk_level"]
            if level not in ("CRITICAL", "HIGH"):
                continue

            needed = []
            if level == "CRITICAL":
                needed = ["pump_team", "rapid_response", "emergency"]
            elif level == "HIGH":
                needed = ["pump_team", "drainage"]

            assigned = []
            for t_type in needed:
                avail = [t for t in available_teams.get(t_type, []) if t.get("status") == "AVAILABLE"]
                if avail:
                    t = avail[0]
                    assigned.append({
                        "team_id": t["team_id"],
                        "team_name": t.get("name", t["team_id"]),
                        "team_type": t_type,
                        "status": "AVAILABLE",
                        "estimated_travel_min": random.randint(5, 25),
                    })

            # Simulated recommendation even without available team
            if not assigned:
                assigned.append({
                    "team_id": "SIMULATED",
                    "team_name": f"Nearest {needed[0].replace('_',' ').title() if needed else 'Response'} Unit",
                    "team_type": needed[0] if needed else "rapid_response",
                    "status": "STANDBY",
                    "estimated_travel_min": random.randint(15, 40),
                })

            recommendations.append({
                "zone": f"{zone['area']}, {zone['city']}",
                "risk_level": level,
                "risk_score": zone["risk_score"],
                "assigned_resources": assigned,
                "priority_score": zone["risk_score"],
                "rationale": (
                    f"{level} risk zone ({zone['risk_score']:.0f}/100). "
                    f"{len(assigned)} resource(s) recommended for deployment."
                ),
                "data_label": "SIMULATED",
            })

        self._log(f"Resource recommendations: {len(recommendations)} zones")
        return recommendations

    def get_status(self) -> dict:
        return {
            "agent": "Chief Response Agent",
            "status": self._status,
            "last_run": self._last_run,
            "recent_activity": self._activity_log[-6:],
        }


# ──────────────────────────────────────────────
# Singleton
# ──────────────────────────────────────────────
_chief_agent: ChiefResponseAgent | None = None


def get_chief_agent() -> ChiefResponseAgent:
    global _chief_agent
    if _chief_agent is None:
        _chief_agent = ChiefResponseAgent()
    return _chief_agent
