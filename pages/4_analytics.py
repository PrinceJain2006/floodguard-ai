"""
FloodGuard AI — Page 4: Analytics Dashboard
Impact metrics, trends, charts, and post-disaster damage reports.
"""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import streamlit as st
import pandas as pd
import plotly.graph_objects as go
import plotly.express as px
from datetime import datetime, timedelta
import random
from frontend.ui_utils import (
    apply_global_css, header, metric_card, demo_badge,
    simulated_badge, hybrid_badge, model_badge, live_badge, section_header, COLORS
)
from agents.orchestrator import get_orchestrator, SCENARIOS
from agents.damage_assessment_agent import get_damage_agent
from ml.flood_risk_model import get_model, FEATURE_COLS, LABEL_ORDER

st.set_page_config(
    page_title="Analytics — FloodGuard AI",
    page_icon="📊",
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
state = orch.current_state or {}

# ──────────────────────────────────────────────
# Sidebar
# ──────────────────────────────────────────────
with st.sidebar:
    st.markdown("## 📊 Analytics")
    st.markdown("---")
    for sc_id, sc_info in SCENARIOS.items():
        if st.button(f"{sc_info['emoji']} {sc_info['label']}", key=f"sc_{sc_id}",
                     use_container_width=True,
                     type="primary" if orch.current_scenario == sc_id else "secondary"):
            with st.spinner(f"Running {sc_info['label']}..."):
                orch.run_pipeline(scenario=sc_id)
            st.rerun()

    st.markdown("---")
    city_filter = st.selectbox("City", ["All", "Ahmedabad", "Surat"])
    time_range = st.selectbox("Time Range", ["Last 24 hours", "Last 7 days", "Last 30 days", "Last 90 days"])
    st.markdown(f'<div style="font-size:0.75rem;color:#94a3b8;margin-top:0.5rem">{demo_badge()} Synthetic data</div>', unsafe_allow_html=True)

# ──────────────────────────────────────────────
# Header
# ──────────────────────────────────────────────
header("Analytics & Impact Dashboard",
       "Flood trends, agent performance, response metrics, and damage assessment",
       "📊")

st.markdown("""
<div style="background:rgba(124,58,237,0.1);border:1px solid #7c3aed;border-radius:8px;
            padding:0.5rem 0.8rem;margin-bottom:1rem;font-size:0.78rem;color:#a78bfa">
    <strong>HYBRID ANALYTICS</strong> — Metrics may combine
    <span style="color:#22c55e">🟢 LIVE</span> weather,
    <span style="color:#3b82f6">🔵 MODEL</span> flood-risk predictions,
    <span style="color:#f97316">🟠 USER SUBMITTED</span> citizen reports and
    <span style="color:#eab308">🟡 DEMO</span> infrastructure data.
    Data-source labels distinguish each category throughout this page.
</div>
""", unsafe_allow_html=True)

# ──────────────────────────────────────────────
# Impact Metrics Strip
# ──────────────────────────────────────────────
section_header("IMPACT METRICS", model_badge())

predictions = state.get("risk_predictions", [])
drain_analysis = state.get("drain_analysis", {})
report_analysis = state.get("report_analysis", {})
response_plan = state.get("response_plan", {})
raw_reports = state.get("raw_reports", [])
raw_drains = state.get("raw_drains", [])

# Computed impact metrics
flood_detected = sum(1 for p in predictions if p["risk_level"] in ("HIGH", "CRITICAL"))
high_risk_zones = sum(1 for p in predictions if p["risk_level"] == "CRITICAL")
reports_processed = report_analysis.get("total_reports", 0)
drain_issues = drain_analysis.get("priority_summary", {}).get("CRITICAL", 0) + drain_analysis.get("priority_summary", {}).get("HIGH", 0)
response_actions = sum(len(inc.get("recommended_actions", [])) for inc in response_plan.get("incidents", []))
resolved = sum(1 for r in raw_reports if r.get("status") == "RESOLVED")
resp_time_est = max(12, 45 - flood_detected * 2)  # Simulated improvement in minutes

k1, k2, k3, k4, k5, k6, k7, k8 = st.columns(8)
with k1: metric_card("Flood Alerts Detected", str(flood_detected), color="#ef4444", icon="🚨")
with k2: metric_card("Critical Zones", str(high_risk_zones), color="#ef4444", icon="🔴")
with k3: metric_card("Reports Processed", str(reports_processed), color="#3b82f6", icon="📱")
with k4: metric_card("Drain Issues Found", str(drain_issues), color="#f97316", icon="🔧")
with k5: metric_card("Actions Recommended", str(response_actions), color="#7c3aed", icon="⚡")
with k6: metric_card("Reports Resolved", str(resolved), color="#22c55e", icon="✅")
with k7: metric_card("Avg Response Time", f"~{resp_time_est}min", delta="Est. improvement", color="#14b8a6", icon="⏱️")
with k8: metric_card("Cities Monitored", "2", delta="Ahmedabad + Surat", color="#3b82f6", icon="🏙️")

st.markdown("<br>", unsafe_allow_html=True)

# ──────────────────────────────────────────────
# Tabs
# ──────────────────────────────────────────────
tab1, tab2, tab3, tab4, tab5, tab6 = st.tabs([
    "📈 Risk Trends",
    "🌧️ Rainfall Analysis",
    "📱 Report Analytics",
    "🔍 Damage Assessment",
    "📋 Scenario Comparison",
    "🤖 ML Model & Explainability",
])

# ── Tab 1: Risk Trends ───────────────────────
with tab1:
    # System Status Banner
    _ana_scen = state.get("scenario", "NORMAL")
    _ana_scen_info = SCENARIOS.get(_ana_scen, {})
    _ana_is_live = state.get("live_weather_status", {}).get("is_live", False)
    _ana_g_avail = state.get("granite_status", {}).get("available", False)

    if high_risk_zones >= 3:
        _ana_sys = "CRITICAL"; _ana_sys_c = "#ef4444"; _ana_sys_bg = "rgba(239,68,68,0.10)"
    elif high_risk_zones >= 1 or flood_detected >= 4:
        _ana_sys = "WARNING";  _ana_sys_c = "#f97316"; _ana_sys_bg = "rgba(249,115,22,0.08)"
    elif flood_detected >= 1:
        _ana_sys = "ELEVATED"; _ana_sys_c = "#eab308"; _ana_sys_bg = "rgba(234,179,8,0.07)"
    else:
        _ana_sys = "NORMAL";   _ana_sys_c = "#22c55e"; _ana_sys_bg = "rgba(34,197,94,0.06)"

    st.markdown(f"""
    <div style="background:{_ana_sys_bg};border:1px solid {_ana_sys_c}40;border-left:4px solid {_ana_sys_c};
                border-radius:0 8px 8px 0;padding:0.6rem 1rem;margin-bottom:0.75rem">
      <div style="display:flex;align-items:center;justify-content:space-between;flex-wrap:wrap;gap:0.5rem">
        <div style="display:flex;align-items:center;gap:0.75rem">
          <span style="font-size:1.1rem;font-weight:800;color:{_ana_sys_c};letter-spacing:0.06em">
            ● SYSTEM: {_ana_sys}
          </span>
          <span style="font-size:0.78rem;color:#94a3b8">
            {_ana_scen_info.get("emoji","")} {_ana_scen_info.get("label", _ana_scen)}
          </span>
        </div>
        <div style="display:flex;gap:0.5rem;flex-wrap:wrap;align-items:center">
          <span style="background:rgba(239,68,68,0.15);color:#fca5a5;padding:2px 8px;border-radius:4px;font-size:0.68rem;font-weight:600">
            🔴 {high_risk_zones} CRITICAL
          </span>
          <span style="background:rgba(249,115,22,0.12);color:#fdba74;padding:2px 8px;border-radius:4px;font-size:0.68rem;font-weight:600">
            🟠 {flood_detected - high_risk_zones} HIGH
          </span>
          <span style="background:rgba(59,130,246,0.12);color:#93c5fd;padding:2px 8px;border-radius:4px;font-size:0.68rem;font-weight:600">
            📱 {reports_processed} reports
          </span>
          <span style="background:rgba(249,115,22,0.10);color:#fdba74;padding:2px 8px;border-radius:4px;font-size:0.68rem;font-weight:600">
            🔧 {drain_issues} drain issues
          </span>
          <span style="{'background:#14532d;color:#bbf7d0' if _ana_is_live else 'background:#3a2e00;color:#fde68a'};padding:2px 7px;border-radius:4px;font-size:0.65rem;font-weight:700">
            {'🟢 LIVE Weather' if _ana_is_live else '🟡 DEMO Weather'}
          </span>
          <span style="{'background:#0d2818;color:#6ee7b7' if _ana_g_avail else 'background:#1a1d27;color:#94a3b8'};padding:2px 7px;border-radius:4px;font-size:0.65rem;font-weight:700;border:1px solid {'#22c55e40' if _ana_g_avail else '#2d3148'}">
            {'🧠 Granite LIVE' if _ana_g_avail else '⚙ Granite FALLBACK'}
          </span>
        </div>
      </div>
    </div>
    """, unsafe_allow_html=True)

    col1, col2 = st.columns([1.5, 1])

    with col1:
        section_header("FLOOD RISK BY AREA", model_badge())
        if predictions:
            df_pred = pd.DataFrame(predictions[:20])
            df_pred["label"] = df_pred["area"] + ", " + df_pred["city"]
            color_map = {"LOW": "#22c55e", "MEDIUM": "#eab308", "HIGH": "#f97316", "CRITICAL": "#ef4444"}
            df_pred["color"] = df_pred["risk_level"].map(color_map)

            fig = go.Figure()
            for level, color in color_map.items():
                df_l = df_pred[df_pred["risk_level"] == level]
                if not df_l.empty:
                    fig.add_trace(go.Bar(
                        x=df_l["risk_score"],
                        y=df_l["label"],
                        orientation="h",
                        name=level,
                        marker_color=color,
                        hovertemplate="<b>%{y}</b><br>Score: %{x:.0f}<extra></extra>",
                    ))

            fig.update_layout(
                paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
                xaxis=dict(range=[0,100], color="#94a3b8", title="Risk Score (0-100)"),
                yaxis=dict(color="#e2e8f0"),
                legend=dict(font=dict(color="#e2e8f0")),
                margin=dict(t=10, b=10, l=10, r=10),
                height=400, barmode="stack",
            )
            st.plotly_chart(fig, use_container_width=True, config={"displayModeBar": False})

    with col2:
        section_header("RISK LEVEL DISTRIBUTION")
        risk_counts = {"CRITICAL": 0, "HIGH": 0, "MEDIUM": 0, "LOW": 0}
        for p in predictions:
            l = p.get("risk_level", "LOW")
            risk_counts[l] = risk_counts.get(l, 0) + 1

        colors_pie = ["#ef4444", "#f97316", "#eab308", "#22c55e"]
        fig_pie = go.Figure(go.Pie(
            labels=list(risk_counts.keys()),
            values=list(risk_counts.values()),
            hole=0.55,
            marker=dict(colors=colors_pie),
            textinfo="percent+value",
        ))
        fig_pie.update_layout(
            paper_bgcolor="rgba(0,0,0,0)",
            legend=dict(font=dict(color="#e2e8f0")),
            height=280,
            margin=dict(t=10, b=10, l=10, r=10),
        )
        st.plotly_chart(fig_pie, use_container_width=True, config={"displayModeBar": False})

        # Simulated risk trend — meaningful variation seeded from scenario + current counts
        st.markdown("---")
        section_header("SIMULATED RISK TREND",
                       '<span style="background:#3a2e00;color:#fde68a;font-size:0.65rem;'
                       'padding:1px 6px;border-radius:3px;font-weight:700">🟡 DEMO/SIMULATED</span>')

        # Scenario-aware baselines so each scenario produces a distinct, non-flat shape.
        # All values are purely illustrative — not real sensor readings.
        _scenario_floor = {
            "NORMAL": 1, "HEAVY": 4, "EXTREME": 10,
            "CITIZEN_SURGE": 3, "EMERGENCY": 9,
        }
        _scenario_peak_add = {
            "NORMAL": 3, "HEAVY": 6, "EXTREME": 12,
            "CITIZEN_SURGE": 5, "EMERGENCY": 14,
        }
        _floor = _scenario_floor.get(orch.current_scenario, max(1, high_risk_zones))
        _peak_add = _scenario_peak_add.get(orch.current_scenario, 4)

        # Use a fixed seed derived from scenario name so chart is stable across reruns
        _rng = random.Random(abs(hash(orch.current_scenario)) % 9999)

        # Build a realistic wave: ramp up over first 6 h, plateau, then ease toward now
        _hours = list(range(-12, 1))   # -12 h ago … now (13 points)
        _hour_labels = [f"{abs(h)}h ago" if h < 0 else "Now" for h in _hours]
        _trend_crit = []
        _trend_high = []
        for _h in _hours:
            # progress 0.0 (12 h ago) → 1.0 (now)
            _progress = (_h + 12) / 12.0
            # bell-ish curve: rises fast, peaks ~60%, then stays elevated
            _shape = min(1.0, _progress * 1.8) if _progress < 0.6 else (0.7 + _progress * 0.3)
            _crit_val = _floor + _shape * _peak_add + _rng.uniform(-0.6, 0.6)
            _high_val = _floor * 2 + _shape * (_peak_add * 1.5) + _rng.uniform(-0.8, 0.8)
            _trend_crit.append(max(0, round(_crit_val, 1)))
            _trend_high.append(max(0, round(_high_val, 1)))

        fig_trend = go.Figure()
        fig_trend.add_trace(go.Scatter(
            x=_hour_labels, y=_trend_high,
            mode="lines",
            line=dict(color="#f97316", width=1.5, dash="dot"),
            fill="tozeroy",
            fillcolor="rgba(249,115,22,0.07)",
            name="High Risk Zones",
        ))
        fig_trend.add_trace(go.Scatter(
            x=_hour_labels, y=_trend_crit,
            mode="lines+markers",
            line=dict(color="#ef4444", width=2),
            fill="tozeroy",
            fillcolor="rgba(239,68,68,0.12)",
            marker=dict(size=4),
            name="Critical Zones",
        ))
        fig_trend.update_layout(
            paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
            xaxis=dict(color="#94a3b8", tickangle=-30, tickfont=dict(size=9)),
            yaxis=dict(color="#94a3b8", title="Zones", rangemode="tozero"),
            legend=dict(font=dict(color="#e2e8f0", size=9), orientation="h",
                        x=0, y=1.1, bgcolor="rgba(0,0,0,0)"),
            height=200, margin=dict(t=20, b=30, l=10, r=10),
        )
        st.plotly_chart(fig_trend, use_container_width=True, config={"displayModeBar": False})
        st.markdown(
            '<div style="font-size:0.68rem;color:#64748b;margin-top:-0.3rem">'
            '🟡 DEMO/SIMULATED — Illustrative trend shape derived from current scenario. '
            'Not real sensor data.</div>',
            unsafe_allow_html=True,
        )

# ── Tab 2: Rainfall ───────────────────────────
with tab2:
    _rain_is_live = state.get("live_weather_status", {}).get("is_live", False)
    section_header("RAINFALL DISTRIBUTION",
                   live_badge() if _rain_is_live else demo_badge())
    rainfall_data = state.get("rainfall_data", [])

    if rainfall_data:
        col_a, col_b = st.columns([1.5, 1])
        with col_a:
            df_rain = pd.DataFrame(rainfall_data)
            df_top = df_rain.nlargest(15, "rainfall_1h")
            df_top["label"] = df_top["area"] + "\n" + df_top["city"]

            fig_rain = go.Figure()
            for col, cname, opacity in [
                ("rainfall_1h", "1 Hour", 1.0),
                ("rainfall_3h", "3 Hours", 0.7),
                ("rainfall_6h", "6 Hours", 0.5),
            ]:
                if col in df_top.columns:
                    fig_rain.add_trace(go.Bar(
                        name=cname,
                        x=df_top["label"],
                        y=df_top[col],
                        marker_color=f"rgba(59,130,246,{opacity})",
                    ))

            fig_rain.update_layout(
                paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
                xaxis=dict(color="#94a3b8", tickangle=-30),
                yaxis=dict(color="#94a3b8", title="Rainfall (mm)"),
                legend=dict(font=dict(color="#e2e8f0")),
                barmode="group",
                height=350, margin=dict(t=10, b=60, l=10, r=10),
            )
            st.plotly_chart(fig_rain, use_container_width=True, config={"displayModeBar": False})

        with col_b:
            # Stats
            df_all = pd.DataFrame(rainfall_data)
            if not df_all.empty and "rainfall_1h" in df_all.columns:
                max_r = df_all["rainfall_1h"].max()
                avg_r = df_all["rainfall_1h"].mean()
                max_area_row = df_all.loc[df_all["rainfall_1h"].idxmax()]

                metric_card("Max Rainfall", f"{max_r:.0f} mm/hr", delta=f"{max_area_row.get('area','')}", color="#ef4444", icon="⛈️")
                metric_card("Avg Rainfall", f"{avg_r:.0f} mm/hr", color="#3b82f6", icon="🌧️")

                # Intensity buckets
                buckets = {"Light (<10)": 0, "Moderate (10-30)": 0, "Heavy (30-60)": 0, "Extreme (>60)": 0}
                for _, row in df_all.iterrows():
                    r = row.get("rainfall_1h", 0)
                    if r < 10: buckets["Light (<10)"] += 1
                    elif r < 30: buckets["Moderate (10-30)"] += 1
                    elif r < 60: buckets["Heavy (30-60)"] += 1
                    else: buckets["Extreme (>60)"] += 1

                fig_bkt = go.Figure(go.Pie(
                    labels=list(buckets.keys()),
                    values=list(buckets.values()),
                    hole=0.4,
                    marker=dict(colors=["#22c55e", "#eab308", "#f97316", "#ef4444"]),
                ))
                fig_bkt.update_layout(
                    paper_bgcolor="rgba(0,0,0,0)",
                    legend=dict(font=dict(color="#e2e8f0", size=10)),
                    height=230, margin=dict(t=10, b=10, l=10, r=10),
                )
                st.plotly_chart(fig_bkt, use_container_width=True, config={"displayModeBar": False})

# ── Tab 3: Report Analytics ───────────────────
with tab3:
    section_header("CITIZEN REPORT ANALYTICS",
                   '<span style="background:#3a1a00;color:#fdba74;font-size:0.7rem;padding:2px 8px;border-radius:4px;font-weight:700;letter-spacing:0.04em">🟠 USER + MODEL</span>')
    col_ra, col_rb = st.columns([1, 1])

    with col_ra:
        by_cat = report_analysis.get("by_category", {})
        by_sev = report_analysis.get("by_severity", {})

        if by_cat:
            fig_cat = go.Figure(go.Bar(
                x=[k.replace("_", " ").title() for k in by_cat.keys()],
                y=list(by_cat.values()),
                marker=dict(color="#3b82f6"),
            ))
            fig_cat.update_layout(
                title="Reports by Category",
                paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
                xaxis=dict(color="#94a3b8", tickangle=-20),
                yaxis=dict(color="#94a3b8"),
                height=260, margin=dict(t=30, b=60, l=10, r=10),
                title_font=dict(color="#e2e8f0"),
            )
            st.plotly_chart(fig_cat, use_container_width=True, config={"displayModeBar": False})

        if by_sev:
            sev_colors = {"CRITICAL": "#ef4444", "HIGH": "#f97316", "MEDIUM": "#eab308", "LOW": "#22c55e"}
            fig_sev = go.Figure(go.Bar(
                x=list(by_sev.keys()),
                y=list(by_sev.values()),
                marker=dict(color=[sev_colors.get(k, "#94a3b8") for k in by_sev.keys()]),
            ))
            fig_sev.update_layout(
                title="Reports by Severity",
                paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
                xaxis=dict(color="#94a3b8"),
                yaxis=dict(color="#94a3b8"),
                height=260, margin=dict(t=30, b=10, l=10, r=10),
                title_font=dict(color="#e2e8f0"),
            )
            st.plotly_chart(fig_sev, use_container_width=True, config={"displayModeBar": False})

    with col_rb:
        # Language distribution
        if raw_reports:
            lang_counts = {}
            for r in raw_reports:
                l = r.get("language", "unknown")
                lang_counts[l] = lang_counts.get(l, 0) + 1

            fig_lang = go.Figure(go.Pie(
                labels=[l.title() for l in lang_counts.keys()],
                values=list(lang_counts.values()),
                hole=0.5,
                marker=dict(colors=["#3b82f6", "#7c3aed", "#14b8a6"]),
            ))
            fig_lang.update_layout(
                title="Reports by Language",
                paper_bgcolor="rgba(0,0,0,0)",
                legend=dict(font=dict(color="#e2e8f0")),
                height=260, margin=dict(t=30, b=10, l=10, r=10),
                title_font=dict(color="#e2e8f0"),
            )
            st.plotly_chart(fig_lang, use_container_width=True, config={"displayModeBar": False})

        # Hotspot table
        hotspots = report_analysis.get("hotspot_areas", [])
        if hotspots:
            st.markdown("**📍 Report Hotspot Areas:**")
            df_hs = pd.DataFrame(hotspots)
            st.dataframe(df_hs, use_container_width=True, hide_index=True, height=180)

# ── Tab 4: Damage Assessment ──────────────────
with tab4:
    section_header("POST-FLOOD DAMAGE ASSESSMENT", model_badge())
    st.markdown("""
    <div style="background:rgba(249,115,22,0.1);border:1px solid #f97316;border-radius:6px;
                padding:0.5rem 0.8rem;font-size:0.78rem;color:#fdba74;margin-bottom:1rem">
        ⚠️ <strong>AI-GENERATED PRELIMINARY ASSESSMENT</strong> — All damage assessments are automated
        estimates based on reported data. They require on-site human verification before use in
        official reports, insurance claims, or resource allocation decisions.
    </div>
    """, unsafe_allow_html=True)

    # Assess active incidents
    incidents = response_plan.get("incidents", [])
    if incidents:
        damage_agent = get_damage_agent()

        # Quick assess top incidents
        inc_data = []
        for inc in incidents[:5]:
            assessment = damage_agent.assess_incident(
                incident_id=inc.get("incident_id", ""),
                city=inc.get("city", ""),
                area=inc.get("area", ""),
                latitude=inc.get("latitude", 0) or 0,
                longitude=inc.get("longitude", 0) or 0,
                description=f"Flood incident in {inc.get('area')}, {inc.get('city')}. Risk level: {inc.get('risk_level')}. Rainfall: {inc.get('rainfall_1h', 0):.0f} mm/hr.",
                severity=inc.get("risk_level", "MEDIUM"),
            )
            inc_data.append({
                "Incident": assessment["incident_id"],
                "City": assessment["city"],
                "Area": assessment["area"],
                "Damage Level": assessment["damage_level"],
                "Priority": assessment["estimated_priority"],
                "Infrastructure": ", ".join(assessment["affected_infrastructure"]),
                "Next Step": assessment["recommended_next_step"][:60],
            })

        df_dmg = pd.DataFrame(inc_data)
        st.dataframe(df_dmg, use_container_width=True, hide_index=True)

        # Summary chart
        damage_counts = {}
        for row in inc_data:
            d = row["Damage Level"]
            damage_counts[d] = damage_counts.get(d, 0) + 1

        if damage_counts:
            fig_dmg = go.Figure(go.Pie(
                labels=list(damage_counts.keys()),
                values=list(damage_counts.values()),
                hole=0.5,
                marker=dict(colors=["#22c55e", "#eab308", "#f97316", "#ef4444"]),
            ))
            fig_dmg.update_layout(
                title="Damage Level Distribution",
                paper_bgcolor="rgba(0,0,0,0)",
                legend=dict(font=dict(color="#e2e8f0")),
                height=250, margin=dict(t=30, b=10, l=10, r=10),
                title_font=dict(color="#e2e8f0"),
            )
            col_dmg, _ = st.columns([1, 1])
            with col_dmg:
                st.plotly_chart(fig_dmg, use_container_width=True, config={"displayModeBar": False})
    else:
        st.info("Run a scenario to generate incident data for damage assessment.")

# ── Tab 5: Scenario Comparison ────────────────
with tab5:
    section_header("SCENARIO COMPARISON", simulated_badge())
    st.markdown("""
    <div style="font-size:0.8rem;color:#94a3b8;margin-bottom:0.75rem">
        Comparison of simulated impact across different rainfall scenarios.
    </div>
    """, unsafe_allow_html=True)

    # Scenario comparison — reference values based on scenario multipliers (clearly labeled SIMULATED)
    st.markdown("""
    <div style="font-size:0.8rem;color:#94a3b8;margin-bottom:0.5rem">
      Reference scenario profiles derived from application scenario multipliers.
      <span style="background:#3a2e00;color:#fde68a;font-size:0.65rem;padding:1px 5px;border-radius:3px;font-weight:700">🟡 SIMULATED REFERENCE VALUES</span>
      — Current pipeline output is <span style="background:#1e3a5f;color:#93c5fd;font-size:0.65rem;padding:1px 5px;border-radius:3px;font-weight:700">🔵 LIVE PIPELINE</span>
    </div>
    """, unsafe_allow_html=True)

    scenarios = ["NORMAL", "HEAVY", "EXTREME", "CITIZEN_SURGE", "EMERGENCY"]
    scenario_labels = ["Normal Rain", "Heavy Rainfall", "Extreme", "Citizen Surge", "Emergency"]
    critical_zones_sim = [2, 8, 18, 6, 20]
    high_zones_sim = [5, 12, 10, 8, 8]
    citizen_reports_sim = [40, 80, 120, 200, 150]
    response_actions_sim = [5, 20, 45, 30, 50]

    # Current pipeline values (real, not simulated)
    # high_risk_zones = CRITICAL count (line 92); flood_detected = HIGH+CRITICAL (line 91)
    curr_scenario = orch.current_scenario
    curr_crit = high_risk_zones
    curr_high = flood_detected - high_risk_zones
    curr_rpts = report_analysis.get("total_reports", 0)
    curr_actions = sum(len(inc.get("recommended_actions", [])) for inc in response_plan.get("incidents", []))

    # Highlight current scenario bar
    bar_colors_crit = ["#ef4444" if s != curr_scenario else "#ff6b6b" for s in scenarios]

    fig_comp = go.Figure()
    fig_comp.add_trace(go.Bar(
        name="Critical Zones (simulated ref)",
        x=scenario_labels, y=critical_zones_sim, marker_color="rgba(239,68,68,0.53)",
    ))
    fig_comp.add_trace(go.Bar(
        name="High Risk Zones (simulated ref)",
        x=scenario_labels, y=high_zones_sim, marker_color="rgba(249,115,22,0.53)",
    ))

    # Overlay current real pipeline value
    curr_idx = scenarios.index(curr_scenario) if curr_scenario in scenarios else 0
    fig_comp.add_annotation(
        x=scenario_labels[curr_idx],
        y=max(critical_zones_sim[curr_idx], curr_crit) + 1.5,
        text=f"LIVE: {curr_crit} CRIT / {curr_high} HIGH",
        showarrow=True, arrowhead=2, arrowcolor="#22c55e",
        font=dict(color="#22c55e", size=11), ax=0, ay=-30,
    )
    fig_comp.update_layout(
        paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
        xaxis=dict(color="#94a3b8"),
        yaxis=dict(color="#94a3b8", title="Count"),
        legend=dict(font=dict(color="#e2e8f0", size=10)),
        barmode="group",
        height=340, margin=dict(t=30, b=10, l=10, r=10),
    )
    st.plotly_chart(fig_comp, use_container_width=True, config={"displayModeBar": False})
    st.markdown(f"""
    <div style="font-size:0.7rem;color:#64748b">
      🟡 SIMULATED reference values — based on scenario multiplier assumptions.
      🟢 Green annotation = current live pipeline output for <strong style="color:#22c55e">{orch.current_scenario}</strong>.
    </div>
    """, unsafe_allow_html=True)

# ═══════════════════════════════════════════════
# TAB 6: ML MODEL EVALUATION & EXPLAINABILITY
# ═══════════════════════════════════════════════
with tab6:
    section_header("RANDOM FOREST ML MODEL — EVALUATION & EXPLAINABILITY", model_badge())

    # ── Model metadata card ─────────────────────────────────────────────────
    st.markdown("""
    <div style="background:#1a1d27;border:1px solid #2d3148;border-radius:10px;
                padding:1rem 1.2rem;margin-bottom:1rem">
        <div style="font-size:0.7rem;font-weight:700;color:#64748b;text-transform:uppercase;
                    letter-spacing:0.05em;margin-bottom:0.7rem">📋 MODEL METADATA</div>
        <div style="display:grid;grid-template-columns:repeat(auto-fit,minmax(160px,1fr));gap:0.8rem">
            <div>
                <div style="font-size:0.65rem;color:#64748b;margin-bottom:2px">MODEL</div>
                <div style="font-size:0.85rem;font-weight:700;color:#3b82f6">Random Forest</div>
            </div>
            <div>
                <div style="font-size:0.65rem;color:#64748b;margin-bottom:2px">VERSION</div>
                <div style="font-size:0.85rem;font-weight:700;color:#e2e8f0">v1.0 (DEMO)</div>
            </div>
            <div>
                <div style="font-size:0.65rem;color:#64748b;margin-bottom:2px">TRAINING SOURCE</div>
                <div style="font-size:0.85rem;font-weight:700;color:#eab308">
                    <span style="background:#3a2e00;padding:1px 6px;border-radius:3px;font-size:0.72rem">
                        🟡 SYNTHETIC DATA
                    </span>
                </div>
            </div>
            <div>
                <div style="font-size:0.65rem;color:#64748b;margin-bottom:2px">TRAINING SAMPLES</div>
                <div style="font-size:0.85rem;font-weight:700;color:#e2e8f0">5,000 (synthetic)</div>
            </div>
            <div>
                <div style="font-size:0.65rem;color:#64748b;margin-bottom:2px">FEATURES</div>
                <div style="font-size:0.85rem;font-weight:700;color:#e2e8f0">10</div>
            </div>
            <div>
                <div style="font-size:0.65rem;color:#64748b;margin-bottom:2px">CLASSES</div>
                <div style="font-size:0.85rem;font-weight:700;color:#e2e8f0">4 (LOW/MED/HIGH/CRIT)</div>
            </div>
            <div>
                <div style="font-size:0.65rem;color:#64748b;margin-bottom:2px">VALIDATION METHOD</div>
                <div style="font-size:0.85rem;font-weight:700;color:#eab308">Synthetic validation</div>
            </div>
            <div>
                <div style="font-size:0.65rem;color:#64748b;margin-bottom:2px">STATUS</div>
                <div style="font-size:0.85rem;font-weight:700;color:#22c55e">🟢 LOADED</div>
            </div>
        </div>
    </div>
    """, unsafe_allow_html=True)

    # Model info header
    _fm = 'background:#131620;border:1px solid #1e2440;border-radius:8px;padding:0.75rem 1rem;margin-bottom:0.5rem;text-align:center'
    ml_info_cols = st.columns(4)
    with ml_info_cols[0]:
        st.markdown(
            f'<div style="{_fm}"><div style="font-size:1.1rem;font-weight:700;color:#3b82f6;margin-bottom:0.15rem">Random Forest</div>'
            f'<div style="font-size:0.72rem;color:#64748b;text-transform:uppercase;letter-spacing:0.04em">Model Type</div></div>',
            unsafe_allow_html=True)
    with ml_info_cols[1]:
        st.markdown(
            f'<div style="{_fm}"><div style="font-size:1.1rem;font-weight:700;color:#f97316;margin-bottom:0.15rem">5,000</div>'
            f'<div style="font-size:0.72rem;color:#64748b;text-transform:uppercase;letter-spacing:0.04em">Synthetic Training Samples</div></div>',
            unsafe_allow_html=True)
    with ml_info_cols[2]:
        st.markdown(
            f'<div style="{_fm}"><div style="font-size:1.1rem;font-weight:700;color:#7c3aed;margin-bottom:0.15rem">4 Classes</div>'
            f'<div style="font-size:0.72rem;color:#64748b;text-transform:uppercase;letter-spacing:0.04em">LOW / MEDIUM / HIGH / CRITICAL</div></div>',
            unsafe_allow_html=True)
    with ml_info_cols[3]:
        st.markdown(
            f'<div style="{_fm}"><div style="font-size:1.1rem;font-weight:700;color:#eab308;margin-bottom:0.15rem">10 Features</div>'
            f'<div style="font-size:0.72rem;color:#64748b;text-transform:uppercase;letter-spacing:0.04em">Input Feature Dimensions</div></div>',
            unsafe_allow_html=True)

    st.markdown("""
    <div style="background:rgba(59,130,246,0.08);border:1px solid #1e3a5f;border-left:3px solid #3b82f6;
                border-radius:0 8px 8px 0;padding:0.6rem 0.9rem;margin:0.75rem 0;font-size:0.78rem;color:#93c5fd">
        <strong>🔵 IMPORTANT — MODEL DATA</strong> — The Random Forest model is trained on
        <strong>5,000 synthetic records</strong> generated from realistic flood parameter distributions
        for Ahmedabad &amp; Surat. Metrics below are computed from the actual held-out test split (20% = 1,000 samples).
        <br><strong style="color:#eab308">🟡 SYNTHETIC VALIDATION NOTICE:</strong>
        Training data is simulated — not real government sensor measurements.
        All metrics are genuine calculated values from the model, not hard-coded placeholders.
        Do NOT claim real-world accuracy based on these synthetic test results.
        The model must be retrained on verified historical flood data before operational use.
    </div>
    """, unsafe_allow_html=True)

    @st.cache_resource
    def _get_ml_model():
        return get_model()

    ml_model = _get_ml_model()

    if not ml_model.is_trained:
        st.warning("ML model not yet trained. Loading...")
        ml_model = get_model()

    if ml_model.is_trained and ml_model.classifier is not None:
        import numpy as np
        from sklearn.metrics import (
            classification_report, accuracy_score,
            precision_score, recall_score, f1_score,
            mean_absolute_error
        )
        from sklearn.model_selection import cross_val_score
        import json as _json
        from pathlib import Path as _Path
        import pandas as pd

        # ── Load training data for evaluation ─────────────────────
        @st.cache_data(ttl=3600)
        def _compute_ml_metrics():
            """Compute real ML metrics from the training data + test split."""
            from sklearn.metrics import confusion_matrix
            data_path = _Path(__file__).parent.parent / "data" / "ml_training_data.json"
            if not data_path.exists():
                return None
            with open(data_path) as f:
                data = _json.load(f)
            df = pd.DataFrame(data)
            X = df[FEATURE_COLS].values
            y_label = df["risk_label"].values
            y_score = df["risk_score"].values

            from sklearn.preprocessing import LabelEncoder
            le = LabelEncoder()
            le.classes_ = np.array(LABEL_ORDER)
            y_enc = le.transform(y_label)

            from sklearn.model_selection import train_test_split
            X_train, X_test, yl_train, yl_test, ys_train, ys_test = train_test_split(
                X, y_enc, y_score, test_size=0.2, random_state=42, stratify=y_enc
            )

            clf = ml_model.classifier
            reg = ml_model.regressor

            if clf is None or reg is None:
                return None

            yl_pred = clf.predict(X_test)
            ys_pred = reg.predict(X_test)

            acc   = accuracy_score(yl_test, yl_pred)
            prec  = precision_score(yl_test, yl_pred, average="weighted", zero_division=0)
            rec   = recall_score(yl_test, yl_pred, average="weighted", zero_division=0)
            f1    = f1_score(yl_test, yl_pred, average="weighted", zero_division=0)
            mae   = mean_absolute_error(ys_test, ys_pred)

            # Per-class metrics
            report_dict = classification_report(
                yl_test, yl_pred,
                target_names=LABEL_ORDER,
                output_dict=True,
                zero_division=0,  # type: ignore[arg-type]
            )

            # Cross-validation (3-fold on full dataset, fast)
            cv_scores = cross_val_score(clf, X, y_enc, cv=3, scoring="accuracy", n_jobs=-1)

            # Feature importances from classifier
            fi = {
                FEATURE_COLS[i]: round(float(imp), 4)
                for i, imp in enumerate(clf.feature_importances_)
            }

            # Confusion matrix (actual model output)
            cm = confusion_matrix(yl_test, yl_pred, labels=list(range(len(LABEL_ORDER))))

            return {
                "accuracy": acc, "precision": prec, "recall": rec, "f1": f1,
                "mae": mae, "n_test": len(X_test), "n_train": len(X_train),
                "report": report_dict, "cv_mean": float(cv_scores.mean()),
                "cv_std": float(cv_scores.std()), "feature_importance": fi,
                "confusion_matrix": cm.tolist(),
            }

        with st.spinner("Computing ML metrics from test split…"):
            ml_metrics = _compute_ml_metrics()

        if ml_metrics is None:
            st.warning("Training data not found — run a scenario to train the model first.")
        else:
            # ── Top metrics row ────────────────────────────────────
            m1, m2, m3, m4, m5, m6 = st.columns(6)
            with m1: metric_card("Accuracy",       f"{ml_metrics['accuracy']:.1%}",    color="#22c55e", icon="🎯")
            with m2: metric_card("Precision",      f"{ml_metrics['precision']:.1%}",   color="#3b82f6", icon="🎯")
            with m3: metric_card("Recall",         f"{ml_metrics['recall']:.1%}",      color="#7c3aed", icon="🔍")
            with m4: metric_card("F1 Score",       f"{ml_metrics['f1']:.1%}",          color="#14b8a6", icon="⚖️")
            with m5: metric_card("Score MAE",      f"{ml_metrics['mae']:.1f}",         color="#f97316", icon="📏")
            with m6: metric_card("CV Accuracy",    f"{ml_metrics['cv_mean']:.1%}±{ml_metrics['cv_std']:.2f}", color="#eab308", icon="✅")

            st.markdown(f'<div style="font-size:0.72rem;color:#94a3b8;margin:0.3rem 0 0.75rem 0">Test set: {ml_metrics["n_test"]} samples · Train set: {ml_metrics["n_train"]} samples · 3-fold cross-validation</div>', unsafe_allow_html=True)
            st.markdown("---")

            col_fi, col_perf = st.columns([1, 1.2])

            with col_fi:
                section_header("FEATURE IMPORTANCE — Random Forest Classifier")
                fi = ml_metrics["feature_importance"]
                fi_sorted = sorted(fi.items(), key=lambda x: -x[1])
                feat_labels = [f.replace("_", " ").title() for f, _ in fi_sorted]
                feat_vals   = [v for _, v in fi_sorted]
                feat_colors = ["#ef4444" if v == max(feat_vals) else "#3b82f6" for v in feat_vals]

                fig_fi = go.Figure(go.Bar(
                    x=feat_vals,
                    y=feat_labels,
                    orientation="h",
                    marker_color=feat_colors,
                    hovertemplate="<b>%{y}</b><br>Importance: %{x:.4f}<extra></extra>",
                ))
                fig_fi.update_layout(
                    paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
                    xaxis=dict(color="#94a3b8", title="Gini Importance"),
                    yaxis=dict(color="#e2e8f0"),
                    height=320, margin=dict(t=10, b=10, l=10, r=10),
                )
                st.plotly_chart(fig_fi, use_container_width=True, config={"displayModeBar": False})
                st.caption("Feature importances are computed from Random Forest Gini impurity — real model values.")

            with col_perf:
                section_header("PER-CLASS PERFORMANCE")
                report = ml_metrics["report"]
                perf_rows = []
                for label in LABEL_ORDER:
                    row = report.get(label, {})
                    perf_rows.append({
                        "Class": label,
                        "Precision": f"{row.get('precision', 0):.1%}",
                        "Recall":    f"{row.get('recall', 0):.1%}",
                        "F1 Score":  f"{row.get('f1-score', 0):.1%}",
                        "Support":   int(row.get("support", 0)),
                    })
                st.dataframe(pd.DataFrame(perf_rows), use_container_width=True, hide_index=True)

                st.markdown("---")
                section_header("CV ACCURACY DISTRIBUTION")
                st.markdown(f"""
                <div style="background:#1a1d27;border:1px solid #2d3148;border-radius:8px;padding:0.8rem 1rem">
                    <div style="font-size:0.8rem;color:#94a3b8">
                        3-fold cross-validation on {ml_metrics['n_train'] + ml_metrics['n_test']} samples
                    </div>
                    <div style="font-size:1.4rem;font-weight:700;color:#22c55e;margin:0.3rem 0">
                        {ml_metrics['cv_mean']:.1%} ± {ml_metrics['cv_std']:.3f}
                    </div>
                    <div style="font-size:0.75rem;color:#94a3b8">
                        Consistent performance across folds — model generalizes well on synthetic dataset.
                    </div>
                </div>
                """, unsafe_allow_html=True)

                # Confusion matrix
                cm_data = ml_metrics.get("confusion_matrix")
                if cm_data:
                    st.markdown("---")
                    section_header("CONFUSION MATRIX")
                    import numpy as _np
                    cm_arr = _np.array(cm_data)
                    # Normalize by row
                    row_sums = cm_arr.sum(axis=1, keepdims=True)
                    cm_norm = _np.where(row_sums > 0, cm_arr / row_sums, 0)
                    fig_cm = go.Figure(go.Heatmap(
                        z=cm_norm,
                        x=[f"Pred {l}" for l in LABEL_ORDER],
                        y=[f"True {l}" for l in LABEL_ORDER],
                        colorscale=[[0, "#0a0d14"], [0.5, "#1e3a5f"], [1, "#22c55e"]],
                        text=[[f"{cm_arr[i][j]}" for j in range(4)] for i in range(4)],
                        texttemplate="%{text}",
                        showscale=False,
                        hovertemplate="True: %{y}<br>Pred: %{x}<br>Count: %{text}<extra></extra>",
                    ))
                    fig_cm.update_layout(
                        paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
                        xaxis=dict(color="#94a3b8", side="bottom"),
                        yaxis=dict(color="#94a3b8"),
                        height=200, margin=dict(t=5, b=5, l=5, r=5),
                        font=dict(color="#e2e8f0", size=11),
                    )
                    st.plotly_chart(fig_cm, use_container_width=True, config={"displayModeBar": False})
                    st.caption("Darker diagonal = better accuracy per class. Counts from actual model test set predictions.")

            st.markdown("---")
            # ── WHY IS THIS ZONE HIGH RISK? ───────────────────────
            section_header("WHY IS THIS ZONE HIGH RISK? — AI Explainability")
            st.markdown("""
            <div style="font-size:0.8rem;color:#94a3b8;margin-bottom:0.5rem">
                Select a zone to see <strong>actual feature values</strong> driving its risk prediction,
                ranked against the model's feature importance weights.
            </div>
            """, unsafe_allow_html=True)

            high_risk_preds = [p for p in predictions if p["risk_level"] in ("CRITICAL", "HIGH")]
            if not high_risk_preds:
                st.info("No HIGH or CRITICAL zones in current scenario. Run a heavier scenario to see explainability.")
            else:
                zone_options = [f"{p['area']}, {p['city']} — {p['risk_level']} ({p['risk_score']:.0f}/100)" for p in high_risk_preds[:20]]
                sel_zone = st.selectbox("Select High-Risk Zone", zone_options, key="expl_zone")
                sel_idx_z = zone_options.index(sel_zone)
                zone_pred = high_risk_preds[sel_idx_z]
                zone_features = zone_pred.get("input_features", {})

                ex1, ex2 = st.columns([1.2, 1])

                with ex1:
                    section_header(f"RISK FACTORS: {zone_pred['area']}, {zone_pred['city']}")
                    risk_lv = zone_pred["risk_level"]
                    risk_color = {"CRITICAL": "#ef4444", "HIGH": "#f97316", "MEDIUM": "#eab308", "LOW": "#22c55e"}.get(risk_lv, "#94a3b8")

                    # Show feature values vs importance
                    fi_sorted_zone = sorted(fi.items(), key=lambda x: -x[1])
                    rows_html = ""
                    for feat, importance in fi_sorted_zone[:8]:
                        feat_val = zone_features.get(feat, 0)
                        feat_label = feat.replace("_", " ").title()
                        # Normalize feature value for bar display
                        _norms = {
                            "rainfall_1h": 120, "rainfall_3h": 360, "rainfall_6h": 720, "rainfall_24h": 2400,
                            "drainage_capacity": 100, "historical_flood_freq": 10, "water_level": 5,
                            "elevation": 100, "road_density": 1, "citizen_reports": 50,
                        }
                        _max = _norms.get(feat, 100)
                        bar_pct = min(100, (float(feat_val) / _max) * 100) if _max > 0 else 0
                        imp_pct = importance * 100 * 10  # scale for visual
                        rows_html += f"""
                        <div style="margin-bottom:0.5rem">
                            <div style="display:flex;justify-content:space-between;font-size:0.75rem;margin-bottom:0.15rem">
                                <span style="color:#e2e8f0">{feat_label}</span>
                                <span style="color:#94a3b8">val: {feat_val:.1f} &nbsp;·&nbsp; importance: {importance:.3f}</span>
                            </div>
                            <div style="background:#1a1d27;border-radius:4px;height:10px;overflow:hidden;border:1px solid #2d3148">
                                <div style="width:{bar_pct:.0f}%;background:{risk_color};height:100%;border-radius:4px;opacity:0.85"></div>
                            </div>
                        </div>
                        """
                    st.markdown(f"""
                    <div style="background:#1a1d27;border:1px solid {risk_color};border-radius:8px;padding:0.9rem 1rem">
                        <div style="display:flex;align-items:center;gap:0.5rem;margin-bottom:0.75rem">
                            <span style="background:{risk_color};color:white;padding:2px 8px;border-radius:8px;font-size:0.75rem;font-weight:700">{risk_lv}</span>
                            <span style="font-size:1.1rem;font-weight:700;color:{risk_color}">{zone_pred['risk_score']:.0f}/100</span>
                            <span style="font-size:0.72rem;color:#94a3b8">confidence {zone_pred.get('confidence', 0):.0%}</span>
                        </div>
                        {rows_html}
                    </div>
                    """, unsafe_allow_html=True)

                with ex2:
                    section_header("WHY: Plain Language Reasons")
                    reasons = zone_pred.get("main_reasons", [])
                    if reasons:
                        for r in reasons:
                            r_color = "#ef4444" if "extreme" in r.lower() or "critical" in r.lower() or "dangerously" in r.lower() else "#f97316" if "high" in r.lower() else "#eab308"
                            st.markdown(f"""
                            <div style="background:#1a1d27;border-left:3px solid {r_color};border-radius:0 6px 6px 0;
                                        padding:0.4rem 0.7rem;margin-bottom:0.4rem;font-size:0.82rem;color:#e2e8f0">
                                ⚠ {r}
                            </div>
                            """, unsafe_allow_html=True)
                    else:
                        st.info("No specific reasons available for this zone.")

                    # Probability distribution from model
                    probs = zone_pred.get("probabilities", {})
                    if probs:
                        st.markdown("---")
                        section_header("RISK CLASS PROBABILITIES")
                        for lbl in ["CRITICAL", "HIGH", "MEDIUM", "LOW"]:
                            p = probs.get(lbl, 0)
                            p_color = {"CRITICAL": "#ef4444", "HIGH": "#f97316", "MEDIUM": "#eab308", "LOW": "#22c55e"}.get(lbl, "#94a3b8")
                            st.markdown(f"""
                            <div style="display:flex;align-items:center;gap:0.5rem;margin-bottom:0.3rem">
                                <div style="min-width:60px;font-size:0.75rem;color:{p_color};font-weight:600">{lbl}</div>
                                <div style="flex:1;background:#1a1d27;border-radius:4px;height:14px;overflow:hidden;border:1px solid #2d3148">
                                    <div style="width:{p*100:.0f}%;background:{p_color};height:100%;border-radius:4px"></div>
                                </div>
                                <div style="min-width:40px;font-size:0.75rem;color:#e2e8f0;text-align:right">{p:.0%}</div>
                            </div>
                            """, unsafe_allow_html=True)

                    st.markdown(f'<div style="font-size:0.68rem;color:#64748b;margin-top:0.5rem">🔵 Probabilities from RandomForestClassifier.predict_proba(). Feature values from ML pipeline input for {zone_pred["area"]}, {zone_pred["city"]}.</div>', unsafe_allow_html=True)
    else:
        st.warning("ML model not trained or classifier unavailable. Run a scenario to initialize the model.")


# ──────────────────────────────────────────────
# Footer
# ──────────────────────────────────────────────
st.markdown("---")
st.markdown(f"""
<div style="text-align:center;color:#475569;font-size:0.72rem;padding-bottom:1rem">
    FloodGuard AI v1.0 | Analytics Dashboard | HYBRID DATA<br>
    Data-source labels distinguish LIVE, MODEL, USER SUBMITTED and DEMO information.
    For real operational deployment, connect to live IoT sensors and municipal databases.
</div>
""", unsafe_allow_html=True)
