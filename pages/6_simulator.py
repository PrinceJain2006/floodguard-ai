"""
FloodGuard AI — Page 6: What-If Flood Simulator + Forecast Timeline + Resource Optimization
Feature 1: What-If Simulator — change rainfall, duration, drainage, blocked drains
Feature 4: Resource Optimization
Feature 5: Forecast Timeline (NOW, +30, +60, +90, +120 min)
All outputs are DEMO/SIMULATED.
"""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import streamlit as st
import plotly.graph_objects as go
import plotly.express as px
import pandas as pd
import random
import math
from datetime import datetime, timedelta
from frontend.ui_utils import (
    apply_global_css, header, metric_card, demo_badge,
    simulated_badge, section_header, COLORS, ai_disclaimer
)
from agents.orchestrator import get_orchestrator, SCENARIOS
from data.seed_generator import AHMEDABAD_AREAS, SURAT_AREAS, ALL_AREAS

st.set_page_config(
    page_title="Simulator — FloodGuard AI",
    page_icon="🌧️",
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
# Header
# ──────────────────────────────────────────────
header("What-If Flood Simulator & Forecast Timeline",
       "Adjust parameters and see simulated risk impact — 100% synthetic demo data", "🌧️")

st.markdown(f"""
<div style="background:rgba(59,130,246,0.1);border:1px solid #3b82f6;border-radius:8px;
            padding:0.5rem 0.9rem;margin-bottom:1rem;font-size:0.78rem;color:#93c5fd">
    {simulated_badge()} This simulator uses a <strong>mathematical model</strong> built on demo data. 
    Outputs are illustrative only and do not represent real flood forecasts or government predictions.
    Never use for real emergency decisions.
</div>
""", unsafe_allow_html=True)

# ──────────────────────────────────────────────
# Tabs
# ──────────────────────────────────────────────
tab1, tab2, tab3 = st.tabs([
    "🌧️ What-If Simulator",
    "⏱️ Forecast Timeline",
    "💼 Resource Optimization",
])

# ═══════════════════════════════════════════════
# TAB 1: WHAT-IF SIMULATOR
# ═══════════════════════════════════════════════
with tab1:
    section_header("WHAT-IF FLOOD SCENARIO SIMULATOR", simulated_badge())

    # ── Controls ─────────────────────────────
    st.markdown("**Adjust parameters to see simulated risk:**")
    ctrl1, ctrl2, ctrl3, ctrl4, ctrl5 = st.columns(5)

    with ctrl1:
        rainfall_mm = st.slider("Rainfall Intensity", 0, 200, 45, step=5,
                                 help="mm per hour — SIMULATED")
        st.markdown(f'<div style="font-size:0.75rem;color:#94a3b8">Current: {rainfall_mm} mm/hr</div>', unsafe_allow_html=True)

    with ctrl2:
        duration_hr = st.slider("Duration (hours)", 0, 24, 3, step=1,
                                 help="How long rainfall has been ongoing — SIMULATED")

    with ctrl3:
        drainage_pct = st.slider("Drainage Capacity %", 0, 100, 60, step=5,
                                  help="% of drainage infrastructure functional — SIMULATED")

    with ctrl4:
        blocked_drains = st.slider("Blocked Drains (%)", 0, 100, 20, step=5,
                                    help="% of drains blocked — SIMULATED")

    with ctrl5:
        city_filter = st.selectbox("City", ["All", "Ahmedabad", "Surat"], key="sim_city")

    st.markdown("<br>", unsafe_allow_html=True)

    # ── Simulation function ───────────────────
    def simulate_risk(area: dict, city: str, rainfall: float, duration: int,
                      drainage: float, blocked: float) -> dict:
        """
        Mathematical simulation of flood risk based on input parameters.
        Completely synthetic — uses area metadata from demo dataset.
        """
        elevation = area.get("elevation", 50)
        density = area.get("density", 0.7)

        # Base risk from rainfall intensity
        rain_risk = min(100, rainfall * 0.7)

        # Duration compounds risk (log scale)
        duration_mult = 1 + math.log(max(1, duration)) * 0.2

        # Low elevation = higher risk
        elevation_factor = max(0, (60 - elevation) / 60) * 30

        # Blocked drains compound risk
        drain_factor = (blocked / 100) * 25

        # Drainage capacity reduces risk
        drain_reduction = (drainage / 100) * 20

        # Population density multiplier
        density_factor = density * 10

        raw_score = (
            rain_risk * duration_mult
            + elevation_factor
            + drain_factor
            + density_factor
            - drain_reduction
        )
        score = max(0, min(100, raw_score))

        if score >= 75:   level = "CRITICAL"
        elif score >= 55: level = "HIGH"
        elif score >= 30: level = "MEDIUM"
        else:             level = "LOW"

        reasons = []
        if rainfall > 60: reasons.append(f"Extreme rainfall ({rainfall} mm/hr)")
        elif rainfall > 30: reasons.append(f"Heavy rainfall ({rainfall} mm/hr)")
        if blocked > 40: reasons.append(f"High drain blockage ({blocked:.0f}%)")
        if elevation < 15: reasons.append(f"Very low elevation ({elevation}m)")
        if duration > 6: reasons.append(f"Prolonged rainfall ({duration}h)")
        if drainage < 40: reasons.append(f"Low drainage capacity ({drainage}%)")

        return {
            "area": area["name"],
            "city": city,
            "lat": area["lat"],
            "lon": area["lon"],
            "simulated_risk_score": round(score, 1),
            "simulated_risk_level": level,
            "reasons": reasons[:3],
        }

    # Run simulation
    areas_to_sim = []
    if city_filter in ("All", "Ahmedabad"):
        areas_to_sim += [(a, "Ahmedabad") for a in AHMEDABAD_AREAS]
    if city_filter in ("All", "Surat"):
        areas_to_sim += [(a, "Surat") for a in SURAT_AREAS]

    sim_results = [
        simulate_risk(a, c, rainfall_mm, duration_hr, drainage_pct, blocked_drains)
        for a, c in areas_to_sim
    ]
    sim_results.sort(key=lambda x: x["simulated_risk_score"], reverse=True)

    # ── Results ──────────────────────────────
    sim_critical = sum(1 for r in sim_results if r["simulated_risk_level"] == "CRITICAL")
    sim_high     = sum(1 for r in sim_results if r["simulated_risk_level"] == "HIGH")
    sim_medium   = sum(1 for r in sim_results if r["simulated_risk_level"] == "MEDIUM")
    sim_low      = sum(1 for r in sim_results if r["simulated_risk_level"] == "LOW")
    avg_score    = sum(r["simulated_risk_score"] for r in sim_results) / max(len(sim_results), 1)

    k1,k2,k3,k4,k5 = st.columns(5)
    with k1: metric_card("CRITICAL Zones",   str(sim_critical), color="#ef4444", icon="🔴")
    with k2: metric_card("HIGH Risk Zones",  str(sim_high),     color="#f97316", icon="🟠")
    with k3: metric_card("MEDIUM Zones",     str(sim_medium),   color="#eab308", icon="🟡")
    with k4: metric_card("LOW Risk Zones",   str(sim_low),      color="#22c55e", icon="🟢")
    with k5: metric_card("Avg Risk Score",   f"{avg_score:.0f}", color="#3b82f6", icon="📊")

    st.markdown("<br>", unsafe_allow_html=True)

    col_chart, col_table = st.columns([1.4, 1])

    with col_chart:
        section_header("SIMULATED RISK BY AREA", simulated_badge())
        df_sim = pd.DataFrame(sim_results)
        color_map = {"CRITICAL": "#ef4444", "HIGH": "#f97316", "MEDIUM": "#eab308", "LOW": "#22c55e"}
        df_sim["color"] = df_sim["simulated_risk_level"].map(color_map)

        fig = go.Figure()
        for level, color in color_map.items():
            df_l = df_sim[df_sim["simulated_risk_level"] == level]
            if not df_l.empty:
                fig.add_trace(go.Bar(
                    x=df_l["simulated_risk_score"],
                    y=df_l["area"] + ", " + df_l["city"],
                    orientation="h",
                    name=level,
                    marker_color=color,
                ))
        fig.update_layout(
            paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
            xaxis=dict(range=[0, 100], color="#94a3b8", title="Simulated Risk Score"),
            yaxis=dict(color="#e2e8f0"),
            legend=dict(font=dict(color="#e2e8f0")),
            height=max(300, len(sim_results) * 18),
            margin=dict(t=10, b=10, l=10, r=10),
            barmode="stack",
        )
        st.plotly_chart(fig, use_container_width=True, config={"displayModeBar": False})

    with col_table:
        section_header("AFFECTED ZONES", simulated_badge())
        # Show top risky zones
        df_top = df_sim[df_sim["simulated_risk_level"].isin(["CRITICAL", "HIGH"])].head(12)
        if not df_top.empty:
            for _, row in df_top.iterrows():
                p_color = color_map[row["simulated_risk_level"]]
                reasons_str = "; ".join(row["reasons"]) if row["reasons"] else "Multiple factors"
                st.markdown(f"""
                <div style="background:#1a1d27;border-left:3px solid {p_color};border-radius:0 6px 6px 0;
                            padding:0.4rem 0.6rem;margin-bottom:0.3rem">
                    <div style="display:flex;justify-content:space-between;align-items:center">
                        <div style="font-size:0.8rem;font-weight:700;color:#e2e8f0">
                            {row['area']}, {row['city']}
                        </div>
                        <div>
                            <span style="background:{p_color};color:white;padding:1px 5px;
                                  border-radius:4px;font-size:0.65rem;font-weight:600">
                                {row['simulated_risk_level']}
                            </span>
                            <span style="font-size:0.72rem;color:#94a3b8;margin-left:0.3rem">
                                {row['simulated_risk_score']:.0f}/100
                            </span>
                        </div>
                    </div>
                    <div style="font-size:0.7rem;color:#64748b;margin-top:0.2rem">{reasons_str}</div>
                </div>
                """, unsafe_allow_html=True)
        else:
            st.success("✅ No CRITICAL or HIGH risk zones with current parameters.")
            st.dataframe(
                df_sim[["area", "city", "simulated_risk_score", "simulated_risk_level"]].head(10),
                use_container_width=True, hide_index=True,
            )

    st.markdown(f'<div style="font-size:0.7rem;color:#64748b;margin-top:0.5rem">⚙ All values are SIMULATED using a mathematical model. Rainfall={rainfall_mm}mm/hr, Duration={duration_hr}h, Drainage={drainage_pct}%, Blocked={blocked_drains}%</div>', unsafe_allow_html=True)


# ═══════════════════════════════════════════════
# TAB 2: FORECAST TIMELINE
# ═══════════════════════════════════════════════
with tab2:
    section_header("FLOOD RISK FORECAST TIMELINE", simulated_badge())
    st.markdown("""
    <div style="font-size:0.8rem;color:#94a3b8;margin-bottom:0.75rem">
        Simulated risk forecast at NOW, +30, +60, +90, and +120 minutes based on current scenario data.
        Uses a decay/escalation model — not real meteorological forecasts.
    </div>
    """, unsafe_allow_html=True)

    predictions = state.get("risk_predictions", [])
    current_scenario = state.get("scenario", "NORMAL")

    # Forecast parameters based on scenario
    scenario_trend = {
        "NORMAL":        {"escalation": -0.05, "label": "Improving"},
        "HEAVY":         {"escalation": +0.08, "label": "Escalating"},
        "EXTREME":       {"escalation": +0.15, "label": "Rapidly Escalating"},
        "CITIZEN_SURGE": {"escalation": +0.05, "label": "Slightly Escalating"},
        "EMERGENCY":     {"escalation": -0.02, "label": "Stabilizing"},
    }
    trend_info = scenario_trend.get(current_scenario, {"escalation": 0, "label": "Stable"})
    escalation = trend_info["escalation"]

    def project_score(base_score: float, minutes_ahead: int, escalation_rate: float) -> float:
        """Project risk score forward in time using exponential model."""
        hours = minutes_ahead / 60
        projected = base_score * (1 + escalation_rate * hours)
        # Add small noise for realism
        projected += random.uniform(-3, 3)
        return max(0, min(100, projected))

    def score_to_level(score: float) -> str:
        if score >= 75: return "CRITICAL"
        if score >= 55: return "HIGH"
        if score >= 30: return "MEDIUM"
        return "LOW"

    time_slots = [0, 30, 60, 90, 120]
    time_labels = ["NOW", "+30 min", "+60 min", "+90 min", "+120 min"]
    level_colors = {"CRITICAL": "#ef4444", "HIGH": "#f97316", "MEDIUM": "#eab308", "LOW": "#22c55e"}

    # Top zones for timeline
    top_zones = sorted(predictions, key=lambda x: x["risk_score"], reverse=True)[:8]

    # ── Timeline heatmap ─────────────────────
    if top_zones:
        col_tl, col_summary = st.columns([1.6, 1])

        with col_tl:
            section_header("RISK TIMELINE HEATMAP")
            zone_labels = [f"{z['area']}, {z['city']}" for z in top_zones]

            # Build matrix
            z_matrix = []
            text_matrix = []
            for zone in top_zones:
                row_scores = []
                row_text = []
                for minutes in time_slots:
                    score = project_score(zone["risk_score"], minutes, escalation)
                    row_scores.append(score)
                    row_text.append(f"{score:.0f}")
                z_matrix.append(row_scores)
                text_matrix.append(row_text)

            fig_heat = go.Figure(go.Heatmap(
                z=z_matrix,
                x=time_labels,
                y=zone_labels,
                text=text_matrix,
                texttemplate="%{text}",
                colorscale=[
                    [0,    "#22c55e"],
                    [0.3,  "#eab308"],
                    [0.55, "#f97316"],
                    [1,    "#ef4444"],
                ],
                zmin=0, zmax=100,
                hovertemplate="<b>%{y}</b><br>%{x}: Score %{z:.0f}<extra></extra>",
            ))
            fig_heat.update_layout(
                paper_bgcolor="rgba(0,0,0,0)",
                plot_bgcolor="rgba(0,0,0,0)",
                xaxis=dict(color="#e2e8f0"),
                yaxis=dict(color="#e2e8f0"),
                height=max(280, len(top_zones) * 38),
                margin=dict(t=10, b=10, l=10, r=80),
            )
            st.plotly_chart(fig_heat, use_container_width=True, config={"displayModeBar": False})

            st.markdown(f"""
            <div style="font-size:0.72rem;color:#64748b;margin-top:0.3rem">
                ⚙ SIMULATED forecast — Trend: <strong style="color:#f97316">{trend_info['label']}</strong> 
                (escalation rate: {escalation:+.0%}/hr based on {current_scenario} scenario)
            </div>
            """, unsafe_allow_html=True)

        with col_summary:
            section_header("TIME-STEP SUMMARY")
            now = datetime.utcnow()
            for i, (minutes, label) in enumerate(zip(time_slots, time_labels)):
                t_stamp = (now + timedelta(minutes=minutes)).strftime("%H:%M")
                # Count projected levels
                counts = {"CRITICAL": 0, "HIGH": 0, "MEDIUM": 0, "LOW": 0}
                for zone in predictions:
                    score = project_score(zone["risk_score"], minutes, escalation)
                    lvl = score_to_level(score)
                    counts[lvl] = counts.get(lvl, 0) + 1

                dom_level = max(counts, key=counts.get)
                dom_color = level_colors.get(dom_level, "#94a3b8")

                st.markdown(f"""
                <div style="background:#1a1d27;border:1px solid #2d3148;border-left:4px solid {dom_color};
                            border-radius:0 8px 8px 0;padding:0.5rem 0.75rem;margin-bottom:0.4rem">
                    <div style="display:flex;justify-content:space-between;align-items:center">
                        <div style="font-weight:700;color:#e2e8f0;font-size:0.85rem">{label}</div>
                        <div style="font-size:0.72rem;color:#64748b">{t_stamp}</div>
                    </div>
                    <div style="font-size:0.72rem;color:#94a3b8;margin-top:0.2rem">
                        🔴 {counts['CRITICAL']} CRITICAL &nbsp;|&nbsp; 
                        🟠 {counts['HIGH']} HIGH &nbsp;|&nbsp;
                        🟡 {counts['MEDIUM']} MED &nbsp;|&nbsp;
                        🟢 {counts['LOW']} LOW
                    </div>
                    <div style="font-size:0.7rem;color:{dom_color};margin-top:0.15rem">
                        Dominant: {dom_level}
                    </div>
                </div>
                """, unsafe_allow_html=True)

        # Line chart for top 3 zones
        st.markdown("---")
        section_header("PROJECTED RISK TRENDS — TOP ZONES")
        fig_line = go.Figure()
        line_colors_list = ["#ef4444", "#f97316", "#eab308", "#3b82f6", "#7c3aed"]

        for zi, zone in enumerate(top_zones[:5]):
            scores = [project_score(zone["risk_score"], m, escalation) for m in time_slots]
            fig_line.add_trace(go.Scatter(
                x=time_labels,
                y=scores,
                mode="lines+markers",
                name=f"{zone['area']}, {zone['city']}",
                line=dict(color=line_colors_list[zi % len(line_colors_list)], width=2),
                marker=dict(size=6),
            ))

        # Add threshold lines
        for threshold, label_t, color_t in [(75, "CRITICAL", "#ef4444"), (55, "HIGH", "#f97316")]:
            fig_line.add_hline(y=threshold, line_dash="dash", line_color=color_t, opacity=0.5,
                               annotation_text=label_t, annotation_font_color=color_t)

        fig_line.update_layout(
            paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
            xaxis=dict(color="#94a3b8"),
            yaxis=dict(color="#94a3b8", range=[0, 105], title="Risk Score"),
            legend=dict(font=dict(color="#e2e8f0", size=10)),
            height=280, margin=dict(t=10, b=10, l=10, r=10),
        )
        st.plotly_chart(fig_line, use_container_width=True, config={"displayModeBar": False})
    else:
        st.info("Run a scenario first to see forecast data.")


# ═══════════════════════════════════════════════
# TAB 3: RESOURCE OPTIMIZATION
# ═══════════════════════════════════════════════
with tab3:
    section_header("RESOURCE OPTIMIZATION ENGINE", simulated_badge())
    ai_disclaimer()
    st.markdown("""
    <div style="font-size:0.8rem;color:#94a3b8;margin-bottom:0.75rem">
        AI-driven resource recommendations based on risk level, priority, distance, and availability.
        Recommends pumps, teams, ambulances, and shelters — SIMULATED optimization only.
    </div>
    """, unsafe_allow_html=True)

    resource_recs = state.get("resource_recommendations", [])
    teams = state.get("teams", [])

    if not resource_recs:
        st.info("Run a scenario to generate resource recommendations.")
    else:
        # Overview metrics
        total_zones = len(resource_recs)
        total_resources = sum(len(r["assigned_resources"]) for r in resource_recs)
        critical_zones = sum(1 for r in resource_recs if r["risk_level"] == "CRITICAL")
        available_teams = sum(1 for t in teams if t.get("status") == "AVAILABLE")

        rc1, rc2, rc3, rc4 = st.columns(4)
        with rc1: metric_card("Zones Needing Resources", str(total_zones), color="#ef4444", icon="📍")
        with rc2: metric_card("Resources Recommended",   str(total_resources), color="#f97316", icon="💼")
        with rc3: metric_card("Critical Priority Zones", str(critical_zones), color="#ef4444", icon="🔴")
        with rc4: metric_card("Available Teams",         str(available_teams), color="#22c55e", icon="✅")

        st.markdown("<br>", unsafe_allow_html=True)

        col_recs, col_matrix = st.columns([1, 1])

        with col_recs:
            section_header("ZONE-BY-ZONE ALLOCATIONS")
            for rec in resource_recs:
                level = rec["risk_level"]
                p_color = COLORS.get(level, "#94a3b8")
                resources_html = ""
                for r in rec["assigned_resources"]:
                    t_color = "#22c55e" if r["status"] == "AVAILABLE" else "#f97316"
                    t_type = r["team_type"].replace("_", " ").title()
                    resources_html += f"""
                    <div style="display:flex;gap:0.5rem;align-items:center;padding:2px 0;font-size:0.72rem">
                        <span style="color:{t_color}">●</span>
                        <span style="color:#e2e8f0">{r['team_name']}</span>
                        <span style="color:#64748b">({t_type})</span>
                        <span style="color:#94a3b8">~{r['estimated_travel_min']}min</span>
                    </div>
                    """

                with st.expander(
                    f"{'🔴' if level=='CRITICAL' else '🟠'} {rec['zone']} — Score: {rec['risk_score']:.0f}",
                    expanded=(level == "CRITICAL"),
                ):
                    st.markdown(f"""
                    <div style="font-size:0.8rem;color:#94a3b8;margin-bottom:0.4rem">
                        {rec['rationale']}
                    </div>
                    {resources_html}
                    <div style="font-size:0.65rem;color:#475569;margin-top:0.3rem">⚙ SIMULATED allocation</div>
                    """, unsafe_allow_html=True)

        with col_matrix:
            section_header("RESOURCE TYPE DISTRIBUTION")
            # Count by resource type
            type_counts: dict[str, int] = {}
            for rec in resource_recs:
                for r in rec["assigned_resources"]:
                    t = r["team_type"].replace("_", " ").title()
                    type_counts[t] = type_counts.get(t, 0) + 1

            if type_counts:
                fig_res = go.Figure(go.Pie(
                    labels=list(type_counts.keys()),
                    values=list(type_counts.values()),
                    hole=0.5,
                    marker=dict(colors=["#3b82f6","#7c3aed","#ef4444","#f97316","#22c55e","#14b8a6"]),
                ))
                fig_res.update_layout(
                    paper_bgcolor="rgba(0,0,0,0)",
                    legend=dict(font=dict(color="#e2e8f0")),
                    height=250, margin=dict(t=10, b=10, l=10, r=10),
                )
                st.plotly_chart(fig_res, use_container_width=True, config={"displayModeBar": False})

            # Team availability summary
            st.markdown("---")
            section_header("TEAM AVAILABILITY")
            status_counts: dict[str, int] = {}
            for t in teams:
                s = t.get("status", "UNKNOWN")
                status_counts[s] = status_counts.get(s, 0) + 1

            status_colors = {"AVAILABLE": "#22c55e", "DEPLOYED": "#f97316", "STANDBY": "#3b82f6", "OFF_DUTY": "#94a3b8"}
            for status, count in sorted(status_counts.items()):
                pct = count / max(len(teams), 1) * 100
                sc = status_colors.get(status, "#94a3b8")
                st.markdown(f"""
                <div style="display:flex;align-items:center;gap:0.75rem;margin-bottom:0.3rem">
                    <div style="min-width:90px;font-size:0.78rem;color:{sc};font-weight:600">{status}</div>
                    <div style="flex:1;background:#1a1d27;border-radius:4px;height:16px;overflow:hidden;border:1px solid #2d3148">
                        <div style="width:{pct:.0f}%;background:{sc};height:100%;border-radius:4px"></div>
                    </div>
                    <div style="min-width:25px;font-size:0.78rem;color:#e2e8f0">{count}</div>
                </div>
                """, unsafe_allow_html=True)

# ──────────────────────────────────────────────
# Footer
# ──────────────────────────────────────────────
st.markdown("---")
st.markdown(f"""
<div style="text-align:center;color:#475569;font-size:0.72rem;padding-bottom:1rem">
    FloodGuard AI | Simulator & Resource Optimization | {simulated_badge()} All outputs are DEMO/SIMULATED mathematical models.<br>
    Not real meteorological forecasts. Not for operational emergency use.
</div>
""", unsafe_allow_html=True)
