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
from datetime import datetime, timezone
from frontend.ui_utils import (
    apply_global_css, header, metric_card, ai_disclaimer, card,
    risk_badge, demo_badge, hybrid_badge, live_badge, model_badge,
    simulated_badge, COLORS, RISK_EMOJI,
    risk_donut, rainfall_bar, risk_gauge, section_header
)
from agents.orchestrator import get_orchestrator, SCENARIOS
from frontend.map_component import build_flood_map
from streamlit_folium import st_folium
from services.report_store import get_user_reports, count_open as _user_open_count
from services.weather_dashboard import get_weather_for_city, cache_age_seconds, GUJARAT_CITIES

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
    # Determine sidebar data-mode badge based on live weather status
    _sb_live = (orch.current_state or {}).get("live_weather_status", {}).get("is_live", False)
    _sb_badge = hybrid_badge() if _sb_live else demo_badge()
    _sb_note  = "🟢 Live Weather + 🟡 Synthetic Model Data" if _sb_live else "Synthetic data — no live source"
    st.markdown(f"""
    <div style="font-size:0.75rem;color:#94a3b8">
        <b>Current Scenario:</b> {SCENARIOS[st.session_state.scenario]['emoji']} {SCENARIOS[st.session_state.scenario]['label']}<br>
        <b>City:</b> {st.session_state.city_filter}<br>
        <b>Last updated:</b> {orch.current_state.get('last_updated','')[:16] if orch.current_state else 'N/A'}<br><br>
        {_sb_badge}<br>
        <span style="font-size:0.68rem">{_sb_note}</span><br><br>
        <span style="background:#1e3a5f;color:#93c5fd;padding:2px 6px;border-radius:4px;font-size:0.7rem">📍 SCOPE</span>
        Ahmedabad &amp; Surat only
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
# ── Merge demo seed reports with persisted USER SUBMITTED reports ─────────
# user_reports is read fresh from disk on every rerun — no caching — so that
# reports submitted from the Citizen Portal page appear here immediately.
_demo_reports = state.get("raw_reports", [])
_user_reports = get_user_reports()
# Tag demo reports with source label if not already set
for _r in _demo_reports:
    if not _r.get("source"):
        _r["source"] = "DEMO/SYNTHETIC"
raw_reports = _user_reports + _demo_reports
live_weather_status      = state.get("live_weather_status",      {"data_mode": "DEMO", "is_live": False, "fallback_reason": "Pipeline not yet run"})
live_weather_records     = state.get("live_weather_records",     [])
live_weather_map_points  = state.get("live_weather_map_points",  [])

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
# Open reports = demo open count + all persisted user-submitted open reports
_demo_open  = report_analysis.get("open_reports", 0)
_user_open  = _user_open_count()
open_reports = _demo_open + _user_open
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
tab1, tab2, tab3, tab4, tab5, tab6, tab7, tab8 = st.tabs([
    "🗺️ Live Risk Map",
    "🌦️ Live Weather",
    "⚡ Incidents",
    "🤖 AI Recommendations",
    "🔧 Drainage",
    "📱 Citizen Reports",
    "🚒 Response Teams",
    "🌧️ Rainfall Data",
])

# ── Tab 1: Live Risk Map ──────────────────────
with tab1:
    col_map, col_detail = st.columns([2, 1])

    with col_map:
        _map_badge = hybrid_badge() if live_weather_records else demo_badge()
        section_header("DIGITAL TWIN MAP — Ahmedabad & Surat, Gujarat", _map_badge)
        st.caption(
            "🎯 **Scope:** Ahmedabad & Surat only — "
            "Smart Urban Flooding & Drainage Management System for Ahmedabad–Surat. "
            "🟢 Live Weather Evidence · 🔵 ML Flood-Risk Prediction · 🟡 Synthetic Demo Layers"
        )
        _is_live_map = bool(live_weather_map_points)
        m = build_flood_map(
            risk_predictions=predictions,
            drain_data=raw_drains[:80],
            report_data=raw_reports[:80],
            team_data=teams,
            city=st.session_state.city_filter,
            weather_data=live_weather_map_points if _is_live_map else None,
            is_live=_is_live_map,
        )
        map_data = st_folium(m, width="100%", height=560, key="cmd_map")

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
            section_header("ACTIVE ALERTS", model_badge())
            for alert in alerts[:4]:
                level = alert.get("alert_level", "INFO")
                cls = {"CRITICAL": "alert-critical", "HIGH": "alert-high"}.get(level, "alert-info")
                st.markdown(f"""
                <div class="{cls}" style="font-size:0.8rem">
                    <b>{alert.get('title','')}</b><br>
                    <span style="color:#cbd5e1">{alert.get('message','')[:120]}</span>
                    <div style="font-size:0.68rem;color:#64748b;margin-top:0.2rem">🔵 MODEL GENERATED</div>
                </div>
                """, unsafe_allow_html=True)

# ── Tab 3: Incidents ──────────────────────────
with tab3:
    section_header("ACTIVE INCIDENTS",
                   '<span style="background:#1e3a5f;color:#93c5fd;font-size:0.7rem;padding:2px 8px;border-radius:4px;font-weight:700;letter-spacing:0.04em">🔵 MODEL + 🟡 DEMO DATA</span>')
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

# ── Tab 4: AI Recommendations ─────────────────
with tab4:
    section_header("AI RECOMMENDATIONS", model_badge())
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
    section_header("📋 AI SITUATION REPORT",
                   '<span style="background:#1e3a5f;color:#93c5fd;font-size:0.7rem;padding:2px 8px;border-radius:4px;font-weight:700;letter-spacing:0.04em">🔵 MODEL / GRANITE</span>')
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

# ── Tab 5: Drainage ───────────────────────────
with tab5:
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

# ── Tab 6: Citizen Reports ────────────────────
with tab6:
    section_header("CITIZEN FLOOD REPORTS",
                   '<span style="background:#3a1a00;color:#fdba74;font-size:0.7rem;padding:2px 8px;border-radius:4px;font-weight:700;letter-spacing:0.04em">🟠 USER SUBMITTED + 🟡 DEMO/SYNTHETIC</span>')

    # ── Refresh button — triggers a rerun which re-reads the file store ──
    _rr_col, _rr_info = st.columns([1, 4])
    with _rr_col:
        if st.button("🔄 Refresh Reports", key="refresh_reports"):
            st.rerun()
    with _rr_info:
        st.markdown(
            f'<div style="font-size:0.75rem;color:#94a3b8;padding-top:0.4rem">'
            f'🟠 <b>{len(_user_reports)}</b> USER SUBMITTED &nbsp;·&nbsp; '
            f'🟡 <b>{len(_demo_reports)}</b> DEMO/SYNTHETIC &nbsp;·&nbsp; '
            f'📋 <b>{len(raw_reports)}</b> total</div>',
            unsafe_allow_html=True,
        )

    col_r1, col_r2 = st.columns([1, 1.5])
    with col_r1:
        # Summary metrics — use merged counts
        ra = report_analysis
        _total_merged  = len(raw_reports)
        _open_merged   = open_reports  # already includes user-submitted open count
        _critical_merged = ra.get("critical_count", 0) + sum(
            1 for r in _user_reports if r.get("severity") == "CRITICAL"
        )
        _dupes_merged  = ra.get("duplicate_count", 0)
        mc1, mc2 = st.columns(2)
        with mc1:
            metric_card("Total Reports", str(_total_merged), color="#3b82f6")
            metric_card("Critical Reports", str(_critical_merged), color="#ef4444", icon="🚨")
        with mc2:
            metric_card("Open Reports", str(_open_merged), color="#f97316")
            metric_card("Duplicates Filtered", str(_dupes_merged), color="#94a3b8")

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

        # If there are user-submitted reports, show them first in a dedicated block
        if _user_reports:
            st.markdown("---")
            section_header("🟠 USER SUBMITTED REPORTS")
            df_usr = pd.DataFrame(_user_reports[:10])
            if not df_usr.empty:
                _ucols = ["report_id", "area", "city", "category", "severity", "status", "submitted_at"]
                _ucols_avail = [c for c in _ucols if c in df_usr.columns]
                df_usr_disp = df_usr[_ucols_avail].copy()
                df_usr_disp["category"] = df_usr_disp["category"].str.replace("_", " ").str.title()
                if "submitted_at" in df_usr_disp.columns:
                    df_usr_disp["submitted_at"] = pd.to_datetime(df_usr_disp["submitted_at"]).dt.strftime("%b %d %H:%M")
                st.dataframe(df_usr_disp, use_container_width=True, hide_index=True, height=200)

        st.markdown("---")
        # Full merged reports table (user first, then demo)
        if raw_reports:
            section_header("ALL REPORTS (Merged)")
            df_r = pd.DataFrame(raw_reports[:40])
            if not df_r.empty:
                # Ensure source column exists
                if "source" not in df_r.columns:
                    df_r["source"] = "DEMO/SYNTHETIC"
                df_r["source"] = df_r["source"].fillna("DEMO/SYNTHETIC")
                cols_to_show = ["report_id", "city", "area", "category", "severity", "status", "source"]
                cols_avail = [c for c in cols_to_show if c in df_r.columns]
                df_display = df_r[cols_avail].copy()
                df_display["category"] = df_display["category"].str.replace("_", " ").str.title()
                st.dataframe(df_display, use_container_width=True, hide_index=True, height=280)

# ── Tab 7: Response Teams ─────────────────────
with tab7:
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

# ── Tab 8: Rainfall ───────────────────────────
with tab8:
    _rain_is_live_cc = state.get("live_weather_status", {}).get("is_live", False)
    section_header("RAINFALL DATA",
                   live_badge() if _rain_is_live_cc else demo_badge())
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

# ── Tab 2: Live Weather ──────────────────────
with tab2:
    from datetime import datetime as _wx_dt
    from services.live_weather import wmo_emoji as _cc_wmo_emoji

    section_header("LIVE WEATHER & FORECAST", live_badge())
    st.caption(
        "Real-time weather for Gujarat cities via Open-Meteo API (no API key required). "
        "Select a city, view hourly and 7-day forecasts, and refresh live data below."
    )

    # ── Session state ──────────────────────────────────────────────────────
    if "cc_wx_city" not in st.session_state:
        st.session_state.cc_wx_city = "Ahmedabad"
    if "cc_wx_force" not in st.session_state:
        st.session_state.cc_wx_force = False

    # ── Controls row: city selector · refresh · cache status ───────────────
    _wx_col_sel, _wx_col_btn, _wx_col_info = st.columns([1.2, 0.7, 2.5])
    with _wx_col_sel:
        _cc_city_sel = st.selectbox(
            "Select City",
            GUJARAT_CITIES,
            index=GUJARAT_CITIES.index(st.session_state.cc_wx_city)
                  if st.session_state.cc_wx_city in GUJARAT_CITIES else 0,
            key="cc_wx_city_select",
        )
        if _cc_city_sel != st.session_state.cc_wx_city:
            st.session_state.cc_wx_city = _cc_city_sel
            st.rerun()
    with _wx_col_btn:
        st.markdown("<div style='margin-top:1.6rem'>", unsafe_allow_html=True)
        if st.button("🔄 Refresh", key="cc_wx_refresh", use_container_width=True):
            st.session_state.cc_wx_force = True
            st.rerun()
        st.markdown("</div>", unsafe_allow_html=True)
    with _wx_col_info:
        _cc_age = cache_age_seconds(st.session_state.cc_wx_city)
        _cc_age_str = f"{int(_cc_age)}s ago" if _cc_age is not None else "not fetched yet"
        st.markdown(
            f'<div style="padding-top:1.8rem;font-size:0.72rem;color:#64748b">'
            f'<span style="background:#14532d;color:#bbf7d0;padding:1px 6px;'
            f'border-radius:3px;font-size:0.7rem;font-weight:700">🟢 LIVE</span>'
            f'&nbsp; Open-Meteo API &nbsp;|&nbsp; Cache: {_cc_age_str}'
            f'</div>',
            unsafe_allow_html=True,
        )

    # ── Fetch ──────────────────────────────────────────────────────────────
    _cc_force = st.session_state.cc_wx_force
    if _cc_force:
        st.session_state.cc_wx_force = False
    _cc_wx, _cc_wx_err = get_weather_for_city(
        st.session_state.cc_wx_city, force_refresh=_cc_force
    )

    # ── Error / warning state ──────────────────────────────────────────────
    if _cc_wx_err and _cc_wx is None:
        st.error(
            f"Live weather data temporarily unavailable "
            f"for {st.session_state.cc_wx_city}: {_cc_wx_err}"
        )
    else:
        if _cc_wx_err:
            st.warning(_cc_wx_err)

        if _cc_wx:
            # ── Extract current-conditions fields ──────────────────────────
            _cc_temp   = _cc_wx.get("temperature", "--")
            _cc_cond   = _cc_wx.get("condition", "--")
            _cc_emoji  = _cc_wx.get("condition_emoji", "")
            _cc_rain   = _cc_wx.get("rainfall_1h", 0)
            _cc_humid  = _cc_wx.get("humidity", "--")
            _cc_wind   = _cc_wx.get("wind_speed", "--")
            _cc_wdir   = _cc_wx.get("wind_direction_label", "--")
            _cc_wdeg   = _cc_wx.get("wind_direction", "--")
            _cc_prob   = _cc_wx.get("precipitation_probability", 0)
            _cc_rain6h = _cc_wx.get("rainfall_6h", 0)
            _cc_rec    = str(_cc_wx.get("recorded_at", ""))[:16].replace("T", " ")
            _cc_rain_c = (
                "#ef4444" if _cc_rain >= 40 else "#f97316" if _cc_rain >= 20
                else "#eab308" if _cc_rain >= 5 else "#22c55e"
            )

            # ── Current conditions hero card ───────────────────────────────
            st.markdown(f"""
            <div style="background:#1a1d27;border:1px solid #22c55e;border-radius:12px;
                        padding:1rem 1.25rem;margin:.5rem 0 1rem">
              <div style="display:flex;align-items:center;gap:0.75rem;margin-bottom:0.75rem">
                <span style="font-size:2rem">{_cc_emoji}</span>
                <div>
                  <div style="font-size:1rem;font-weight:800;color:#e2e8f0">
                    {st.session_state.cc_wx_city} &mdash; {_cc_cond}</div>
                  <div style="font-size:0.68rem;color:#475569">
                    Observed: {_cc_rec} IST &nbsp;|&nbsp;
                    <span style="color:#6ee7b7">&#128994; LIVE</span>
                    &nbsp; Open-Meteo
                  </div>
                </div>
              </div>
              <div style="display:grid;grid-template-columns:repeat(auto-fit,minmax(105px,1fr));gap:0.55rem">
                <div style="background:#111827;border-radius:8px;padding:.5rem;text-align:center">
                  <div style="font-size:1.35rem;font-weight:800;color:#f97316">{_cc_temp}&#176;C</div>
                  <div style="font-size:0.62rem;color:#94a3b8">TEMPERATURE</div>
                </div>
                <div style="background:#111827;border-radius:8px;padding:.5rem;text-align:center">
                  <div style="font-size:1.35rem;font-weight:800;color:{_cc_rain_c}">{_cc_rain} mm</div>
                  <div style="font-size:0.62rem;color:#94a3b8">RAIN / HR</div>
                </div>
                <div style="background:#111827;border-radius:8px;padding:.5rem;text-align:center">
                  <div style="font-size:1.35rem;font-weight:800;color:#3b82f6">{_cc_humid}%</div>
                  <div style="font-size:0.62rem;color:#94a3b8">HUMIDITY</div>
                </div>
                <div style="background:#111827;border-radius:8px;padding:.5rem;text-align:center">
                  <div style="font-size:1.35rem;font-weight:800;color:#14b8a6">{_cc_wind} km/h</div>
                  <div style="font-size:0.62rem;color:#94a3b8">WIND SPEED</div>
                </div>
                <div style="background:#111827;border-radius:8px;padding:.5rem;text-align:center">
                  <div style="font-size:1.35rem;font-weight:800;color:#a78bfa">{_cc_wdir}</div>
                  <div style="font-size:0.62rem;color:#94a3b8">WIND DIR</div>
                </div>
                <div style="background:#111827;border-radius:8px;padding:.5rem;text-align:center">
                  <div style="font-size:1.35rem;font-weight:800;color:#64748b">{int(_cc_prob)}%</div>
                  <div style="font-size:0.62rem;color:#94a3b8">PRECIP PROB</div>
                </div>
                <div style="background:#111827;border-radius:8px;padding:.5rem;text-align:center">
                  <div style="font-size:1.35rem;font-weight:800;color:#22d3ee">{_cc_rain6h} mm</div>
                  <div style="font-size:0.62rem;color:#94a3b8">RAIN NEXT 6H</div>
                </div>
              </div>
            </div>
            """, unsafe_allow_html=True)

            # ── Shared helper for time label ───────────────────────────────
            def _cc_fmt_t(t):
                try:
                    return _wx_dt.strptime(t, "%Y-%m-%dT%H:%M").strftime("%H:%M")
                except Exception:
                    return t[:5]

            # ── Hourly arrays (48 h from API) ──────────────────────────────
            _cc_h_times   = _cc_wx.get("hourly_times",       [])
            _cc_h_temp    = _cc_wx.get("hourly_temp",        [])
            _cc_h_precip  = _cc_wx.get("hourly_precip",      [])
            _cc_h_prob    = _cc_wx.get("hourly_precip_prob", [])
            _cc_h_wind    = _cc_wx.get("hourly_windspeed",   [])
            _cc_h_winddir = _cc_wx.get("hourly_winddir",     [])

            # Show 48 h for hourly views
            _cc_n   = min(48, len(_cc_h_times))
            _cc_lbl = [_cc_fmt_t(t) for t in _cc_h_times[:_cc_n]]

            # ── Three view tabs: Temperature · Precipitation · Wind ─────────
            _wx_tab_t, _wx_tab_p, _wx_tab_w = st.tabs([
                "🌡️ Temperature",
                "🌧️ Precipitation",
                "💨 Wind",
            ])

            # Shared chart base settings — defined once, no yaxis key here
            _cc_layout_base = dict(
                paper_bgcolor="rgba(0,0,0,0)",
                plot_bgcolor="rgba(0,0,0,0)",
                font=dict(color="#94a3b8", size=10),
                margin=dict(t=10, b=35, l=40, r=10),
                xaxis=dict(
                    color="#64748b",
                    gridcolor="#1e2030",
                    nticks=12,
                    tickangle=-45,
                ),
                hovermode="x unified",
            )

            # ── Temperature tab ────────────────────────────────────────────
            with _wx_tab_t:
                section_header(
                    "HOURLY TEMPERATURE (48 h)",
                    '<span style="background:#14532d;color:#bbf7d0;font-size:0.65rem;'
                    'padding:1px 6px;border-radius:3px;font-weight:700">LIVE</span>',
                )
                if _cc_h_temp and _cc_lbl:
                    _fig_t = go.Figure(go.Scatter(
                        x=_cc_lbl, y=_cc_h_temp[:_cc_n],
                        mode="lines+markers",
                        line=dict(color="#f97316", width=2),
                        marker=dict(size=3, color="#f97316"),
                        fill="tozeroy",
                        fillcolor="rgba(249,115,22,0.08)",
                        name="Temperature",
                        hovertemplate="%{x}<br><b>%{y:.1f}&#176;C</b><extra></extra>",
                    ))
                    _fig_t.update_layout(
                        _cc_layout_base,
                        height=220,
                        yaxis=dict(
                            color="#94a3b8",
                            gridcolor="#1e2030",
                            title="&#176;C",
                        ),
                    )
                    st.plotly_chart(_fig_t, use_container_width=True,
                                    config={"displayModeBar": False})
                    # Current + daily summary metrics
                    _t_col1, _t_col2, _t_col3 = st.columns(3)
                    with _t_col1:
                        metric_card("Current", f"{_cc_temp}°C", color="#f97316", icon="🌡️")
                    with _t_col2:
                        _d_max = _cc_wx.get("daily_temp_max", [None])
                        _dmax_v = f"{_d_max[0]:.0f}°C" if _d_max and _d_max[0] is not None else "--"
                        metric_card("Today Max", _dmax_v, color="#ef4444", icon="⬆️")
                    with _t_col3:
                        _d_min = _cc_wx.get("daily_temp_min", [None])
                        _dmin_v = f"{_d_min[0]:.0f}°C" if _d_min and _d_min[0] is not None else "--"
                        metric_card("Today Min", _dmin_v, color="#3b82f6", icon="⬇️")
                else:
                    st.info("Hourly temperature data not available.")

            # ── Precipitation tab ──────────────────────────────────────────
            with _wx_tab_p:
                section_header(
                    "HOURLY PRECIPITATION & PROBABILITY (48 h)",
                    '<span style="background:#14532d;color:#bbf7d0;font-size:0.65rem;'
                    'padding:1px 6px;border-radius:3px;font-weight:700">LIVE</span>',
                )
                if _cc_h_precip and _cc_lbl:
                    _fig_p = go.Figure()
                    # Precipitation bars — primary y-axis
                    _fig_p.add_trace(go.Bar(
                        x=_cc_lbl, y=_cc_h_precip[:_cc_n],
                        name="Precipitation (mm)",
                        marker_color=[
                            "#ef4444" if v >= 40 else "#f97316" if v >= 20
                            else "#eab308" if v >= 5 else "#3b82f6"
                            for v in _cc_h_precip[:_cc_n]
                        ],
                        hovertemplate="%{x}<br><b>%{y:.2f} mm</b><extra></extra>",
                        yaxis="y",
                    ))
                    # Probability line — secondary y-axis
                    if _cc_h_prob:
                        _fig_p.add_trace(go.Scatter(
                            x=_cc_lbl, y=_cc_h_prob[:_cc_n],
                            mode="lines",
                            line=dict(color="#a78bfa", width=1.5, dash="dot"),
                            name="Precip Prob (%)",
                            hovertemplate="%{x}<br><b>%{y:.0f}%</b><extra></extra>",
                            yaxis="y2",
                        ))
                    _fig_p.update_layout(
                        _cc_layout_base,
                        height=240,
                        barmode="overlay",
                        yaxis=dict(
                            color="#94a3b8",
                            gridcolor="#1e2030",
                            title="mm",
                        ),
                        yaxis2=dict(
                            title="%",
                            overlaying="y",
                            side="right",
                            range=[0, 100],
                            color="#a78bfa",
                            showgrid=False,
                        ),
                        legend=dict(
                            orientation="h",
                            yanchor="bottom",
                            y=1.02,
                            font=dict(color="#94a3b8", size=9),
                        ),
                    )
                    st.plotly_chart(_fig_p, use_container_width=True,
                                    config={"displayModeBar": False})
                    _p_col1, _p_col2, _p_col3 = st.columns(3)
                    with _p_col1:
                        metric_card("Now (1h)", f"{_cc_rain} mm", color="#3b82f6", icon="🌧️")
                    with _p_col2:
                        metric_card("Next 6h", f"{_cc_rain6h} mm", color="#3b82f6", icon="🌊")
                    with _p_col3:
                        metric_card("Precip Prob", f"{int(_cc_prob)}%", color="#a78bfa", icon="📊")
                else:
                    st.info("Hourly precipitation data not available.")

            # ── Wind tab ───────────────────────────────────────────────────
            with _wx_tab_w:
                section_header(
                    "HOURLY WIND SPEED (48 h)",
                    '<span style="background:#14532d;color:#bbf7d0;font-size:0.65rem;'
                    'padding:1px 6px;border-radius:3px;font-weight:700">LIVE</span>',
                )
                if _cc_h_wind and _cc_lbl:
                    _fig_w = go.Figure(go.Scatter(
                        x=_cc_lbl, y=_cc_h_wind[:_cc_n],
                        mode="lines+markers",
                        line=dict(color="#14b8a6", width=2),
                        marker=dict(size=3, color="#14b8a6"),
                        fill="tozeroy",
                        fillcolor="rgba(20,184,166,0.08)",
                        name="Wind Speed",
                        hovertemplate="%{x}<br><b>%{y:.1f} km/h</b><extra></extra>",
                    ))
                    _fig_w.update_layout(
                        _cc_layout_base,
                        height=220,
                        yaxis=dict(
                            color="#94a3b8",
                            gridcolor="#1e2030",
                            title="km/h",
                        ),
                    )
                    st.plotly_chart(_fig_w, use_container_width=True,
                                    config={"displayModeBar": False})
                    _w_col1, _w_col2, _w_col3 = st.columns(3)
                    with _w_col1:
                        metric_card("Speed", f"{_cc_wind} km/h", color="#14b8a6", icon="💨")
                    with _w_col2:
                        metric_card("Direction", f"{_cc_wdir}", color="#a78bfa", icon="🧭")
                    with _w_col3:
                        metric_card("Degrees", f"{_cc_wdeg}°", color="#64748b", icon="📐")
                else:
                    st.info("Hourly wind data not available.")

            # ── 7-day forecast ─────────────────────────────────────────────
            _cc_d_times  = _cc_wx.get("daily_times",          [])
            _cc_d_tmax   = _cc_wx.get("daily_temp_max",       [])
            _cc_d_tmin   = _cc_wx.get("daily_temp_min",       [])
            _cc_d_precip = _cc_wx.get("daily_precip_sum",     [])
            _cc_d_prob   = _cc_wx.get("daily_precip_prob_max",[])
            _cc_d_wcode  = _cc_wx.get("daily_weathercode",    [])

            if _cc_d_times:
                st.markdown("---")
                section_header("7-DAY FORECAST", live_badge())

                def _cc_day_lbl(d):
                    try:
                        return _wx_dt.strptime(d, "%Y-%m-%d").strftime("%a %d")
                    except Exception:
                        return d

                _cc_dcols = st.columns(min(7, len(_cc_d_times)))
                for _di, (_dcol, _dday) in enumerate(zip(_cc_dcols, _cc_d_times[:7])):
                    with _dcol:
                        _dtmax  = _cc_d_tmax[_di]  if _di < len(_cc_d_tmax)  else None
                        _dtmin  = _cc_d_tmin[_di]  if _di < len(_cc_d_tmin)  else None
                        _dprec  = _cc_d_precip[_di] if _di < len(_cc_d_precip) else 0
                        _dprob  = _cc_d_prob[_di]   if _di < len(_cc_d_prob)   else 0
                        _dwc    = _cc_d_wcode[_di]  if _di < len(_cc_d_wcode)  else 0
                        _dem    = _cc_wmo_emoji(_dwc)
                        _tmax_s = f"{_dtmax:.0f}&#176;" if _dtmax is not None else "--"
                        _tmin_s = f"{_dtmin:.0f}&#176;" if _dtmin is not None else "--"
                        st.markdown(f"""
                        <div style="background:#111827;border:1px solid #2d3148;
                                    border-radius:8px;padding:.5rem .3rem;text-align:center">
                          <div style="font-size:1.1rem">{_dem}</div>
                          <div style="font-size:0.68rem;font-weight:700;color:#e2e8f0">
                            {_cc_day_lbl(_dday)}</div>
                          <div style="font-size:0.75rem;color:#f97316;font-weight:700">
                            {_tmax_s}</div>
                          <div style="font-size:0.65rem;color:#64748b">{_tmin_s}</div>
                          <div style="font-size:0.62rem;color:#3b82f6">{_dprec:.1f}mm</div>
                          <div style="font-size:0.6rem;color:#a78bfa">{int(_dprob)}%</div>
                        </div>
                        """, unsafe_allow_html=True)

            # ── Footer note ────────────────────────────────────────────────
            st.markdown(
                '<div style="margin-top:.75rem;font-size:0.68rem;color:#475569">'
                '&#128994; LIVE = Open-Meteo real-time data &nbsp;|&nbsp; '
                '&#128309; MODEL = ML flood-risk prediction &nbsp;|&nbsp; '
                '&#128993; DEMO/SYNTHETIC = drainage / reports / teams seed data'
                '</div>',
                unsafe_allow_html=True,
            )


# ──────────────────────────────────────────────
# Live Data Intelligence section
# ──────────────────────────────────────────────
st.markdown("---")
_lws = live_weather_status
_is_live = _lws.get("is_live", False)
_data_mode = _lws.get("data_mode", "DEMO")
_source = _lws.get("source", "Synthetic")
_last_upd = _lws.get("last_updated", "N/A")
_fallback = _lws.get("fallback_reason", "")
_stale = _lws.get("is_stale", False)

# When live weather is available, show HYBRID (not just LIVE — flood model is still synthetic)
# When unavailable, show DEMO
_top_badge_html = hybrid_badge() if _is_live else demo_badge()
_top_sub = "🟢 Live Weather · 🔵 ML Flood Risk · 🟡 Synthetic Drainage / Reports / Teams" if _is_live else "🟡 All data is synthetic — live source unavailable"

st.markdown(f"""
<div style="display:flex;align-items:center;gap:0.75rem;margin-bottom:0.2rem">
  <div style="font-size:1rem;font-weight:800;color:#e2e8f0;text-transform:uppercase;
              letter-spacing:0.06em">📡 Live Data Intelligence</div>
  {_top_badge_html}
  {"<span style='color:#f97316;font-size:0.7rem'>⚠ Stale data</span>" if _stale else ""}
</div>
<div style="font-size:0.72rem;color:#94a3b8;margin-bottom:0.5rem">{_top_sub}</div>
""", unsafe_allow_html=True)

_ldi_c1, _ldi_c2, _ldi_c3 = st.columns([1, 1, 1.4])

with _ldi_c1:
    _ahm = _lws.get("cities", {}).get("Ahmedabad", {})
    st.markdown(f"""
    <div style="background:#1a1d27;border:1px solid #2d3148;border-radius:8px;padding:0.75rem 1rem">
      <div style="font-weight:700;color:#93c5fd;margin-bottom:0.4rem">📍 Ahmedabad</div>
      {"".join([
          f'<div style="font-size:0.8rem;color:#e2e8f0"><b>Rainfall:</b> {_ahm.get("rainfall_1h","—")} mm/hr</div>',
          f'<div style="font-size:0.8rem;color:#e2e8f0"><b>Condition:</b> {_ahm.get("condition","—")}</div>',
          f'<div style="font-size:0.8rem;color:#e2e8f0"><b>Temp:</b> {_ahm.get("temperature","—")}°C</div>',
          f'<div style="font-size:0.8rem;color:#e2e8f0"><b>Precip Prob:</b> {_ahm.get("precip_prob","—")}%</div>',
          f'<div style="font-size:0.7rem;color:#94a3b8;margin-top:0.3rem">Updated: {str(_ahm.get("recorded_at","—"))[:16]}</div>',
      ]) if _ahm.get("available") else '<div style="font-size:0.8rem;color:#94a3b8">Live data unavailable</div>'}
    </div>
    """, unsafe_allow_html=True)

with _ldi_c2:
    _srt = _lws.get("cities", {}).get("Surat", {})
    st.markdown(f"""
    <div style="background:#1a1d27;border:1px solid #2d3148;border-radius:8px;padding:0.75rem 1rem">
      <div style="font-weight:700;color:#93c5fd;margin-bottom:0.4rem">📍 Surat</div>
      {"".join([
          f'<div style="font-size:0.8rem;color:#e2e8f0"><b>Rainfall:</b> {_srt.get("rainfall_1h","—")} mm/hr</div>',
          f'<div style="font-size:0.8rem;color:#e2e8f0"><b>Condition:</b> {_srt.get("condition","—")}</div>',
          f'<div style="font-size:0.8rem;color:#e2e8f0"><b>Temp:</b> {_srt.get("temperature","—")}°C</div>',
          f'<div style="font-size:0.8rem;color:#e2e8f0"><b>Precip Prob:</b> {_srt.get("precip_prob","—")}%</div>',
          f'<div style="font-size:0.7rem;color:#94a3b8;margin-top:0.3rem">Updated: {str(_srt.get("recorded_at","—"))[:16]}</div>',
      ]) if _srt.get("available") else '<div style="font-size:0.8rem;color:#94a3b8">Live data unavailable</div>'}
    </div>
    """, unsafe_allow_html=True)

with _ldi_c3:
    _cache_age = _lws.get("cache_age_sec")
    _next_refresh = (
        f"{max(0, int(600 - _cache_age))}s" if _cache_age is not None else "—"
    )
    st.markdown(f"""
    <div style="background:#1a1d27;border:1px solid #2d3148;border-radius:8px;padding:0.75rem 1rem">
      <div style="font-weight:700;color:#94a3b8;margin-bottom:0.4rem">📊 Data Status</div>
      <div style="font-size:0.8rem;color:#e2e8f0;margin-bottom:0.25rem"><b>Weather:</b>
        {live_badge() if _is_live else demo_badge()}
      </div>
      <div style="font-size:0.8rem;color:#e2e8f0;margin-bottom:0.25rem"><b>Flood Risk:</b>
        {model_badge()}
      </div>
      <div style="font-size:0.8rem;color:#e2e8f0;margin-bottom:0.25rem"><b>Drainage / Reports:</b>
        {demo_badge()}
      </div>
      <div style="font-size:0.8rem;color:#e2e8f0"><b>Source:</b> {_source}</div>
      <div style="font-size:0.8rem;color:#e2e8f0"><b>Last updated:</b> {str(_last_upd)[:19]}</div>
      <div style="font-size:0.8rem;color:#e2e8f0"><b>Next refresh:</b> {_next_refresh}</div>
      {f'<div style="font-size:0.75rem;color:#f97316;margin-top:0.3rem">⚠ {_fallback[:80]}</div>' if _fallback else ""}
      <div style="font-size:0.7rem;color:#94a3b8;margin-top:0.4rem;border-top:1px solid #2d3148;padding-top:0.3rem">
        🟢 LIVE = Open-Meteo weather evidence<br>
        🔵 MODEL = ML flood-risk prediction<br>
        🟡 DEMO = synthetic drainage / reports / teams<br>
        Live weather is <b>evidence</b> — not a confirmed flood location.
      </div>
    </div>
    """, unsafe_allow_html=True)

# Manual refresh button
_ref_col, _ = st.columns([1, 3])
with _ref_col:
    if st.button("🔄 Refresh Live Data", key="live_refresh_btn", use_container_width=True):
        try:
            from services.live_data_manager import get_live_data_manager as _get_ldm
            _get_ldm().refresh(force=True)
            # Re-run the pipeline to blend fresh weather
            with st.spinner("Fetching live weather and re-running pipeline..."):
                orch.run_pipeline(
                    scenario=st.session_state.scenario,
                    city=st.session_state.city_filter,
                )
            st.rerun()
        except Exception as _e:
            st.warning(f"Live refresh unavailable: {_e}")

# ──────────────────────────────────────────────
# Footer
# ──────────────────────────────────────────────
st.markdown("---")
_footer_badge = hybrid_badge() if _is_live else demo_badge()
_footer_note  = (
    "🟢 Live weather from Open-Meteo · 🔵 ML flood-risk prediction · 🟡 Synthetic drainage, reports &amp; teams."
    if _is_live else
    "All data is synthetic/demo — live weather source unavailable."
)
st.markdown(f"""
<div style="text-align:center;color:#475569;font-size:0.72rem">
    FloodGuard AI v1.0 | Municipal Command Center |
    Scenario: {SCENARIOS[st.session_state.scenario]['label']} |
    {_footer_badge}<br>
    {_footer_note}<br>
    AI recommendations require authorized human verification. Not for operational emergency use.
</div>
""", unsafe_allow_html=True)
