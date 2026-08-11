"""
FloodGuard AI — Agent 2: Drainage Maintenance Prioritization Agent
Analyzes drainage infrastructure to identify high-risk drains
and generate prioritized maintenance schedules.
"""
import uuid
from datetime import datetime, timedelta
from typing import Any


class DrainageAgent:
    """
    Agent 2 — Drainage Maintenance Prioritization Agent.
    Scores each drain based on condition, blockage history, proximity
    to flood zones, and current rainfall conditions.
    """

    def __init__(self):
        self.name = "Drainage Agent"
        self.last_run = None
        self.activity_log: list[str] = []

    def _log(self, msg: str):
        ts = datetime.utcnow().strftime("%H:%M:%S")
        self.activity_log.append(f"[{ts}] {msg}")
        if len(self.activity_log) > 50:
            self.activity_log = self.activity_log[-50:]

    def score_drain(self, drain: dict, rainfall_1h: float = 0.0, area_flood_risk: float = 0.0) -> dict:
        """
        Calculate composite risk score for a single drain.

        Scoring factors:
          - Drainage capacity (inverse)      : 25%
          - Blockage frequency               : 25%
          - Near flood zone flag             : 15%
          - Condition rating                 : 20%
          - Days since last cleaned          : 10%
          - Current rainfall / flood risk    :  5%
        """
        capacity = drain.get("capacity_rating", 50)
        blockage_freq = drain.get("blockage_frequency", 0)
        near_flood = drain.get("near_flood_zone", False)
        condition = drain.get("condition", "FAIR")
        last_cleaned_str = drain.get("last_cleaned")
        status = drain.get("status", "OPERATIONAL")

        # Days since cleaned
        days_dirty = 180
        if last_cleaned_str:
            try:
                last_cleaned = datetime.fromisoformat(last_cleaned_str)
                days_dirty = (datetime.utcnow() - last_cleaned).days
            except Exception:
                pass

        # Condition score (0-100, lower is worse)
        cond_score = {"GOOD": 90, "FAIR": 60, "POOR": 30, "CRITICAL": 5}.get(condition, 50)

        # Component scores (each 0-100)
        capacity_component  = (100 - capacity) * 0.25
        blockage_component  = min(blockage_freq * 8, 100) * 0.25
        flood_zone_component = 80 * 0.15 if near_flood else 0
        condition_component = (100 - cond_score) * 0.20
        cleaning_component  = min(days_dirty / 3, 100) * 0.10
        rainfall_component  = (rainfall_1h / 120 * 100) * 0.03 + (area_flood_risk / 100 * 100) * 0.02

        # Bonus if currently blocked
        blocked_bonus = 20 if status == "BLOCKED" else 0

        total_score = (
            capacity_component + blockage_component + flood_zone_component +
            condition_component + cleaning_component + rainfall_component + blocked_bonus
        )
        total_score = max(0, min(100, total_score))

        # Priority classification
        if total_score >= 75 or status == "BLOCKED":
            priority = "CRITICAL"
        elif total_score >= 50:
            priority = "HIGH"
        elif total_score >= 25:
            priority = "MEDIUM"
        else:
            priority = "LOW"

        # Reasons
        reasons = []
        if status == "BLOCKED":
            reasons.append("Currently BLOCKED — immediate intervention required")
        if blockage_freq >= 6:
            reasons.append(f"High blockage frequency: {blockage_freq} times/year")
        elif blockage_freq >= 3:
            reasons.append(f"Moderate blockage frequency: {blockage_freq} times/year")
        if near_flood:
            reasons.append("Located in or near flood-prone zone")
        if capacity < 30:
            reasons.append(f"Critically low capacity: {capacity:.0f}%")
        elif capacity < 60:
            reasons.append(f"Reduced capacity: {capacity:.0f}%")
        if condition in ("POOR", "CRITICAL"):
            reasons.append(f"Physical condition: {condition}")
        if days_dirty > 90:
            reasons.append(f"Not cleaned in {days_dirty} days")
        if rainfall_1h > 50:
            reasons.append(f"Active heavy rainfall: {rainfall_1h:.0f} mm/hr")

        # Recommended action
        action_map = {
            "CRITICAL": "Inspect and clean IMMEDIATELY. Deploy maintenance team now.",
            "HIGH": "Schedule inspection within 24 hours. Check for blockages.",
            "MEDIUM": "Schedule routine maintenance within 1 week.",
            "LOW": "Monitor. Include in next scheduled maintenance cycle.",
        }

        scored = dict(drain)
        scored.update({
            "computed_risk_score": round(total_score, 1),
            "maintenance_priority": priority,
            "priority_reasons": reasons[:4],
            "recommended_action": action_map[priority],
            "days_since_cleaned": days_dirty,
            "assessed_at": datetime.utcnow().isoformat(),
        })
        return scored

    def prioritize_drains(
        self,
        drains: list[dict],
        rainfall_records: list[dict],
        risk_predictions: list[dict],
    ) -> dict:
        """
        Score and rank all drains. Returns prioritized list + summary.
        """
        self._log(f"Starting drain prioritization — {len(drains)} drains")

        # Build lookup maps
        area_rainfall = {f"{r['area']}_{r['city']}": r.get("rainfall_1h", 0) for r in rainfall_records}
        area_risk = {f"{p['area']}_{p['city']}": p.get("risk_score", 0) for p in risk_predictions}

        scored_drains = []
        for drain in drains:
            key = f"{drain.get('area', '')}_{drain.get('city', '')}"
            rain = area_rainfall.get(key, 0)
            risk = area_risk.get(key, 0)
            scored = self.score_drain(drain, rainfall_1h=rain, area_flood_risk=risk)
            scored_drains.append(scored)

        # Sort by risk score
        scored_drains.sort(key=lambda x: x["computed_risk_score"], reverse=True)

        # Summary stats
        by_priority = {"CRITICAL": 0, "HIGH": 0, "MEDIUM": 0, "LOW": 0}
        for d in scored_drains:
            by_priority[d["maintenance_priority"]] = by_priority.get(d["maintenance_priority"], 0) + 1

        top5 = scored_drains[:5]
        self._log(f"Prioritization complete: {by_priority['CRITICAL']} CRITICAL, {by_priority['HIGH']} HIGH drains")
        self._log(f"Top priority drain: {top5[0]['drain_id']} in {top5[0]['area']} (score: {top5[0]['computed_risk_score']:.0f})")
        self.last_run = datetime.utcnow().isoformat()

        return {
            "scored_drains": scored_drains,
            "priority_summary": by_priority,
            "top_5_critical": top5,
            "total_drains": len(scored_drains),
            "requires_immediate_action": [
                d["drain_id"] for d in scored_drains if d["maintenance_priority"] == "CRITICAL"
            ],
            "maintenance_schedule": _generate_schedule(scored_drains),
            "assessed_at": datetime.utcnow().isoformat(),
        }

    def get_status(self) -> dict:
        return {
            "agent": self.name,
            "status": "ACTIVE",
            "last_run": self.last_run,
            "recent_activity": self.activity_log[-5:],
        }


def _generate_schedule(drains: list[dict]) -> list[dict]:
    """Generate a simple maintenance schedule from scored drains."""
    schedule = []
    today = datetime.utcnow()
    for drain in drains:
        priority = drain["maintenance_priority"]
        if priority == "CRITICAL":
            due = today.strftime("%Y-%m-%d") + " (TODAY — IMMEDIATE)"
        elif priority == "HIGH":
            due = (today + timedelta(days=1)).strftime("%Y-%m-%d") + " (Within 24h)"
        elif priority == "MEDIUM":
            due = (today + timedelta(days=7)).strftime("%Y-%m-%d") + " (This week)"
        else:
            due = (today + timedelta(days=30)).strftime("%Y-%m-%d") + " (Routine)"

        schedule.append({
            "drain_id": drain["drain_id"],
            "area": drain.get("area", ""),
            "city": drain.get("city", ""),
            "priority": priority,
            "action": drain.get("recommended_action", ""),
            "due_by": due,
        })
        if len(schedule) >= 20:
            break
    return schedule


# Singleton
_drainage_agent: DrainageAgent | None = None


def get_drainage_agent() -> DrainageAgent:
    global _drainage_agent
    if _drainage_agent is None:
        _drainage_agent = DrainageAgent()
    return _drainage_agent
