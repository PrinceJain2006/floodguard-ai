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
    render_agent_trace, render_granite_panel, risk_level_indicator,
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
# Granite status — granite_status() now probes real generation internally
# Result is cached per session to avoid hitting the API on every rerun.
# ──────────────────────────────────────────────
if "granite_status_cache" not in st.session_state:
    st.session_state.granite_status_cache = granite_status()

g_status        = st.session_state.granite_status_cache
g_available     = g_status.get("available", False)      # True = real generation confirmed
g_iam_ok        = g_status.get("iam_ok", False)         # True = IAM token obtained
g_key_ok        = g_status.get("api_key_configured", False)
g_pid_ok        = g_status.get("project_configured", False)
g_rate_limited  = g_status.get("rate_limited", False)   # True = 429 backoff active
g_error         = g_status.get("error") or ""

if g_available:
    granite_color = "#22c55e"
    granite_label = "CONNECTED"
elif g_rate_limited:
    # 429 — credentials and IAM are fine, just rate-limited
    granite_color = "#eab308"
    granite_label = "RATE LIMITED"
elif g_iam_ok:
    # IAM worked but generation failed for another reason
    granite_color = "#f97316"
    granite_label = "DEGRADED"
elif g_key_ok or g_pid_ok:
    # Credentials present but IAM exchange failed
    granite_color = "#ef4444"
    granite_label = "AUTH ERROR"
else:
    granite_color = "#94a3b8"
    granite_label = "FALLBACK"

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
    pass  # CONNECTED — no banner needed
elif g_rate_limited:
    # 429 — show a distinct yellow rate-limit banner; no misleading "check project" advice
    _imsg  = g_status.get("ibm_error_msg") or ""
    _endpt = g_status.get("endpoint", "/ml/v1/text/generation")
    st.markdown(f"""
    <div style="background:rgba(234,179,8,0.08);border:1px solid #ca8a04;border-radius:6px;
                padding:0.6rem 0.9rem;font-size:0.8rem;color:#fef08a;margin-bottom:1rem">
        🚦 <strong>WatsonX Rate Limited</strong> — HTTP 429
        <code>consumption_limit_reached</code><br>
        <div style="margin:0.3rem 0 0.15rem;color:#fde68a;font-size:0.78rem">
            {_imsg[:240] if _imsg else g_error[:240]}
        </div>
        <div style="color:#fef08a">{g_error[:300]}</div>
        <div style="margin-top:0.3rem;color:#94a3b8;font-size:0.75rem">
            Endpoint: <code>{_endpt}</code><br>
            The free-tier concurrent request limit for
            <code>{g_status.get('model','')}</code> is temporarily exhausted.
            The app is automatically backing off and will retry after the
            cooldown window. Rule-based fallback is active in the meantime.
        </div>
    </div>
    """, unsafe_allow_html=True)
elif g_iam_ok:
    # IAM OK but generation failed for a non-429 reason — show full diagnostic
    _http   = g_status.get("http_status")
    _icode  = g_status.get("ibm_error_code") or ""
    _imsg   = g_status.get("ibm_error_msg")  or ""
    _endpt  = g_status.get("endpoint", "/ml/v1/text/generation")

    # Build safe detail line — only code, IBM fields, and endpoint path (no secrets)
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
        ⚠️ <strong>WatsonX Generation Unavailable</strong> — IAM authentication succeeded
        but the text-generation request failed.<br>
        <div style="margin:0.35rem 0 0.2rem;color:#fcd34d;font-size:0.78rem">{_detail_html}</div>
        <div style="color:#fdba74">{g_error}</div>
        <div style="margin-top:0.3rem;color:#94a3b8;font-size:0.75rem">
            Check: (1) project has <code>{g_status.get('model','')}</code> enabled,
            (2) WATSONX_URL region matches the project,
            (3) API key has Watson Machine Learning Editor/Admin role.
            Rule-based responses are active.
        </div>
    </div>
    """, unsafe_allow_html=True)
elif g_key_ok:
    st.markdown(f"""
    <div style="background:rgba(239,68,68,0.1);border:1px solid #ef4444;border-radius:6px;
                padding:0.5rem 0.8rem;font-size:0.8rem;color:#fca5a5;margin-bottom:1rem">
        🔑 <strong>Authentication Failed</strong> — API key is set but IAM token exchange failed.<br>
        <span style="color:#fcd34d">{g_error}</span><br>
        Verify that <code>WATSONX_API_KEY</code> is current and not expired.
        Rule-based responses are being used for all AI features.
    </div>
    """, unsafe_allow_html=True)
else:
    st.markdown("""
    <div style="background:rgba(148,163,184,0.08);border:1px solid #475569;border-radius:6px;
                padding:0.5rem 0.8rem;font-size:0.8rem;color:#94a3b8;margin-bottom:1rem">
        ⚙️ <strong>Fallback Mode Active</strong> — IBM Granite is not configured.<br>
        Set <code>WATSONX_API_KEY</code> and <code>WATSONX_PROJECT_ID</code>
        in Streamlit Cloud → App settings → Secrets (or in a local <code>.env</code> file).
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
                output_summary = "🟢 LIVE — generation verified"
                agent_data_labels["IBM Granite"] = (
                    '<span style="background:#14532d;color:#bbf7d0;font-size:0.6rem;padding:1px 5px;border-radius:3px;font-weight:700">🟢 LIVE</span>'
                )
            elif g_rate_limited:
                output_summary = "🚦 RATE LIMITED — backing off, fallback active"
                agent_data_labels["IBM Granite"] = (
                    '<span style="background:#422006;color:#fef08a;font-size:0.6rem;padding:1px 5px;border-radius:3px;font-weight:700">🚦 RATE LIMITED</span>'
                )
            elif g_iam_ok:
                output_summary = "⚠ UNAVAILABLE — IAM OK but generation failed"
                agent_data_labels["IBM Granite"] = (
                    '<span style="background:#3a1a00;color:#fdba74;font-size:0.6rem;padding:1px 5px;border-radius:3px;font-weight:700">⚠ UNAVAILABLE</span>'
                )
            else:
                output_summary = "⚪ FALLBACK — configure credentials"
                agent_data_labels["IBM Granite"] = (
                    '<span style="background:#1a1d27;border:1px solid #475569;color:#94a3b8;font-size:0.6rem;padding:1px 5px;border-radius:3px;font-weight:700">⚪ FALLBACK</span>'
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
        <style>@keyframes pulse {{0%,100%{{opacity:1}}50%{{opacity:0.5}}}}</style>
        <div class="fg-card" style="min-height:200px">
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
            <!-- INPUT → PROCESS → OUTPUT -->
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
        ts = entry.get("timestamp", "")[:19]
        step = entry.get("step", "")
        agent = entry.get("agent", "")
        details = entry.get("details", "")

        st.markdown(f"""
        <div style="display:flex;gap:0.75rem;padding:0.35rem 0;border-bottom:1px solid rgba(45,49,72,0.5);
                    font-size:0.8rem;align-items:baseline">
            <span style="color:{s_color};font-weight:700;min-width:16px">{s_icon}</span>
            <span style="color:#475569;min-width:80px;font-family:monospace">{ts[11:]}</span>
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
# Architecture diagram — clean dark-theme SVG
# ──────────────────────────────────────────────
st.markdown("<br>", unsafe_allow_html=True)
section_header("AGENT ORCHESTRATION ARCHITECTURE")

st.markdown("""
<div style="background:#13151f;border:1px solid #2d3148;border-radius:10px;padding:1.5rem 1.5rem 1rem">

  <!-- Row 0: DATA SOURCES -->
  <div style="font-size:0.65rem;font-weight:700;color:#475569;text-transform:uppercase;
              letter-spacing:0.1em;margin-bottom:0.5rem">Data Sources</div>
  <div style="display:flex;gap:0.5rem;flex-wrap:wrap;margin-bottom:0.5rem">
    <span style="background:#0f2d1a;color:#6ee7b7;font-size:0.68rem;padding:3px 8px;border-radius:4px;border:1px solid #22c55e;white-space:nowrap">🟢 Rainfall (Open-Meteo LIVE)</span>
    <span style="background:#1e3a5f;color:#93c5fd;font-size:0.68rem;padding:3px 8px;border-radius:4px;border:1px solid #3b82f6;white-space:nowrap">🔵 Flood Risk (ML Model)</span>
    <span style="background:#3a2e00;color:#fde68a;font-size:0.68rem;padding:3px 8px;border-radius:4px;border:1px solid #eab308;white-space:nowrap">🟡 Drainage Infrastructure (DEMO)</span>
    <span style="background:#3a1a00;color:#fdba74;font-size:0.68rem;padding:3px 8px;border-radius:4px;border:1px solid #f97316;white-space:nowrap">🟠 Citizen Reports (USER SUBMITTED)</span>
    <span style="background:#3a2e00;color:#fde68a;font-size:0.68rem;padding:3px 8px;border-radius:4px;border:1px solid #eab308;white-space:nowrap">🟡 Response Teams (DEMO)</span>
  </div>

  <!-- Arrow down -->
  <div style="text-align:center;color:#2d3148;font-size:1.4rem;line-height:1;margin-bottom:0.5rem">▼</div>

  <!-- Row 1: ORCHESTRATOR label -->
  <div style="border:1px solid #2d3148;border-radius:8px;padding:0.75rem 1rem;background:#1a1d27;margin-bottom:0.5rem">
    <div style="font-size:0.65rem;font-weight:700;color:#475569;text-transform:uppercase;letter-spacing:0.1em;margin-bottom:0.6rem">
      Agent Orchestrator — Sequential Pipeline
    </div>

    <!-- Row 1: specialist agents -->
    <div style="display:flex;gap:0.5rem;flex-wrap:wrap;margin-bottom:0.5rem">
      <div style="background:#0f1117;border:1px solid #3b82f6;border-radius:6px;padding:0.4rem 0.7rem;flex:1;min-width:120px">
        <div style="font-size:0.78rem">🌊</div>
        <div style="font-size:0.72rem;font-weight:700;color:#93c5fd">Flood Risk Agent</div>
        <div style="font-size:0.62rem;color:#475569">ML · Random Forest · risk scores</div>
      </div>
      <div style="background:#0f1117;border:1px solid #eab308;border-radius:6px;padding:0.4rem 0.7rem;flex:1;min-width:120px">
        <div style="font-size:0.78rem">🔧</div>
        <div style="font-size:0.72rem;font-weight:700;color:#fde68a">Drainage Agent</div>
        <div style="font-size:0.62rem;color:#475569">blockage priority · maintenance schedule</div>
      </div>
      <div style="background:#0f1117;border:1px solid #f97316;border-radius:6px;padding:0.4rem 0.7rem;flex:1;min-width:120px">
        <div style="font-size:0.78rem">📱</div>
        <div style="font-size:0.72rem;font-weight:700;color:#fdba74">Citizen Report Agent</div>
        <div style="font-size:0.62rem;color:#475569">EN/HI/GU · classify · route</div>
      </div>
      <div style="background:#0f1117;border:1px solid #7c3aed;border-radius:6px;padding:0.4rem 0.7rem;flex:1;min-width:120px">
        <div style="font-size:0.78rem">⚡</div>
        <div style="font-size:0.72rem;font-weight:700;color:#c4b5fd">Response Coord. Agent</div>
        <div style="font-size:0.62rem;color:#475569">incidents · priority queue · teams</div>
      </div>
      <div style="background:#0f1117;border:1px solid #94a3b8;border-radius:6px;padding:0.4rem 0.7rem;flex:1;min-width:120px">
        <div style="font-size:0.78rem">🔍</div>
        <div style="font-size:0.72rem;font-weight:700;color:#cbd5e1">Damage Assessment Agent</div>
        <div style="font-size:0.62rem;color:#475569">post-flood infra impact scoring</div>
      </div>
    </div>

    <!-- Arrow down -->
    <div style="text-align:center;color:#2d3148;font-size:1.1rem;line-height:1;margin-bottom:0.5rem">▼</div>

    <!-- Row 2: Chief + Granite side by side -->
    <div style="display:flex;gap:0.5rem;flex-wrap:wrap;margin-bottom:0.35rem">
      <div style="background:#0f1117;border:1px solid #22c55e;border-radius:6px;padding:0.4rem 0.7rem;flex:1;min-width:140px">
        <div style="font-size:0.78rem">🎯</div>
        <div style="font-size:0.72rem;font-weight:700;color:#86efac">Chief Response Agent</div>
        <div style="font-size:0.62rem;color:#475569">unified action plan · resource allocation</div>
      </div>
      <div style="background:#0f1117;border:1px solid #3b82f6;border-radius:6px;padding:0.4rem 0.7rem;flex:2;min-width:160px">
        <div style="font-size:0.78rem">🧠</div>
        <div style="font-size:0.72rem;font-weight:700;color:#93c5fd">IBM Granite (WatsonX)</div>
        <div style="font-size:0.62rem;color:#475569">situation report · WHY explanations · NL query · incident classification</div>
      </div>
    </div>
  </div>

  <!-- Arrow down -->
  <div style="text-align:center;color:#2d3148;font-size:1.4rem;line-height:1;margin-bottom:0.5rem">▼</div>

  <!-- Row 3: Decision flow -->
  <div style="display:flex;gap:0.5rem;align-items:center;flex-wrap:wrap;margin-bottom:0.5rem">
    <div style="background:#1e3a5f;border:1px solid #3b82f6;border-radius:6px;padding:0.4rem 0.7rem;flex:1;min-width:120px;text-align:center">
      <div style="font-size:0.68rem;font-weight:700;color:#93c5fd">🤖 AI Recommendations</div>
    </div>
    <div style="color:#475569;font-size:1rem">→</div>
    <div style="background:#3a1a00;border:1px solid #f97316;border-radius:6px;padding:0.4rem 0.7rem;flex:1;min-width:120px;text-align:center">
      <div style="font-size:0.68rem;font-weight:700;color:#fdba74">🔐 Human Approval</div>
    </div>
    <div style="color:#475569;font-size:1rem">→</div>
    <div style="background:#14532d;border:1px solid #22c55e;border-radius:6px;padding:0.4rem 0.7rem;flex:1;min-width:120px;text-align:center">
      <div style="font-size:0.68rem;font-weight:700;color:#86efac">🏙️ Civic Action Logged</div>
    </div>
    <div style="color:#475569;font-size:1rem">→</div>
    <div style="background:#1a0f1f;border:1px solid #7c3aed;border-radius:6px;padding:0.4rem 0.7rem;flex:1;min-width:140px;text-align:center">
      <div style="font-size:0.68rem;font-weight:700;color:#c4b5fd">🔄 Prediction–Outcome Feedback</div>
    </div>
  </div>

  <!-- Row 4: Outputs -->
  <div style="display:flex;gap:0.5rem;flex-wrap:wrap">
    <span style="background:#0f1117;border:1px solid #2d3148;border-radius:4px;padding:3px 8px;font-size:0.66rem;color:#94a3b8">📊 Live Risk Map</span>
    <span style="background:#0f1117;border:1px solid #2d3148;border-radius:4px;padding:3px 8px;font-size:0.66rem;color:#94a3b8">🔔 Alerts</span>
    <span style="background:#0f1117;border:1px solid #2d3148;border-radius:4px;padding:3px 8px;font-size:0.66rem;color:#94a3b8">📋 Situation Report</span>
    <span style="background:#0f1117;border:1px solid #2d3148;border-radius:4px;padding:3px 8px;font-size:0.66rem;color:#94a3b8">🌧️ Rainfall Data</span>
    <span style="background:#0f1117;border:1px solid #2d3148;border-radius:4px;padding:3px 8px;font-size:0.66rem;color:#94a3b8">🚒 Response Teams</span>
    <span style="background:#0f1117;border:1px solid #2d3148;border-radius:4px;padding:3px 8px;font-size:0.66rem;color:#94a3b8">📱 Citizen Reports</span>
  </div>

</div>
""", unsafe_allow_html=True)

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
        <div class="fg-card-blue" style="margin-top:0.5rem">
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
            <div class="fg-card-blue" style="font-size:0.85rem;color:#e2e8f0">{answer}</div>
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
        <div class="fg-card-blue">
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
        <div class="fg-card" style="text-align:center;padding:2rem;color:#64748b;font-size:0.85rem">
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
        time_str = ts[11:19] if len(ts) >= 19 else ts

        icon = next((v for k, v in _step_icons.items() if k in step), "•")
        s_color = _status_colors.get(status, "#94a3b8")
        row_bg = "rgba(34,197,94,0.05)" if status == "COMPLETE" else \
                 "rgba(239,68,68,0.05)" if status == "ERROR" else \
                 "rgba(59,130,246,0.04)"

        rows_html += f"""
        <div style="display:grid;grid-template-columns:80px 140px 100px 1fr;gap:0.5rem;
                    padding:0.4rem 0.7rem;border-bottom:1px solid #1e2440;
                    font-size:0.72rem;align-items:center;background:{row_bg}">
            <div style="color:#475569;font-family:monospace">{time_str}</div>
            <div style="color:#e2e8f0;font-weight:600">{icon} {step[:16]}</div>
            <div>
                <span style="background:rgba({int(s_color[1:3],16) if len(s_color)==7 else 59},
                             {int(s_color[3:5],16) if len(s_color)==7 else 130},
                             {int(s_color[5:7],16) if len(s_color)==7 else 246},0.15);
                             border:1px solid {s_color}40;color:{s_color};
                             padding:1px 6px;border-radius:3px;font-size:0.65rem;font-weight:700">
                    {status}
                </span>
            </div>
            <div style="color:#64748b;overflow:hidden;text-overflow:ellipsis;white-space:nowrap"
                 title="{details}">{details[:90]}</div>
        </div>
        """

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
