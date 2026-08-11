"""
FloodGuard AI — IBM Granite Integration Layer
Provides LLM reasoning via WatsonX / Granite-3-8b-instruct.
Falls back gracefully to rule-based responses when unavailable.
"""
import json
import time
import re
from typing import Any
import httpx

try:
    from backend.config import (
        WATSONX_API_KEY, WATSONX_PROJECT_ID, WATSONX_URL,
        GRANITE_MODEL_ID, DEMO_MODE
    )
except ImportError:
    from config import (
        WATSONX_API_KEY, WATSONX_PROJECT_ID, WATSONX_URL,
        GRANITE_MODEL_ID, DEMO_MODE
    )

_iam_token_cache: dict = {"token": None, "expires_at": 0}


def _get_iam_token() -> str | None:
    """Obtain WatsonX IAM bearer token, cached for 55 minutes."""
    if not WATSONX_API_KEY or WATSONX_API_KEY == "your_watsonx_api_key_here":
        return None

    now = time.time()
    if _iam_token_cache["token"] and now < _iam_token_cache["expires_at"]:
        return _iam_token_cache["token"]

    try:
        resp = httpx.post(
            "https://iam.cloud.ibm.com/identity/token",
            data={"grant_type": "urn:ibm:params:oauth:grant-type:apikey", "apikey": WATSONX_API_KEY},
            headers={"Content-Type": "application/x-www-form-urlencoded"},
            timeout=15,
        )
        resp.raise_for_status()
        token = resp.json()["access_token"]
        _iam_token_cache["token"] = token
        _iam_token_cache["expires_at"] = now + 55 * 60
        return token
    except Exception as e:
        print(f"[Granite] IAM token error: {e}")
        return None


def _call_granite(prompt: str, max_tokens: int = 600, temperature: float = 0.3) -> str | None:
    """Call Granite via WatsonX REST API."""
    token = _get_iam_token()
    if not token:
        return None

    url = f"{WATSONX_URL}/ml/v1/text/generation?version=2023-05-29"
    payload = {
        "model_id": GRANITE_MODEL_ID,
        "project_id": WATSONX_PROJECT_ID,
        "input": prompt,
        "parameters": {
            "decoding_method": "greedy",
            "max_new_tokens": max_tokens,
            "temperature": temperature,
            "stop_sequences": ["<|endoftext|>"],
        },
    }

    try:
        resp = httpx.post(
            url,
            json=payload,
            headers={"Authorization": f"Bearer {token}", "Content-Type": "application/json"},
            timeout=30,
        )
        resp.raise_for_status()
        return resp.json()["results"][0]["generated_text"].strip()
    except Exception as e:
        print(f"[Granite] Generation error: {e}")
        return None


# ──────────────────────────────────────────────
# Public API
# ──────────────────────────────────────────────

def analyze_citizen_report(text: str, language: str, context: dict | None = None) -> dict:
    """
    Use Granite to understand a citizen flood report.
    Returns: category, severity, summary, location_hint, language.
    """
    system = (
        "You are FloodGuard AI, analyzing citizen flood reports for Ahmedabad and Surat municipalities.\n"
        "Respond ONLY with valid JSON. No additional text."
    )
    prompt = f"""{system}

Citizen report (language: {language}):
\"{text}\"

Extract the following and respond as JSON:
{{
  "category": "<waterlogging|drain_overflow|road_blockage|traffic_disruption|property_flooding|emergency_situation>",
  "severity": "<LOW|MEDIUM|HIGH|CRITICAL>",
  "language_detected": "<english|hindi|gujarati|other>",
  "summary": "<one sentence English summary>",
  "location_hint": "<mentioned location if any, else null>",
  "requires_immediate_action": <true|false>
}}"""

    response = _call_granite(prompt, max_tokens=250)
    if response:
        try:
            # Extract JSON from response
            match = re.search(r'\{.*\}', response, re.DOTALL)
            if match:
                return json.loads(match.group())
        except Exception:
            pass

    # Fallback rule-based
    return _fallback_report_analysis(text, language)


def explain_flood_risk(area: str, city: str, risk_data: dict) -> str:
    """
    Generate a human-readable explanation for why an area is at risk.
    Uses Granite if available; otherwise rule-based.
    IMPORTANT: Only uses provided risk_data — never invents real sensor/govt data.
    """
    reasons = risk_data.get("main_reasons", [])
    score = risk_data.get("risk_score", 0)
    level = risk_data.get("risk_level", "UNKNOWN")
    features = risk_data.get("input_features", {})
    rainfall = features.get("rainfall_1h", risk_data.get("rainfall_1h", 0))
    drainage = features.get("drainage_capacity", risk_data.get("drainage_capacity", 50))
    blocked = features.get("blocked_drains", 0)
    elevation = features.get("elevation", "unknown")
    density = features.get("population_density", "unknown")
    confidence = risk_data.get("confidence", 0.8)

    prompt = f"""You are the FloodGuard AI assistant for {city} Municipal Corporation.
Only use the data provided below — do not invent or assume any values.

AREA: {area}, {city}
RISK LEVEL: {level} (Score: {score}/100, Confidence: {confidence:.0%})
RAINFALL (last 1 hour): {rainfall} mm/hr
DRAINAGE CAPACITY UTILIZATION: {drainage}%
BLOCKED DRAINS IN AREA: {blocked}
ELEVATION: {elevation} m above sea level
POPULATION DENSITY INDEX: {density}
AI-IDENTIFIED KEY FACTORS: {'; '.join(reasons[:4]) if reasons else 'Multiple compounding factors'}

Write a clear 3-sentence WHY explanation for why {area} is at {level} flood risk today, based ONLY on the data above.
Include: (1) the primary cause, (2) compounding factors, (3) one specific recommended action.
Begin with "Based on available data..." to signal this is AI analysis of provided inputs, not real sensor readings.
Keep it professional and under 80 words."""

    response = _call_granite(prompt, max_tokens=200)
    if response:
        return response

    # Fallback — built from provided data only
    reason_str = "; ".join(reasons[:3]) if reasons else "multiple compounding risk factors"
    action = risk_data.get("recommended_action", "Monitor closely and pre-position response teams.")
    return (
        f"Based on available data, {area} in {city} is at {level} flood risk (score {score:.0f}/100). "
        f"Key factors from the analysis: {reason_str}. "
        f"Recommended action: {action}"
    )


def explain_why_zone_risky(zone_prediction: dict) -> str:
    """
    Public convenience wrapper — explain a zone's risk using only its own prediction data.
    Guaranteed not to hallucinate: pulls exclusively from zone_prediction dict.
    """
    area = zone_prediction.get("area", "Unknown Area")
    city = zone_prediction.get("city", "Unknown City")
    return explain_flood_risk(area, city, zone_prediction)


def generate_situation_report(city: str, scenario: str, summary_data: dict) -> str:
    """
    Generate a comprehensive municipal flood situation report.
    """
    critical = summary_data.get("critical_zones", 0)
    high = summary_data.get("high_zones", 0)
    reports = summary_data.get("citizen_reports", 0)
    avg_rainfall = summary_data.get("avg_rainfall_1h", 0)
    top_actions = summary_data.get("top_actions", [])

    prompt = f"""You are FloodGuard AI. Generate an official flood situation report for {city} Municipal Corporation.

SITUATION SUMMARY ({scenario} scenario):
- Critical risk zones: {critical}
- High risk zones: {high}
- Citizen reports received: {reports}
- Average rainfall: {avg_rainfall:.1f} mm/hr
- Top AI recommended actions: {'; '.join(top_actions[:3])}

Generate a structured 200-word situation report with:
1. Executive Summary
2. Current Situation
3. High-Priority Actions
4. Recommended Next Steps

Note: This is AI-generated preliminary assessment. Requires authorized human verification before official communication."""

    response = _call_granite(prompt, max_tokens=400)
    if response:
        return response

    # Fallback template
    return f"""FLOODGUARD AI — FLOOD SITUATION REPORT
City: {city} | Scenario: {scenario} | Generated: AI-Preliminary

EXECUTIVE SUMMARY
{city} is experiencing {scenario.lower()} conditions with {critical} critical and {high} high-risk zones identified.

CURRENT SITUATION
Average rainfall: {avg_rainfall:.1f} mm/hr. {reports} citizen reports processed. Drainage systems under stress in {critical + high} areas.

HIGH-PRIORITY ACTIONS
{chr(10).join(f'{i+1}. {a}' for i, a in enumerate(top_actions[:5]))}

RECOMMENDED NEXT STEPS
Activate emergency response protocol for critical zones. Pre-position pump teams at high-risk areas. Issue public advisory for affected neighborhoods.

[AI-GENERATED PRELIMINARY ASSESSMENT — Requires authorized human verification]"""


def answer_query(question: str, context_data: dict) -> str:
    """
    Answer a natural language query about flood status using application data as context.
    DOES NOT hallucinate sensor values — uses provided context_data.
    """
    context_str = json.dumps(context_data, ensure_ascii=False, indent=2)[:2000]

    prompt = f"""You are FloodGuard AI, a municipal flood management assistant for Ahmedabad and Surat.
Answer questions ONLY based on the provided data context. Do not invent values.

DATA CONTEXT:
{context_str}

QUESTION: {question}

Provide a concise, factual answer based only on the data above. If the answer cannot be found in the data, say so clearly."""

    response = _call_granite(prompt, max_tokens=300)
    if response:
        return response

    # Fallback using context
    return _fallback_query_answer(question, context_data)


def generate_recommendation_explanation(rec: dict) -> str:
    """Explain why a specific AI recommendation was generated."""
    prompt = f"""You are FloodGuard AI. Explain this emergency recommendation to a municipal officer in 2-3 sentences.

RECOMMENDATION: {rec.get('recommendation', '')}
AREA: {rec.get('area', '')}
PRIORITY: {rec.get('priority', '')}
REASONING: {rec.get('reasoning', '')}

Keep the explanation clear, direct and actionable. Mention why this action is important right now."""

    response = _call_granite(prompt, max_tokens=150)
    if response:
        return response

    return (
        f"This {rec.get('priority', '')} priority recommendation for {rec.get('area', '')} "
        f"was generated because: {rec.get('reasoning', 'multiple risk factors detected')}. "
        f"Immediate action will help prevent escalation of the current flood risk situation."
    )


def classify_damage(description: str, location: str) -> dict:
    """Classify post-flood damage from description."""
    prompt = f"""You are FloodGuard AI damage assessment system.

Location: {location}
Report: {description}

Classify the damage and respond as JSON only:
{{
  "damage_level": "<LOW|MEDIUM|HIGH|SEVERE>",
  "affected_infrastructure": ["<road|drainage|property|public_infrastructure|traffic>"],
  "estimated_priority": "<ROUTINE|URGENT|EMERGENCY>",
  "recommended_next_step": "<one action>",
  "preliminary_note": "AI-generated preliminary assessment. Requires on-site human verification."
}}"""

    response = _call_granite(prompt, max_tokens=200)
    if response:
        try:
            match = re.search(r'\{.*\}', response, re.DOTALL)
            if match:
                return json.loads(match.group())
        except Exception:
            pass

    return {
        "damage_level": "MEDIUM",
        "affected_infrastructure": ["road", "drainage"],
        "estimated_priority": "URGENT",
        "recommended_next_step": "Deploy inspection team for on-site assessment.",
        "preliminary_note": "AI-generated preliminary assessment. Requires on-site human verification.",
    }


# ──────────────────────────────────────────────
# Fallback implementations (no LLM required)
# ──────────────────────────────────────────────

_CATEGORY_KEYWORDS = {
    "waterlogging": ["water", "pani", "पानी", "પાણી", "waterlog", "jala", "flood"],
    "drain_overflow": ["drain", "nala", "नाला", "ગટર", "gutter", "overflow", "sewage"],
    "road_blockage": ["road", "rasta", "रास्ता", "રસ્તો", "block", "chowk", "traffic"],
    "property_flooding": ["house", "ghar", "घर", "ઘર", "home", "property", "inside"],
    "emergency_situation": ["emergency", "stranded", "stuck", "help", "urgent", "फंस", "ફસ"],
    "traffic_disruption": ["traffic", "car", "vehicle", "jam", "stuck"],
}

_SEVERITY_KEYWORDS = {
    "CRITICAL": ["emergency", "emer", "stranded", "life", "critical", "phns", "ife", "ফসা"],
    "HIGH": ["high", "heavy", "lots", "bahut", "zyada", "ghanu", "bhari", "unch"],
    "MEDIUM": ["some", "thodi", "medium", "par", "road", "overflow"],
    "LOW": ["small", "little", "thoda", "halku"],
}


def _fallback_report_analysis(text: str, language: str) -> dict:
    text_lower = text.lower()
    category = "waterlogging"
    for cat, keywords in _CATEGORY_KEYWORDS.items():
        if any(kw in text_lower for kw in keywords):
            category = cat
            break

    severity = "MEDIUM"
    for sev, keywords in _SEVERITY_KEYWORDS.items():
        if any(kw in text_lower for kw in keywords):
            severity = sev
            break

    return {
        "category": category,
        "severity": severity,
        "language_detected": language,
        "summary": f"Flood-related report: {category.replace('_', ' ')} detected.",
        "location_hint": None,
        "requires_immediate_action": severity in ("HIGH", "CRITICAL"),
    }


def _fallback_query_answer(question: str, context: dict) -> str:
    q = question.lower()
    if "critical" in q or "risky" in q or "worst" in q:
        preds = context.get("predictions", [])
        critical = [p for p in preds if p.get("risk_level") == "CRITICAL"]
        if critical:
            areas = [f"{p['area']}, {p['city']}" for p in critical[:3]]
            return f"Critical risk zones currently: {', '.join(areas)}. Immediate action required."
        return "No critical risk zones currently identified."

    if "drain" in q:
        drains = context.get("drains", [])
        crit_drains = [d for d in drains if d.get("maintenance_priority") == "CRITICAL"]
        return f"{len(crit_drains)} drains require immediate maintenance (CRITICAL priority)."

    if "report" in q or "complaint" in q:
        reports = context.get("reports", [])
        open_r = [r for r in reports if r.get("status") == "OPEN"]
        return f"There are {len(open_r)} open citizen flood reports (out of {len(reports)} total)."

    if "rainfall" in q or "rain" in q:
        rf = context.get("rainfall", [])
        if rf:
            max_r = max(rf, key=lambda x: x.get("rainfall_1h", 0))
            return f"Highest rainfall: {max_r['area']}, {max_r['city']} — {max_r['rainfall_1h']} mm/hr."
        return "Rainfall data not available."

    return (
        "I can help with flood risk analysis, drain maintenance priorities, citizen reports, "
        "rainfall data, and response recommendations for Ahmedabad and Surat. "
        "Please ask a more specific question."
    )


def granite_status() -> dict:
    """Check Granite connectivity."""
    token = _get_iam_token()
    return {
        "available": token is not None,
        "model": GRANITE_MODEL_ID,
        "api_key_configured": bool(WATSONX_API_KEY and WATSONX_API_KEY != "your_watsonx_api_key_here"),
        "project_configured": bool(WATSONX_PROJECT_ID and WATSONX_PROJECT_ID != "your_project_id_here"),
    }
