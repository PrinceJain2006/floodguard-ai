"""
FloodGuard AI — Page 3: AI Agent Monitor
Shows real-time agent activity, pipeline execution, and Granite status.
Feature 8: Enhanced Agent Activity Panel with live processing/status indicators.
"""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import streamlit as st
import time
from datetime import datetime
from frontend.ui_utils import (
    apply_global_css, header, metric_card, demo_badge,
    simulated_badge, section_header, COLORS,
    render_agent_trace, render_granite_panel, risk_level_indicator, _utc_to_ist,
)
from agents.orchestrator import get_orchestrator, SCENARIOS
from agents.granite_service import granite_status, explain_why_zone_risky

st.set_page_config(
    page_title="Agent Monitor — FloodGuard AI",
    page_icon="🤖",
    layout="wide",
)
apply_global_css()

@st.cache_resource
def get_orch():
    orch = get_orchestrator()
    if not orch.current_state:
        orch.run_pipeline("NORMAL")
    return orch

orch = get_orch()

# ──────────────────────────────────────────────
# Sidebar
# ──────────────────────────────────────────────
with st.sidebar:
    st.markdown("## 🤖 Agent Monitor")
    st.markdown("---")
    st.markdown("### 🎬 Run Scenarios")
    for sc_id, sc_info in SCENARIOS.items():
        if st.button(
            f"{sc_info['emoji']} {sc_info['label']}",
            key=f"sc_{sc_id}",
            use_container_width=True,
            type="primary" if orch.current_scenario == sc_id else "secondary",
        ):
            with st.spinner(f"Running {sc_info['label']}..."):
                orch.run_pipeline(scenario=sc_id, city="All")
            st.rerun()

    st.markdown("---")
    st.markdown(f"""
<div style="font-size:0.75rem;color:#94a3b8">
    Current: {SCENARIOS[orch.current_scenario]['emoji']} {SCENARIOS[orch.current_scenario]['label']}<br>
    Pipeline runs: {len(orch.pipeline_log)} log entries
</div>
    """, unsafe_allow_html=True)

# ──────────────────────────────────────────────
# Header
# ──────────────────────────────────────────────
header("AI Agent Monitor", "Real-time view of multi-agent pipeline execution", "🤖")

# Prototype note — honest disclosure at top of page
st.markdown("""
<div style="background:rgba(124,92,216,0.08);border:1px solid #7c3aed;border-radius:6px;
            padding:0.5rem 0.9rem;margin-bottom:0.75rem;font-size:0.75rem;color:#c4b5fd;
            display:flex;align-items:center;gap:0.6rem">
    <span style="font-size:1rem">🔬</span>
    <span><strong>Prototype Note:</strong> Some datasets are synthetic/demo data for hackathon demonstration.
    Live layers are labelled LIVE; model-generated predictions are labelled MODEL;
    infrastructure and team data are DEMO/SYNTHETIC.</span>
</div>
""", unsafe_allow_html=True)

# ──────────────────────────────────────────────
# Granite status — uses module-level cache in granite_service.py
# The session-state cache here avoids even the cheap cache lookup on every
# Streamlit rerun; it refreshes after _AGENT_STATUS_TTL seconds or when
# the user explicitly runs a scenario.
# ──────────────────────────────────────────────
_AGENT_STATUS_TTL = 120   # seconds between status re-checks in this page

if (
    "granite_status_cache" not in st.session_state
    or "granite_status_ts" not in st.session_state
    or (time.time() - st.session_state.get("granite_status_ts", 0)) > _AGENT_STATUS_TTL
):
    st.session_state.granite_status_cache = granite_status()
    st.session_state.granite_status_ts    = time.time()

g_status        = st.session_state.granite_status_cache
g_available     = g_status.get("available", False)        # True = real generation confirmed
g_iam_ok        = g_status.get("iam_ok", False)           # True = IAM token obtained
g_key_ok        = g_status.get("api_key_configured", False)
g_pid_ok        = g_status.get("project_configured", False)
g_rate_limited  = g_status.get("rate_limited", False)     # True = 429 backoff active
g_config_error  = g_status.get("config_error", False)     # True = bad credentials
g_error         = g_status.get("error") or ""

# ── Granite status label / colour ─────────────────────────────────────────────
# States:
#   GRANITE CONNECTED    — actual generation succeeded (HTTP 200)
#   GRANITE RATE LIMITED — HTTP 429 (credentials fine, just throttled)
#   GRANITE FALLBACK     — IAM OK but generation failed for other reason
#   GRANITE CONFIG ERROR — credentials / project misconfigured
if g_available:
    granite_color = "#22c55e"
    granite_label = "🟢 GRANITE CONNECTED"
elif g_rate_limited:
    # HTTP 429 — integration is reachable, just temporarily exhausted
    granite_color = "#eab308"
    granite_label = "🟠 GRANITE RATE LIMITED"
elif g_config_error or (not g_key_ok) or (not g_pid_ok):
    # Missing or invalid credentials
    granite_color = "#ef4444"
    granite_label = "🔴 GRANITE CONFIGURATION ERROR"
elif g_iam_ok:
    # IAM worked but generation failed (5xx, 403, etc.)
    granite_color = "#f97316"
    granite_label = "🟠 GRANITE FALLBACK MODE"
else:
    granite_color = "#94a3b8"
    granite_label = "⚙ GRANITE FALLBACK MODE"

# Credential display: show CONFIGURED only for keys, never imply CONNECTED
_key_badge = "✅ Configured" if g_key_ok else "❌ Not set"
_pid_badge = "✅ Configured" if g_pid_ok else "❌ Not set"

st.markdown(f"""
<div style="background:rgba(59,130,246,0.1);border:1px solid #3b82f6;border-radius:8px;
            padding:0.8rem 1.2rem;margin-bottom:1rem;display:flex;align-items:center;gap:1.5rem;flex-wrap:wrap">
    <div style="font-size:1.5rem">🧠</div>
    <div style="flex:1">
        <div style="font-weight:700;color:#e2e8f0">IBM Granite — {g_status.get('model','')}</div>
        <div style="font-size:0.8rem;color:#94a3b8">
            API Key: {_key_badge} &nbsp;|&nbsp;
            Project ID: {_pid_badge} &nbsp;|&nbsp;
            IAM: {'✅ OK' if g_iam_ok else '❌ Failed'}
        </div>
    </div>
    <div>
        <span style="background:{granite_color};color:white;padding:4px 12px;border-radius:8px;
                     font-weight:700;font-size:0.8rem">{granite_label}</span>
    </div>
</div>
""", unsafe_allow_html=True)

if g_available:
    # ✅ Granite CONNECTED — actual generation succeeded
    st.markdown("""
<div style="background:rgba(34,197,94,0.08);border:1px solid #22c55e;border-radius:6px;
            padding:0.5rem 0.9rem;font-size:0.8rem;color:#86efac;margin-bottom:1rem">
    🟢 <strong>IBM Granite — Live Generation</strong>
    WatsonX text-generation request succeeded.
    All AI explanations and summaries are generated by IBM Granite.
</div>
    """, unsafe_allow_html=True)
elif g_rate_limited:
    # 🟠 429 — credentials and IAM are fine; just temporarily throttled
    # Do NOT call this "disconnected" or "auth error"
    _imsg  = g_status.get("ibm_error_msg") or ""
    _endpt = g_status.get("endpoint", "/ml/v1/text/generation")
    st.markdown(f"""
<div style="background:rgba(234,179,8,0.08);border:1px solid #ca8a04;border-radius:6px;
            padding:0.6rem 0.9rem;font-size:0.8rem;color:#fef08a;margin-bottom:1rem">
    🟠 <strong>IBM Granite — Rate Limited (HTTP 429)</strong><br>
    <code>consumption_limit_reached</code> — WatsonX authentication and
    integration are reachable. The free-tier concurrent request limit for
    <code>{g_status.get('model','')}</code> is temporarily exhausted.<br>
    <div style="margin:0.3rem 0 0.15rem;color:#fde68a;font-size:0.78rem">
        {_imsg[:200] if _imsg else ""}
    </div>
    <div style="margin-top:0.3rem;color:#94a3b8;font-size:0.75rem">
        Endpoint: <code>{_endpt}</code> &nbsp;·&nbsp;
        Controlled backoff active — retrying automatically after cooldown window.<br>
        <strong style="color:#fef08a">⚙ Rule-Based Fallback Active</strong> —
        all pipeline outputs continue working normally.
    </div>
</div>
    """, unsafe_allow_html=True)
elif g_config_error or (not g_key_ok) or (not g_pid_ok):
    # 🔴 Configuration error — credentials missing or IAM exchange failed
    st.markdown(f"""
<div style="background:rgba(239,68,68,0.1);border:1px solid #ef4444;border-radius:6px;
            padding:0.5rem 0.8rem;font-size:0.8rem;color:#fca5a5;margin-bottom:1rem">
    🔴 <strong>Granite Configuration Error</strong> —
    {'WATSONX_API_KEY not configured.' if not g_key_ok else
     'WATSONX_PROJECT_ID not configured.' if not g_pid_ok else
     'IAM token exchange failed — check WATSONX_API_KEY validity.'}<br>
    <span style="color:#fcd34d;font-size:0.75rem">{g_error}</span><br>
    <span style="color:#94a3b8;font-size:0.75rem">
        Set <code>WATSONX_API_KEY</code> and <code>WATSONX_PROJECT_ID</code>
        in Streamlit Cloud → App settings → Secrets (or a local <code>.env</code> file).
        ⚙ Rule-based fallback is active.
    </span>
</div>
    """, unsafe_allow_html=True)
elif g_iam_ok:
    # 🟠 IAM OK but generation failed for a non-429 reason (5xx, 403, etc.)
    _http   = g_status.get("http_status")
    _icode  = g_status.get("ibm_error_code") or ""
    _imsg   = g_status.get("ibm_error_msg")  or ""
    _endpt  = g_status.get("endpoint", "/ml/v1/text/generation")

    _detail_parts = []
    if _http:
        _detail_parts.append(f"HTTP {_http}")
    if _icode:
        _detail_parts.append(f"IBM code: <code>{_icode}</code>")
    if _imsg:
        _detail_parts.append(f"IBM message: <em>{_imsg[:200]}</em>")
    _detail_parts.append(f"Endpoint: <code>{_endpt}</code>")
    _detail_html = " &nbsp;·&nbsp; ".join(_detail_parts)

    st.markdown(f"""
<div style="background:rgba(249,115,22,0.1);border:1px solid #f97316;border-radius:6px;
            padding:0.6rem 0.9rem;font-size:0.8rem;color:#fdba74;margin-bottom:1rem">
    🟠 <strong>Granite Fallback Mode</strong> — IAM authentication succeeded
    but the generation request failed.<br>
    <div style="margin:0.35rem 0 0.2rem;color:#fcd34d;font-size:0.78rem">{_detail_html}</div>
    <div style="color:#fdba74;font-size:0.75rem">{g_error}</div>
    <div style="margin-top:0.3rem;color:#94a3b8;font-size:0.75rem">
        Check: (1) project has <code>{g_status.get('model','')}</code> enabled,
        (2) WATSONX_URL region matches the project,
        (3) API key has Watson Machine Learning Editor/Admin role.
        ⚙ Rule-based fallback is active.
    </div>
</div>
    """, unsafe_allow_html=True)
else:
    # ⚙ No credentials — plain fallback, no error
    st.markdown("""
<div style="background:rgba(148,163,184,0.08);border:1px solid #475569;border-radius:6px;
            padding:0.5rem 0.8rem;font-size:0.8rem;color:#94a3b8;margin-bottom:1rem">
    ⚙ <strong>Granite Fallback Mode Active</strong> — IBM Granite is not configured.<br>
    Set <code>WATSONX_API_KEY</code> and <code>WATSONX_PROJECT_ID</code>
    in Streamlit Cloud → App settings → Secrets (or a local <code>.env</code> file).
    Rule-based responses are being used for all AI features.
</div>
    """, unsafe_allow_html=True)

# ──────────────────────────────────────────────
# Agent Activity Panel (Feature 8 — enhanced)
# ──────────────────────────────────────────────
section_header("🤖 AGENT ACTIVITY",
               '<span style="background:#1e3a5f;color:#93c5fd;font-size:0.7rem;padding:2px 8px;border-radius:4px;font-weight:700;letter-spacing:0.04em">MODEL / APPLICATION PIPELINE</span>')

# AI Recommendation → Human Approval → Civic Action flow
_resp_plan   = (orch.current_state or {}).get("response_plan", {})
_action_plan = (orch.current_state or {}).get("action_plan", {})
_total_recs  = len(_resp_plan.get("top_recommendations", []))
_need_appr   = _action_plan.get("approval_needed", 0)
_incidents   = len(_resp_plan.get("incidents", []))
st.markdown(f"""
<div style="background:#1a1d27;border:1px solid #2d3148;border-radius:8px;
            padding:0.75rem 1.2rem;margin-bottom:1rem">
    <div style="font-size:0.72rem;font-weight:700;color:#94a3b8;text-transform:uppercase;
                letter-spacing:0.07em;margin-bottom:0.6rem">
        AI Decision Pipeline — Current Cycle
    </div>
    <div style="display:flex;align-items:center;gap:0;flex-wrap:nowrap;overflow-x:auto">
        <div style="text-align:center;padding:0.5rem 0.9rem;background:#1e3a5f;border-radius:6px;
                    border:1px solid #3b82f6;min-width:110px">
            <div style="font-size:1.1rem">🤖</div>
            <div style="font-size:0.68rem;font-weight:700;color:#93c5fd">AI RECOMMENDATIONS</div>
            <div style="font-size:1rem;font-weight:800;color:#e2e8f0">{_total_recs}</div>
        </div>
        <div style="color:#475569;font-size:1rem;padding:0 0.4rem">→</div>
        <div style="text-align:center;padding:0.5rem 0.9rem;background:#3a1a00;border-radius:6px;
                    border:1px solid #f97316;min-width:110px">
            <div style="font-size:1.1rem">🔐</div>
            <div style="font-size:0.68rem;font-weight:700;color:#fdba74">HUMAN APPROVAL</div>
            <div style="font-size:1rem;font-weight:800;color:#e2e8f0">{_need_appr} required</div>
        </div>
        <div style="color:#475569;font-size:1rem;padding:0 0.4rem">→</div>
        <div style="text-align:center;padding:0.5rem 0.9rem;background:#14532d;border-radius:6px;
                    border:1px solid #22c55e;min-width:110px">
            <div style="font-size:1.1rem">🏙️</div>
            <div style="font-size:0.68rem;font-weight:700;color:#86efac">CIVIC ACTION</div>
            <div style="font-size:1rem;font-weight:800;color:#e2e8f0">{_incidents} incidents</div>
        </div>
        <div style="color:#475569;font-size:1rem;padding:0 0.4rem">→</div>
        <div style="text-align:center;padding:0.5rem 0.9rem;background:#1a0f1f;border-radius:6px;
                    border:1px solid #7c3aed;min-width:110px">
            <div style="font-size:1.1rem">🔄</div>
            <div style="font-size:0.68rem;font-weight:700;color:#c4b5fd">FEEDBACK LOOP</div>
            <div style="font-size:0.65rem;color:#94a3b8">Prediction-Outcome</div>
        </div>
    </div>
    <div style="font-size:0.65rem;color:#475569;margin-top:0.5rem">
        Counts reflect current pipeline run · Human approval is simulated in demo · Feedback loop tracks prediction accuracy (no live model retraining)
    </div>
</div>
""", unsafe_allow_html=True)
agent_statuses = orch.get_agent_statuses()
state = orch.current_state or {}

agent_icons = {
    "Flood Risk Agent":            "🌊",
    "Drainage Agent":              "🔧",
    "Citizen Report Agent":        "📱",
    "Response Coordination Agent": "⚡",
    "Damage Assessment Agent":     "🔍",
    "Chief Response Agent":        "🎯",
    "IBM Granite":                 "🧠",
}

agent_descriptions = {
    "Flood Risk Agent":            "ML-based risk scoring for all zones",
    "Drainage Agent":              "Drain blockage and maintenance priority",
    "Citizen Report Agent":        "Multilingual report classification",
    "Response Coordination Agent": "Incident response plan generation",
    "Damage Assessment Agent":     "Post-flood infrastructure assessment",
    "Chief Response Agent":        "Unified emergency action planning",
    "IBM Granite":                 "LLM reasoning & explanation layer",
}

agent_data_labels = {
    "Flood Risk Agent":            '<span style="background:#1e3a5f;color:#93c5fd;font-size:0.6rem;padding:1px 5px;border-radius:3px;font-weight:700">🔵 MODEL</span>',
    "Drainage Agent":              '<span style="background:#3a2e00;color:#fde68a;font-size:0.6rem;padding:1px 5px;border-radius:3px;font-weight:700">🟡 DEMO INFRASTRUCTURE</span>',
    "Citizen Report Agent":        '<span style="background:#3a1a00;color:#fdba74;font-size:0.6rem;padding:1px 5px;border-radius:3px;font-weight:700">🟠 USER + MODEL</span>',
    "Response Coordination Agent": '<span style="background:#1e3a5f;color:#93c5fd;font-size:0.6rem;padding:1px 5px;border-radius:3px;font-weight:700">🔵 MODEL</span>&nbsp;<span style="background:#3a2e00;color:#fde68a;font-size:0.6rem;padding:1px 5px;border-radius:3px;font-weight:700">🟡 DEMO RESOURCES</span>',
    "Damage Assessment Agent":     '<span style="background:#1e3a5f;color:#93c5fd;font-size:0.6rem;padding:1px 5px;border-radius:3px;font-weight:700">🔵 MODEL / DEMO</span>',
    "Chief Response Agent":        '<span style="background:#1e3a5f;color:#93c5fd;font-size:0.6rem;padding:1px 5px;border-radius:3px;font-weight:700">🔵 MODEL DECISION SUPPORT</span>',
    "IBM Granite":                 "",  # dynamic — set below
}

# KPI strip for agent panel
total_agents = len(agent_statuses)
active_agents = sum(1 for a in agent_statuses if a.get("status") in ("ACTIVE", "COMPLETE", "FALLBACK"))
pipeline_runs = len(orch.pipeline_log)

pa1, pa2, pa3, pa4 = st.columns(4)
with pa1: metric_card("Total Agents",    str(total_agents),  color="#3b82f6", icon="🤖")
with pa2: metric_card("Active/Ready",    str(active_agents), color="#22c55e", icon="✅")
with pa3: metric_card("Pipeline Runs",   str(pipeline_runs), color="#7c3aed", icon="▶️")
with pa4: metric_card("Last Run",        state.get("last_updated","N/A")[:16], color="#3b82f6", icon="🕐")

st.markdown("<div style='height:0.75rem'></div>", unsafe_allow_html=True)

# ── Agentic Workflow Visualization ────────────────────────────────────────
section_header("🔄 AGENTIC DECISION PIPELINE",
               '<span style="background:#7c3aed22;color:#a78bfa;font-size:0.7rem;padding:2px 8px;border-radius:4px;font-weight:700;border:1px solid #7c3aed">6 AGENTS IN SEQUENCE</span>')

st.markdown("""
<div style="font-size:0.78rem;color:#94a3b8;margin-bottom:0.75rem">
    The six AI agents run in a fixed sequence. Each agent receives outputs from the previous agent
    as its input. The final action plan is presented to a human officer for approval.
</div>
""", unsafe_allow_html=True)

# Build per-agent IO from pipeline_log entries
_pipeline_io: dict = {}
for _entry in orch.pipeline_log:
    _step = _entry.get("step", "")
    if _entry.get("status") == "COMPLETE" and _entry.get("agent_output"):
        _pipeline_io[_step] = _entry

_WORKFLOW_STEPS = [
    {
        "step_key":   "INPUT",
        "label":      "DATA INPUT",
        "icon":       "📡",
        "color":      "#3b82f6",
        "bg":         "rgba(59,130,246,0.08)",
        "border":     "#3b82f6",
        "input_text": f"Scenario: {SCENARIOS.get(orch.current_scenario,{}).get('label','—')} · Weather (LIVE/DEMO) · Infrastructure (DEMO) · Citizen reports (USER SUBMITTED)",
        "output_text":"Rainfall records, drain records, citizen reports, incident records, response teams",
        "why_text":   "Seed generator builds scenario-scaled dataset; live weather blended when Open-Meteo available",
        "pipeline_step": "DATA_LOAD",
    },
    {
        "step_key":   "FLOOD_RISK",
        "label":      "Agent 1: Flood Risk Agent",
        "icon":       "🌊",
        "color":      "#ef4444",
        "bg":         "rgba(239,68,68,0.06)",
        "border":     "#ef4444",
        "input_text": "Rainfall records + drain data + citizen reports + area metadata",
        "output_text":"Risk score 0–100 + risk level + key factors per zone",
        "why_text":   "Random Forest ML model (10 features) — output labelled MODEL/SIMULATED",
        "pipeline_step": "FLOOD_RISK",
    },
    {
        "step_key":   "DRAINAGE",
        "label":      "Agent 2: Drainage Agent",
        "icon":       "🔧",
        "color":      "#14b8a6",
        "bg":         "rgba(20,184,166,0.06)",
        "border":     "#14b8a6",
        "input_text": "Drain records + rainfall intensity + Agent 1 risk predictions",
        "output_text":"Ranked drain priority list: CRITICAL / HIGH / MEDIUM / LOW",
        "why_text":   "Scoring = capacity + blockage frequency + flood-zone flag + condition + rainfall",
        "pipeline_step": "DRAINAGE",
    },
    {
        "step_key":   "CITIZEN_REPORTS",
        "label":      "Agent 3: Citizen Report Agent",
        "icon":       "📱",
        "color":      "#f97316",
        "bg":         "rgba(249,115,22,0.06)",
        "border":     "#f97316",
        "input_text": "Citizen text reports (EN / HI / GU) + location + category hint",
        "output_text":"Classified reports: category + severity + routing + hotspot areas",
        "why_text":   "NLP keyword matching + IBM Granite classification; output labelled USER SUBMITTED",
        "pipeline_step": "CITIZEN_REPORTS",
    },
    {
        "step_key":   "DAMAGE_ASSESSMENT",
        "label":      "Agent 4: Damage Assessment Agent",
        "icon":       "🔍",
        "color":      "#a855f7",
        "bg":         "rgba(168,85,247,0.06)",
        "border":     "#a855f7",
        "input_text": "Active/resolved incident descriptions + location data",
        "output_text":"Preliminary damage level + affected infrastructure + recommended next step",
        "why_text":   "AI-generated PRELIMINARY assessment — requires field verification before official use",
        "pipeline_step": "DAMAGE_ASSESSMENT",
    },
    {
        "step_key":   "RESPONSE",
        "label":      "Agent 5: Response Coordination Agent",
        "icon":       "⚡",
        "color":      "#eab308",
        "bg":         "rgba(234,179,8,0.06)",
        "border":     "#eab308",
        "input_text": "Outputs from Agents 1–4 + team availability (DEMO)",
        "output_text":"Ranked incident list + action recommendations + team assignments",
        "why_text":   "Priority queue ranks areas by risk score; CRITICAL actions require human approval",
        "pipeline_step": "RESPONSE",
    },
    {
        "step_key":   "CHIEF_RESPONSE",
        "label":      "Agent 6: Chief Response Agent",
        "icon":       "🎯",
        "color":      "#22c55e",
        "bg":         "rgba(34,197,94,0.07)",
        "border":     "#22c55e",
        "input_text": "All agent outputs + resource state + scenario",
        "output_text":"Unified action plan + escalation path + executive summary",
        "why_text":   "Final AI decision layer — combines all evidence before presenting to human officer",
        "pipeline_step": "CHIEF_RESPONSE",
    },
    {
        "step_key":   "HUMAN",
        "label":      "HUMAN OFFICER DECISION",
        "icon":       "👤",
        "color":      "#60a5fa",
        "bg":         "rgba(96,165,250,0.10)",
        "border":     "#60a5fa",
        "input_text": "Chief Response Agent action plan + Granite situation report",
        "output_text":"Approve / Review / Reject — logged in audit trail",
        "why_text":   "AI recommends; human officer makes the final operational decision",
        "pipeline_step": "PIPELINE_COMPLETE",
    },
]

# Render as vertical chain
_wf_html = '<div style="display:flex;flex-direction:column;gap:0;margin-bottom:1.5rem">'
for _wi, _ws in enumerate(_WORKFLOW_STEPS):
    _log_entry = _pipeline_io.get(_ws["pipeline_step"], {})
    _live_output = _log_entry.get("agent_output", "") or _ws["output_text"]
    _live_why    = _log_entry.get("why", "") or _ws["why_text"]
    _ts          = _log_entry.get("timestamp", "")
    _ts_str      = _utc_to_ist(_ts, "%H:%M IST") if _ts else ""
    _status      = _log_entry.get("status", "")
    _status_badge = ""
    if _status == "COMPLETE":
        _status_badge = '<span style="background:#14532d;color:#86efac;font-size:0.6rem;padding:1px 5px;border-radius:3px;font-weight:700">COMPLETE</span>'
    elif _status == "RUNNING":
        _status_badge = '<span style="background:#1e3a5f;color:#93c5fd;font-size:0.6rem;padding:1px 5px;border-radius:3px;font-weight:700">RUNNING</span>'
    elif _ws["step_key"] == "HUMAN":
        _status_badge = '<span style="background:#1e3a5f;color:#93c5fd;font-size:0.6rem;padding:1px 5px;border-radius:3px;font-weight:700">AWAITING</span>'
    else:
        _status_badge = '<span style="background:#1a1d27;color:#475569;font-size:0.6rem;padding:1px 5px;border-radius:3px;border:1px solid #2d3148;font-weight:700">PENDING</span>'

    # connector arrow (skip on last item)
    _arrow = '' if _wi == len(_WORKFLOW_STEPS) - 1 else '<div style="text-align:center;color:#2d3148;font-size:1.1rem;line-height:1.2;padding:2px 0">&#9660;</div>'

    _ts_badge = (f'<span style="color:#475569;font-size:0.62rem;font-family:monospace">{_ts_str}</span>'
                 if _ts_str else "")
    _wf_html += (
        f'<div style="background:{_ws["bg"]};border:1px solid {_ws["border"]}40;border-left:3px solid {_ws["border"]};'
        f'border-radius:8px;padding:0.5rem 0.8rem;">'
        f'<div style="display:flex;align-items:center;gap:0.5rem;flex-wrap:wrap">'
        f'<span style="font-size:1.1rem">{_ws["icon"]}</span>'
        f'<span style="font-size:0.8rem;font-weight:700;color:#e2e8f0;flex:1">{_ws["label"]}</span>'
        f'{_status_badge}'
        f'{_ts_badge}'
        f'</div>'
        f'<div style="margin-top:0.3rem;display:grid;grid-template-columns:1fr 1fr;gap:0.3rem">'
        f'<div style="background:#080d18;border-radius:4px;padding:3px 6px">'
        f'<div style="font-size:0.55rem;color:#475569;font-weight:700;text-transform:uppercase">INPUT</div>'
        f'<div style="font-size:0.65rem;color:#64748b">{_ws["input_text"]}</div>'
        f'</div>'
        f'<div style="background:#080d18;border-radius:4px;padding:3px 6px">'
        f'<div style="font-size:0.55rem;color:{_ws["color"]};font-weight:700;text-transform:uppercase">OUTPUT</div>'
        f'<div style="font-size:0.65rem;color:#94a3b8">{_live_output[:120]}</div>'
        f'</div>'
        f'</div>'
        f'<div style="margin-top:0.25rem;font-size:0.62rem;color:#475569;font-style:italic">'
        f'WHY: {_live_why[:130]}'
        f'</div>'
        f'</div>'
        f'{_arrow}'
    )
_wf_html += '</div>'
st.markdown(_wf_html, unsafe_allow_html=True)

st.markdown("<div style='font-size:0.65rem;color:#475569;margin-bottom:1.5rem'>Pipeline sequence is fixed. Each agent receives structured outputs from the previous agent. IBM Granite is the reasoning layer — not an additional agent.</div>", unsafe_allow_html=True)

# ── Agent Trace (enhanced visual pipeline trace) ─────────────────────────
col_trace, col_agents_grid = st.columns([1, 1.8])
with col_trace:
    section_header("🔬 PIPELINE TRACE",
                   '<span style="background:#1e3a5f;color:#93c5fd;font-size:0.68rem;padding:1px 6px;border-radius:3px;font-weight:700">LIVE</span>')
    render_agent_trace(
        pipeline_log=orch.pipeline_log[-20:],
        granite_available=g_available,
        granite_rate_limited=g_rate_limited,
    )

with col_agents_grid:
    st.markdown("<div style='height:0.5rem'></div>", unsafe_allow_html=True)

st.markdown("<br>", unsafe_allow_html=True)

cols = st.columns(3)
for i, agent in enumerate(agent_statuses):
    col = cols[i % 3]
    with col:
        name = agent.get("agent", "")
        status = agent.get("status", "UNKNOWN")
        last_run = agent.get("last_run") or "Not run yet"
        activity = agent.get("recent_activity", [])
        icon = agent_icons.get(name, "🤖")
        desc = agent_descriptions.get(name, "")

        # For IBM Granite, override status with the probe-verified generation result.
        # g_available is True only when a real generation call succeeded (set above).
        granite_generation_live = g_available  # alias used by output_summary branch below
        if name == "IBM Granite":
            if granite_generation_live:
                status          = "LIVE"
                s_color         = "#22c55e"
                status_dot_anim = ""
            elif g_rate_limited:
                status          = "RATE LIMITED"
                s_color         = "#eab308"
                status_dot_anim = ""
            elif g_iam_ok:
                status          = "UNAVAILABLE"
                s_color         = "#f97316"
                status_dot_anim = ""
            else:
                status          = "FALLBACK"
                s_color         = "#94a3b8"
                status_dot_anim = ""
        else:
            status_colors = {
                "ACTIVE":    "#22c55e", "COMPLETE": "#22c55e",
                "FALLBACK":  "#f97316", "INACTIVE": "#94a3b8", "UNKNOWN": "#64748b",
            }
            status_dot_anim = "animation:pulse 2s infinite;" if status in ("ACTIVE",) else ""
            s_color = status_colors.get(status, "#94a3b8")

        activities_html = ""
        for act in activity[-5:]:
            activities_html += f'<div style="font-size:0.7rem;color:#94a3b8;padding:1px 0;white-space:nowrap;overflow:hidden;text-overflow:ellipsis">✓ {str(act)[:65]}</div>'
        if not activities_html:
            activities_html = '<div style="font-size:0.7rem;color:#475569">No activity yet</div>'

        # Derive output stats from state
        output_summary = ""
        if name == "Flood Risk Agent":
            n = len(state.get("risk_predictions", []))
            crit = sum(1 for p in state.get("risk_predictions", []) if p["risk_level"] == "CRITICAL")
            output_summary = f"Analyzed {n} zones — {crit} CRITICAL"
        elif name == "Drainage Agent":
            n = len(state.get("drain_analysis", {}).get("scored_drains", []))
            output_summary = f"Scored {n} drains"
        elif name == "Citizen Report Agent":
            n = state.get("report_analysis", {}).get("total_reports", 0)
            output_summary = f"Processed {n} reports"
        elif name == "Response Coordination Agent":
            n = len(state.get("response_plan", {}).get("incidents", []))
            output_summary = f"Generated {n} incident plans"
        elif name == "Chief Response Agent":
            n = state.get("action_plan", {}).get("total_actions", 0)
            output_summary = f"Created {n} action items"
        elif name == "IBM Granite":
            if granite_generation_live:
                output_summary = "🟢 IBM Granite — Live Generation"
                agent_data_labels["IBM Granite"] = (
                    '<span style="background:#14532d;color:#bbf7d0;font-size:0.6rem;padding:1px 5px;border-radius:3px;font-weight:700">🟢 LIVE</span>'
                )
            elif g_rate_limited:
                output_summary = "🟠 IBM Granite — Rate Limited · ⚙ Rule-Based Fallback Active"
                agent_data_labels["IBM Granite"] = (
                    '<span style="background:#422006;color:#fef08a;font-size:0.6rem;padding:1px 5px;border-radius:3px;font-weight:700">🟠 RATE LIMITED</span>'
                )
            elif g_config_error or (not g_key_ok) or (not g_pid_ok):
                output_summary = "🔴 Configuration Error — check WATSONX credentials"
                agent_data_labels["IBM Granite"] = (
                    '<span style="background:#3a0000;color:#fca5a5;font-size:0.6rem;padding:1px 5px;border-radius:3px;font-weight:700">🔴 CONFIG ERROR</span>'
                )
            elif g_iam_ok:
                output_summary = "🟠 Granite Fallback Mode — IAM OK, generation failed"
                agent_data_labels["IBM Granite"] = (
                    '<span style="background:#3a1a00;color:#fdba74;font-size:0.6rem;padding:1px 5px;border-radius:3px;font-weight:700">🟠 FALLBACK</span>'
                )
            else:
                output_summary = "⚙ Rule-Based Fallback — configure WatsonX credentials"
                agent_data_labels["IBM Granite"] = (
                    '<span style="background:#1a1d27;border:1px solid #475569;color:#94a3b8;font-size:0.6rem;padding:1px 5px;border-radius:3px;font-weight:700">⚙ FALLBACK</span>'
                )

        data_label_html = agent_data_labels.get(name, "")

        # Build INPUT/PROCESS/OUTPUT summaries per agent
        _ipo = {
            "Flood Risk Agent": {
                "input": "Rainfall records, drain data, citizen reports, area metadata",
                "process": "Random Forest ML → risk score 0–100 per zone",
            },
            "Drainage Agent": {
                "input": "Drain records, rainfall intensity, area flood risk",
                "process": "Rule-based scoring: capacity + blockage + condition",
            },
            "Citizen Report Agent": {
                "input": "Citizen text (EN/HI/GU), location, category hint",
                "process": "NLP classification → severity + routing + dedup",
            },
            "Response Coordination Agent": {
                "input": "Risk predictions, drain analysis, report analysis, teams",
                "process": "Priority queue → incident plans + team assignments",
            },
            "Chief Response Agent": {
                "input": "All agent outputs, resource state, scenario",
                "process": "Unified action plan + resource allocation",
            },
            "Damage Assessment Agent": {
                "input": "Incident descriptions, location data",
                "process": "Rule-based + Granite damage classification",
            },
            "IBM Granite": {
                "input": "Situation summary, zone data, user queries",
                "process": "WatsonX LLM → NL reasoning + explanations",
            },
        }
        _ipo_data = _ipo.get(name, {})

        st.markdown(f"""
<div style="background:#131620;border:1px solid #1e2440;border-radius:10px;padding:1rem 1.2rem;margin-bottom:0.75rem;min-height:200px">
    <div style="display:flex;align-items:center;gap:0.6rem;margin-bottom:0.5rem">
        <span style="font-size:1.5rem">{icon}</span>
        <div style="flex:1;min-width:0">
            <div style="font-weight:700;color:#e2e8f0;font-size:0.88rem">{name}</div>
            <div style="font-size:0.65rem;color:#64748b">{desc}</div>
        </div>
        <div style="display:flex;flex-direction:column;align-items:flex-end;gap:2px">
            <span style="background:{s_color};color:white;padding:2px 7px;
                  border-radius:6px;font-size:0.68rem;font-weight:600;white-space:nowrap;{status_dot_anim}">{status}</span>
            {data_label_html}
        </div>
    </div>
    <div style="display:flex;flex-direction:column;gap:3px;margin-bottom:0.4rem">
      <div style="background:#0a1020;border:1px solid #1e2440;border-radius:5px;padding:3px 6px">
        <div style="font-size:0.56rem;color:#475569;font-weight:700;text-transform:uppercase">INPUT</div>
        <div style="font-size:0.65rem;color:#64748b">{_ipo_data.get('input','—')}</div>
      </div>
      <div style="text-align:center;color:#2d3148;font-size:0.7rem;line-height:1">▼</div>
      <div style="background:#0a1020;border:1px solid #3b82f620;border-radius:5px;padding:3px 6px">
        <div style="font-size:0.56rem;color:#3b82f6;font-weight:700;text-transform:uppercase">PROCESS</div>
        <div style="font-size:0.65rem;color:#64748b">{_ipo_data.get('process','—')}</div>
      </div>
      <div style="text-align:center;color:#2d3148;font-size:0.7rem;line-height:1">▼</div>
      <div style="background:#0d1117;border:1px solid {s_color}40;border-radius:5px;padding:3px 6px">
        <div style="font-size:0.56rem;color:{s_color};font-weight:700;text-transform:uppercase">OUTPUT</div>
        <div style="font-size:0.65rem;color:#94a3b8">{output_summary if output_summary else "Awaiting pipeline run"}</div>
      </div>
    </div>
    <div style="font-size:0.63rem;color:#475569;margin-bottom:0.25rem">
        Last run: {str(last_run)[:19]}
    </div>
    <div style="border-top:1px solid #2d3148;padding-top:0.3rem">
        {activities_html}
    </div>
</div>
        """, unsafe_allow_html=True)

# ──────────────────────────────────────────────
# Pipeline execution log
# ──────────────────────────────────────────────
st.markdown("<br>", unsafe_allow_html=True)
section_header("PIPELINE EXECUTION LOG")

pipeline_log = orch.pipeline_log[-30:]
if pipeline_log:
    status_colors = {"COMPLETE": "#22c55e", "RUNNING": "#3b82f6", "FAILED": "#ef4444", "RUNNING": "#f97316"}
    status_icons  = {"COMPLETE": "✓", "RUNNING": "→", "FAILED": "✗"}

    for entry in reversed(pipeline_log):
        s = entry.get("status", "")
        s_color = status_colors.get(s, "#94a3b8")
        s_icon = status_icons.get(s, "·")
        ts_ist = _utc_to_ist(entry.get("timestamp", ""), "%H:%M IST")
        step = entry.get("step", "")
        agent = entry.get("agent", "")
        details = entry.get("details", "")

        st.markdown(f"""
<div style="display:flex;gap:0.75rem;padding:0.35rem 0;border-bottom:1px solid rgba(45,49,72,0.5);
            font-size:0.8rem;align-items:baseline">
    <span style="color:{s_color};font-weight:700;min-width:16px">{s_icon}</span>
    <span style="color:#475569;min-width:80px;font-family:monospace">{ts_ist}</span>
    <span style="color:#e2e8f0;min-width:200px;font-weight:600">{step}</span>
    <span style="color:#64748b;min-width:180px">{agent}</span>
    <span style="color:#94a3b8;flex:1">{details[:80]}</span>
    <span style="background:{s_color};color:white;padding:1px 5px;border-radius:4px;
                 font-size:0.65rem;font-weight:600;white-space:nowrap">{s}</span>
</div>
        """, unsafe_allow_html=True)
else:
    st.info("No pipeline log yet. Run a scenario.")

# ──────────────────────────────────────────────
# Architecture diagram — Mermaid flow diagram
# ──────────────────────────────────────────────
st.markdown("<br>", unsafe_allow_html=True)
section_header("AGENT ORCHESTRATION ARCHITECTURE")
st.caption("Live data-flow between the 6 specialised agents, IBM Granite reasoning layer, and the orchestrator. DEMO/SIMULATED labels show data provenance.")

# ── Architecture visualization — HTML pipeline diagram ───────────────────────
# Badge helpers
def _src_badge(color_bg, color_text, label):
    return (
        f'<span style="background:{color_bg};color:{color_text};'
        f'font-size:0.65rem;padding:2px 7px;border-radius:3px;font-weight:700">{label}</span>'
    )

def _arrow_down():
    return '<div style="text-align:center;color:#2d3148;font-size:1.3rem;line-height:1;margin:2px 0">\u25BC</div>'

def _agent_row(emoji, name, detail, border_color="#7c3aed"):
    return (
        f'<div style="display:flex;align-items:center;gap:0.6rem;'
        f'background:#0f1420;border:1px solid {border_color}40;border-left:3px solid {border_color};'
        f'border-radius:0 6px 6px 0;padding:0.45rem 0.8rem;margin-bottom:0">'
        f'<span style="font-size:1.1rem">{emoji}</span>'
        f'<div style="flex:1">'
        f'<span style="font-size:0.82rem;font-weight:700;color:#e2e8f0">{name}</span>'
        f'<span style="font-size:0.72rem;color:#64748b;margin-left:0.5rem">{detail}</span>'
        f'</div>'
        f'</div>'
    )

# DATA SOURCES row
_sources_html = (
    '<div style="background:#0a0d18;border:1px solid #1e3a5f;border-radius:8px;padding:0.6rem 1rem;margin-bottom:0">'
    '<div style="font-size:0.65rem;color:#475569;font-weight:700;text-transform:uppercase;letter-spacing:0.06em;margin-bottom:0.4rem">DATA SOURCES</div>'
    '<div style="display:flex;flex-wrap:wrap;gap:6px">'
    + _src_badge("#14532d", "#bbf7d0", "\U0001F7E2 Rainfall \u2014 Open-Meteo \u00b7 LIVE")
    + _src_badge("#1e3a5f", "#93c5fd", "\U0001F535 Flood Risk \u2014 Random Forest \u00b7 ML MODEL")
    + _src_badge("#3a2e00", "#fde68a", "\U0001F7E1 Drainage Infrastructure \u2014 DEMO")
    + _src_badge("#3a1a00", "#fdba74", "\U0001F7E0 Citizen Reports \u2014 USER SUBMITTED")
    + _src_badge("#3a2e00", "#fde68a", "\U0001F7E1 Response Teams \u2014 DEMO")
    + '</div></div>'
)

# ORCHESTRATOR
_orch_html = (
    '<div style="background:#0f1a2e;border:2px solid #3b82f6;border-radius:8px;'
    'padding:0.55rem 1rem;text-align:center">'
    '<span style="font-size:0.9rem;font-weight:800;color:#93c5fd">\U0001F3DB AGENT ORCHESTRATOR</span>'
    '<span style="font-size:0.72rem;color:#475569;margin-left:0.6rem">Sequential Pipeline</span>'
    '</div>'
)

# 6 AGENTS
_agents_html = (
    '<div style="background:#080d18;border:1px solid #2d3148;border-radius:8px;padding:0.5rem 0.7rem;display:flex;flex-direction:column;gap:4px">'
    '<div style="font-size:0.6rem;color:#475569;font-weight:700;text-transform:uppercase;letter-spacing:0.05em;margin-bottom:2px">6 AI AGENTS</div>'
    + _agent_row("\U0001F30A", "Flood Risk Agent", "Random Forest \u00b7 Risk Scores", "#7c3aed")
    + '<div style="height:3px"></div>'
    + _agent_row("\U0001F527", "Drainage Agent", "Blockage Priority \u00b7 Maintenance Schedule", "#3b82f6")
    + '<div style="height:3px"></div>'
    + _agent_row("\U0001F4F1", "Citizen Report Agent", "EN / HI / GU \u00b7 Classification \u00b7 Routing", "#22c55e")
    + '<div style="height:3px"></div>'
    + _agent_row("\U0001F50D", "Damage Assessment Agent", "Post-Flood Infrastructure Impact Scoring", "#eab308")
    + '<div style="height:3px"></div>'
    + _agent_row("\u26A1", "Response Coordination Agent", "Incidents \u00b7 Priority Queue \u00b7 Teams", "#f97316")
    + '<div style="height:3px"></div>'
    + _agent_row("\U0001F3AF", "Chief Response Agent", "Unified Action Plan \u00b7 Resource Allocation", "#ef4444")
    + '</div>'
)

# IBM GRANITE
_granite_html = (
    '<div style="background:linear-gradient(135deg,rgba(59,130,246,0.08),rgba(124,58,237,0.08));'
    'border:1px solid #3b82f6;border-radius:8px;padding:0.55rem 1rem">'
    '<div style="display:flex;align-items:center;gap:0.5rem;flex-wrap:wrap">'
    '<span style="font-size:1.1rem">\U0001F9E0</span>'
    '<span style="font-size:0.88rem;font-weight:800;color:#93c5fd">IBM Granite \u00b7 watsonx</span>'
    '<span style="background:#1e3a5f;color:#93c5fd;font-size:0.6rem;padding:1px 6px;border-radius:3px;font-weight:700">REASONING LAYER</span>'
    '</div>'
    '<div style="font-size:0.72rem;color:#64748b;margin-top:0.25rem">'
    'Situation Report \u00b7 WHY Explanations \u00b7 NL Query \u00b7 Incident Classification'
    '</div>'
    '</div>'
)

# DECISION CHAIN
_decision_html = (
    '<div style="background:#080d18;border:1px solid #2d3148;border-radius:8px;padding:0.5rem 0.8rem;display:flex;flex-direction:column;gap:3px">'
    '<div style="font-size:0.6rem;color:#475569;font-weight:700;text-transform:uppercase;letter-spacing:0.05em;margin-bottom:3px">DECISION CHAIN</div>'
    '<div style="display:flex;align-items:center;gap:0.5rem;padding:0.3rem 0.5rem;background:#1e2a0a;border-radius:5px">'
    '<span>\U0001F916</span><span style="font-size:0.78rem;font-weight:700;color:#e2e8f0">AI RECOMMENDATIONS</span>'
    '</div>'
    '<div style="text-align:center;color:#2d3148;font-size:0.9rem">\u25BC</div>'
    '<div style="display:flex;align-items:center;gap:0.5rem;padding:0.3rem 0.5rem;background:#1a0a0a;border-radius:5px">'
    '<span>\U0001F510</span><span style="font-size:0.78rem;font-weight:700;color:#fca5a5">HUMAN APPROVAL</span>'
    '<span style="font-size:0.65rem;color:#64748b;margin-left:auto">approve / reject / modify</span>'
    '</div>'
    '<div style="text-align:center;color:#2d3148;font-size:0.9rem">\u25BC</div>'
    '<div style="display:flex;align-items:center;gap:0.5rem;padding:0.3rem 0.5rem;background:#0a1a10;border-radius:5px">'
    '<span>\U0001F3D9</span><span style="font-size:0.78rem;font-weight:700;color:#6ee7b7">CIVIC ACTION LOGGED</span>'
    '<span style="font-size:0.65rem;color:#64748b;margin-left:auto">audit trail</span>'
    '</div>'
    '<div style="text-align:center;color:#2d3148;font-size:0.9rem">\u25BC</div>'
    '<div style="display:flex;align-items:center;gap:0.5rem;padding:0.3rem 0.5rem;background:#12082e;border-radius:5px">'
    '<span>\U0001F504</span><span style="font-size:0.78rem;font-weight:700;color:#c4b5fd">PREDICTION \u2192 OUTCOME FEEDBACK</span>'
    '</div>'
    '</div>'
)

# OPERATIONAL OUTPUTS
_outputs_html = (
    '<div style="background:#0a0d18;border:1px solid #1e3a5f;border-radius:8px;padding:0.6rem 1rem">'
    '<div style="font-size:0.65rem;color:#475569;font-weight:700;text-transform:uppercase;letter-spacing:0.06em;margin-bottom:0.4rem">OPERATIONAL OUTPUTS</div>'
    '<div style="display:flex;flex-wrap:wrap;gap:6px">'
    + _src_badge("#1e3a5f", "#93c5fd", "\U0001F4CA Live Risk Map")
    + _src_badge("#450a0a", "#fca5a5", "\U0001F514 Alerts")
    + _src_badge("#1a1d27", "#a78bfa", "\U0001F4CB Situation Report")
    + _src_badge("#14532d", "#bbf7d0", "\U0001F327 Rainfall Data")
    + _src_badge("#3a1a00", "#fdba74", "\U0001F692 Response Teams")
    + _src_badge("#1e2440", "#94a3b8", "\U0001F4F1 Citizen Reports")
    + '</div></div>'
)

# Assemble full diagram
_arch_html = (
    '<div style="display:flex;flex-direction:column;gap:0;margin-bottom:1rem">'
    + _sources_html
    + _arrow_down()
    + _orch_html
    + _arrow_down()
    + _agents_html
    + _arrow_down()
    + _granite_html
    + _arrow_down()
    + _decision_html
    + _arrow_down()
    + _outputs_html
    + '</div>'
)
st.markdown(_arch_html, unsafe_allow_html=True)

# ──────────────────────────────────────────────
# NL Query
# ──────────────────────────────────────────────
st.markdown("<br>", unsafe_allow_html=True)
section_header("🔍 NATURAL LANGUAGE COMMAND CENTER")
st.markdown("""
<div style="font-size:0.8rem;color:#94a3b8;margin-bottom:0.75rem">
    Query the system using natural language. Answers are grounded in FloodGuard AI application data — sources are labeled LIVE, MODEL, USER SUBMITTED or DEMO.
    <span style="background:#7c3aed;color:white;padding:1px 6px;border-radius:4px;font-size:0.7rem">IBM Granite powered</span>
</div>
""", unsafe_allow_html=True)

example_queries = [
    "Show critical flood zones",
    "Why is the top area high risk?",
    "Which drains need immediate maintenance?",
    "How many unresolved flood complaints are there?",
    "Which area received the highest rainfall?",
    "Give me the top 5 recommended municipal actions",
]

col_q, col_e = st.columns([1.5, 1])
with col_q:
    query = st.text_input(
        "Ask FloodGuard AI:",
        placeholder="e.g. Show critical flood zones in Ahmedabad",
        key="nl_query",
    )
    if st.button("🔍 Ask AI", type="primary") and query:
        with st.spinner("Querying agents + Granite..."):
            answer = orch.query(query)
        st.markdown(f"""
<div style="background:#080f1e;border:1px solid #1e3a5f;border-radius:10px;padding:1rem 1.2rem;margin-bottom:0.75rem;margin-top:0.5rem">
    <div style="font-size:0.75rem;color:#94a3b8;margin-bottom:0.3rem">
        🧠 IBM Granite Response {'(Live)' if g_available else '(Fallback)'}
    </div>
    <div style="color:#e2e8f0;font-size:0.9rem;line-height:1.6">{answer}</div>
    <div style="font-size:0.7rem;color:#475569;margin-top:0.5rem">
        Grounded in FloodGuard AI application data · Sources: LIVE / MODEL / USER SUBMITTED / DEMO
    </div>
</div>
        """, unsafe_allow_html=True)

with col_e:
    st.markdown("""
<div style="font-size:0.8rem;color:#94a3b8;margin-bottom:0.4rem"><b>Example queries:</b></div>
    """, unsafe_allow_html=True)
    for q in example_queries:
        if st.button(q, key=f"ex_{q[:20]}", use_container_width=True):
            with st.spinner("Querying..."):
                answer = orch.query(q)
            st.markdown(f"""
<div style="background:#080f1e;border:1px solid #1e3a5f;border-radius:10px;padding:1rem 1.2rem;margin-bottom:0.75rem;font-size:0.85rem;color:#e2e8f0">{answer}</div>
            """, unsafe_allow_html=True)

# ──────────────────────────────────────────────
# IBM Granite WHY Explanation Panel
# ──────────────────────────────────────────────
st.markdown("<br>", unsafe_allow_html=True)
section_header("🧠 IBM GRANITE WHY EXPLANATION")
st.markdown("""
<div style="font-size:0.8rem;color:#94a3b8;margin-bottom:0.75rem">
    Ask IBM Granite to explain WHY a zone is high-risk.
    Uses <strong>only available project data</strong> — never invents real sensor or government readings.
    <span style="background:#7c3aed;color:white;padding:1px 6px;border-radius:4px;font-size:0.7rem">IBM Granite powered</span>
</div>
""", unsafe_allow_html=True)

if "why_explanations" not in st.session_state:
    st.session_state.why_explanations = {}

predictions = (orch.current_state or {}).get("risk_predictions", [])
why_col1, why_col2 = st.columns([1, 1.5])

with why_col1:
    if predictions:
        risky_zones = sorted(predictions, key=lambda x: x["risk_score"], reverse=True)[:15]
        zone_opts = [
            f"{p['area']}, {p['city']} — {p['risk_level']} ({p['risk_score']:.0f}/100)"
            for p in risky_zones
        ]
        selected_why = st.selectbox("Select zone to explain:", zone_opts, key="why_zone_monitor")
        if st.button("🧠 Explain WHY this zone is risky", key="why_btn_monitor", type="primary"):
            idx = zone_opts.index(selected_why)
            zone_pred = risky_zones[idx]
            cache_key = f"{zone_pred['area']}_{zone_pred['city']}_{orch.current_scenario}"
            if cache_key not in st.session_state.why_explanations:
                with st.spinner("IBM Granite analyzing risk factors..."):
                    explanation = explain_why_zone_risky(zone_pred)
                    st.session_state.why_explanations[cache_key] = (explanation, zone_pred)
            selected_key = cache_key
            st.session_state["why_selected"] = cache_key

with why_col2:
    show_key = st.session_state.get("why_selected")
    if show_key and show_key in st.session_state.why_explanations:
        explanation, zone_pred = st.session_state.why_explanations[show_key]
        level = zone_pred.get("risk_level", "UNKNOWN")
        level_colors = {"CRITICAL": "#ef4444", "HIGH": "#f97316", "MEDIUM": "#eab308", "LOW": "#22c55e"}
        l_color = level_colors.get(level, "#94a3b8")
        features = zone_pred.get("input_features", {})
        st.markdown(f"""
<div style="background:#080f1e;border:1px solid #1e3a5f;border-radius:10px;padding:1rem 1.2rem;margin-bottom:0.75rem">
    <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:0.5rem">
        <div style="font-weight:700;color:#e2e8f0">{zone_pred['area']}, {zone_pred['city']}</div>
        <span style="background:{l_color};color:white;padding:2px 8px;border-radius:6px;font-size:0.72rem;font-weight:600">{level} RISK</span>
    </div>
    <div style="font-size:0.82rem;color:#e2e8f0;line-height:1.6;margin-bottom:0.5rem">
        {explanation}
    </div>
    <div style="display:grid;grid-template-columns:1fr 1fr;gap:0.3rem;font-size:0.7rem;color:#94a3b8;border-top:1px solid #2d3148;padding-top:0.4rem">
        <div>Rainfall: {features.get('rainfall_1h', 0):.0f} mm/hr</div>
        <div>Score: {zone_pred['risk_score']:.0f}/100</div>
        <div>Confidence: {zone_pred.get('confidence', 0):.0%}</div>
        <div>Scenario: {orch.current_scenario}</div>
    </div>
    <div style="font-size:0.65rem;color:#475569;margin-top:0.3rem">
        🧠 IBM Granite {'(🟢 LIVE — generation verified)' if granite_generation_live else '(⚪ Fallback — rule-based)'} ·
        Uses only available application data — never invents real sensor or government readings
    </div>
</div>
        """, unsafe_allow_html=True)
    else:
        st.markdown("""
<div style="background:#131620;border:1px solid #1e2440;border-radius:10px;padding:1rem 1.2rem;margin-bottom:0.75rem;text-align:center;padding:2rem;color:#64748b;font-size:0.85rem">
    Select a zone and click "Explain WHY" to see IBM Granite's risk explanation.
</div>
        """, unsafe_allow_html=True)

# ──────────────────────────────────────────────
# Live Pipeline Execution Log
# ──────────────────────────────────────────────
st.markdown("<br>", unsafe_allow_html=True)
st.markdown("---")
section_header("⚡ PIPELINE EXECUTION LOG",
               '<span style="background:#1e3a5f;color:#93c5fd;font-size:0.7rem;padding:2px 8px;border-radius:4px;font-weight:700">LIVE TRACE</span>')

st.markdown("""
<div style="font-size:0.8rem;color:#94a3b8;margin-bottom:0.75rem">
    Real-time execution trace of the multi-agent pipeline.
    Each row corresponds to one pipeline step logged by the Orchestrator.
    <span style="background:#1e3a5f;color:#93c5fd;font-size:0.68rem;padding:1px 5px;border-radius:3px;font-weight:700">LIVE TRACE</span>
    — no fabricated steps.
</div>
""", unsafe_allow_html=True)

_log = orch.pipeline_log[-30:] if orch.pipeline_log else []

if not _log:
    st.info("No pipeline log entries yet. Run a scenario to see the execution trace.")
else:
    # Status colour map
    _status_colors = {
        "RUNNING":   "#3b82f6",
        "COMPLETE":  "#22c55e",
        "FALLBACK":  "#eab308",
        "ERROR":     "#ef4444",
        "SKIPPED":   "#94a3b8",
    }
    _step_icons = {
        "PIPELINE_START": "▶",
        "DATA_LOAD":      "📂",
        "LIVE_WEATHER":   "🌐",
        "FLOOD_RISK":     "🌊",
        "DRAINAGE":       "🔧",
        "CITIZEN":        "📱",
        "RESPONSE":       "⚡",
        "DAMAGE":         "🔍",
        "CHIEF":          "🎯",
        "GRANITE":        "🧠",
        "LEARNING":       "🔄",
        "PIPELINE_COMPLETE": "✅",
    }

    # Build header
    st.markdown("""
<div style="display:grid;grid-template-columns:80px 140px 100px 1fr;gap:0.5rem;
            padding:0.4rem 0.7rem;background:#1a1d27;border-radius:6px 6px 0 0;
            font-size:0.68rem;font-weight:700;color:#94a3b8;text-transform:uppercase;
            letter-spacing:0.04em">
    <div>Time</div><div>Step</div><div>Status</div><div>Details</div>
</div>
    """, unsafe_allow_html=True)

    rows_html = ""
    for entry in reversed(_log[-20:]):  # most recent first
        step   = entry.get("step", "")
        agent  = entry.get("agent", "")
        status = entry.get("status", "")
        details = entry.get("details", "")
        ts     = entry.get("timestamp", "")
        time_str = _utc_to_ist(ts, "%H:%M IST") if ts else ts

        icon = next((v for k, v in _step_icons.items() if k in step), "•")
        s_color = _status_colors.get(status, "#94a3b8")
        row_bg = "rgba(34,197,94,0.05)" if status == "COMPLETE" else \
                 "rgba(239,68,68,0.05)" if status == "ERROR" else \
                 "rgba(59,130,246,0.04)"

        if len(s_color) == 7:
            sr, sg, sb = int(s_color[1:3], 16), int(s_color[3:5], 16), int(s_color[5:7], 16)
        else:
            sr, sg, sb = 59, 130, 246
        badge_bg = f"rgba({sr},{sg},{sb},0.15)"

        rows_html += (
            f'<div style="display:grid;grid-template-columns:80px 140px 100px 1fr;gap:0.5rem;'
            f'padding:0.4rem 0.7rem;border-bottom:1px solid #1e2440;'
            f'font-size:0.72rem;align-items:center;background:{row_bg}">'
            f'<div style="color:#475569;font-family:monospace">{time_str}</div>'
            f'<div style="color:#e2e8f0;font-weight:600">{icon} {step[:16]}</div>'
            f'<div><span style="background:{badge_bg};border:1px solid {s_color}40;color:{s_color};'
            f'padding:1px 6px;border-radius:3px;font-size:0.65rem;font-weight:700">'
            f'{status}</span></div>'
            f'<div style="color:#64748b;overflow:hidden;text-overflow:ellipsis;white-space:nowrap"'
            f' title="{details}">{details[:90]}</div>'
            f'</div>\n'
        )

    st.markdown(f"""
<div style="border:1px solid #2d3148;border-radius:0 0 6px 6px;
            max-height:380px;overflow-y:auto">
    {rows_html}
</div>
    """, unsafe_allow_html=True)

    st.markdown(f"""
<div style="font-size:0.68rem;color:#475569;margin-top:0.3rem">
    Showing last {min(20, len(_log))} of {len(_log)} pipeline log entries.
    Log is bounded to the last 100 entries (rolling window).
</div>
    """, unsafe_allow_html=True)

# ──────────────────────────────────────────────
# Footer
# ──────────────────────────────────────────────
st.markdown("---")
st.markdown(f"""
<div style="text-align:center;color:#475569;font-size:0.72rem;padding-bottom:1rem">
    FloodGuard AI — Agent Monitor | 6-Agent Pipeline |
    🔵 MODEL predictions · 🟡 DEMO infrastructure · 🟢 LIVE weather (Open-Meteo)
</div>
""", unsafe_allow_html=True)
