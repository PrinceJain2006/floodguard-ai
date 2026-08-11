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
    simulated_badge, section_header, COLORS
)
from agents.orchestrator import get_orchestrator, SCENARIOS
from agents.damage_assessment_agent import get_damage_agent

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

st.markdown(f"""
<div style="background:rgba(124,58,237,0.1);border:1px solid #7c3aed;border-radius:8px;
            padding:0.5rem 0.8rem;margin-bottom:1rem;font-size:0.78rem;color:#a78bfa">
    {simulated_badge()} All metrics are DEMO/SIMULATED data representing a hypothetical scenario for Ahmedabad & Surat.
    These do not represent real government operational data.
</div>
""", unsafe_allow_html=True)

# ──────────────────────────────────────────────
# Impact Metrics Strip
# ──────────────────────────────────────────────
section_header("IMPACT METRICS", simulated_badge())

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
tab1, tab2, tab3, tab4, tab5 = st.tabs([
    "📈 Risk Trends",
    "🌧️ Rainfall Analysis",
    "📱 Report Analytics",
    "🔍 Damage Assessment",
    "📋 Scenario Comparison",
])

# ── Tab 1: Risk Trends ───────────────────────
with tab1:
    col1, col2 = st.columns([1.5, 1])

    with col1:
        section_header("FLOOD RISK BY AREA", demo_badge())
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

        # Simulated trend line
        st.markdown("---")
        section_header("SIMULATED RISK TREND")
        hours = list(range(-12, 1))
        base_critical = high_risk_zones
        trend = [max(0, base_critical - 8 + i + random.randint(-1,1)) for i in hours]

        fig_trend = go.Figure()
        fig_trend.add_trace(go.Scatter(
            x=hours, y=trend,
            mode="lines+markers",
            line=dict(color="#ef4444", width=2),
            fill="tozeroy",
            fillcolor="rgba(239,68,68,0.1)",
            name="Critical Zones",
        ))
        fig_trend.update_layout(
            paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
            xaxis=dict(color="#94a3b8", title="Hours Ago"),
            yaxis=dict(color="#94a3b8", title="Critical Zones"),
            height=200, margin=dict(t=10, b=10, l=10, r=10),
            showlegend=False,
        )
        st.plotly_chart(fig_trend, use_container_width=True, config={"displayModeBar": False})
        st.markdown(f'<div style="font-size:0.7rem;color:#64748b">⚙ SIMULATED trend data</div>', unsafe_allow_html=True)

# ── Tab 2: Rainfall ───────────────────────────
with tab2:
    section_header("RAINFALL DISTRIBUTION", demo_badge())
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
    section_header("CITIZEN REPORT ANALYTICS", demo_badge())
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
    section_header("POST-FLOOD DAMAGE ASSESSMENT", demo_badge())
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

    # Hardcoded comparison (based on scenario configs)
    scenarios = ["NORMAL", "HEAVY", "EXTREME", "CITIZEN_SURGE", "EMERGENCY"]
    scenario_labels = ["Normal Rain", "Heavy Rainfall", "Extreme", "Citizen Surge", "Emergency"]
    critical_zones_sim = [2, 8, 18, 6, 20]
    high_zones_sim = [5, 12, 10, 8, 8]
    citizen_reports_sim = [40, 80, 120, 200, 150]
    response_actions_sim = [5, 20, 45, 30, 50]

    fig_comp = go.Figure()
    fig_comp.add_trace(go.Bar(name="Critical Zones", x=scenario_labels, y=critical_zones_sim, marker_color="#ef4444"))
    fig_comp.add_trace(go.Bar(name="High Risk Zones", x=scenario_labels, y=high_zones_sim, marker_color="#f97316"))
    fig_comp.add_trace(go.Bar(name="Citizen Reports (÷5)", x=scenario_labels, y=[c//5 for c in citizen_reports_sim], marker_color="#3b82f6"))
    fig_comp.add_trace(go.Bar(name="Response Actions", x=scenario_labels, y=response_actions_sim, marker_color="#7c3aed"))

    fig_comp.update_layout(
        paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
        xaxis=dict(color="#94a3b8"),
        yaxis=dict(color="#94a3b8", title="Count"),
        legend=dict(font=dict(color="#e2e8f0")),
        barmode="group",
        height=360, margin=dict(t=10, b=10, l=10, r=10),
    )
    st.plotly_chart(fig_comp, use_container_width=True, config={"displayModeBar": False})
    st.markdown(f'<div style="font-size:0.7rem;color:#64748b">⚙ SIMULATED comparison data — not real measurements</div>', unsafe_allow_html=True)

# ──────────────────────────────────────────────
# Footer
# ──────────────────────────────────────────────
st.markdown("---")
st.markdown(f"""
<div style="text-align:center;color:#475569;font-size:0.72rem;padding-bottom:1rem">
    FloodGuard AI v1.0 | Analytics Dashboard | {demo_badge()} All metrics are synthetic demo data.<br>
    For real operational deployment, connect to live IoT sensors and municipal databases.
</div>
""", unsafe_allow_html=True)
