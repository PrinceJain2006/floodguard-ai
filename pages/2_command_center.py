"""
FloodGuard AI — Page 2: Municipal Command Center
Main dashboard for operators — live map, risk zones, incidents, drainage, recommendations.
"""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import streamlit as st
import pandas as pd
import plotly.graph_objects as go
import plotly.express as px
from datetime import datetime
from frontend.ui_utils import (
    apply_global_css, header, metric_card, ai_disclaimer, card,
    risk_badge, demo_badge, simulated_badge, COLORS, RISK_EMOJI,
    risk_donut, rainfall_bar, risk_gauge, section_header
)
from agents.orchestrator import get_orchestrator, SCENARIOS
from frontend.map_component import build_flood_map
from streamlit_folium import st_folium

st.set_page_config(
    page_title="Command Center — FloodGuard AI",
    page_icon="🖥️",
    layout="wide",
    initial_sidebar_state="expanded",
)
apply_global_css()

# ──────────────────────────────────────────────
# Session state
# ──────────────────────────────────────────────
if "scenario" not in st.session_state:
    st.session_state.scenario = "NORMAL"
if "city_filter" not in st.session_state:
    st.session_state.city_filter = "All"
if "approved_recs" not in st.session_state:
    st.session_state.approved_recs = set()
if "rejected_recs" not in st.session_state:
    st.session_state.rejected_recs = set()
if "pipeline_running" not in st.session_state:
    st.session_state.pipeline_running = False


@st.cache_resource
def get_orch():
    orch = get_orchestrator()
    if not orch.current_state:
        orch.run_pipeline("NORMAL")
    return orch

orch = get_orch()

# ──────────────────────────────────────────────
# Sidebar — scenario controls
# ──────────────────────────────────────────────
with st.sidebar:
    st.markdown("## 🖥️ Command Center")
    st.markdown("---")
    st.markdown("### 🎬 Demo Scenarios")

    scenario_buttons = {
        "NORMAL":        ("🌦️", "Normal Rain",        "green"),
        "HEAVY":         ("🌧️", "Heavy Rainfall",     "orange"),
        "EXTREME":       ("⛈️", "Extreme Rainfall",   "red"),
        "CITIZEN_SURGE": ("📱", "Citizen Surge",      "blue"),
        "EMERGENCY":     ("🚨", "Emergency Response", "red"),
    }

    for sc_id, (emoji, sc_label, color) in scenario_buttons.items():
        if st.button(f"{emoji} {sc_label}", key=f"sc_{sc_id}", use_container_width=True,
                     type="primary" if st.session_state.scenario == sc_id else "secondary"):
            with st.spinner(f"Running {sc_label} scenario..."):
                orch.run_pipeline(scenario=sc_id, city=st.session_state.city_filter)
                st.session_state.scenario = sc_id
            st.rerun()

    st.markdown("---")
    city_filter = st.selectbox("🏙️ City Filter", ["All", "Ahmedabad", "Surat"],
                                key="city_select")
    if city_filter != st.session_state.city_filter:
        st.session_state.city_filter = city_filter
        with st.spinner("Updating..."):
            orch.run_pipeline(scenario=st.session_state.scenario, city=city_filter)
        st.rerun()

    st.markdown("---")
    st.markdown(f"""
    <div style="font-size:0.75rem;color:#94a3b8">
        <b>Current Scenario:</b> {SCENARIOS[st.session_state.scenario]['emoji']} {SCENARIOS[st.session_state.scenario]['label']}<br>
        <b>City:</b> {st.session_state.city_filter}<br>
        <b>Last updated:</b> {orch.current_state.get('last_updated','')[:16] if orch.current_state else 'N/A'}<br><br>
        <span style="background:#7c3aed;color:white;padding:2px 6px;border-radius:4px;font-size:0.7rem">DEMO DATA</span>
        Synthetic data only
    </div>
    """, unsafe_allow_html=True)

    st.markdown("---")
    role = st.selectbox("👤 Viewing as", ["Municipal Operator", "Administrator", "Observer"])

# ──────────────────────────────────────────────
# Get current state
# ──────────────────────────────────────────────
state = orch.current_state or {}
predictions = state.get("risk_predictions", [])
drain_analysis = state.get("drain_analysis", {})
report_analysis = state.get("report_analysis", {})
response_plan = state.get("response_plan", {})
alerts = state.get("alerts", [])
teams = state.get("teams", [])
rainfall_data = state.get("rainfall_data", [])
raw_drains = state.get("raw_drains", [])
raw_reports = state.get("raw_reports", [])

# ──────────────────────────────────────────────
# Header
# ──────────────────────────────────────────────
header("FloodGuard AI — Municipal Command Center",
       f"Scenario: {SCENARIOS[st.session_state.scenario]['emoji']} {SCENARIOS[st.session_state.scenario]['label']} | {st.session_state.city_filter}",
       "🖥️")

ai_disclaimer()

# ──────────────────────────────────────────────
# KPI Strip
# ──────────────────────────────────────────────
critical = sum(1 for p in predictions if p["risk_level"] == "CRITICAL")
high     = sum(1 for p in predictions if p["risk_level"] == "HIGH")
medium   = sum(1 for p in predictions if p["risk_level"] == "MEDIUM")
total_zones = len(predictions)

critical_drains = drain_analysis.get("priority_summary", {}).get("CRITICAL", 0)
open_reports = report_analysis.get("open_reports", 0)
incidents = response_plan.get("incidents", [])
available_teams = sum(1 for t in teams if t.get("status") == "AVAILABLE")
avg_rain = sum(r.get("rainfall_1h", 0) for r in rainfall_data) / max(len(rainfall_data), 1)

k1, k2, k3, k4, k5, k6, k7, k8 = st.columns(8)
with k1: metric_card("Critical Zones", str(critical),  color="#ef4444", icon="🔴")
with k2: metric_card("High Risk Zones", str(high),     color="#f97316", icon="🟠")
with k3: metric_card("Total Areas", str(total_zones),  color="#3b82f6", icon="📍")
with k4: metric_card("Avg Rainfall", f"{avg_rain:.0f}", delta="mm/hr", color="#3b82f6", icon="🌧️")
with k5: metric_card("Open Reports", str(open_reports), color="#eab308", icon="📱")
with k6: metric_card("Critical Drains", str(critical_drains), color="#f97316", icon="🔧")
with k7: metric_card("Active Incidents", str(len(incidents)), color="#7c3aed", icon="⚡")
with k8: metric_card("Teams Available", str(available_teams), color="#22c55e", icon="🚒")

st.markdown("<br>", unsafe_allow_html=True)

# ──────────────────────────────────────────────
# Tabs
# ──────────────────────────────────────────────
tab1, tab2, tab3, tab4, tab5, tab6, tab7 = st.tabs([
    "🗺️ Live Risk Map",
    "⚡ Incidents",
    "🤖 AI Recommendations",
    "🔧 Drainage",
    "📱 Citizen Reports",
    "🚒 Response Teams",
    "🌧️ Rainfall Data",
])

# ── Tab 1: Live Risk Map ──────────────────────
with tab1:
    col_map, col_detail = st.columns([1.6, 1])

    with col_map:
        section_header("LIVE FLOOD RISK MAP", demo_badge())
        m = build_flood_map(
            risk_predictions=predictions,
            drain_data=raw_drains[:80],
            report_data=raw_reports[:80],
            team_data=teams,
            city=st.session_state.city_filter,
        )
        map_data = st_folium(m, width="100%", height=500, key="cmd_map")

    with col_detail:
        section_header("RISK DISTRIBUTION")

        # Donut chart
        risk_counts = {
            "CRITICAL": critical, "HIGH": high, "MEDIUM": medium,
            "LOW": total_zones - critical - high - medium
        }
        if total_zones > 0:
            fig_donut = risk_donut(risk_counts)
            st.plotly_chart(fig_donut, use_container_width=True, config={"displayModeBar": False})

        st.markdown("---")
        section_header("CRITICAL AREAS")
        crit_areas = [p for p in predictions if p["risk_level"] == "CRITICAL"][:5]
        if crit_areas:
            for p in crit_areas:
                rf = p.get("input_features", {}).get("rainfall_1h", 0)
                st.markdown(f"""
                <div class="fg-card-danger" style="padding:0.6rem 0.8rem">
                    <div style="display:flex;justify-content:space-between;align-items:center">
                        <div style="font-weight:700;color:#e2e8f0;font-size:0.85rem">{p['area']}, {p['city']}</div>
                        <div style="background:#ef4444;color:white;padding:1px 6px;border-radius:8px;font-size:0.7rem;font-weight:600">CRITICAL</div>
                    </div>
                    <div style="font-size:0.75rem;color:#94a3b8;margin-top:0.2rem">
                        Score: {p['risk_score']:.0f}/100 &nbsp;|&nbsp; Rain: {rf:.0f} mm/hr &nbsp;|&nbsp; Conf: {p['confidence']:.0%}
                    </div>
                    <div style="font-size:0.72rem;color:#fca5a5;margin-top:0.2rem">{p['main_reasons'][0] if p.get('main_reasons') else ''}</div>
                </div>
                """, unsafe_allow_html=True)
        else:
            st.markdown('<div class="fg-card-success"><div style="color:#22c55e">✅ No critical risk areas currently.</div></div>', unsafe_allow_html=True)

        # Alerts
        if alerts:
            st.markdown("---")
            section_header("ACTIVE ALERTS", simulated_badge())
            for alert in alerts[:4]:
                level = alert.get("alert_level", "INFO")
                cls = {"CRITICAL": "alert-critical", "HIGH": "alert-high"}.get(level, "alert-info")
                st.markdown(f"""
                <div class="{cls}" style="font-size:0.8rem">
                    <b>{alert.get('title','')}</b><br>
                    <span style="color:#cbd5e1">{alert.get('message','')[:120]}</span>
                    <div style="font-size:0.68rem;color:#64748b;margin-top:0.2rem">⚙ SIMULATED</div>
                </div>
                """, unsafe_allow_html=True)

# ── Tab 2: Incidents ──────────────────────────
with tab2:
    section_header("ACTIVE INCIDENTS", demo_badge())
    if not incidents:
        st.info("No active incidents for current scenario.")
    else:
        for inc in incidents[:8]:
            risk_level = inc.get("risk_level", "MEDIUM")
            variant = {"CRITICAL": "danger", "HIGH": "warn", "MEDIUM": "blue"}.get(risk_level, "default")
            actions_html = ""
            for action in inc.get("recommended_actions", [])[:4]:
                req = "🔐 Requires Approval" if action.get("requires_approval") else "✅ Auto-authorized"
                p_color = "#ef4444" if action["priority"] == "CRITICAL" else "#f97316" if action["priority"] == "HIGH" else "#eab308"
                actions_html += f"""
                <div style="display:flex;gap:0.5rem;padding:0.3rem 0;border-bottom:1px solid rgba(255,255,255,0.05);font-size:0.8rem">
                    <span style="min-width:20px;color:#94a3b8">{action['index']}.</span>
                    <span style="color:#e2e8f0;flex:1">{action['action']}</span>
                    <span style="color:{p_color};white-space:nowrap;font-size:0.72rem">{req}</span>
                </div>
                """

            with st.expander(
                f"{'🔴' if risk_level=='CRITICAL' else '🟠' if risk_level=='HIGH' else '🟡'} "
                f"{inc['incident_id']} — {inc['area']}, {inc['city']} | {risk_level} | Rain: {inc.get('rainfall_1h',0):.0f} mm/hr",
                expanded=(risk_level == "CRITICAL"),
            ):
                col_a, col_b, col_c, col_d = st.columns(4)
                with col_a: st.metric("Risk Score", f"{inc.get('risk_score',0):.0f}/100")
                with col_b: st.metric("Citizen Reports", inc.get("citizen_reports", 0))
                with col_c: st.metric("Drainage Risk", inc.get("drain_risk", "N/A"))
                with col_d: st.metric("Status", inc.get("status", "ACTIVE"))

                st.markdown(f"**🤖 AI Recommended Actions:**")
                st.markdown(f'<div style="background:#111827;border-radius:8px;padding:0.5rem 0.8rem">{actions_html}</div>', unsafe_allow_html=True)

                if inc.get("requires_human_approval"):
                    st.markdown("""
                    <div style="background:rgba(239,68,68,0.15);border:1px solid #ef4444;border-radius:6px;
                                padding:0.5rem 0.8rem;font-size:0.8rem;color:#fca5a5;margin-top:0.5rem">
                        🔐 <strong>HUMAN APPROVAL REQUIRED</strong> — Emergency actions require municipal officer authorization.
                    </div>
                    """, unsafe_allow_html=True)
                    col_approve, col_reject = st.columns(2)
                    with col_approve:
                        if st.button("✅ Approve Actions", key=f"approve_{inc['incident_id']}", type="primary"):
                            st.session_state.approved_recs.add(inc["incident_id"])
                            st.success(f"Actions approved for {inc['incident_id']} [DEMO — logged]")
                    with col_reject:
                        if st.button("❌ Reject", key=f"reject_{inc['incident_id']}"):
                            st.session_state.rejected_recs.add(inc["incident_id"])
                            st.warning(f"Actions rejected for {inc['incident_id']} [DEMO — logged]")

# ── Tab 3: AI Recommendations ─────────────────
with tab3:
    section_header("AI RECOMMENDATIONS", demo_badge())
    ai_disclaimer()

    recs = response_plan.get("top_recommendations", [])
    if not recs:
        st.info("Run a scenario to generate AI recommendations.")
    else:
        for rec in recs:
            priority = rec.get("priority", "MEDIUM")
            p_colors = {"CRITICAL": "#ef4444", "HIGH": "#f97316", "MEDIUM": "#eab308", "LOW": "#22c55e"}
            p_color = p_colors.get(priority, "#94a3b8")
            approved = rec.get("rec_id") in st.session_state.approved_recs
            rejected = rec.get("rec_id") in st.session_state.rejected_recs

            status_html = ""
            if approved:
                status_html = '<span style="background:#22c55e;color:white;padding:2px 8px;border-radius:8px;font-size:0.7rem">✅ APPROVED</span>'
            elif rejected:
                status_html = '<span style="background:#ef4444;color:white;padding:2px 8px;border-radius:8px;font-size:0.7rem">❌ REJECTED</span>'
            else:
                status_html = '<span style="background:#eab308;color:#1a1d27;padding:2px 8px;border-radius:8px;font-size:0.7rem">⏳ PENDING</span>'

            st.markdown(f"""
            <div class="fg-card" style="border-left:4px solid {p_color}">
                <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:0.5rem">
                    <div>
                        <span style="background:{p_color};color:{'black' if priority=='MEDIUM' else 'white'};
                              padding:2px 8px;border-radius:8px;font-size:0.72rem;font-weight:600">{priority}</span>
                        &nbsp;<span style="font-size:0.72rem;color:#94a3b8">{rec.get('agent','')}</span>
                    </div>
                    {status_html}
                </div>
                <div style="font-weight:600;color:#e2e8f0;margin-bottom:0.3rem;font-size:0.9rem">
                    {rec.get('recommendation','')}
                </div>
                <div style="font-size:0.8rem;color:#94a3b8">
                    <b>Reasoning:</b> {rec.get('reasoning','')}
                </div>
            </div>
            """, unsafe_allow_html=True)

            if not approved and not rejected and rec.get("requires_approval"):
                c1, c2 = st.columns([1, 1])
                with c1:
                    if st.button("✅ Approve", key=f"rec_approve_{rec['rec_id']}"):
                        st.session_state.approved_recs.add(rec["rec_id"])
                        st.rerun()
                with c2:
                    if st.button("❌ Reject", key=f"rec_reject_{rec['rec_id']}"):
                        st.session_state.rejected_recs.add(rec["rec_id"])
                        st.rerun()
            elif not approved and not rejected:
                if st.button("✅ Mark Implemented", key=f"rec_impl_{rec['rec_id']}", type="secondary"):
                    st.session_state.approved_recs.add(rec["rec_id"])
                    st.rerun()

    # Situation report
    st.markdown("---")
    section_header("📋 AI SITUATION REPORT", simulated_badge())
    situation_report = state.get("situation_report", "")
    if situation_report:
        st.markdown(f"""
        <div class="fg-card-blue" style="font-family:monospace;font-size:0.82rem;
                    white-space:pre-wrap;color:#e2e8f0;line-height:1.6">
{situation_report}
        </div>
        """, unsafe_allow_html=True)
        if st.download_button(
            "📥 Download Situation Report",
            data=situation_report,
            file_name=f"flood_situation_{datetime.utcnow().strftime('%Y%m%d_%H%M')}.txt",
            mime="text/plain",
        ):
            pass

# ── Tab 4: Drainage ───────────────────────────
with tab4:
    section_header("DRAINAGE STATUS", demo_badge())
    scored_drains = drain_analysis.get("scored_drains", [])
    priority_summary = drain_analysis.get("priority_summary", {})

    col_sum, col_sched = st.columns([1, 1.5])
    with col_sum:
        for lvl, cnt in [("CRITICAL", "#ef4444"), ("HIGH", "#f97316"), ("MEDIUM", "#eab308"), ("LOW", "#22c55e")]:
            n = priority_summary.get(lvl, 0)
            pct = n / max(len(scored_drains), 1) * 100
            st.markdown(f"""
            <div style="display:flex;align-items:center;gap:0.75rem;margin-bottom:0.4rem">
                <div style="min-width:80px;font-size:0.8rem;font-weight:600;color:{cnt}">{lvl}</div>
                <div style="flex:1;background:#1a1d27;border-radius:4px;height:18px;overflow:hidden;border:1px solid #2d3148">
                    <div style="width:{pct:.0f}%;background:{cnt};height:100%;
                                border-radius:4px;transition:width 0.3s"></div>
                </div>
                <div style="min-width:30px;font-size:0.8rem;color:#e2e8f0;text-align:right">{n}</div>
            </div>
            """, unsafe_allow_html=True)

        st.markdown(f"""
        <div style="margin-top:0.75rem;font-size:0.8rem;color:#f97316">
            ⚡ {len(drain_analysis.get('requires_immediate_action',[]))} drain(s) require IMMEDIATE action
        </div>
        """, unsafe_allow_html=True)

    with col_sched:
        schedule = drain_analysis.get("maintenance_schedule", [])
        if schedule:
            df_sched = pd.DataFrame(schedule[:12])
            df_sched_display = df_sched[["drain_id", "area", "city", "priority", "action", "due_by"]].copy()
            df_sched_display.columns = ["Drain ID", "Area", "City", "Priority", "Action", "Due By"]
            st.dataframe(df_sched_display, use_container_width=True, hide_index=True, height=250)

    st.markdown("---")
    # Top critical drains
    top_drains = drain_analysis.get("top_5_critical", [])
    if top_drains:
        section_header("TOP CRITICAL DRAINS")
        cols = st.columns(min(5, len(top_drains)))
        for i, drain in enumerate(top_drains[:5]):
            with cols[i]:
                score = drain.get("computed_risk_score", 0)
                cond = drain.get("condition", "UNKNOWN")
                st.markdown(f"""
                <div class="fg-card-danger" style="padding:0.7rem;text-align:center">
                    <div style="font-size:1.3rem;font-weight:800;color:#ef4444">{score:.0f}</div>
                    <div style="font-size:0.7rem;color:#94a3b8">Risk Score</div>
                    <div style="font-weight:700;color:#e2e8f0;font-size:0.8rem;margin:0.3rem 0">{drain.get('drain_id')}</div>
                    <div style="font-size:0.72rem;color:#94a3b8">{drain.get('area')}</div>
                    <div style="font-size:0.72rem;color:#94a3b8">{drain.get('city')}</div>
                    <div style="font-size:0.7rem;color:#f97316;margin-top:0.3rem">{cond}</div>
                </div>
                """, unsafe_allow_html=True)

# ── Tab 5: Citizen Reports ────────────────────
with tab5:
    section_header("CITIZEN FLOOD REPORTS", demo_badge())

    col_r1, col_r2 = st.columns([1, 1.5])
    with col_r1:
        # Summary metrics
        ra = report_analysis
        mc1, mc2 = st.columns(2)
        with mc1:
            metric_card("Total Reports", str(ra.get("total_reports", 0)), color="#3b82f6")
            metric_card("Critical Reports", str(ra.get("critical_count", 0)), color="#ef4444", icon="🚨")
        with mc2:
            metric_card("Open Reports", str(ra.get("open_reports", 0)), color="#f97316")
            metric_card("Duplicates Filtered", str(ra.get("duplicate_count", 0)), color="#94a3b8")

        st.markdown("---")
        # Category breakdown
        by_cat = ra.get("by_category", {})
        if by_cat:
            fig_cat = go.Figure(go.Bar(
                x=list(by_cat.values()),
                y=[k.replace("_", " ").title() for k in by_cat.keys()],
                orientation="h",
                marker_color="#3b82f6",
            ))
            fig_cat.update_layout(
                paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
                xaxis=dict(color="#94a3b8"), yaxis=dict(color="#e2e8f0"),
                margin=dict(t=10, b=10, l=10, r=10), height=200,
            )
            st.plotly_chart(fig_cat, use_container_width=True, config={"displayModeBar": False})

    with col_r2:
        # Report hotspots
        hotspots = ra.get("hotspot_areas", [])
        if hotspots:
            section_header("REPORT HOTSPOTS")
            for hs in hotspots[:5]:
                n = hs["report_count"]
                bar_w = min(100, n * 3)
                st.markdown(f"""
                <div style="display:flex;align-items:center;gap:0.75rem;margin-bottom:0.4rem">
                    <div style="min-width:120px;font-size:0.82rem;color:#e2e8f0">{hs['area']}</div>
                    <div style="flex:1;background:#1a1d27;border-radius:4px;height:16px;border:1px solid #2d3148">
                        <div style="width:{bar_w}%;background:#3b82f6;height:100%;border-radius:4px"></div>
                    </div>
                    <div style="min-width:30px;font-size:0.8rem;color:#94a3b8">{n}</div>
                </div>
                """, unsafe_allow_html=True)

        st.markdown("---")
        # Reports table
        if raw_reports:
            df_r = pd.DataFrame(raw_reports[:30])
            if not df_r.empty:
                cols_to_show = ["report_id", "city", "area", "category", "severity", "language", "status"]
                cols_avail = [c for c in cols_to_show if c in df_r.columns]
                df_display = df_r[cols_avail].copy()
                df_display["category"] = df_display["category"].str.replace("_", " ").str.title()
                st.dataframe(df_display, use_container_width=True, hide_index=True, height=280)

# ── Tab 6: Response Teams ─────────────────────
with tab6:
    section_header("RESPONSE TEAMS", demo_badge())

    # Status overview
    team_status = {"AVAILABLE": 0, "DEPLOYED": 0, "STANDBY": 0, "OFF_DUTY": 0}
    for t in teams:
        s = t.get("status", "OFF_DUTY")
        team_status[s] = team_status.get(s, 0) + 1

    t1, t2, t3, t4 = st.columns(4)
    with t1: metric_card("Available", str(team_status["AVAILABLE"]), color="#22c55e", icon="✅")
    with t2: metric_card("Deployed", str(team_status["DEPLOYED"]), color="#f97316", icon="🚨")
    with t3: metric_card("Standby", str(team_status["STANDBY"]), color="#3b82f6", icon="⏸️")
    with t4: metric_card("Off Duty", str(team_status["OFF_DUTY"]), color="#94a3b8", icon="🔴")

    st.markdown("<br>", unsafe_allow_html=True)

    if teams:
        df_teams = pd.DataFrame(teams)
        cols_t = [c for c in ["team_id", "name", "city", "team_type", "status", "capacity"] if c in df_teams.columns]
        df_teams_display = df_teams[cols_t].copy()
        df_teams_display["team_type"] = df_teams_display["team_type"].str.replace("_", " ").str.title()
        st.dataframe(df_teams_display, use_container_width=True, hide_index=True, height=400)

# ── Tab 7: Rainfall ───────────────────────────
with tab7:
    section_header("RAINFALL DATA", demo_badge())
    if rainfall_data:
        col_chart, col_table = st.columns([1.3, 1])
        with col_chart:
            fig_rain = rainfall_bar(rainfall_data, top_n=15)
            st.plotly_chart(fig_rain, use_container_width=True, config={"displayModeBar": False})
        with col_table:
            df_rain = pd.DataFrame(rainfall_data)
            cols_rain = [c for c in ["city", "area", "rainfall_1h", "rainfall_3h", "rainfall_6h", "rainfall_24h"] if c in df_rain.columns]
            df_rain_sorted = df_rain[cols_rain].sort_values("rainfall_1h", ascending=False).head(20)
            df_rain_sorted.columns = ["City", "Area", "1h mm", "3h mm", "6h mm", "24h mm"]
            st.dataframe(df_rain_sorted, use_container_width=True, hide_index=True, height=380)

# ──────────────────────────────────────────────
# Footer
# ──────────────────────────────────────────────
st.markdown("---")
st.markdown(f"""
<div style="text-align:center;color:#475569;font-size:0.72rem">
    FloodGuard AI v1.0 | Municipal Command Center | 
    Scenario: {SCENARIOS[st.session_state.scenario]['label']} | 
    {demo_badge()} All displayed values are synthetic demo data.<br>
    AI recommendations require authorized human verification. Not for operational emergency use.
</div>
""", unsafe_allow_html=True)
