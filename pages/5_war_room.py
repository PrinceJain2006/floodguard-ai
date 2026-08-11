"""
FloodGuard AI — Page 5: Emergency War Room
Unified command view: risk, incidents, agents, resources, recommendations and approvals.
All data is DEMO/SIMULATED.
"""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import streamlit as st
import plotly.graph_objects as go
from datetime import datetime
from frontend.ui_utils import (
    apply_global_css, header, metric_card, ai_disclaimer, demo_badge,
    simulated_badge, section_header, COLORS, risk_badge
)
from agents.orchestrator import get_orchestrator, SCENARIOS
from agents.granite_service import explain_why_zone_risky
from frontend.map_component import build_flood_map
from streamlit_folium import st_folium

st.set_page_config(
    page_title="War Room — FloodGuard AI",
    page_icon="🚨",
    layout="wide",
    initial_sidebar_state="collapsed",
)
apply_global_css()

# ──────────────────────────────────────────────
# Session state
# ──────────────────────────────────────────────
if "war_approved" not in st.session_state:
    st.session_state.war_approved = set()
if "war_rejected" not in st.session_state:
    st.session_state.war_rejected = set()
if "war_scenario" not in st.session_state:
    st.session_state.war_scenario = "NORMAL"
if "why_cache" not in st.session_state:
    st.session_state.why_cache = {}

@st.cache_resource
def get_orch():
    orch = get_orchestrator()
    if not orch.current_state:
        orch.run_pipeline("NORMAL")
    return orch

orch = get_orch()

# ──────────────────────────────────────────────
# Header strip
# ──────────────────────────────────────────────
state = orch.current_state or {}
scenario = state.get("scenario", "NORMAL")

# Blinking red dot for CRITICAL/EXTREME scenarios
dot_color = "#ef4444" if scenario in ("EXTREME", "EMERGENCY") else "#f97316" if scenario == "HEAVY" else "#22c55e"
dot_anim = "animation:blink 1s infinite;" if scenario in ("EXTREME", "EMERGENCY") else ""

st.markdown(f"""
<style>
@keyframes blink {{ 0%,100% {{opacity:1}} 50% {{opacity:0.2}} }}
.war-room-header {{
    background: linear-gradient(135deg, #0d0d1a 0%, #1a0f2e 100%);
    border: 1px solid #ef4444;
    border-radius: 10px;
    padding: 1rem 1.5rem;
    margin-bottom: 1rem;
    display: flex;
    align-items: center;
    gap: 1.5rem;
}}
</style>
<div class="war-room-header">
    <div style="font-size:2.5rem">🚨</div>
    <div style="flex:1">
        <div style="font-size:1.5rem;font-weight:800;color:#e2e8f0;letter-spacing:0.05em">
            EMERGENCY WAR ROOM
        </div>
        <div style="font-size:0.85rem;color:#94a3b8">
            AI-Powered Urban Flood Emergency Command Center &nbsp;|&nbsp; 
            Scenario: <strong style="color:#f97316">{SCENARIOS.get(scenario,{}).get('emoji','')} {SCENARIOS.get(scenario,{}).get('label','')}</strong> &nbsp;|&nbsp;
            City: {state.get('city','All')} &nbsp;|&nbsp;
            Last update: {state.get('last_updated','')[:19]}
        </div>
    </div>
    <div style="text-align:right">
        <div style="display:flex;align-items:center;gap:0.5rem;justify-content:flex-end">
            <div style="width:12px;height:12px;border-radius:50%;background:{dot_color};{dot_anim}"></div>
            <span style="color:{dot_color};font-weight:700;font-size:0.9rem">
                {'🚨 EMERGENCY ACTIVE' if scenario in ('EXTREME','EMERGENCY') else '⚠️ ELEVATED ALERT' if scenario == 'HEAVY' else '✅ MONITORING'}
            </span>
        </div>
        <div style="font-size:0.7rem;color:#475569;margin-top:0.3rem">{demo_badge()} DEMO/SIMULATED DATA</div>
    </div>
</div>
""", unsafe_allow_html=True)

# Scenario selector (inline)
sc_cols = st.columns(7)
with sc_cols[0]:
    st.markdown('<div style="font-size:0.8rem;color:#94a3b8;padding-top:0.5rem">Scenario:</div>', unsafe_allow_html=True)
for i, (sc_id, sc_info) in enumerate(SCENARIOS.items()):
    with sc_cols[i+1]:
        if st.button(
            f"{sc_info['emoji']} {sc_info['label']}",
            key=f"war_sc_{sc_id}",
            type="primary" if orch.current_scenario == sc_id else "secondary",
            use_container_width=True,
        ):
            with st.spinner(f"Activating {sc_info['label']}..."):
                orch.run_pipeline(scenario=sc_id, city="All")
                st.session_state.war_scenario = sc_id
                st.session_state.why_cache = {}
            st.rerun()

st.markdown("<br>", unsafe_allow_html=True)

# ──────────────────────────────────────────────
# Re-fetch state after possible scenario change
# ──────────────────────────────────────────────
state = orch.current_state or {}
predictions = state.get("risk_predictions", [])
action_plan = state.get("action_plan", {})
resource_recs = state.get("resource_recommendations", [])
response_plan = state.get("response_plan", {})
drain_analysis = state.get("drain_analysis", {})
report_analysis = state.get("report_analysis", {})
teams = state.get("teams", [])
alerts = state.get("alerts", [])
raw_drains = state.get("raw_drains", [])
raw_reports = state.get("raw_reports", [])

# ──────────────────────────────────────────────
# KPI strip
# ──────────────────────────────────────────────
critical = sum(1 for p in predictions if p["risk_level"] == "CRITICAL")
high     = sum(1 for p in predictions if p["risk_level"] == "HIGH")
total_actions = action_plan.get("total_actions", 0)
needs_approval = action_plan.get("approval_needed", 0)
open_reports = report_analysis.get("open_reports", 0)
available_teams = sum(1 for t in teams if t.get("status") == "AVAILABLE")
approved_count = len(st.session_state.war_approved)

k1,k2,k3,k4,k5,k6,k7,k8 = st.columns(8)
with k1: metric_card("Critical Zones",   str(critical),       color="#ef4444", icon="🔴")
with k2: metric_card("High Risk Zones",  str(high),           color="#f97316", icon="🟠")
with k3: metric_card("AI Actions",       str(total_actions),  color="#7c3aed", icon="⚡")
with k4: metric_card("Pending Approval", str(max(0, needs_approval - approved_count)), color="#ef4444", icon="🔐")
with k5: metric_card("Open Reports",     str(open_reports),   color="#eab308", icon="📱")
with k6: metric_card("Teams Available",  str(available_teams),color="#22c55e", icon="🚒")
with k7: metric_card("Actions Approved", str(approved_count), color="#22c55e", icon="✅")
with k8: metric_card("Active Alerts",    str(len(alerts)),    color="#ef4444", icon="🔔")

st.markdown("<br>", unsafe_allow_html=True)

# ──────────────────────────────────────────────
# Main grid: 3-column layout
# ──────────────────────────────────────────────
col_left, col_mid, col_right = st.columns([1.2, 1.4, 1])

# ── LEFT: Live Map ───────────────────────────
with col_left:
    section_header("DIGITAL TWIN MAP", demo_badge())
    m = build_flood_map(
        risk_predictions=predictions,
        drain_data=raw_drains[:60],
        report_data=raw_reports[:60],
        team_data=teams,
        city=state.get("city", "All"),
        zoom=10,
    )
    st_folium(m, width="100%", height=420, key="war_map")

    # Active alerts
    if alerts:
        st.markdown("---")
        section_header("🔔 ACTIVE ALERTS", simulated_badge())
        for alert in alerts[:3]:
            level = alert.get("alert_level", "INFO")
            cls = {"CRITICAL": "alert-critical", "HIGH": "alert-high"}.get(level, "alert-warning")
            st.markdown(f"""
            <div class="{cls}" style="font-size:0.8rem;margin-bottom:0.3rem">
                <strong>{alert.get('title','')}</strong><br>
                <span style="color:#cbd5e1;font-size:0.75rem">{alert.get('message','')[:120]}</span>
            </div>
            """, unsafe_allow_html=True)

# ── MIDDLE: Chief Response Action Plan ───────
with col_mid:
    section_header("🤖 CHIEF RESPONSE AGENT — ACTION PLAN", demo_badge())
    ai_disclaimer()

    if action_plan:
        exec_summary = action_plan.get("executive_summary", "")
        st.markdown(f"""
        <div style="background:rgba(124,58,237,0.1);border:1px solid #7c3aed;border-radius:8px;
                    padding:0.6rem 0.9rem;font-size:0.8rem;color:#a78bfa;margin-bottom:0.75rem">
            🧠 {exec_summary}
        </div>
        """, unsafe_allow_html=True)

        actions = action_plan.get("actions", [])
        for action in actions[:8]:
            aid = action["action_id"]
            priority = action["priority"]
            p_colors = {"CRITICAL": "#ef4444", "HIGH": "#f97316", "MEDIUM": "#eab308", "LOW": "#22c55e"}
            p_color = p_colors.get(priority, "#94a3b8")
            approved = aid in st.session_state.war_approved
            rejected = aid in st.session_state.war_rejected

            if approved:
                status_html = '<span style="background:#22c55e;color:white;padding:1px 6px;border-radius:6px;font-size:0.65rem">✅ APPROVED</span>'
                border_color = "#22c55e"
            elif rejected:
                status_html = '<span style="background:#ef4444;color:white;padding:1px 6px;border-radius:6px;font-size:0.65rem">❌ REJECTED</span>'
                border_color = "#475569"
            else:
                status_html = '<span style="background:#eab308;color:#1a1d27;padding:1px 6px;border-radius:6px;font-size:0.65rem">⏳ PENDING</span>'
                border_color = p_color

            with st.expander(
                f"{'🔴' if priority=='CRITICAL' else '🟠' if priority=='HIGH' else '🟡'} "
                f"{aid} — {action['title'][:60]}",
                expanded=(priority == "CRITICAL" and not approved and not rejected),
            ):
                cat_col, stat_col, src_col = st.columns([1.2, 1, 1])
                with cat_col: st.markdown(f'<span style="background:{p_color};color:white;padding:2px 8px;border-radius:6px;font-size:0.7rem;font-weight:600">{priority}</span>', unsafe_allow_html=True)
                with stat_col: st.markdown(status_html, unsafe_allow_html=True)
                with src_col: st.markdown(f'<span style="font-size:0.7rem;color:#64748b">via {action["source_agent"]}</span>', unsafe_allow_html=True)

                st.markdown(f'<div style="font-size:0.82rem;color:#e2e8f0;margin:0.4rem 0">{action["description"]}</div>', unsafe_allow_html=True)

                r_html = " ".join(
                    f'<span style="background:#1e293b;border:1px solid #2d3148;border-radius:4px;padding:1px 6px;font-size:0.68rem;color:#94a3b8">{r.replace("_"," ").title()}</span>'
                    for r in action.get("resources_needed", [])
                )
                st.markdown(f'<div style="margin:0.3rem 0">Resources: {r_html}</div>', unsafe_allow_html=True)
                st.markdown(f'<div style="font-size:0.72rem;color:#64748b">⏱ Est. {action["estimated_time_min"]} min | Confidence: {action["confidence"]:.0%}</div>', unsafe_allow_html=True)

                if action.get("requires_human_approval") and not approved and not rejected:
                    st.markdown(f"""
                    <div style="background:rgba(239,68,68,0.1);border:1px solid #ef4444;border-radius:6px;
                                padding:0.4rem 0.7rem;font-size:0.75rem;color:#fca5a5;margin:0.4rem 0">
                        🔐 <strong>HUMAN APPROVAL REQUIRED</strong> — {action.get('approval_reason','')}
                    </div>
                    """, unsafe_allow_html=True)
                    c1, c2 = st.columns(2)
                    with c1:
                        if st.button("✅ Approve", key=f"war_app_{aid}", type="primary"):
                            st.session_state.war_approved.add(aid)
                            st.rerun()
                    with c2:
                        if st.button("❌ Reject", key=f"war_rej_{aid}"):
                            st.session_state.war_rejected.add(aid)
                            st.rerun()
                elif not action.get("requires_human_approval") and not approved:
                    if st.button("✅ Mark Executed", key=f"war_exec_{aid}", type="secondary"):
                        st.session_state.war_approved.add(aid)
                        st.rerun()
    else:
        st.info("Run a scenario to generate the Chief Response Agent action plan.")

# ── RIGHT: Resource Status + Agents ──────────
with col_right:
    # Resource recommendations
    section_header("💼 RESOURCE RECOMMENDATIONS", simulated_badge())
    if resource_recs:
        for rec in resource_recs[:5]:
            level = rec["risk_level"]
            p_color = COLORS.get(level, "#94a3b8")
            assigned = rec.get("assigned_resources", [])
            res_html = ""
            for r in assigned:
                t_color = "#22c55e" if r["status"] == "AVAILABLE" else "#f97316"
                res_html += f'<div style="font-size:0.72rem;color:{t_color};padding:1px 0">💼 {r["team_name"]} (~{r["estimated_travel_min"]}min)</div>'
            st.markdown(f"""
            <div style="background:#1a1d27;border:1px solid {p_color};border-radius:8px;
                        padding:0.5rem 0.75rem;margin-bottom:0.4rem">
                <div style="display:flex;justify-content:space-between;align-items:center">
                    <div style="font-size:0.8rem;font-weight:700;color:#e2e8f0">{rec['zone']}</div>
                    <span style="background:{p_color};color:white;padding:1px 5px;border-radius:4px;font-size:0.65rem;font-weight:600">{level}</span>
                </div>
                <div style="font-size:0.7rem;color:#94a3b8;margin:0.2rem 0">{rec['rationale']}</div>
                {res_html}
            </div>
            """, unsafe_allow_html=True)
    else:
        st.info("No resource recommendations yet.")

    st.markdown("---")
    # Agent activity panel
    section_header("🤖 AGENT ACTIVITY", demo_badge())
    agent_statuses = orch.get_agent_statuses()
    agent_icons = {
        "Flood Risk Agent": "🌊", "Drainage Agent": "🔧",
        "Citizen Report Agent": "📱", "Response Coordination Agent": "⚡",
        "Damage Assessment Agent": "🔍", "Chief Response Agent": "🎯", "IBM Granite": "🧠",
    }
    for agent in agent_statuses:
        name = agent.get("agent", "")
        status = agent.get("status", "UNKNOWN")
        icon = agent_icons.get(name, "🤖")
        s_colors = {"ACTIVE": "#22c55e", "COMPLETE": "#22c55e", "FALLBACK": "#f97316", "INACTIVE": "#94a3b8"}
        s_color = s_colors.get(status, "#94a3b8")
        last_act = agent.get("recent_activity", [])
        last_msg = last_act[-1] if last_act else "No recent activity"
        st.markdown(f"""
        <div style="display:flex;align-items:center;gap:0.5rem;padding:0.3rem 0;
                    border-bottom:1px solid rgba(45,49,72,0.5)">
            <span style="font-size:1rem">{icon}</span>
            <div style="flex:1;min-width:0">
                <div style="font-size:0.78rem;font-weight:600;color:#e2e8f0">{name}</div>
                <div style="font-size:0.68rem;color:#64748b;white-space:nowrap;overflow:hidden;text-overflow:ellipsis">{str(last_msg)[:55]}</div>
            </div>
            <span style="background:{s_color};color:white;padding:1px 5px;border-radius:4px;font-size:0.62rem;font-weight:600;white-space:nowrap">{status}</span>
        </div>
        """, unsafe_allow_html=True)

st.markdown("<br>", unsafe_allow_html=True)
st.markdown("---")

# ──────────────────────────────────────────────
# Bottom row: IBM Granite WHY + Response Teams + Incidents
# ──────────────────────────────────────────────
bot_col1, bot_col2, bot_col3 = st.columns([1, 1, 1])

with bot_col1:
    section_header("🧠 IBM GRANITE WHY EXPLANATION", simulated_badge())
    st.markdown("""
    <div style="font-size:0.75rem;color:#94a3b8;margin-bottom:0.5rem">
        Select a risk zone to get an AI explanation of why it's high-risk.<br>
        Uses only available project data — never invents real sensor/govt values.
    </div>
    """, unsafe_allow_html=True)

    zone_options = [f"{p['area']}, {p['city']} — {p['risk_level']} ({p['risk_score']:.0f})"
                    for p in sorted(predictions, key=lambda x: x["risk_score"], reverse=True)[:12]]
    if zone_options:
        selected_zone_str = st.selectbox("Select Zone:", zone_options, key="why_zone_war")
        if st.button("🧠 Explain WHY", key="why_btn_war", type="primary"):
            idx = zone_options.index(selected_zone_str)
            zone_pred = sorted(predictions, key=lambda x: x["risk_score"], reverse=True)[idx]
            cache_key = f"{zone_pred['area']}_{zone_pred['city']}_{scenario}"
            if cache_key not in st.session_state.why_cache:
                with st.spinner("IBM Granite analyzing risk factors..."):
                    explanation = explain_why_zone_risky(zone_pred)
                    st.session_state.why_cache[cache_key] = explanation
            st.markdown(f"""
            <div class="fg-card-blue" style="margin-top:0.5rem;font-size:0.82rem;line-height:1.6">
                <div style="font-size:0.7rem;color:#94a3b8;margin-bottom:0.3rem">🧠 IBM Granite WHY Analysis</div>
                <div style="color:#e2e8f0">{st.session_state.why_cache.get(cache_key,'')}</div>
                <div style="font-size:0.65rem;color:#475569;margin-top:0.4rem">
                    ⚙ Based on demo data only — not real sensor/government readings
                </div>
            </div>
            """, unsafe_allow_html=True)
    else:
        st.info("Run a scenario to load risk zones.")

with bot_col2:
    section_header("🚒 RESPONSE TEAMS STATUS", demo_badge())
    if teams:
        status_groups = {}
        for t in teams:
            s = t.get("status", "UNKNOWN")
            status_groups.setdefault(s, []).append(t)

        status_colors = {"AVAILABLE": "#22c55e", "DEPLOYED": "#f97316", "STANDBY": "#3b82f6", "OFF_DUTY": "#94a3b8"}
        for status, tlist in sorted(status_groups.items()):
            s_color = status_colors.get(status, "#94a3b8")
            st.markdown(f"""
            <div style="font-size:0.75rem;font-weight:700;color:{s_color};margin:0.4rem 0 0.2rem">
                {status} ({len(tlist)})
            </div>
            """, unsafe_allow_html=True)
            for t in tlist[:4]:
                t_type = t.get("team_type", "").replace("_", " ").title()
                st.markdown(f"""
                <div style="font-size:0.72rem;color:#94a3b8;padding:1px 0 1px 0.5rem;
                            border-left:2px solid {s_color}">
                    {t.get('name',t['team_id'])} — {t_type}, {t.get('city','')}
                </div>
                """, unsafe_allow_html=True)
    else:
        st.info("No team data available.")

with bot_col3:
    section_header("⚡ TOP ACTIVE INCIDENTS", demo_badge())
    incidents = response_plan.get("incidents", [])
    if incidents:
        for inc in sorted(incidents, key=lambda x: x.get("risk_score", 0), reverse=True)[:6]:
            level = inc.get("risk_level", "MEDIUM")
            p_color = COLORS.get(level, "#94a3b8")
            st.markdown(f"""
            <div style="background:#1a1d27;border-left:3px solid {p_color};border-radius:0 6px 6px 0;
                        padding:0.4rem 0.6rem;margin-bottom:0.3rem">
                <div style="font-size:0.78rem;font-weight:700;color:#e2e8f0">
                    {inc.get('area')}, {inc.get('city')}
                </div>
                <div style="font-size:0.7rem;color:#94a3b8">
                    Score: {inc.get('risk_score',0):.0f} | Rain: {inc.get('rainfall_1h',0):.0f} mm/hr |
                    <span style="color:{p_color}">{level}</span>
                </div>
                <div style="font-size:0.68rem;color:#64748b">
                    Reports: {inc.get('citizen_reports',0)} | Status: {inc.get('status','ACTIVE')}
                </div>
            </div>
            """, unsafe_allow_html=True)
    else:
        st.info("No active incidents.")

# ──────────────────────────────────────────────
# Footer
# ──────────────────────────────────────────────
st.markdown("---")
st.markdown(f"""
<div style="text-align:center;color:#475569;font-size:0.72rem;padding-bottom:1rem">
    FloodGuard AI — Emergency War Room | {demo_badge()} All data is DEMO/SIMULATED.<br>
    AI actions require authorized human verification. Not for real operational emergency use.
</div>
""", unsafe_allow_html=True)
