"""
FloodGuard AI — Main Streamlit Application Entry Point
AI Flood Command Center — Landing page and navigation hub.
"""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import streamlit as st
from datetime import datetime, timezone
from frontend.ui_utils import apply_global_css

st.set_page_config(
    page_title="FloodGuard AI — Command Center",
    page_icon="🌊",
    layout="wide",
    initial_sidebar_state="collapsed",
    menu_items={
        "Get Help": None,
        "Report a bug": None,
        "About": "FloodGuard AI — Agentic AI for Urban Flood Management",
    },
)

apply_global_css()

# ── Extra landing-page CSS ────────────────────────────────────────────────────
st.markdown("""
<style>
.cmd-hero {
    background: linear-gradient(135deg, #0a0f1e 0%, #0f1a2e 50%, #0a1020 100%);
    border: 1px solid #1e3a5f;
    border-radius: 12px;
    padding: 2.5rem 2rem 2rem;
    margin-bottom: 1.5rem;
    position: relative;
    overflow: hidden;
}
.cmd-hero::before {
    content: '';
    position: absolute; top: 0; left: 0; right: 0; height: 3px;
    background: linear-gradient(90deg, #ef4444, #f97316, #eab308, #22c55e, #3b82f6, #7c3aed);
}
.cmd-portal-card {
    background: #1a1d27;
    border: 1px solid #2d3148;
    border-radius: 10px;
    padding: 1.4rem 1rem;
    text-align: center;
    min-height: 150px;
    display: flex;
    flex-direction: column;
    align-items: center;
    justify-content: center;
    transition: border-color 0.2s;
}
.cmd-portal-card:hover { border-color: #3b82f6; }
.cmd-agent-chip {
    background: #0f1420;
    border: 1px solid #1e3a5f;
    border-radius: 8px;
    padding: 0.6rem 0.8rem;
    text-align: center;
}
.status-pulse {
    display: inline-block;
    width: 8px; height: 8px;
    border-radius: 50%;
    background: #22c55e;
    animation: pulse 2s infinite;
    margin-right: 5px;
}
@keyframes pulse {
    0%, 100% { opacity: 1; }
    50% { opacity: 0.4; }
}
</style>
""", unsafe_allow_html=True)

# ── Hero header ───────────────────────────────────────────────────────────────
now_str = datetime.now(timezone.utc).strftime("%d %b %Y · %H:%M UTC")

# Try to read live pipeline state for the status strip (best-effort, non-blocking)
try:
    from agents.orchestrator import get_orchestrator as _get_orch_hp
    from agents.evidence_fusion import get_audit_trail as _get_audit_hp
    _hp_orch = _get_orch_hp()
    _hp_state = _hp_orch.current_state or {}
    _hp_preds = _hp_state.get("risk_predictions", [])
    _hp_crit  = sum(1 for p in _hp_preds if p.get("risk_level") == "CRITICAL")
    _hp_high  = sum(1 for p in _hp_preds if p.get("risk_level") == "HIGH")
    _hp_scen  = _hp_state.get("scenario", "NORMAL")
    _hp_live  = _hp_state.get("live_weather_status", {}).get("is_live", False)
    _hp_gran  = _hp_state.get("granite_status", {}).get("available", False)
    _hp_audit = len(_get_audit_hp().get_all())
    _hp_ready = bool(_hp_preds)
except Exception:
    _hp_crit = _hp_high = _hp_scen = _hp_live = _hp_gran = _hp_audit = 0
    _hp_ready = False

st.markdown(f"""
<div class="cmd-hero">
  <div style="display:flex;align-items:center;justify-content:space-between;flex-wrap:wrap;gap:1rem">
    <div>
      <div style="display:flex;align-items:center;gap:0.75rem;margin-bottom:0.5rem">
        <span style="font-size:2.8rem">🌊</span>
        <div>
          <div style="font-size:2rem;font-weight:800;letter-spacing:-0.02em;
                      background:linear-gradient(135deg,#3b82f6,#7c3aed);
                      -webkit-background-clip:text;-webkit-text-fill-color:transparent;
                      line-height:1.1">FLOODGUARD AI</div>
          <div style="font-size:0.85rem;color:#64748b;letter-spacing:0.08em;font-weight:600">
            AI FLOOD COMMAND CENTER — AHMEDABAD &amp; SURAT, GUJARAT
          </div>
        </div>
      </div>
      <div style="font-size:0.9rem;color:#94a3b8;max-width:620px">
        Agentic AI system combining ML flood-risk prediction, IBM Granite reasoning,
        citizen intelligence and drainage analytics for urban flood emergency management.
      </div>
    </div>
    <div style="text-align:right">
      <div style="font-size:0.7rem;color:#475569;margin-bottom:0.4rem">{now_str}</div>
      <div style="display:flex;flex-wrap:wrap;gap:5px;justify-content:flex-end;margin-bottom:0.3rem">
        <span style="background:#0f4c2a;color:#6ee7b7;font-size:0.68rem;padding:2px 8px;border-radius:4px;font-weight:700">🌐 HYBRID DATA</span>
        <span style="background:#0d2818;color:#4ade80;font-size:0.68rem;padding:2px 8px;border-radius:4px;font-weight:700">🤖 6 AGENTS ACTIVE</span>
        <span style="background:#1e3a5f;color:#93c5fd;font-size:0.68rem;padding:2px 8px;border-radius:4px;font-weight:700">🧠 IBM GRANITE</span>
        <span style="background:#1a1500;color:#fde68a;font-size:0.68rem;padding:2px 8px;border-radius:4px;font-weight:700">⚙ DEMO/SYNTHETIC</span>
      </div>
      {f'''<div style="display:flex;flex-wrap:wrap;gap:5px;justify-content:flex-end">
        <span style="background:rgba(239,68,68,0.15);color:#fca5a5;font-size:0.65rem;padding:1px 7px;border-radius:4px;font-weight:600">🔴 {_hp_crit} CRITICAL</span>
        <span style="background:rgba(249,115,22,0.12);color:#fdba74;font-size:0.65rem;padding:1px 7px;border-radius:4px;font-weight:600">🟠 {_hp_high} HIGH</span>
        <span style="background:{"#14532d" if _hp_live else "#3a2e00"};color:{"#bbf7d0" if _hp_live else "#fde68a"};font-size:0.65rem;padding:1px 7px;border-radius:4px;font-weight:600">{"🟢 Live" if _hp_live else "🟡 Demo"} Weather</span>
        <span style="background:{"#0d2818" if _hp_gran else "#1a1d27"};color:{"#6ee7b7" if _hp_gran else "#94a3b8"};font-size:0.65rem;padding:1px 7px;border-radius:4px;font-weight:600">{"🧠 Granite LIVE" if _hp_gran else "⚙ Granite FALLBACK"}</span>
        <span style="background:#1a1d27;color:#a78bfa;font-size:0.65rem;padding:1px 7px;border-radius:4px;font-weight:600">📋 {_hp_audit} audit entries</span>
      </div>''' if _hp_ready else ''}
    </div>
  </div>
</div>
""", unsafe_allow_html=True)

# ── Portal buttons — Row 1 ─────────────────────────────────────────────────────
def portal_card(col, emoji, title, subtitle, page, color, badge=""):
    with col:
        st.markdown(f"""
        <div style="background:#1a1d27;border:1px solid #2d3148;border-top:3px solid {color};
                    border-radius:10px;padding:1.4rem 1rem;text-align:center;min-height:155px;
                    display:flex;flex-direction:column;align-items:center;justify-content:center">
            <div style="font-size:2.2rem;margin-bottom:0.4rem">{emoji}</div>
            <div style="font-size:0.95rem;font-weight:700;color:#e2e8f0;margin-bottom:0.3rem">{title}</div>
            <div style="font-size:0.75rem;color:#64748b;margin-bottom:0.3rem">{subtitle}</div>
            {f'<div style="font-size:0.62rem;margin-top:0.2rem">{badge}</div>' if badge else ''}
        </div>
        """, unsafe_allow_html=True)
        if st.button(f"Open {title}", key=f"btn_{page}", use_container_width=True):
            st.switch_page(f"pages/{page}.py")

col1, col2, col3, col4 = st.columns(4)
portal_card(col1, "📱", "Citizen Portal",
            "Report floods · Track status · Multilingual AI",
            "1_citizen_portal", "#22c55e",
            '<span style="background:#14532d;color:#bbf7d0;padding:1px 5px;border-radius:3px;font-weight:700;font-size:0.65rem">EN · हिंदी · ગુ</span>')
portal_card(col2, "🖥️", "Command Center",
            "Live map · Risk zones · Incidents · Teams",
            "2_command_center", "#3b82f6",
            '<span style="background:#1e3a5f;color:#93c5fd;padding:1px 5px;border-radius:3px;font-weight:700;font-size:0.65rem">LIVE MAP</span>')
portal_card(col3, "🤖", "Agent Monitor",
            "Watch 6 agents · WHY explanations · NL query",
            "3_agent_monitor", "#7c3aed",
            '<span style="background:#2e1065;color:#c4b5fd;padding:1px 5px;border-radius:3px;font-weight:700;font-size:0.65rem">AGENT TRACE</span>')
portal_card(col4, "📊", "Analytics & ML",
            "Trends · Feature importance · Model evaluation",
            "4_analytics", "#f97316",
            '<span style="background:#3a1a00;color:#fdba74;padding:1px 5px;border-radius:3px;font-weight:700;font-size:0.65rem">RANDOM FOREST</span>')

st.markdown("<div style='height:0.75rem'></div>", unsafe_allow_html=True)

col5, col6, col7, col8 = st.columns(4)
portal_card(col5, "🚨", "Emergency War Room",
            "Chief Agent · Approvals · Resources · HITL",
            "5_war_room", "#ef4444",
            '<span style="background:#450a0a;color:#fca5a5;padding:1px 5px;border-radius:3px;font-weight:700;font-size:0.65rem">HUMAN APPROVAL</span>')
portal_card(col6, "🌧️", "Flood Simulator",
            "What-if · Scenario sliders · Before/After",
            "6_simulator", "#14b8a6",
            '<span style="background:#042f2e;color:#5eead4;padding:1px 5px;border-radius:3px;font-weight:700;font-size:0.65rem">DRAINAGE SIM</span>')
portal_card(col7, "🔄", "Learning Loop",
            "Prediction vs outcome · Accuracy tracking",
            "7_learning_loop", "#a855f7",
            '<span style="background:#2e1065;color:#d8b4fe;padding:1px 5px;border-radius:3px;font-weight:700;font-size:0.65rem">CLOSED LOOP</span>')
portal_card(col8, "🧭", "Decision Intelligence",
            "Evidence fusion · Priority · Why? · Audit",
            "8_decision_intelligence", "#14b8a6",
            '<span style="background:#042f2e;color:#5eead4;padding:1px 5px;border-radius:3px;font-weight:700;font-size:0.65rem">EXPLAINABILITY</span>')

st.markdown("<div style='height:0.5rem'></div>", unsafe_allow_html=True)
st.markdown("---")

# ── Multi-agent architecture strip ────────────────────────────────────────────
st.markdown("""
<div style="display:flex;align-items:center;gap:0.6rem;margin-bottom:0.8rem">
  <span style="font-size:0.9rem;font-weight:700;color:#e2e8f0;text-transform:uppercase;letter-spacing:0.06em">🤖 6-Agent AI Architecture</span>
  <span style="font-size:0.7rem;color:#475569">— Multi-agent pipeline with IBM Granite reasoning layer</span>
</div>
""", unsafe_allow_html=True)

# Agent flow visualization
flow_html = """
<div style="display:flex;align-items:center;flex-wrap:wrap;gap:4px;margin-bottom:1rem;font-size:0.72rem">
  <div style="background:#1e3a5f;color:#93c5fd;padding:4px 10px;border-radius:6px;font-weight:700;border:1px solid #3b82f6">📡 DATA SOURCES</div>
  <div style="color:#475569;font-size:1rem">→</div>
  <div style="background:#1a0a1a;color:#c4b5fd;padding:4px 10px;border-radius:6px;font-weight:700;border:1px solid #7c3aed">🌊 Flood Risk Agent</div>
  <div style="color:#475569;font-size:1rem">→</div>
  <div style="background:#1a0a1a;color:#c4b5fd;padding:4px 10px;border-radius:6px;font-weight:700;border:1px solid #7c3aed">🔧 Drainage Agent</div>
  <div style="color:#475569;font-size:1rem">→</div>
  <div style="background:#1a0a1a;color:#c4b5fd;padding:4px 10px;border-radius:6px;font-weight:700;border:1px solid #7c3aed">📱 Citizen Report Agent</div>
  <div style="color:#475569;font-size:1rem">→</div>
  <div style="background:#1a0a1a;color:#c4b5fd;padding:4px 10px;border-radius:6px;font-weight:700;border:1px solid #7c3aed">⚡ Response Agent</div>
  <div style="color:#475569;font-size:1rem">→</div>
  <div style="background:#0d2818;color:#bbf7d0;padding:4px 10px;border-radius:6px;font-weight:700;border:1px solid #22c55e">🧠 IBM GRANITE</div>
  <div style="color:#475569;font-size:1rem">→</div>
  <div style="background:#1a0a1a;color:#c4b5fd;padding:4px 10px;border-radius:6px;font-weight:700;border:1px solid #7c3aed">🎯 Chief Response Agent</div>
  <div style="color:#475569;font-size:1rem">→</div>
  <div style="background:#450a0a;color:#fca5a5;padding:4px 10px;border-radius:6px;font-weight:700;border:1px solid #ef4444">👤 HUMAN APPROVAL</div>
  <div style="color:#475569;font-size:1rem">→</div>
  <div style="background:#042f2e;color:#5eead4;padding:4px 10px;border-radius:6px;font-weight:700;border:1px solid #14b8a6">✅ RESPONSE</div>
</div>
"""
st.markdown(flow_html, unsafe_allow_html=True)

cols = st.columns(8)
agents = [
    ("🌊", "Flood Risk Agent",      "#7c3aed", "ML flood prediction per area"),
    ("🔧", "Drainage Agent",        "#3b82f6", "Drain maintenance prioritization"),
    ("📱", "Citizen Report Agent",  "#22c55e", "Multilingual NLP classification"),
    ("⚡", "Response Coord Agent",  "#f97316", "Incident response planning"),
    ("🎯", "Chief Response Agent",  "#ef4444", "Unified emergency action plan"),
    ("🔍", "Damage Agent",          "#eab308", "Post-flood damage assessment"),
    ("🔄", "Learning Loop",         "#a855f7", "Prediction→outcome feedback"),
    ("🧭", "Decision Intelligence", "#14b8a6", "Evidence fusion + explainability"),
]
for col, (emoji, name, color, desc) in zip(cols, agents):
    with col:
        st.markdown(f"""
        <div class="cmd-agent-chip" style="border-top:2px solid {color}">
            <div style="font-size:1.5rem;margin-bottom:0.2rem">{emoji}</div>
            <div style="font-size:0.72rem;font-weight:700;color:#e2e8f0;margin-bottom:0.2rem">{name}</div>
            <div style="font-size:0.64rem;color:#475569">{desc}</div>
        </div>
        """, unsafe_allow_html=True)

st.markdown("---")

# ── IBM Granite strip ─────────────────────────────────────────────────────────
st.markdown("""
<div style="background:linear-gradient(135deg,rgba(59,130,246,0.08),rgba(124,58,237,0.08));
            border:1px solid #3b82f6;border-radius:8px;padding:0.9rem 1.2rem;
            display:flex;align-items:center;gap:1rem;margin-bottom:1rem">
  <div style="font-size:1.8rem">🧠</div>
  <div style="flex:1">
    <div style="font-weight:700;color:#e2e8f0;font-size:0.9rem">IBM Granite Integration
      <span style="background:#14532d;color:#bbf7d0;font-size:0.65rem;padding:1px 6px;border-radius:3px;font-weight:700;margin-left:6px">ibm/granite-4-h-small</span>
    </div>
    <div style="color:#64748b;font-size:0.78rem;margin-top:0.2rem">
      Provides situation summaries · incident classification · multilingual report understanding ·
      recommendation explanations · natural language Q&amp;A via WatsonX API.
      Set <code style="background:#1a1d27;padding:1px 4px;border-radius:3px;color:#a78bfa">WATSONX_API_KEY</code> +
      <code style="background:#1a1d27;padding:1px 4px;border-radius:3px;color:#a78bfa">WATSONX_PROJECT_ID</code> to enable live mode.
      Falls back gracefully to rule-based responses with clear <strong style="color:#eab308">GRANITE FALLBACK</strong> labelling.
    </div>
  </div>
  <div style="text-align:right;font-size:0.7rem;color:#475569;white-space:nowrap">
    Configure in .env<br><strong style="color:#a78bfa">Fallback always active</strong>
  </div>
</div>
""", unsafe_allow_html=True)

# ── Data transparency footer ──────────────────────────────────────────────────
st.markdown("""
<div style="text-align:center;color:#475569;font-size:0.73rem;padding:0.5rem 0 1rem;
            border-top:1px solid #1e293b;margin-top:0.5rem">
  <strong style="color:#64748b">DATA TRANSPARENCY</strong> —
  FloodGuard AI combines live weather (Open-Meteo API), ML flood-risk predictions (Random Forest),
  IBM Granite AI reasoning, user-submitted citizen reports, and clearly labelled
  <strong style="color:#eab308">DEMO/SYNTHETIC</strong> infrastructure data.
  Drainage assets, response teams and baseline flood incidents are demo data.
  All AI recommendations require authorized human verification before real-world implementation.
  This application is a hackathon demonstration and does not constitute an official municipal emergency system.
</div>
""", unsafe_allow_html=True)
