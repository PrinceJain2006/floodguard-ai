"""
FloodGuard AI — Agent 3: Citizen Flood Reporting Agent
Processes multilingual citizen flood reports (English, Hindi, Gujarati).
Handles classification, severity detection, deduplication, and routing.
"""
import uuid
import hashlib
from datetime import datetime
from difflib import SequenceMatcher
from typing import Any

try:
    from agents.granite_service import analyze_citizen_report
except ImportError:
    from granite_service import analyze_citizen_report


CATEGORIES = [
    "waterlogging", "drain_overflow", "road_blockage",
    "traffic_disruption", "property_flooding", "emergency_situation",
]

SEVERITY_PRIORITY_MAP = {
    "CRITICAL": 9,
    "HIGH": 7,
    "MEDIUM": 5,
    "LOW": 3,
}

ROUTING_MAP = {
    "waterlogging":        "Pump Team",
    "drain_overflow":      "Drainage Maintenance Team",
    "road_blockage":       "Traffic Control + Emergency Team",
    "traffic_disruption":  "Traffic Control",
    "property_flooding":   "Emergency Response Team",
    "emergency_situation": "Emergency Response Team + Senior Officer",
}

# Simple keyword patterns for language detection
_GUJARATI_CHARS = set("અઆઇઈઉઊઋઌઍ઎એએઐઑ઒ઓઔકખગઘઙચછજઝઞટઠડઢણતથદધનપફબભમયયરલળવશષસહ")
_DEVANAGARI_CHARS = set("अआइईउऊएऐओऔकखगघचछजझटठडढतथदधनपफबभमयरलवशषसह")


def detect_language(text: str) -> str:
    if any(c in _GUJARATI_CHARS for c in text):
        return "gujarati"
    if any(c in _DEVANAGARI_CHARS for c in text):
        return "hindi"
    return "english"


def _text_fingerprint(text: str) -> str:
    """Generate a normalized fingerprint for duplicate detection."""
    normalized = "".join(c.lower() for c in text if c.isalnum() or c.isspace())
    return hashlib.md5(normalized.encode()).hexdigest()


class CitizenReportAgent:
    """
    Agent 3 — Citizen Flood Reporting Agent.
    Processes, classifies, deduplicates, and routes citizen flood reports.
    """

    def __init__(self):
        self.name = "Citizen Report Agent"
        self.last_run = None
        self.activity_log: list[str] = []
        self._seen_fingerprints: dict[str, str] = {}   # fingerprint → report_id

    def _log(self, msg: str):
        ts = datetime.utcnow().strftime("%H:%M:%S")
        self.activity_log.append(f"[{ts}] {msg}")
        if len(self.activity_log) > 50:
            self.activity_log = self.activity_log[-50:]

    def process_report(
        self,
        text: str,
        area: str,
        city: str,
        latitude: float | None = None,
        longitude: float | None = None,
        user_id: int | None = None,
        image_path: str | None = None,
        existing_reports: list[dict] | None = None,
    ) -> dict:
        """
        Full pipeline for a single incoming citizen report.
        Returns enriched report dict ready for DB storage.
        """
        report_id = f"RPT-{uuid.uuid4().hex[:8].upper()}"

        # 1. Language detection
        language = detect_language(text)
        self._log(f"Report {report_id}: language={language}, area={area}")

        # 2. AI classification via Granite
        ai_result = analyze_citizen_report(text, language)

        category = ai_result.get("category", "waterlogging")
        severity = ai_result.get("severity", "MEDIUM")
        summary = ai_result.get("summary", text[:100])
        location_hint = ai_result.get("location_hint", area)
        requires_immediate = ai_result.get("requires_immediate_action", False)

        # 3. Priority score
        priority = SEVERITY_PRIORITY_MAP.get(severity, 5)
        if requires_immediate:
            priority = min(10, priority + 1)

        # 4. Duplicate detection
        fingerprint = _text_fingerprint(text)
        is_duplicate = False
        duplicate_of = None

        if fingerprint in self._seen_fingerprints:
            is_duplicate = True
            duplicate_of = self._seen_fingerprints[fingerprint]
            self._log(f"Report {report_id} detected as duplicate of {duplicate_of}")
        else:
            # Fuzzy duplicate check against existing reports
            if existing_reports:
                for existing in existing_reports:
                    if (
                        existing.get("area") == area
                        and existing.get("category") == category
                        and _text_similarity(text, existing.get("original_text", "")) > 0.80
                    ):
                        is_duplicate = True
                        duplicate_of = existing.get("report_id")
                        self._log(f"Report {report_id} fuzzy-matched duplicate of {duplicate_of}")
                        break

            if not is_duplicate:
                self._seen_fingerprints[fingerprint] = report_id

        # 5. Routing
        assigned_team = ROUTING_MAP.get(category, "Municipal Response Team")

        # 6. Build report
        report = {
            "report_id": report_id,
            "user_id": user_id,
            "city": city,
            "area": area,
            "latitude": latitude,
            "longitude": longitude,
            "category": category,
            "severity": severity,
            "language": language,
            "original_text": text,
            "translated_text": text if language == "english" else f"[Auto-translated] {summary}",
            "ai_summary": summary,
            "status": "OPEN",
            "priority": priority,
            "is_duplicate": is_duplicate,
            "duplicate_of": duplicate_of,
            "image_path": image_path,
            "assigned_team": assigned_team,
            "requires_immediate_action": requires_immediate,
            "routing_reason": f"Category '{category}' → {assigned_team}",
            "created_at": datetime.utcnow().isoformat(),
        }

        self.last_run = datetime.utcnow().isoformat()
        if not is_duplicate:
            self._log(f"Report {report_id}: {category}/{severity} in {area}, {city} → {assigned_team}")
        return report

    def batch_analyze(self, reports: list[dict]) -> dict:
        """Analyze a batch of existing reports to extract trends."""
        self._log(f"Batch analyzing {len(reports)} reports")

        by_category = {}
        by_severity = {}
        by_area = {}
        by_city = {}
        open_count = 0
        duplicate_count = 0

        for r in reports:
            cat = r.get("category", "unknown")
            sev = r.get("severity", "MEDIUM")
            area = r.get("area", "unknown")
            city = r.get("city", "unknown")

            by_category[cat] = by_category.get(cat, 0) + 1
            by_severity[sev] = by_severity.get(sev, 0) + 1
            by_area[area] = by_area.get(area, 0) + 1
            by_city[city] = by_city.get(city, 0) + 1
            if r.get("status") == "OPEN":
                open_count += 1
            if r.get("is_duplicate"):
                duplicate_count += 1

        top_areas = sorted(by_area.items(), key=lambda x: -x[1])[:5]
        hotspots = [
            {
                "area": area,
                "report_count": count,
                "city": next(
                    (r["city"] for r in reports if r.get("area") == area), "Unknown"
                ),
            }
            for area, count in top_areas
        ]

        self._log(f"Batch complete: {open_count} open, {duplicate_count} duplicates, {len(hotspots)} hotspots")
        self.last_run = datetime.utcnow().isoformat()

        return {
            "total_reports": len(reports),
            "open_reports": open_count,
            "duplicate_count": duplicate_count,
            "by_category": by_category,
            "by_severity": by_severity,
            "by_city": by_city,
            "hotspot_areas": hotspots,
            "critical_count": by_severity.get("CRITICAL", 0),
            "high_count": by_severity.get("HIGH", 0),
            "analyzed_at": datetime.utcnow().isoformat(),
        }

    def get_status(self) -> dict:
        return {
            "agent": self.name,
            "status": "ACTIVE",
            "last_run": self.last_run,
            "recent_activity": self.activity_log[-5:],
            "fingerprints_tracked": len(self._seen_fingerprints),
        }


def _text_similarity(a: str, b: str) -> float:
    return SequenceMatcher(None, a.lower(), b.lower()).ratio()


# Singleton
_citizen_agent: CitizenReportAgent | None = None


def get_citizen_agent() -> CitizenReportAgent:
    global _citizen_agent
    if _citizen_agent is None:
        _citizen_agent = CitizenReportAgent()
    return _citizen_agent
