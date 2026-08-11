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
    simulated_badge, section_header, COLORS
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

# ──────────────────────────────────────────────
# Granite status
# ──────────────────────────────────────────────
g_status = granite_status()
g_available = g_status.get("available", False)
granite_color = "#22c55e" if g_available else "#f97316"
granite_label = "LIVE" if g_available else "FALLBACK MODE"

st.markdown(f"""
<div style="background:rgba(59,130,246,0.1);border:1px solid #3b82f6;border-radius:8px;
            padding:0.8rem 1.2rem;margin-bottom:1rem;display:flex;align-items:center;gap:1.5rem;flex-wrap:wrap">
    <div style="font-size:1.5rem">🧠</div>
    <div style="flex:1">
        <div style="font-weight:700;color:#e2e8f0">IBM Granite — {g_status.get('model','')}</div>
        <div style="font-size:0.8rem;color:#94a3b8">
            WatsonX API Key: {'✅ Configured' if g_status.get('api_key_configured') else '❌ Not configured (using fallback)'} &nbsp;|&nbsp;
            Project ID: {'✅ Configured' if g_status.get('project_configured') else '❌ Not configured'}
        </div>
    </div>
    <div>
        <span style="background:{granite_color};color:white;padding:4px 12px;border-radius:8px;
                     font-weight:700;font-size:0.8rem">{granite_label}</span>
    </div>
</div>
""", unsafe_allow_html=True)

if not g_available:
    st.markdown("""
    <div style="background:rgba(249,115,22,0.1);border:1px solid #f97316;border-radius:6px;
                padding:0.5rem 0.8rem;font-size:0.8rem;color:#fdba74;margin-bottom:1rem">
        ⚙️ <strong>Fallback Mode Active</strong> — Set <code>WATSONX_API_KEY</code> and <code>WATSONX_PROJECT_ID</code> 
        in your <code>.env</code> file to enable live IBM Granite responses. 
        Rule-based responses are being used for all AI features.
    </div>
    """, unsafe_allow_html=True)

# ──────────────────────────────────────────────
# Agent Activity Panel (Feature 8 — enhanced)
# ──────────────────────────────────────────────
section_header("AGENT ACTIVITY PANEL", demo_badge())
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

# KPI strip for agent panel
total_agents = len(agent_statuses)
active_agents = sum(1 for a in agent_statuses if a.get("status") in ("ACTIVE", "COMPLETE", "FALLBACK"))
pipeline_runs = len(orch.pipeline_log)

pa1, pa2, pa3, pa4 = st.columns(4)
with pa1: metric_card("Total Agents",    str(total_agents),  color="#3b82f6", icon="🤖")
with pa2: metric_card("Active/Ready",    str(active_agents), color="#22c55e", icon="✅")
with pa3: metric_card("Pipeline Runs",   str(pipeline_runs), color="#7c3aed", icon="▶️")
with pa4: metric_card("Last Run",        state.get("last_updated","N/A")[:16], color="#3b82f6", icon="🕐")

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
            g = granite_status()
            output_summary = "LIVE (WatsonX)" if g["available"] else "Fallback mode — configure .env"

        st.markdown(f"""
        <style>@keyframes pulse {{0%,100%{{opacity:1}}50%{{opacity:0.5}}}}</style>
        <div class="fg-card" style="min-height:180px">
            <div style="display:flex;align-items:center;gap:0.6rem;margin-bottom:0.5rem">
                <span style="font-size:1.5rem">{icon}</span>
                <div style="flex:1;min-width:0">
                    <div style="font-weight:700;color:#e2e8f0;font-size:0.88rem">{name}</div>
                    <div style="font-size:0.68rem;color:#64748b">{desc}</div>
                </div>
                <span style="background:{s_color};color:white;padding:2px 7px;
                      border-radius:6px;font-size:0.68rem;font-weight:600;white-space:nowrap;{status_dot_anim}">{status}</span>
            </div>
            <div style="background:#0f1117;border-radius:6px;padding:0.4rem 0.5rem;margin-bottom:0.4rem;font-size:0.7rem;color:#94a3b8;min-height:24px">
                📊 {output_summary if output_summary else "Awaiting pipeline run"}
            </div>
            <div style="font-size:0.68rem;color:#475569;margin-bottom:0.3rem">
                Last run: {str(last_run)[:19]}
            </div>
            <div style="border-top:1px solid #2d3148;padding-top:0.35rem">
                {activities_html}
            </div>
        </div>
        """, unsafe_allow_html=True)

# ──────────────────────────────────────────────
# Pipeline execution log
# ──────────────────────────────────────────────
st.markdown("<br>", unsafe_allow_html=True)
section_header("PIPELINE EXECUTION LOG", demo_badge())

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
# Architecture diagram
# ──────────────────────────────────────────────
st.markdown("<br>", unsafe_allow_html=True)
section_header("AGENT ORCHESTRATION ARCHITECTURE")

st.markdown("""
<div style="background:#1a1d27;border:1px solid #2d3148;border-radius:10px;padding:1.5rem;overflow-x:auto">
<pre style="color:#94a3b8;font-size:0.78rem;line-height:1.8;margin:0">
┌─────────────────────────────────────────────────────────────────────────┐
│                        FLOODGUARD AI — AGENT PIPELINE                   │
├─────────────────────────────────────────────────────────────────────────┤
│                                                                          │
│  DATA SOURCES                                                            │
│  ├── Rainfall Records (1h/3h/6h/24h) ─── [DEMO/SYNTHETIC]              │
│  ├── Drainage Infrastructure Database                                    │
│  ├── Historical Flood Incidents                                          │
│  ├── Citizen Reports (EN/HI/GU)                                         │
│  └── Response Team Status                                                │
│                          ↓                                               │
│  ┌──────────────────────────────────────────────────────────┐           │
│  │                   AGENT ORCHESTRATOR                      │           │
│  │                                                          │           │
│  │  ┌─────────────────┐    ┌──────────────────────┐        │           │
│  │  │ 🌊 Flood Risk   │    │ 🔧 Drainage Agent    │        │           │
│  │  │ Agent (ML+RF)   │    │ Maintenance Priority │        │           │
│  │  └────────┬────────┘    └──────────┬───────────┘        │           │
│  │           │                        │                     │           │
│  │  ┌────────┴────────┐    ┌──────────┴───────────┐        │           │
│  │  │ 📱 Citizen      │    │ ⚡ Response Coord.   │        │           │
│  │  │ Report Agent    │────│ Agent (Priority Queue│        │           │
│  │  └─────────────────┘    └──────────────────────┘        │           │
│  │                                   │                      │           │
│  │              ┌────────────────────┴──────────┐          │           │
│  │              │  🧠 IBM Granite (WatsonX)      │          │           │
│  │              │  Reasoning & Language Layer    │          │           │
│  │              │  - Incident classification     │          │           │
│  │              │  - Report generation           │          │           │
│  │              │  - NL explanations             │          │           │
│  │              └───────────────────────────────┘          │           │
│  └──────────────────────────────────────────────────────────┘           │
│                          ↓                                               │
│  RECOMMENDATIONS → HUMAN APPROVAL → ACTION LOGGED                       │
│                          ↓                                               │
│  DASHBOARD + ALERTS + SITUATION REPORT                                   │
└─────────────────────────────────────────────────────────────────────────┘
</pre>
</div>
""", unsafe_allow_html=True)

# ──────────────────────────────────────────────
# NL Query
# ──────────────────────────────────────────────
st.markdown("<br>", unsafe_allow_html=True)
section_header("🔍 NATURAL LANGUAGE COMMAND CENTER")
st.markdown("""
<div style="font-size:0.8rem;color:#94a3b8;margin-bottom:0.75rem">
    Query the system using natural language. Answers are grounded in demo data — not hallucinated.
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
                Grounded in demo data | Not real-time government data
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
section_header("🧠 IBM GRANITE WHY EXPLANATION", demo_badge())
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
                🧠 IBM Granite {'(Live)' if granite_status()['available'] else '(Fallback)'} |
                Based on demo data only — not real sensor/government readings
            </div>
        </div>
        """, unsafe_allow_html=True)
    else:
        st.markdown("""
        <div class="fg-card" style="text-align:center;padding:2rem;color:#64748b;font-size:0.85rem">
            Select a zone and click "Explain WHY" to see IBM Granite's risk explanation.
        </div>
        """, unsafe_allow_html=True)
