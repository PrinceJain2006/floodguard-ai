"""
FloodGuard AI — Main Streamlit Application Entry Point
Landing page and navigation hub.
"""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import streamlit as st
from frontend.ui_utils import apply_global_css

st.set_page_config(
    page_title="FloodGuard AI",
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

# ──────────────────────────────────────────────
# Landing page
# ──────────────────────────────────────────────
st.markdown("""
<div style="text-align:center;padding:3rem 1rem 2rem">
    <div style="font-size:4rem;margin-bottom:0.5rem">🌊</div>
    <h1 style="font-size:3rem;font-weight:800;color:#e2e8f0;margin:0;
               background:linear-gradient(135deg,#3b82f6,#7c3aed);
               -webkit-background-clip:text;-webkit-text-fill-color:transparent">
        FLOODGUARD AI
    </h1>
    <p style="font-size:1.2rem;color:#94a3b8;margin:0.75rem 0 0.5rem;max-width:700px;margin-left:auto;margin-right:auto">
        AI-Powered Urban Flood Emergency Command Center — Predictive · Agentic · Multilingual
    </p>
    <p style="font-size:0.9rem;color:#64748b;margin-bottom:2rem">
        Ahmedabad &amp; Surat, Gujarat, India &nbsp;|&nbsp;
        <span style="background:#7c3aed;color:white;padding:2px 8px;border-radius:4px;font-size:0.8rem;font-weight:600">DEMO MODE</span>
        &nbsp; Synthetic data — not real government data
    </p>
</div>
""", unsafe_allow_html=True)

# ──────────────────────────────────────────────
# Portal buttons — Row 1
# ──────────────────────────────────────────────
col1, col2, col3, col4 = st.columns(4)

def portal_card(col, emoji, title, subtitle, page, color):
    with col:
        st.markdown(f"""
        <div style="background:#1a1d27;border:1px solid #2d3148;border-top:3px solid {color};
                    border-radius:10px;padding:1.5rem;text-align:center;min-height:160px;
                    display:flex;flex-direction:column;align-items:center;justify-content:center">
            <div style="font-size:2.5rem;margin-bottom:0.5rem">{emoji}</div>
            <div style="font-size:1rem;font-weight:700;color:#e2e8f0;margin-bottom:0.4rem">{title}</div>
            <div style="font-size:0.8rem;color:#94a3b8">{subtitle}</div>
        </div>
        """, unsafe_allow_html=True)
        if st.button(f"Open {title}", key=f"btn_{page}", use_container_width=True):
            st.switch_page(f"pages/{page}.py")

portal_card(col1, "📱", "Citizen Portal",
            "Report floods · Track status · Get alerts",
            "1_citizen_portal", "#22c55e")
portal_card(col2, "🖥️", "Command Center",
            "Live map · Incidents · Risk zones · Response",
            "2_command_center", "#3b82f6")
portal_card(col3, "🤖", "Agent Monitor",
            "Watch agents work · WHY explanations · NL query",
            "3_agent_monitor", "#7c3aed")
portal_card(col4, "📊", "Analytics",
            "Trends · Impact metrics · Damage reports",
            "4_analytics", "#f97316")

st.markdown("<br>", unsafe_allow_html=True)

# ──────────────────────────────────────────────
# Portal buttons — Row 2 (new advanced features)
# ──────────────────────────────────────────────
col5, col6, col7, col8 = st.columns(4)

portal_card(col5, "🚨", "Emergency War Room",
            "Live command · Chief Agent · Approvals · Resources",
            "5_war_room", "#ef4444")
portal_card(col6, "🌧️", "What-If Simulator",
            "Flood simulation · Forecast timeline · Resources",
            "6_simulator", "#14b8a6")
portal_card(col7, "🔄", "Learning Loop",
            "Prediction vs outcome · Accuracy tracking",
            "7_learning_loop", "#a855f7")
# Placeholder for future expansion
col8.markdown("""
<div style="background:#0f1117;border:1px dashed #2d3148;border-radius:10px;
            padding:1.5rem;text-align:center;min-height:160px;
            display:flex;flex-direction:column;align-items:center;justify-content:center;
            opacity:0.5">
    <div style="font-size:2.5rem;margin-bottom:0.5rem">🔧</div>
    <div style="font-size:0.9rem;font-weight:600;color:#64748b;margin-bottom:0.4rem">More Features</div>
    <div style="font-size:0.75rem;color:#475569">Coming in next release</div>
</div>
""", unsafe_allow_html=True)

st.markdown("<br>", unsafe_allow_html=True)

# ──────────────────────────────────────────────
# System overview strip
# ──────────────────────────────────────────────
st.markdown("---")
st.markdown("""
<h3 style="color:#e2e8f0;font-size:1rem;font-weight:700;margin-bottom:1rem;text-transform:uppercase;
           letter-spacing:0.05em">🤖 MULTI-AGENT SYSTEM OVERVIEW</h3>
""", unsafe_allow_html=True)

cols = st.columns(7)
agents = [
    ("🌊", "Flood Risk Agent",     "Predicts risk scores per area using ML + rainfall data"),
    ("🔧", "Drainage Agent",       "Prioritizes drain maintenance based on blockage & capacity"),
    ("📱", "Citizen Report Agent", "Processes multilingual reports (EN/HI/GU) with AI classification"),
    ("⚡", "Response Coord Agent", "Generates prioritized incident response plans"),
    ("🎯", "Chief Response Agent", "Combines all agents into unified emergency action plan"),
    ("🔍", "Damage Agent",         "Assesses post-flood infrastructure damage"),
    ("🔄", "Learning Loop",        "Tracks Prediction → Incident → Response → Outcome cycles"),
]
for col, (emoji, name, desc) in zip(cols, agents):
    with col:
        st.markdown(f"""
        <div style="background:#1a1d27;border:1px solid #2d3148;border-radius:8px;
                    padding:0.8rem;text-align:center;min-height:120px">
            <div style="font-size:1.8rem">{emoji}</div>
            <div style="font-size:0.78rem;font-weight:700;color:#e2e8f0;margin:0.3rem 0">{name}</div>
            <div style="font-size:0.7rem;color:#64748b">{desc}</div>
        </div>
        """, unsafe_allow_html=True)

st.markdown("---")
# IBM Granite
st.markdown("""
<div style="background:rgba(59,130,246,0.1);border:1px solid #3b82f6;border-radius:8px;
            padding:0.8rem 1.2rem;display:flex;align-items:center;gap:1rem">
    <div style="font-size:1.5rem">🧠</div>
    <div>
        <div style="font-weight:700;color:#e2e8f0;font-size:0.9rem">IBM Granite Integration</div>
        <div style="color:#94a3b8;font-size:0.8rem">
            Using <strong>ibm/granite-3-8b-instruct</strong> via WatsonX for multilingual report understanding, 
            incident classification, situation reports, explanation generation, and natural language queries.
            Configure <code>WATSONX_API_KEY</code> in <code>.env</code> to enable live Granite responses.
        </div>
    </div>
</div>
""", unsafe_allow_html=True)

st.markdown("<br>", unsafe_allow_html=True)
st.markdown("""
<div style="text-align:center;color:#475569;font-size:0.75rem;padding-bottom:1rem">
    ⚠️ FloodGuard AI uses <strong>synthetic demo data</strong> for Ahmedabad &amp; Surat. 
    It does not represent real government operational data or guarantee flood prediction accuracy.<br>
    AI recommendations require authorized human verification before implementation.
</div>
""", unsafe_allow_html=True)
