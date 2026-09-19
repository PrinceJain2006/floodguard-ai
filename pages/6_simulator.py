"""
FloodGuard AI — Page 6: What-If Flood Simulator + Forecast Timeline + Resource Optimization
Feature 1: What-If Simulator — change rainfall, duration, drainage, blocked drains
Feature 4: Resource Optimization
Feature 5: Forecast Timeline (NOW, +30, +60, +90, +120 min)
Feature NEW: RUN FLOOD SCENARIO — calls real orchestrator pipeline, shows before/after state
Feature NEW: Drainage Before/After simulation using real DrainageAgent scoring
All parameter-tuned simulation outputs are labeled SIMULATED.
RUN FLOOD SCENARIO outputs come from the real pipeline.
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
from datetime import datetime, timedelta, timezone
from frontend.ui_utils import (
    apply_global_css, header, metric_card, demo_badge,
    simulated_badge, section_header, COLORS, ai_disclaimer, model_badge,
    render_agent_trace, render_granite_panel,
)
from agents.orchestrator import get_orchestrator, SCENARIOS
from agents.drainage_agent import get_drainage_agent
from data.seed_generator import AHMEDABAD_AREAS, SURAT_AREAS, ALL_AREAS
from ml.flood_risk_model import get_model as get_flood_model

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
# Session state for scenario tracking
# ──────────────────────────────────────────────
if "sim_before_state" not in st.session_state:
    st.session_state.sim_before_state = None
if "sim_after_state" not in st.session_state:
    st.session_state.sim_after_state = None
if "sim_scenario_ran" not in st.session_state:
    st.session_state.sim_scenario_ran = False
# Custom what-if simulator state
if "custom_sim_results" not in st.session_state:
    st.session_state.custom_sim_results = None
if "custom_sim_params" not in st.session_state:
    st.session_state.custom_sim_params = {}

@st.cache_resource
def _get_ml_model_sim():
    """Load the flood risk ML model for simulator use."""
    try:
        return get_flood_model()
    except Exception:
        return None

# ──────────────────────────────────────────────
# Header
# ──────────────────────────────────────────────
st.markdown("""
<div style="background:linear-gradient(135deg,#0d1020 0%,#0a1628 100%);
            border:1px solid #1d4ed8;border-radius:12px;
            padding:1.2rem 1.5rem;margin-bottom:1rem">
    <div style="display:flex;align-items:center;gap:1rem;flex-wrap:wrap">
        <div style="font-size:2.5rem">🌧️</div>
        <div style="flex:1">
            <div style="font-size:1.6rem;font-weight:800;color:#e2e8f0">
                FLOOD SCENARIO SIMULATOR
            </div>
            <div style="font-size:0.85rem;color:#94a3b8;margin-top:0.2rem">
                RUN FLOOD SCENARIO · What-If Analysis · Forecast Timeline · Drainage Simulation · Resource Optimization
            </div>
        </div>
        <div>
            <span style="background:#1e3a5f;color:#93c5fd;padding:3px 10px;border-radius:6px;font-size:0.78rem;font-weight:600">
                🔵 MODEL Pipeline · 🟡 DEMO Infrastructure
            </span>
        </div>
    </div>
</div>
""", unsafe_allow_html=True)

# ══════════════════════════════════════════════════════════════════════
# ▶  RUN FLOOD SCENARIO — P0 FEATURE
#    Calls the real orchestrator pipeline; shows live state transition
# ══════════════════════════════════════════════════════════════════════
st.markdown("""
<div style="font-size:1rem;font-weight:700;color:#e2e8f0;margin-bottom:0.5rem;letter-spacing:0.03em">
    ▶ RUN FLOOD SCENARIO
</div>
<div style="font-size:0.8rem;color:#94a3b8;margin-bottom:0.75rem">
    Select a scenario and run the full multi-agent pipeline. The system will transition through
    <span style="color:#22c55e;font-weight:600">NORMAL</span> →
    <span style="color:#eab308;font-weight:600">WARNING</span> →
    <span style="color:#ef4444;font-weight:600">CRITICAL</span> states based on real agent outputs.
</div>
""", unsafe_allow_html=True)

sc_cols = st.columns([1, 1, 1, 1, 1, 1.3])
_scenario_map = [
    ("NORMAL",        "🌦️", "Normal Rain",        "#22c55e"),
    ("HEAVY",         "🌧️", "Heavy Rainfall",     "#eab308"),
    ("EXTREME",       "⛈️", "Extreme Rainfall",   "#ef4444"),
    ("CITIZEN_SURGE", "📱", "Citizen Surge",      "#3b82f6"),
    ("EMERGENCY",     "🚨", "Emergency Response", "#ef4444"),
]
chosen_scenario = None
for i, (sc_id, em, sc_label, sc_color) in enumerate(_scenario_map):
    with sc_cols[i]:
        is_active = orch.current_scenario == sc_id
        btn_label = f"{em} {'[ACTIVE]' if is_active else sc_label}"
        if st.button(btn_label, key=f"run_sc_{sc_id}", use_container_width=True,
                     type="primary" if is_active else "secondary"):
            chosen_scenario = sc_id

with sc_cols[5]:
    run_city = st.selectbox("City", ["All", "Ahmedabad", "Surat"], key="run_city", label_visibility="collapsed")
    st.markdown(f'<div style="font-size:0.7rem;color:#94a3b8;text-align:center">City scope</div>', unsafe_allow_html=True)

if chosen_scenario:
    # Capture before-state snapshot
    before_snap = {}
    if orch.current_state:
        preds_before = orch.current_state.get("risk_predictions", [])
        before_snap = {
            "scenario":        orch.current_scenario,
            "critical":        sum(1 for p in preds_before if p["risk_level"] == "CRITICAL"),
            "high":            sum(1 for p in preds_before if p["risk_level"] == "HIGH"),
            "avg_score":       sum(p["risk_score"] for p in preds_before) / max(len(preds_before), 1),
            "open_reports":    orch.current_state.get("report_analysis", {}).get("open_reports", 0),
            "critical_drains": orch.current_state.get("drain_analysis", {}).get("priority_summary", {}).get("CRITICAL", 0),
            "teams_avail":     sum(1 for t in orch.current_state.get("teams", []) if t.get("status") == "AVAILABLE"),
        }
    st.session_state.sim_before_state = before_snap

    # Run the real pipeline
    prog_bar = st.progress(0, text="Starting pipeline…")
    with st.spinner(f"Running {SCENARIOS[chosen_scenario]['label']} scenario through all agents…"):
        prog_bar.progress(20, text="🔵 Flood Risk Agent analyzing…")
        new_state = orch.run_pipeline(scenario=chosen_scenario, city=run_city)
        prog_bar.progress(60, text="🔵 Drainage Agent + Citizen Reports Agent processing…")
        import time as _time; _time.sleep(0.3)
        prog_bar.progress(80, text="🤖 IBM Granite generating situation report…")
        _time.sleep(0.2)
        prog_bar.progress(100, text="✅ Pipeline complete")

    state = orch.current_state or {}

    # Capture after-state
    preds_after = state.get("risk_predictions", [])
    after_snap = {
        "scenario":        chosen_scenario,
        "critical":        sum(1 for p in preds_after if p["risk_level"] == "CRITICAL"),
        "high":            sum(1 for p in preds_after if p["risk_level"] == "HIGH"),
        "avg_score":       sum(p["risk_score"] for p in preds_after) / max(len(preds_after), 1),
        "open_reports":    state.get("report_analysis", {}).get("open_reports", 0),
        "critical_drains": state.get("drain_analysis", {}).get("priority_summary", {}).get("CRITICAL", 0),
        "teams_avail":     sum(1 for t in state.get("teams", []) if t.get("status") == "AVAILABLE"),
    }
    st.session_state.sim_after_state = after_snap
    st.session_state.sim_scenario_ran = True
    prog_bar.empty()

# ── Show before / after transition if a scenario has been run ──
if st.session_state.sim_scenario_ran and st.session_state.sim_after_state:
    bef = st.session_state.sim_before_state or {}
    aft = st.session_state.sim_after_state

    # Determine system status level
    aft_crit = aft.get("critical", 0)
    aft_high  = aft.get("high", 0)
    if aft_crit >= 3:
        sys_status = "CRITICAL"; sys_color = "#ef4444"; sys_bg = "rgba(239,68,68,0.15)"
    elif aft_crit >= 1 or aft_high >= 3:
        sys_status = "WARNING";  sys_color = "#f97316"; sys_bg = "rgba(249,115,22,0.12)"
    else:
        sys_status = "NORMAL";   sys_color = "#22c55e"; sys_bg = "rgba(34,197,94,0.10)"

    st.markdown(f"""
    <div style="background:{sys_bg};border:2px solid {sys_color};border-radius:10px;
                padding:0.8rem 1.2rem;margin:0.5rem 0 1rem 0">
        <div style="display:flex;align-items:center;gap:0.75rem;flex-wrap:wrap">
            <div style="font-size:1.5rem;font-weight:900;color:{sys_color};letter-spacing:0.06em">
                ● SYSTEM STATUS: {sys_status}
            </div>
            <div style="flex:1;font-size:0.82rem;color:#94a3b8">
                Scenario: {SCENARIOS.get(aft['scenario'], {}).get('emoji', '')} {SCENARIOS.get(aft['scenario'], {}).get('label', aft['scenario'])}
                &nbsp;·&nbsp; Pipeline run at {datetime.now(timezone.utc).strftime('%H:%M UTC')}
            </div>
            <span style="background:#1e3a5f;color:#93c5fd;padding:2px 8px;border-radius:4px;font-size:0.72rem;font-weight:700">
                🔵 PIPELINE OUTPUT
            </span>
        </div>
    </div>
    """, unsafe_allow_html=True)

    # Before / After metrics
    def _delta_html(before_val, after_val, invert=False):
        """Returns colored delta HTML. invert=True means increase is good."""
        if before_val is None:
            return ""
        diff = after_val - before_val
        if diff == 0:
            return '<span style="color:#94a3b8;font-size:0.72rem">→ no change</span>'
        arrow = "▲" if diff > 0 else "▼"
        # For risk metrics: increase is bad (red). For teams: decrease is bad.
        if invert:
            color = "#22c55e" if diff > 0 else "#ef4444"
        else:
            color = "#ef4444" if diff > 0 else "#22c55e"
        return f'<span style="color:{color};font-size:0.72rem">{arrow} {abs(diff):.0f}</span>'

    st.markdown("**State Transition — Before vs After:**")
    ba1, ba2, ba3, ba4, ba5, ba6 = st.columns(6)
    pairs = [
        (ba1, "Critical Zones",    "#ef4444", bef.get("critical"), aft["critical"],       False),
        (ba2, "High Risk Zones",   "#f97316", bef.get("high"),     aft["high"],            False),
        (ba3, "Avg Risk Score",    "#3b82f6", bef.get("avg_score"),aft["avg_score"],        False),
        (ba4, "Open Reports",      "#eab308", bef.get("open_reports"), aft["open_reports"], False),
        (ba5, "Critical Drains",   "#f97316", bef.get("critical_drains"), aft["critical_drains"], False),
        (ba6, "Teams Available",   "#22c55e", bef.get("teams_avail"),  aft["teams_avail"],  True),
    ]
    for col, label, color, b_val, a_val, inv in pairs:
        with col:
            display_val = f"{a_val:.0f}" if isinstance(a_val, float) else str(a_val)
            delta_html = _delta_html(b_val, a_val, invert=inv)
            st.markdown(f"""
            <div style="background:#1a1d27;border:1px solid #2d3148;border-radius:8px;
                        padding:0.8rem;text-align:center">
                <div style="font-size:1.6rem;font-weight:700;color:{color}">{display_val}</div>
                <div style="font-size:0.7rem;color:#94a3b8;text-transform:uppercase;
                            letter-spacing:0.04em;margin:0.2rem 0">{label}</div>
                <div style="min-height:1rem">{delta_html}</div>
            </div>
            """, unsafe_allow_html=True)

    st.markdown("<br>", unsafe_allow_html=True)

st.markdown("---")

# ──────────────────────────────────────────────
# Tabs
# ──────────────────────────────────────────────
tab1, tab2, tab3, tab4 = st.tabs([
    "🌧️ What-If Simulator",
    "⏱️ Forecast Timeline",
    "🔧 Drainage Simulation",
    "💼 Resource Optimization",
])

# ═══════════════════════════════════════════════
# TAB 1: WHAT-IF SIMULATOR
# ═══════════════════════════════════════════════
with tab1:
    section_header("WHAT-IF FLOOD SCENARIO SIMULATOR", simulated_badge())

    # ── Controls ─────────────────────────────
    st.markdown("""
    <div style="font-size:0.82rem;color:#64748b;margin-bottom:0.75rem">
      Adjust flood parameters and click <strong style="color:#3b82f6">RUN SIMULATION</strong>
      to calculate flood risk using the actual ML model.
      All values are <strong style="color:#eab308">SIMULATED</strong> — not real sensor data.
    </div>
    """, unsafe_allow_html=True)

    ctrl1, ctrl2, ctrl3 = st.columns(3)
    ctrl4, ctrl5, ctrl6 = st.columns(3)

    with ctrl1:
        rainfall_mm = st.slider("🌧️ Rainfall Intensity (mm/hr)", 0, 200, 45, step=5,
                                 help="Rainfall intensity in mm per hour — SIMULATED")
    with ctrl2:
        duration_hr = st.slider("⏱️ Duration (hours)", 0, 24, 3, step=1,
                                 help="How long rainfall has been ongoing — SIMULATED")
    with ctrl3:
        drainage_pct = st.slider("🔧 Drainage Capacity (%)", 0, 100, 60, step=5,
                                  help="% of drainage infrastructure functional — SIMULATED")
    with ctrl4:
        blocked_drains = st.slider("🚫 Blocked Drains (%)", 0, 100, 20, step=5,
                                    help="% of drains blocked — SIMULATED")
    with ctrl5:
        water_level_m = st.slider("💧 Water Level (m)", 0.0, 5.0, 0.5, step=0.1,
                                   help="Current water level at sensor points — SIMULATED")
    with ctrl6:
        citizen_rpts = st.slider("📱 Citizen Reports", 0, 200, 15, step=5,
                                  help="Number of incoming citizen flood reports — SIMULATED")

    _ctrl_city_col, _ctrl_run_col, _ctrl_reset_col = st.columns([1.5, 1, 1])
    with _ctrl_city_col:
        city_filter = st.selectbox("🏙️ City", ["All", "Ahmedabad", "Surat"], key="sim_city")
    with _ctrl_run_col:
        run_sim = st.button("▶ RUN SIMULATION", key="run_custom_sim", type="primary", use_container_width=True)
    with _ctrl_reset_col:
        reset_sim = st.button("↺ RESET SCENARIO", key="reset_custom_sim", use_container_width=True)

    if reset_sim:
        st.session_state.custom_sim_results = None
        st.session_state.custom_sim_params = {}
        st.rerun()

    st.markdown("<div style='height:0.5rem'></div>", unsafe_allow_html=True)

    # ── Simulation function — uses ML model when available ────────────────
    _ml_model_sim = _get_ml_model_sim()

    def simulate_risk(area: dict, city: str, rainfall: float, duration: int,
                      drainage: float, blocked: float,
                      water_level: float = 0.5, citizen_rep: int = 15) -> dict:
        """
        Simulate flood risk for an area using the actual ML model.
        Falls back to rule-based math if model unavailable.
        All outputs are SIMULATED — not real sensor readings.
        """
        elevation = area.get("elevation", 50)
        density = area.get("density", 0.7)
        hff = max(1, int(3 + (50 - elevation) / 10))  # historical freq estimate

        r1h  = float(rainfall)
        r3h  = round(r1h * (2.5 + duration * 0.1), 1)
        r6h  = round(r1h * (5.0 + duration * 0.15), 1)
        r24h = round(r1h * (15 + duration * 0.5), 1)
        dc   = max(5, drainage - blocked * 0.3)

        features = {
            "rainfall_1h":           r1h,
            "rainfall_3h":           r3h,
            "rainfall_6h":           r6h,
            "rainfall_24h":          r24h,
            "drainage_capacity":     dc,
            "historical_flood_freq": hff,
            "water_level":           water_level,
            "elevation":             float(elevation),
            "road_density":          density,
            "citizen_reports":       float(citizen_rep),
        }

        if _ml_model_sim and _ml_model_sim.is_trained:
            pred = _ml_model_sim.predict(features)
            score = pred["risk_score"]
            level = pred["risk_level"]
            reasons = pred.get("main_reasons", [])
            fi = pred.get("feature_importance", {})
            model_used = "ML MODEL"
        else:
            # Rule-based fallback
            rain_risk = min(100, rainfall * 0.7)
            duration_mult = 1 + math.log(max(1, duration)) * 0.2
            elevation_factor = max(0, (60 - elevation) / 60) * 30
            drain_factor = (blocked / 100) * 25
            drain_reduction = (drainage / 100) * 20
            density_factor = density * 10
            wl_factor = water_level * 8
            raw_score = (rain_risk * duration_mult + elevation_factor
                         + drain_factor + density_factor + wl_factor - drain_reduction)
            score = max(0, min(100, raw_score))
            level = ("CRITICAL" if score >= 75 else "HIGH" if score >= 55
                     else "MEDIUM" if score >= 30 else "LOW")
            reasons = []
            if rainfall > 60: reasons.append(f"Extreme rainfall ({rainfall} mm/hr)")
            elif rainfall > 30: reasons.append(f"Heavy rainfall ({rainfall} mm/hr)")
            if blocked > 40: reasons.append(f"High drain blockage ({blocked:.0f}%)")
            if water_level >= 2: reasons.append(f"High water level ({water_level:.1f}m)")
            if drainage < 40: reasons.append(f"Low drainage capacity ({drainage}%)")
            fi = {}
            model_used = "RULE-BASED"

        return {
            "area": area["name"],
            "city": city,
            "lat": area["lat"],
            "lon": area["lon"],
            "simulated_risk_score": round(score, 1),
            "simulated_risk_level": level,
            "reasons": reasons[:3],
            "feature_importance": fi,
            "model_used": model_used,
        }

    # Run simulation (on button click or if results already exist)
    areas_to_sim = []
    if city_filter in ("All", "Ahmedabad"):
        areas_to_sim += [(a, "Ahmedabad") for a in AHMEDABAD_AREAS]
    if city_filter in ("All", "Surat"):
        areas_to_sim += [(a, "Surat") for a in SURAT_AREAS]

    # Compute results immediately for display (live update as sliders move)
    sim_results = [
        simulate_risk(a, c, rainfall_mm, duration_hr, drainage_pct, blocked_drains,
                      water_level=water_level_m, citizen_rep=citizen_rpts)
        for a, c in areas_to_sim
    ]
    sim_results.sort(key=lambda x: x["simulated_risk_score"], reverse=True)

    # Determine model source for badge
    _model_src = sim_results[0].get("model_used", "RULE-BASED") if sim_results else "RULE-BASED"
    _model_badge_html = (
        '<span style="background:#1e3a5f;color:#93c5fd;font-size:0.68rem;padding:1px 6px;border-radius:3px;font-weight:700">🔵 ML MODEL</span>'
        if _model_src == "ML MODEL" else
        '<span style="background:#1a1500;color:#fde68a;font-size:0.68rem;padding:1px 6px;border-radius:3px;font-weight:700">⚙ RULE-BASED</span>'
    )
    st.markdown(f"""
    <div style="font-size:0.72rem;color:#475569;margin-bottom:0.5rem">
      Simulation using: {_model_badge_html}
      &nbsp;·&nbsp; <span style="color:#475569">All values SIMULATED — not real sensor data</span>
    </div>
    """, unsafe_allow_html=True)

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
            now = datetime.now(timezone.utc)
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
# TAB 3: DRAINAGE BEFORE/AFTER SIMULATION
# ═══════════════════════════════════════════════
with tab3:
    section_header("DRAINAGE INTERVENTION SIMULATOR", model_badge())
    st.markdown("""
    <div style="font-size:0.8rem;color:#94a3b8;margin-bottom:0.75rem">
        Simulate an AI-recommended maintenance intervention on a drain.
        Scores use the real <strong>DrainageAgent</strong> scoring formula.
        Select a drain, adjust parameters, and compare BEFORE vs AFTER.
    </div>
    """, unsafe_allow_html=True)

    # Get drain data from current state
    raw_drains = state.get("raw_drains", [])
    rainfall_data_drain = state.get("rainfall_data", [])
    risk_preds_drain = state.get("risk_predictions", [])

    if not raw_drains:
        st.info("Run a scenario first to load drain data.")
    else:
        drain_agent = get_drainage_agent()

        # Average rainfall for context
        avg_rain_drain = (
            sum(r.get("rainfall_1h", 0) for r in rainfall_data_drain) /
            max(len(rainfall_data_drain), 1)
        )

        # Build drain selector
        drain_names = [f"{d.get('drain_id','?')} — {d.get('area','?')}, {d.get('city','?')}" for d in raw_drains[:30]]
        selected_drain_label = st.selectbox("Select Drain", drain_names, key="drain_sel")
        sel_idx = drain_names.index(selected_drain_label)
        base_drain = dict(raw_drains[sel_idx])

        # Get area flood risk for context
        area_risk_val = 0.0
        for rp in risk_preds_drain:
            if rp.get("area") == base_drain.get("area") and rp.get("city") == base_drain.get("city"):
                area_risk_val = rp.get("risk_score", 0.0)
                break

        # Score the drain BEFORE any intervention
        before_score_result = drain_agent.score_drain(base_drain, avg_rain_drain, area_risk_val)

        st.markdown("---")
        col_before, col_arrow, col_after = st.columns([1, 0.15, 1])

        with col_before:
            bpri = before_score_result.get("maintenance_priority", "N/A")
            bscore = before_score_result.get("computed_risk_score", 0)
            bcolor = {"CRITICAL": "#ef4444", "HIGH": "#f97316", "MEDIUM": "#eab308", "LOW": "#22c55e"}.get(bpri, "#94a3b8")
            st.markdown(f"""
            <div style="background:#1a0f0f;border:2px solid {bcolor};border-radius:10px;padding:1rem;margin-bottom:0.5rem">
                <div style="font-size:0.75rem;color:#94a3b8;font-weight:700;letter-spacing:0.05em;margin-bottom:0.5rem">BEFORE MAINTENANCE</div>
                <div style="font-size:2.5rem;font-weight:900;color:{bcolor}">{bscore:.0f}</div>
                <div style="font-size:0.75rem;color:#94a3b8">Risk Score / 100</div>
                <div style="margin-top:0.5rem">
                    <span style="background:{bcolor};color:white;padding:2px 8px;border-radius:8px;font-size:0.75rem;font-weight:600">{bpri}</span>
                </div>
                <div style="font-size:0.72rem;color:#94a3b8;margin-top:0.5rem">
                    Capacity: {base_drain.get('capacity_rating', '?')}% &nbsp;·&nbsp;
                    Condition: {base_drain.get('condition', '?')} &nbsp;·&nbsp;
                    Status: {base_drain.get('status', '?')}
                </div>
            </div>
            """, unsafe_allow_html=True)
            for reason in before_score_result.get("priority_reasons", [])[:3]:
                st.markdown(f'<div style="font-size:0.75rem;color:#f97316;padding:2px 0">⚠ {reason}</div>', unsafe_allow_html=True)

        with col_arrow:
            st.markdown('<div style="font-size:2rem;color:#38bdf8;text-align:center;padding-top:2rem">→</div>', unsafe_allow_html=True)

        with col_after:
            st.markdown("**AI-Recommended Maintenance:**")
            dc1, dc2, dc3 = st.columns(3)
            with dc1:
                new_capacity = st.slider("New Capacity %", 0, 100,
                    min(100, base_drain.get("capacity_rating", 50) + 30),
                    step=5, key="drain_cap")
            with dc2:
                new_cond = st.selectbox("Condition After", ["GOOD", "FAIR", "POOR", "CRITICAL"],
                    index=0, key="drain_cond")
            with dc3:
                clear_block = st.checkbox("Clear Blockage", value=True, key="drain_block")

            # Build modified drain for post-intervention scoring
            modified_drain = {
                **base_drain,
                "capacity_rating": new_capacity,
                "condition": new_cond,
                "status": "OPERATIONAL" if clear_block else base_drain.get("status", "OPERATIONAL"),
                "last_cleaned": datetime.now(timezone.utc).isoformat(),
            }
            after_score_result = drain_agent.score_drain(modified_drain, avg_rain_drain, area_risk_val)

            apri = after_score_result.get("maintenance_priority", "N/A")
            ascore = after_score_result.get("computed_risk_score", 0)
            acolor = {"CRITICAL": "#ef4444", "HIGH": "#f97316", "MEDIUM": "#eab308", "LOW": "#22c55e"}.get(apri, "#94a3b8")
            improvement = bscore - ascore

            st.markdown(f"""
            <div style="background:#0a1a0a;border:2px solid {acolor};border-radius:10px;padding:1rem;margin-bottom:0.5rem">
                <div style="font-size:0.75rem;color:#94a3b8;font-weight:700;letter-spacing:0.05em;margin-bottom:0.5rem">AFTER INTERVENTION</div>
                <div style="font-size:2.5rem;font-weight:900;color:{acolor}">{ascore:.0f}</div>
                <div style="font-size:0.75rem;color:#94a3b8">Risk Score / 100</div>
                <div style="margin-top:0.5rem">
                    <span style="background:{acolor};color:white;padding:2px 8px;border-radius:8px;font-size:0.75rem;font-weight:600">{apri}</span>
                    {'&nbsp;<span style="color:#22c55e;font-size:0.78rem;font-weight:700">▼ ' + f'{improvement:.0f} improved</span>' if improvement > 0 else ''}
                </div>
                <div style="font-size:0.72rem;color:#94a3b8;margin-top:0.5rem">
                    Capacity: {new_capacity}% &nbsp;·&nbsp;
                    Condition: {new_cond} &nbsp;·&nbsp;
                    Status: {'OPERATIONAL' if clear_block else base_drain.get('status', '?')}
                </div>
            </div>
            """, unsafe_allow_html=True)

            rec_action = after_score_result.get("recommended_action", "Monitor and schedule next inspection.")
            st.markdown(f'<div style="font-size:0.75rem;color:#22c55e;padding:2px 0">✅ Recommended: {rec_action}</div>', unsafe_allow_html=True)

        # Before/After summary card
        st.markdown("---")
        _impr_pct = ((bscore - ascore) / max(bscore, 1)) * 100 if bscore > 0 else 0
        _impr_color = "#22c55e" if improvement > 5 else "#eab308" if improvement > 0 else "#ef4444"
        st.markdown(f"""
        <div style="background:#080c14;border:1px solid #1e2440;border-radius:10px;padding:1rem;margin-top:0.5rem">
          <div style="display:flex;align-items:center;justify-content:space-between;margin-bottom:0.75rem;flex-wrap:wrap;gap:0.5rem">
            <div style="font-size:0.85rem;font-weight:700;color:#e2e8f0;text-transform:uppercase;letter-spacing:0.05em">
              🔧 DRAINAGE MAINTENANCE IMPACT
            </div>
            <div style="background:{'rgba(34,197,94,0.1)' if improvement > 5 else 'rgba(234,179,8,0.1)'};
                        border:1px solid {_impr_color}40;border-radius:6px;padding:0.25rem 0.7rem">
              <span style="color:{_impr_color};font-size:0.85rem;font-weight:700">
                {"▼" if improvement > 0 else "="} {abs(improvement):.0f} pts ({abs(_impr_pct):.0f}%) {'improvement' if improvement > 0 else 'change'}
              </span>
            </div>
          </div>
          <div style="display:flex;align-items:center;gap:1rem;flex-wrap:wrap">
            <div style="flex:1;min-width:120px">
              <div style="font-size:0.65rem;color:#64748b;margin-bottom:0.2rem;text-transform:uppercase">BEFORE</div>
              <div style="background:#1e2440;border-radius:4px;height:24px;position:relative;overflow:hidden">
                <div style="width:{bscore:.0f}%;background:{bcolor};height:100%;border-radius:4px;
                            display:flex;align-items:center;justify-content:flex-end;padding-right:6px">
                  <span style="color:white;font-size:0.7rem;font-weight:700">{bscore:.0f}</span>
                </div>
              </div>
              <div style="font-size:0.7rem;color:{bcolor};margin-top:0.1rem;font-weight:700">{bpri}</div>
            </div>
            <div style="font-size:1.5rem;color:#475569">→</div>
            <div style="flex:1;min-width:120px">
              <div style="font-size:0.65rem;color:#64748b;margin-bottom:0.2rem;text-transform:uppercase">AFTER</div>
              <div style="background:#1e2440;border-radius:4px;height:24px;position:relative;overflow:hidden">
                <div style="width:{ascore:.0f}%;background:{acolor};height:100%;border-radius:4px;
                            display:flex;align-items:center;justify-content:flex-end;padding-right:6px">
                  <span style="color:white;font-size:0.7rem;font-weight:700">{ascore:.0f}</span>
                </div>
              </div>
              <div style="font-size:0.7rem;color:{acolor};margin-top:0.1rem;font-weight:700">{apri}</div>
            </div>
          </div>
          <div style="font-size:0.65rem;color:#475569;margin-top:0.6rem">
            ⚙ Scores from DrainageAgent real scoring formula ·
            Drain: {base_drain.get('drain_id','?')} ·
            Rainfall: {avg_rain_drain:.1f} mm/hr (DEMO) ·
            Area flood risk: {area_risk_val:.0f}/100 (MODEL)
          </div>
        </div>
        """, unsafe_allow_html=True)


# ═══════════════════════════════════════════════
# TAB 4: RESOURCE OPTIMIZATION
# ═══════════════════════════════════════════════
with tab4:
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
    FloodGuard AI | Simulator & Resource Optimization | {simulated_badge()} Mathematical model outputs.<br>
    Not real meteorological forecasts. Infrastructure inputs are DEMO data. Not for operational emergency use.
</div>
""", unsafe_allow_html=True)
