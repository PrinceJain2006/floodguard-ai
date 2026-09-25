"""
FloodGuard AI — Agent 6: Post-Disaster Damage Assessment Agent
Classifies post-flood damage from citizen images and incident reports.
Generates structured damage assessments with human-verification disclaimer.
"""
import uuid
from datetime import datetime, timezone
from typing import Any

try:
    from agents.granite_service import classify_damage
except ImportError:
    from granite_service import classify_damage


DAMAGE_LEVELS = ["LOW", "MEDIUM", "HIGH", "SEVERE"]
INFRA_TYPES = ["road", "drainage", "property", "public_infrastructure", "traffic"]


class DamageAssessmentAgent:
    """
    Agent 6 — Post-Disaster Damage Assessment Agent.
    Analyzes incident reports and optional images to classify
    post-flood damage. All outputs are clearly labeled as
    AI-generated preliminary assessments.
    """

    def __init__(self):
        self.name = "Damage Assessment Agent"
        self.last_run = None
        self.activity_log: list[str] = []

    def _log(self, msg: str):
        ts = datetime.now(timezone.utc).strftime("%H:%M:%S")
        self.activity_log.append(f"[{ts}] {msg}")
        if len(self.activity_log) > 50:
            self.activity_log = self.activity_log[-50:]

    def assess_incident(
        self,
        incident_id: str,
        city: str,
        area: str,
        latitude: float,
        longitude: float,
        description: str,
        flood_duration_hours: float = 0.0,
        severity: str = "MEDIUM",
        image_paths: list[str] | None = None,
    ) -> dict:
        """
        Assess damage for a single incident.
        Returns a structured damage report with AI disclaimer.
        """
        self._log(f"Assessing incident {incident_id} in {area}, {city}")

        # Get AI classification from Granite
        ai_result = classify_damage(description, f"{area}, {city}")

        damage_level = ai_result.get("damage_level", "MEDIUM")
        affected_infra = ai_result.get("affected_infrastructure", ["road"])
        priority = ai_result.get("estimated_priority", "URGENT")
        next_step = ai_result.get("recommended_next_step", "Deploy inspection team")

        # Adjust damage level based on duration and severity
        if flood_duration_hours > 24 or severity == "CRITICAL":
            if damage_level in ("LOW", "MEDIUM"):
                damage_level = "HIGH"
        elif flood_duration_hours > 6 and severity == "HIGH":
            if damage_level == "LOW":
                damage_level = "MEDIUM"

        # Infrastructure scoring
        infra_damage_scores = {}
        for infra in affected_infra:
            if infra == "road":
                infra_damage_scores["road"] = round(
                    min(100, 30 + flood_duration_hours * 2 + (40 if severity == "CRITICAL" else 20)), 1
                )
            elif infra == "drainage":
                infra_damage_scores["drainage"] = round(
                    min(100, 20 + flood_duration_hours * 1.5 + 20), 1
                )
            elif infra == "property":
                infra_damage_scores["property"] = round(
                    min(100, 25 + flood_duration_hours * 3), 1
                )
            elif infra == "public_infrastructure":
                infra_damage_scores["public_infrastructure"] = round(
                    min(100, 15 + flood_duration_hours * 2), 1
                )
            else:
                infra_damage_scores[infra] = 40.0

        # Separate reported (from description/severity) vs potential (model-extrapolated) impact
        _reported_impact = f"Severity reported as {severity}. " + (
            description[:200] if description else "No description provided."
        )
        _potential_impact = (
            f"Potential damage level: {damage_level}. "
            f"Affected infrastructure: {', '.join(affected_infra) if affected_infra else 'Unknown'}. "
            f"If flood duration exceeds {flood_duration_hours:.0f}h, structural damage risk increases."
        )

        report = {
            "assessment_id": f"DMG-{uuid.uuid4().hex[:8].upper()}",
            "incident_id": incident_id,
            "city": city,
            "area": area,
            "latitude": latitude,
            "longitude": longitude,
            "damage_level": damage_level,
            "affected_infrastructure": affected_infra,
            "infrastructure_damage_scores": infra_damage_scores,
            "flood_duration_hours": flood_duration_hours,
            "estimated_priority": priority,
            "recommended_next_step": next_step,
            "ai_assessment": description[:500],
            # Data-transparency impact labels
            "reported_impact": _reported_impact,
            "potential_impact": _potential_impact,
            "reported_impact_label": "USER SUBMITTED — unverified citizen report",
            "potential_impact_label": "ESTIMATED — AI extrapolation from reported severity + duration",
            "image_paths": image_paths or [],
            "is_preliminary": True,
            "disclaimer": (
                "⚠️ AI-GENERATED PRELIMINARY ASSESSMENT — "
                "This is an automated analysis based on reported information. "
                "It requires on-site human verification before being used for "
                "official damage assessment, insurance claims, or emergency allocations."
            ),
            "requires_field_verification": True,
            "created_at": datetime.now(timezone.utc).isoformat(),
        }

        self._log(f"Assessment complete: {incident_id} → {damage_level} damage, {priority} priority")
        self.last_run = datetime.now(timezone.utc).isoformat()
        return report

    def batch_assess(self, incidents: list[dict]) -> dict:
        """Assess multiple incidents and produce a consolidated damage report."""
        self._log(f"Batch assessing {len(incidents)} incidents")
        assessments = []

        for inc in incidents:
            if inc.get("status") in ("ACTIVE", "RESOLVED"):
                assessment = self.assess_incident(
                    incident_id=inc.get("incident_id", ""),
                    city=inc.get("city", ""),
                    area=inc.get("area", ""),
                    latitude=inc.get("latitude", 0),
                    longitude=inc.get("longitude", 0),
                    description=inc.get("description", ""),
                    flood_duration_hours=inc.get("duration_hours", 0),
                    severity=inc.get("severity", "MEDIUM"),
                )
                assessments.append(assessment)

        # Summary
        by_damage = {}
        all_infra = []
        for a in assessments:
            lvl = a["damage_level"]
            by_damage[lvl] = by_damage.get(lvl, 0) + 1
            all_infra.extend(a["affected_infrastructure"])

        from collections import Counter
        top_infra = Counter(all_infra).most_common(3)

        # Sub-Task F: Build plain-English infrastructure_summary
        infra_summary = ""
        if top_infra:
            parts = [f"{item.replace('_', ' ').title()} ({count} incident{'s' if count != 1 else ''})"
                     for item, count in top_infra]
            infra_summary = "Primary impact: " + ", ".join(parts) + "."
            severe = by_damage.get("SEVERE", 0) + by_damage.get("HIGH", 0)
            if severe > 0:
                infra_summary += f" {severe} incident{'s' if severe != 1 else ''} rated HIGH/SEVERE."

        self.last_run = datetime.now(timezone.utc).isoformat()
        return {
            "assessments": assessments,
            "summary": {
                "total_assessed": len(assessments),
                "by_damage_level": by_damage,
                "most_affected_infrastructure": [k for k, _ in top_infra],
                "severe_count": by_damage.get("SEVERE", 0) + by_damage.get("HIGH", 0),
            },
            "infrastructure_summary": infra_summary,
            "is_preliminary": True,
            "disclaimer": "All assessments are AI-generated and require field verification.",
            "assessed_at": datetime.now(timezone.utc).isoformat(),
        }

    def get_status(self) -> dict:
        return {
            "agent": self.name,
            "status": "ACTIVE",
            "last_run": self.last_run,
            "recent_activity": self.activity_log[-5:],
        }


# Singleton
_damage_agent: DamageAssessmentAgent | None = None


def get_damage_agent() -> DamageAssessmentAgent:
    global _damage_agent
    if _damage_agent is None:
        _damage_agent = DamageAssessmentAgent()
    return _damage_agent
