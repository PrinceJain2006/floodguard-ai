"""
FloodGuard AI — Page 8: Decision Intelligence Center
=====================================================
Evidence Fusion · Zone Priority · Why This Zone · Why Now
Agent Decision Trace · Human-in-the-Loop Approval · Audit Trail

HYBRID INPUTS: Live Weather (Open-Meteo) · ML Predictions (Random Forest) ·
User Reports (Citizen Portal) · Demo Infrastructure (drainage/teams/incidents).
Priority scores are application decision-support scores — NOT scientifically
validated emergency-response scores.
"""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import streamlit as st
from datetime import datetime, timezone

from frontend.ui_utils import (
    apply_global_css, header, metric_card,
    demo_badge, simulated_badge, hybrid_badge, model_badge, section_header, COLORS, risk_badge
)
from agents.orchestrator import get_orchestrator, SCENARIOS
from agents.evidence_fusion import (
    fuse_all_zones,
    build_why_now,
    build_agent_decision_trace,
    get_recommended_action,
    get_audit_trail,
    EVIDENCE_WEIGHTS,
    PRIORITY_LEVELS,
)

st.set_page_config(
    page_title="Decision Intelligence — FloodGuard AI",
    page_icon="🧭",
    layout="wide",
    initial_sidebar_state="collapsed",
)
apply_global_css()

# ──────────────────────────────────────────────────────────────────────────────
# Session state initialisation
# ──────────────────────────────────────────────────────────────────────────────
if "di_scenario" not in st.session_state:
    st.session_state.di_scenario = "NORMAL"
if "di_prev_fusions" not in st.session_state:
    st.session_state.di_prev_fusions = {}          # area_city → previous fusion
if "di_approved_actions" not in st.session_state:
    st.session_state.di_approved_actions = {}      # action_id → decision dict
if "di_pending_actions" not in st.session_state:
    st.session_state.di_pending_actions = {}       # action_id → action dict


# ──────────────────────────────────────────────────────────────────────────────
# Orchestrator + data
# ──────────────────────────────────────────────────────────────────────────────
@st.cache_resource
def get_orch():
    orch = get_orchestrator()
    if not orch.current_state:
        orch.run_pipeline("NORMAL")
    return orch


orch     = get_orch()
audit    = get_audit_trail()


# ──────────────────────────────────────────────────────────────────────────────
# Compute evidence fusions helper (defined early so it can be used anywhere)
# ──────────────────────────────────────────────────────────────────────────────
def _compute_fusions(s: dict) -> list[dict]:
    return fuse_all_zones(
        risk_predictions  = s.get("risk_predictions",   []),
        drain_records     = s.get("raw_drains",          []),
        report_records    = s.get("raw_reports",          []),
        incident_records  = s.get("drain_analysis", {}).get("scored_drains", []),
        live_weather_records = s.get("live_weather_records", []),
    )


state    = orch.current_state or {}


# ──────────────────────────────────────────────────────────────────────────────
# Header
# ──────────────────────────────────────────────────────────────────────────────
st.markdown(f"""
<div style="background:linear-gradient(135deg,#0d1020 0%,#1a1040 100%);
            border:1px solid #7c3aed;border-radius:12px;
            padding:1.2rem 1.5rem;margin-bottom:1rem">
    <div style="display:flex;align-items:center;gap:1rem;flex-wrap:wrap">
        <div style="font-size:2.5rem">🧭</div>
        <div style="flex:1">
            <div style="font-size:1.6rem;font-weight:800;color:#e2e8f0">
                DECISION INTELLIGENCE CENTER
            </div>
            <div style="font-size:0.85rem;color:#94a3b8;margin-top:0.2rem">
                Evidence Fusion &nbsp;·&nbsp; Zone Priority &nbsp;·&nbsp; Why This Zone &nbsp;·&nbsp;
                Why Now &nbsp;·&nbsp; Agent Trace &nbsp;·&nbsp; Human-in-the-Loop &nbsp;·&nbsp; Audit
            </div>
        </div>
        <div style="display:flex;flex-direction:column;gap:0.4rem;align-items:flex-end">
            <div style="font-size:0.72rem;color:#94a3b8">
                <span style="background:#14532d;color:#bbf7d0;padding:1px 6px;border-radius:3px;font-size:0.65rem;font-weight:700">🟢 LIVE</span> Weather &nbsp;
                <span style="background:#1e3a5f;color:#93c5fd;padding:1px 6px;border-radius:3px;font-size:0.65rem;font-weight:700">🔵 MODEL</span> Predictions &nbsp;
                <span style="background:#3a1a00;color:#fdba74;padding:1px 6px;border-radius:3px;font-size:0.65rem;font-weight:700">🟠 USER</span> Reports &nbsp;
                <span style="background:#3a2e00;color:#fde68a;padding:1px 6px;border-radius:3px;font-size:0.65rem;font-weight:700">🟡 DEMO</span> Infrastructure
            </div>
            <span style="background:#1a1d27;border:1px solid #7c3aed;color:#a78bfa;
                         padding:3px 10px;border-radius:6px;font-size:0.78rem;font-weight:600">
                Decision-support layer — Not a validated emergency score
            </span>
        </div>
    </div>
</div>
""", unsafe_allow_html=True)

# ──────────────────────────────────────────────────────────────────────────────
# Scenario selector
# ──────────────────────────────────────────────────────────────────────────────
sc_cols = st.columns([1] + [1] * 5)
with sc_cols[0]:
    st.markdown('<div style="font-size:0.8rem;color:#94a3b8;padding-top:0.5rem">Scenario:</div>',
                unsafe_allow_html=True)
for i, (sc_id, sc_info) in enumerate(SCENARIOS.items()):
    with sc_cols[i + 1]:
        active = (orch.current_scenario == sc_id)
        if st.button(
            f"{sc_info['emoji']} {sc_info['label']}",
            key=f"di_sc_{sc_id}",
            type="primary" if active else "secondary",
            use_container_width=True,
        ):
            # Save current fusions before overwriting
            if state:
                prev = _compute_fusions(state)
                st.session_state.di_prev_fusions = {
                    f"{f['area']}_{f['city']}": f for f in prev
                }
            with st.spinner(f"Running {sc_info['label']} scenario…"):
                orch.run_pipeline(scenario=sc_id, city="All")
                st.session_state.di_scenario = sc_id
                st.session_state.di_pending_actions = {}
            st.rerun()


state  = orch.current_state or {}
fusions = _compute_fusions(state) if state else []

# ──────────────────────────────────────────────────────────────────────────────
# KPI strip
# ──────────────────────────────────────────────────────────────────────────────
if fusions:
    n_critical = sum(1 for f in fusions if f["priority_level"] == "CRITICAL")
    n_high     = sum(1 for f in fusions if f["priority_level"] == "HIGH")
    n_medium   = sum(1 for f in fusions if f["priority_level"] == "MEDIUM")
    n_low      = sum(1 for f in fusions if f["priority_level"] == "LOW")
    top_score  = fusions[0]["priority_score"] if fusions else 0
    top_zone   = f"{fusions[0]['area']}, {fusions[0]['city']}" if fusions else "N/A"
    n_approved = len(st.session_state.di_approved_actions)
    n_audit    = len(audit.get_all())

    k1, k2, k3, k4, k5, k6, k7, k8 = st.columns(8)
    with k1: metric_card("Critical Zones",  str(n_critical),  color="#ef4444", icon="🔴")
    with k2: metric_card("High Zones",      str(n_high),      color="#f97316", icon="🟠")
    with k3: metric_card("Medium Zones",    str(n_medium),    color="#eab308", icon="🟡")
    with k4: metric_card("Low Zones",       str(n_low),       color="#22c55e", icon="🟢")
    with k5: metric_card("Top Score",       f"{top_score:.0f}/100", color="#7c3aed", icon="📊")
    with k6: metric_card("Top Zone",        top_zone[:16],    color="#7c3aed", icon="📍")
    with k7: metric_card("Decisions Made",  str(n_approved),  color="#3b82f6", icon="✅")
    with k8: metric_card("Audit Entries",   str(n_audit),     color="#3b82f6", icon="📋")

st.markdown("<br>", unsafe_allow_html=True)

# ──────────────────────────────────────────────────────────────────────────────
# Explainer banner — what this page does
# ──────────────────────────────────────────────────────────────────────────────
st.markdown("""
<div style="background:rgba(124,58,237,0.08);border:1px solid #7c3aed;
            border-radius:10px;padding:0.9rem 1.2rem;margin-bottom:1.2rem;font-size:0.84rem;color:#c4b5fd">
    <strong>🧭 How Decision Intelligence works</strong><br>
    FloodGuard AI does not just predict flooding. It combines available evidence from all agents,
    explains <em>why</em> a zone is prioritised, recommends what should happen next, and keeps the
    final decision with a human. Scores are <strong>application decision-support priority scores</strong>
    derived from demo/synthetic data — they are not scientifically validated emergency-response scores.
</div>
""", unsafe_allow_html=True)

if not fusions:
    st.info("No analysis data available. Run a scenario from the War Room or Agent Monitor.")
    st.stop()

# ──────────────────────────────────────────────────────────────────────────────
# TABS
# ──────────────────────────────────────────────────────────────────────────────
tab_priority, tab_why, tab_trace, tab_hitl, tab_audit = st.tabs([
    "📊 Zone Priority",
    "🔍 Why This Zone / Why Now",
    "🤖 Agent Decision Trace",
    "🔐 Human-in-the-Loop",
    "📋 Audit Trail",
])


# ══════════════════════════════════════════════════════════════════════════════
# TAB 1 — ZONE PRIORITY
# ══════════════════════════════════════════════════════════════════════════════
with tab_priority:
    section_header("ZONE PRIORITY SCORES",
                   '<span style="background:#1e3a5f;color:#93c5fd;font-size:0.7rem;padding:2px 8px;border-radius:4px;font-weight:700;letter-spacing:0.04em">🔵 DECISION SUPPORT</span>')
    st.markdown("""
    <div style="font-size:0.8rem;color:#94a3b8;margin-bottom:0.75rem">
        Evidence-fused decision-support priority scores for all monitored zones.
        Each score combines ML risk prediction, rainfall, drainage, citizen reports,
        historical data, and water level. <strong>Not a real emergency score.</strong>
    </div>
    """, unsafe_allow_html=True)

    # Evidence weight legend
    with st.expander("📐 Evidence Weight Breakdown (how the score is calculated)", expanded=False):
        cols_w = st.columns(len(EVIDENCE_WEIGHTS))
        weight_labels = {
            "ml_risk_score":          "ML Risk",
            "rainfall_intensity":     "Rainfall",
            "drainage_status":        "Drainage",
            "citizen_reports":        "Reports",
            "historical_vulnerability": "History",
            "water_level_proxy":      "Water Level",
        }
        weight_icons = {
            "ml_risk_score": "🌊", "rainfall_intensity": "🌧️", "drainage_status": "🔧",
            "citizen_reports": "📱", "historical_vulnerability": "📖", "water_level_proxy": "💧",
        }
        for col, (key, w) in zip(cols_w, EVIDENCE_WEIGHTS.items()):
            with col:
                metric_card(
                    weight_labels[key],
                    f"{w*100:.0f}%",
                    icon=weight_icons[key],
                    color="#7c3aed",
                )

    st.markdown("<br>", unsafe_allow_html=True)

    # Filter controls
    fcol1, fcol2, fcol3 = st.columns([1, 1, 2])
    with fcol1:
        city_filter = st.selectbox("City", ["All", "Ahmedabad", "Surat"], key="di_city")
    with fcol2:
        level_filter = st.selectbox("Priority Level", ["All", "CRITICAL", "HIGH", "MEDIUM", "LOW"],
                                    key="di_level")
    with fcol3:
        top_n = st.slider("Show top N zones", 5, 30, 15, key="di_topn")

    # Apply filters
    display_fusions = fusions
    if city_filter != "All":
        display_fusions = [f for f in display_fusions if f["city"] == city_filter]
    if level_filter != "All":
        display_fusions = [f for f in display_fusions if f["priority_level"] == level_filter]
    display_fusions = display_fusions[:top_n]

    # Zone cards
    for fusion in display_fusions:
        level  = fusion["priority_level"]
        score  = fusion["priority_score"]
        color  = fusion["priority_color"]
        emoji  = fusion["priority_emoji"]
        area   = fusion["area"]
        city   = fusion["city"]

        ev = fusion["evidence_breakdown"]
        factors = fusion["contributing_factors"]
        top_factor = factors[0] if factors else {}

        # Evidence mini-bar
        bar_html = ""
        bar_icons = {
            "ml_risk_score": "🌊", "rainfall_intensity": "🌧️", "drainage_status": "🔧",
            "citizen_reports": "📱", "historical_vulnerability": "📖", "water_level_proxy": "💧",
        }
        for key, raw_val in ev.items():
            bar_color = (
                "#ef4444" if raw_val >= 75 else
                "#f97316" if raw_val >= 50 else
                "#eab308" if raw_val >= 25 else "#22c55e"
            )
            bar_html += f"""
            <div style="margin-bottom:2px">
                <div style="display:flex;align-items:center;gap:4px">
                    <span style="font-size:0.65rem;min-width:14px">{bar_icons.get(key,'•')}</span>
                    <div style="flex:1;background:#2d3148;border-radius:2px;height:6px">
                        <div style="width:{raw_val:.0f}%;background:{bar_color};height:6px;border-radius:2px"></div>
                    </div>
                    <span style="font-size:0.6rem;color:#94a3b8;min-width:24px;text-align:right">{raw_val:.0f}</span>
                </div>
            </div>
            """

        _rain_live = fusion.get("rainfall_is_live", False)
        _live_badge = '<span style="background:#0d2818;color:#6ee7b7;font-size:0.55rem;padding:1px 4px;border-radius:3px;font-weight:700;margin-left:3px">LIVE</span>' if _rain_live else ""

        st.markdown(f"""
        <div style="background:#1a1d27;border:1px solid {color};border-left:4px solid {color};
                    border-radius:10px;padding:0.7rem 1rem;margin-bottom:0.4rem">
            <div style="display:flex;align-items:center;gap:0.75rem;flex-wrap:wrap">
                <div style="flex:1;min-width:150px">
                    <div style="font-size:0.95rem;font-weight:700;color:#e2e8f0">{emoji} {area}</div>
                    <div style="font-size:0.7rem;color:#64748b">{city}</div>
                </div>
                <div style="text-align:center;min-width:80px">
                    <div style="font-size:1.6rem;font-weight:800;color:{color};line-height:1">{score:.0f}</div>
                    <div style="font-size:0.6rem;color:#64748b">/ 100</div>
                </div>
                <div style="min-width:75px;text-align:center">
                    <span style="background:{color};color:white;padding:2px 9px;
                                 border-radius:6px;font-size:0.72rem;font-weight:700">{level}</span>
                </div>
                <div style="flex:2;min-width:180px">
                    {bar_html}
                </div>
                <div style="font-size:0.7rem;color:#94a3b8;min-width:140px;max-width:190px">
                    <div style="font-size:0.65rem;color:#64748b;margin-bottom:1px">Top factor{_live_badge}</div>
                    <strong style="color:#e2e8f0;font-size:0.72rem">{top_factor.get('label','')}</strong><br>
                    <span style="font-size:0.65rem">{top_factor.get('note','')[:55]}</span>
                </div>
            </div>
        </div>
        """, unsafe_allow_html=True)


# ══════════════════════════════════════════════════════════════════════════════
# TAB 2 — WHY THIS ZONE / WHY NOW
# ══════════════════════════════════════════════════════════════════════════════
with tab_why:
    section_header("WHY THIS ZONE? — ZONE EXPLANATION",
                   '<span style="background:#1e3a5f;color:#93c5fd;font-size:0.7rem;padding:2px 8px;border-radius:4px;font-weight:700;letter-spacing:0.04em">🔵 DECISION SUPPORT</span>')

    if not fusions:
        st.info("Run a scenario to see zone explanations.")
    else:
        zone_opts = [
            f"{f['area']}, {f['city']} — {f['priority_level']} ({f['priority_score']:.0f})"
            for f in fusions[:20]
        ]
        selected_why = st.selectbox("Select zone:", zone_opts, key="di_why_zone")
        idx_why = zone_opts.index(selected_why)
        fusion  = fusions[idx_why]
        level   = fusion["priority_level"]
        score   = fusion["priority_score"]
        color   = fusion["priority_color"]
        area    = fusion["area"]
        city    = fusion["city"]

        # ── WHY THIS ZONE card ──
        wl_col, wr_col = st.columns([1.3, 1])

        with wl_col:
            section_header("WHY THIS ZONE?",
                           '<span style="background:#1e3a5f;color:#93c5fd;font-size:0.7rem;padding:2px 8px;border-radius:4px;font-weight:700;letter-spacing:0.04em">🔵 DECISION SUPPORT</span>')
            factors = fusion["contributing_factors"]
            significant = [f for f in factors if f["significant"]]

            # Get ML prediction for this zone
            pred_why = next(
                (p for p in state.get("risk_predictions", [])
                 if p.get("area") == area and p.get("city") == city),
                {}
            )
            ml_score_why = pred_why.get("risk_score", 0)
            conf_why = pred_why.get("confidence", 0)
            top_feats_why = pred_why.get("top_features", [])
            main_reasons_why = pred_why.get("main_reasons", [])
            features_why = pred_why.get("input_features", {})

            # Summary card with FLOOD RISK SCORE
            st.markdown(f"""
            <div style="background:#1a1d27;border:1px solid {color};border-top:3px solid {color};
                        border-radius:10px;padding:1rem 1.2rem;margin-bottom:0.75rem">
                <div style="display:flex;justify-content:space-between;align-items:flex-start;flex-wrap:wrap;gap:0.5rem">
                    <div>
                        <div style="font-size:1.1rem;font-weight:800;color:#e2e8f0">{area}</div>
                        <div style="font-size:0.78rem;color:#94a3b8">{city}</div>
                        <div style="margin-top:0.4rem;font-size:0.7rem;color:#64748b">
                            FLOOD RISK SCORE (ML)
                        </div>
                        <div style="font-size:1.5rem;font-weight:900;color:{color};line-height:1.1">
                            {ml_score_why:.0f} <span style="font-size:0.9rem">/ 100</span>
                            <span style="font-size:0.75rem;font-weight:700;background:{color};color:white;
                                         padding:2px 8px;border-radius:6px;margin-left:4px">{level}</span>
                        </div>
                        <div style="font-size:0.7rem;color:#64748b;margin-top:0.15rem">
                            confidence: {conf_why:.0%} &nbsp;|&nbsp; fused priority: {score:.0f}/100
                        </div>
                    </div>
                    <div style="text-align:right">
                        {"<span style='background:#0d2818;color:#6ee7b7;font-size:0.65rem;padding:2px 8px;border-radius:4px;font-weight:700'>🟢 LIVE WEATHER</span>" if fusion.get("rainfall_is_live") else "<span style='background:#3a2e00;color:#fde68a;font-size:0.65rem;padding:2px 8px;border-radius:4px;font-weight:700'>🟡 DEMO RAINFALL</span>"}
                        <div style="font-size:0.65rem;color:#475569;margin-top:0.25rem">
                            🔵 ML Model + 🟡 DEMO infra
                        </div>
                    </div>
                </div>
            </div>
            """, unsafe_allow_html=True)

            # ML main reasons
            if main_reasons_why:
                st.markdown("""
                <div style="font-size:0.75rem;font-weight:700;color:#a78bfa;margin-bottom:0.3rem;
                            text-transform:uppercase;letter-spacing:0.05em">
                    🤖 ML Model Reasons (Random Forest)
                </div>""", unsafe_allow_html=True)
                for reason in main_reasons_why[:4]:
                    r_color = "#ef4444" if any(w in reason.lower() for w in ["extreme","critical","dangerously"]) else \
                              "#f97316" if "high" in reason.lower() else "#eab308"
                    st.markdown(f"""
                    <div style="font-size:0.78rem;color:{r_color};padding:2px 0 2px 8px;
                                border-left:2px solid {r_color};margin-bottom:3px">
                        {reason}
                    </div>""", unsafe_allow_html=True)

            # Top ML feature importances
            if top_feats_why:
                st.markdown("""
                <div style="font-size:0.75rem;font-weight:700;color:#93c5fd;margin:0.5rem 0 0.3rem;
                            text-transform:uppercase;letter-spacing:0.05em">
                    📊 Top ML Feature Importance
                </div>""", unsafe_allow_html=True)
                for feat_name, importance in top_feats_why[:4]:
                    feat_label = feat_name.replace("_", " ").title()
                    feat_val = features_why.get(feat_name, 0)
                    bar_pct = min(100, importance * 100 * 8)
                    st.markdown(f"""
                    <div style="display:flex;align-items:center;gap:0.5rem;margin-bottom:3px">
                        <div style="min-width:140px;font-size:0.72rem;color:#e2e8f0">{feat_label}</div>
                        <div style="flex:1;background:#2d3148;border-radius:3px;height:7px">
                            <div style="width:{bar_pct:.0f}%;background:#7c3aed;height:7px;border-radius:3px"></div>
                        </div>
                        <div style="min-width:40px;font-size:0.68rem;color:#a78bfa;text-align:right">{importance:.1%}</div>
                        <div style="min-width:50px;font-size:0.68rem;color:#64748b">(val: {feat_val:.1f})</div>
                    </div>""", unsafe_allow_html=True)

            st.markdown("<div style='height:0.4rem'></div>", unsafe_allow_html=True)

            # Evidence fusion factors
            st.markdown("""
            <div style="font-size:0.75rem;font-weight:700;color:#94a3b8;margin-bottom:0.3rem;
                        text-transform:uppercase;letter-spacing:0.05em">
                🔀 Evidence Fusion Factors
            </div>""", unsafe_allow_html=True)
            for f in factors:
                raw  = f["raw_score"]
                fcolor = (
                    "#ef4444" if raw >= 75 else
                    "#f97316" if raw >= 50 else
                    "#eab308" if raw >= 25 else "#22c55e"
                )
                checkmark = "✓" if f["significant"] else "·"
                src_badge = ""
                if f.get("is_live"):
                    src_badge = '<span style="background:#0d2818;color:#6ee7b7;font-size:0.55rem;padding:1px 4px;border-radius:3px;font-weight:700;margin-left:3px">LIVE</span>'
                st.markdown(f"""
                <div style="display:flex;align-items:center;gap:0.5rem;padding:0.3rem 0;
                            border-bottom:1px solid rgba(45,49,72,0.4)">
                    <span style="color:{fcolor};font-weight:700;min-width:14px">{checkmark}</span>
                    <div style="flex:1">
                        <div style="font-size:0.8rem;font-weight:600;color:#e2e8f0">
                            {f['label']}{src_badge}
                        </div>
                        <div style="font-size:0.68rem;color:#94a3b8">{f['note'][:80]}</div>
                    </div>
                    <div style="text-align:right;min-width:45px">
                        <div style="font-size:0.82rem;font-weight:700;color:{fcolor}">{raw:.0f}</div>
                        <div style="font-size:0.58rem;color:#475569">wt {f['weight']*100:.0f}%</div>
                    </div>
                    <div style="min-width:55px">
                        <div style="background:#2d3148;border-radius:3px;height:7px">
                            <div style="width:{raw:.0f}%;background:{fcolor};height:7px;border-radius:3px"></div>
                        </div>
                    </div>
                </div>
                """, unsafe_allow_html=True)

            # Disclaimer
            st.markdown(f"""
            <div style="font-size:0.68rem;color:#475569;margin-top:0.5rem;
                        border-top:1px solid #2d3148;padding-top:0.4rem">
                ⚠ Decision-support priority score. LIVE weather · MODEL predictions · USER SUBMITTED reports · DEMO infrastructure.
                Fused at {fusion['fused_at'][:19]} UTC.
            </div>
            """, unsafe_allow_html=True)

        with wr_col:
            # ── WHY NOW card ──
            section_header("WHY NOW?",
                           '<span style="background:#1e3a5f;color:#93c5fd;font-size:0.7rem;padding:2px 8px;border-radius:4px;font-weight:700;letter-spacing:0.04em">🔵 DECISION SUPPORT</span>')
            prev_key = f"{area}_{city}"
            prev_fusion = st.session_state.di_prev_fusions.get(prev_key)
            why_now = build_why_now(fusion, prev_fusion)

            if why_now["available"]:
                delta     = why_now["score_delta"]
                d_color   = "#ef4444" if delta > 5 else "#22c55e" if delta < -5 else "#eab308"
                d_arrow   = "↑" if delta > 0 else "↓" if delta < 0 else "→"

                # Build all change items as a single HTML string so the whole
                # card is emitted in one st.markdown call — no split open/close tags.
                _changes_html = "".join(
                    f'<div style="font-size:0.75rem;color:#e2e8f0;padding:2px 0;'
                    f'padding-left:0.5rem;border-left:2px solid #3b82f6">• {change}</div>'
                    for change in why_now["changes"]
                )
                _score_delta_text = (
                    f"increased by {abs(delta):.1f}" if delta > 0
                    else f"decreased by {abs(delta):.1f}" if delta < 0
                    else "unchanged"
                )
                _level_changed_text = " | Level escalated" if why_now["level_changed"] else ""
                st.markdown(f"""
                <div style="background:#1a1d27;border:1px solid #3b82f6;
                            border-radius:10px;padding:1rem 1.2rem;margin-bottom:0.75rem">
                    <div style="display:flex;justify-content:space-between;margin-bottom:0.5rem">
                        <div>
                            <div style="font-size:0.78rem;color:#94a3b8">Previous Scenario</div>
                            <div style="font-size:1.1rem;font-weight:700;color:#e2e8f0">
                                {why_now['prev_score']:.0f} — {why_now['prev_level']}
                            </div>
                        </div>
                        <div style="font-size:2rem;font-weight:800;color:{d_color}">{d_arrow}</div>
                        <div style="text-align:right">
                            <div style="font-size:0.78rem;color:#94a3b8">Current Scenario</div>
                            <div style="font-size:1.1rem;font-weight:700;color:{color}">
                                {why_now['curr_score']:.0f} — {why_now['curr_level']}
                            </div>
                        </div>
                    </div>
                    <div style="font-size:0.75rem;font-weight:600;color:{d_color};margin-bottom:0.5rem">
                        Score {_score_delta_text}{_level_changed_text}
                    </div>
                    <div style="font-size:0.75rem;color:#94a3b8;font-weight:600;margin-bottom:0.3rem">Key changes:</div>
                    {_changes_html}
                </div>
                """, unsafe_allow_html=True)
            else:
                st.markdown(f"""
                <div style="background:#1a1d27;border:1px solid #2d3148;
                            border-radius:10px;padding:1rem 1.2rem">
                    <div style="font-size:0.85rem;color:#94a3b8">
                        <strong style="color:#e2e8f0">WHY NOW?</strong><br><br>
                        {why_now['message']}<br><br>
                        <span style="font-size:0.72rem;color:#475569">
                            To see temporal comparison, switch between scenarios using the
                            selector above. The first run will save a baseline.
                        </span>
                    </div>
                </div>
                """, unsafe_allow_html=True)

            # Recommended action summary
            pred = next(
                (p for p in state.get("risk_predictions", [])
                 if p.get("area") == area and p.get("city") == city),
                {}
            )
            if pred:
                rec_action = get_recommended_action(fusion, pred)
                action_color = COLORS.get(rec_action["priority_level"], "#94a3b8")
                st.markdown(f"""
                <div style="background:rgba(124,58,237,0.1);border:1px solid #7c3aed;
                            border-radius:10px;padding:1rem 1.2rem;margin-top:0.75rem">
                    <div style="font-size:0.75rem;color:#a78bfa;font-weight:700;margin-bottom:0.4rem">
                        🤖 AI RECOMMENDATION
                    </div>
                    <div style="font-size:0.85rem;font-weight:600;color:#e2e8f0;margin-bottom:0.3rem">
                        {rec_action['title']}
                    </div>
                    <div style="font-size:0.75rem;color:#94a3b8;margin-bottom:0.4rem">
                        Urgency: <strong style="color:{action_color}">{rec_action['urgency']}</strong>
                    </div>
                    <div style="font-size:0.72rem;color:#64748b">
                        {"🔐 Requires human approval" if rec_action['requires_approval'] else "✅ Can be executed without approval"}
                    </div>
                </div>
                """, unsafe_allow_html=True)


# ══════════════════════════════════════════════════════════════════════════════
# TAB 3 — AGENT DECISION TRACE
# ══════════════════════════════════════════════════════════════════════════════
with tab_trace:
    section_header("AGENT DECISION TRACE",
                   '<span style="background:#1e3a5f;color:#93c5fd;font-size:0.7rem;padding:2px 8px;border-radius:4px;font-weight:700;letter-spacing:0.04em">MODEL / APPLICATION PIPELINE</span>')
    st.markdown("""
    <div style="font-size:0.8rem;color:#94a3b8;margin-bottom:0.75rem">
        See which agents contributed to a zone's priority score, and how each piece of evidence
        feeds into the final decision. No agent outputs are fabricated — trace is built from
        actual pipeline data.
    </div>
    """, unsafe_allow_html=True)

    if not fusions:
        st.info("No data available.")
    else:
        trace_opts = [
            f"{f['area']}, {f['city']} — {f['priority_level']} ({f['priority_score']:.0f})"
            for f in fusions[:20]
        ]
        selected_trace = st.selectbox("Select zone:", trace_opts, key="di_trace_zone")
        idx_trace = trace_opts.index(selected_trace)
        fusion_t  = fusions[idx_trace]

        pred_t = next(
            (p for p in state.get("risk_predictions", [])
             if p.get("area") == fusion_t["area"] and p.get("city") == fusion_t["city"]),
            {}
        )

        trace_steps = build_agent_decision_trace(
            fusion_result   = fusion_t,
            risk_prediction = pred_t,
            drain_analysis  = state.get("drain_analysis", {}),
            report_analysis = state.get("report_analysis", {}),
            response_plan   = state.get("response_plan",  {}),
            action_plan     = state.get("action_plan",    {}),
        )

        st.markdown(f"""
        <div style="font-size:0.82rem;color:#94a3b8;margin-bottom:1rem">
            Showing decision trace for:
            <strong style="color:#e2e8f0">{fusion_t['area']}, {fusion_t['city']}</strong>
            — Priority Score <strong style="color:{fusion_t['priority_color']}">{fusion_t['priority_score']:.0f}/100 ({fusion_t['priority_level']})</strong>
        </div>
        """, unsafe_allow_html=True)

        for i, step in enumerate(trace_steps):
            is_final = (step["agent"] == "Final Decision")
            agent    = step["agent"]
            emoji    = step["emoji"]
            contrib  = step["contribution"]
            details  = step["details"]
            output   = step["output_label"]
            mode     = step["mode"]

            card_color = (
                PRIORITY_LEVELS.get(fusion_t["priority_level"], {}).get("color", "#7c3aed")
                if is_final else "#2d3148"
            )
            card_bg = (
                f"rgba({int(card_color[1:3],16)},{int(card_color[3:5],16)},{int(card_color[5:7],16)},0.1)"
                if is_final else "#1a1d27"
            )
            border_top = f"border-top:3px solid {card_color};" if is_final else ""

            st.markdown(f"""
            <div style="display:flex;gap:0.75rem;margin-bottom:0.5rem;align-items:flex-start">
                <div style="display:flex;flex-direction:column;align-items:center">
                    <div style="font-size:1.4rem">{emoji}</div>
                    {"" if i == len(trace_steps)-1 else
                     '<div style="width:2px;height:30px;background:#2d3148;margin-top:4px"></div>'}
                </div>
                <div style="flex:1;background:{card_bg};border:1px solid {card_color};
                            border-radius:10px;padding:0.7rem 1rem;{border_top}">
                    <div style="display:flex;justify-content:space-between;align-items:center;flex-wrap:wrap;gap:0.3rem">
                        <div style="font-weight:700;color:#e2e8f0;font-size:0.9rem">
                            {'✓ ' if not is_final else '🎯 '}{agent}
                        </div>
                        <span style="background:#1a1d27;border:1px solid #2d3148;color:#94a3b8;
                                     padding:1px 8px;border-radius:4px;font-size:0.65rem">{mode}</span>
                    </div>
                    <div style="font-size:0.82rem;color:#e2e8f0;margin:0.3rem 0;
                                {'font-size:1rem;font-weight:700;color:'+card_color if is_final else ''}">
                        {contrib}
                    </div>
                    <div style="font-size:0.72rem;color:#64748b">{details}</div>
                    <div style="margin-top:0.3rem">
                        <span style="background:#2d3148;color:#94a3b8;padding:1px 8px;
                                     border-radius:4px;font-size:0.7rem">Output: {output}</span>
                    </div>
                </div>
            </div>
            """, unsafe_allow_html=True)

        st.markdown(f"""
        <div style="background:rgba(124,58,237,0.08);border:1px solid #7c3aed;
                    border-radius:8px;padding:0.6rem 1rem;font-size:0.75rem;color:#a78bfa;margin-top:0.5rem">
            ↓ FINAL PRIORITY: <strong style="color:{fusion_t['priority_color']}">{fusion_t['priority_level']}</strong>
            &nbsp;|&nbsp; Score: {fusion_t['priority_score']:.0f}/100
            &nbsp;|&nbsp; Inputs: LIVE weather evidence + MODEL predictions + USER SUBMITTED reports + DEMO infrastructure.
            No real sensor or government emergency systems were queried.
        </div>
        """, unsafe_allow_html=True)


# ══════════════════════════════════════════════════════════════════════════════
# TAB 4 — HUMAN-IN-THE-LOOP
# ══════════════════════════════════════════════════════════════════════════════
with tab_hitl:
    section_header("🔐 HUMAN-IN-THE-LOOP APPROVAL",
                   '<span style="background:#1e3a5f;color:#93c5fd;font-size:0.7rem;padding:2px 8px;border-radius:4px;font-weight:700;letter-spacing:0.04em">Decision-support demonstration</span>')
    st.markdown("""
    <div style="background:rgba(239,68,68,0.08);border:1px solid rgba(239,68,68,0.3);
                border-radius:8px;padding:0.6rem 1rem;font-size:0.78rem;color:#fca5a5;margin-bottom:1rem">
        🔐 <strong>Demo Safety Notice:</strong> These approval buttons do NOT trigger real-world emergency actions.
        They update application state only and are recorded in the audit trail for demonstration purposes.
        Real emergency response requires authorised government personnel.
    </div>
    """, unsafe_allow_html=True)

    # Show CRITICAL and HIGH zones for approval
    approval_fusions = [f for f in fusions if f["priority_level"] in ("CRITICAL", "HIGH")]

    if not approval_fusions:
        st.info("No CRITICAL or HIGH priority zones in current scenario. Switch to HEAVY or EXTREME.")
    else:
        # Pre-populate pending actions if not already done
        for fusion_h in approval_fusions:
            key = f"{fusion_h['area']}_{fusion_h['city']}"
            if key not in st.session_state.di_pending_actions:
                pred_h = next(
                    (p for p in state.get("risk_predictions", [])
                     if p.get("area") == fusion_h["area"] and p.get("city") == fusion_h["city"]),
                    {}
                )
                action_h = get_recommended_action(fusion_h, pred_h)
                st.session_state.di_pending_actions[key] = action_h

        # Workflow diagram
        st.markdown("""
        <div style="display:flex;align-items:center;gap:0.5rem;flex-wrap:wrap;
                    font-size:0.82rem;color:#94a3b8;margin-bottom:1rem">
            <span style="background:#7c3aed;color:white;padding:3px 10px;border-radius:6px">AI Recommendation</span>
            <span>→</span>
            <span style="background:#1a1d27;border:1px solid #2d3148;color:#e2e8f0;padding:3px 10px;border-radius:6px">Human Decision</span>
            <span>→</span>
            <span style="background:#1a1d27;border:1px solid #22c55e;color:#22c55e;padding:3px 10px;border-radius:6px">Final Decision Recorded</span>
        </div>
        """, unsafe_allow_html=True)

        for fusion_h in approval_fusions[:8]:
            action_key  = f"{fusion_h['area']}_{fusion_h['city']}"
            action_h    = st.session_state.di_pending_actions.get(action_key)
            if not action_h:
                continue

            action_id   = action_h["action_id"]
            level       = fusion_h["priority_level"]
            score       = fusion_h["priority_score"]
            color       = fusion_h["priority_color"]
            area        = fusion_h["area"]
            city        = fusion_h["city"]

            existing    = st.session_state.di_approved_actions.get(action_id)

            if existing:
                dec_color = {
                    "APPROVED": "#22c55e", "REJECTED": "#ef4444", "MODIFIED": "#f97316"
                }.get(existing["decision"], "#94a3b8")
                dec_icon  = {
                    "APPROVED": "✅", "REJECTED": "❌", "MODIFIED": "🔄"
                }.get(existing["decision"], "•")
                st.markdown(f"""
                <div style="background:#1a1d27;border:1px solid {dec_color};
                            border-radius:10px;padding:0.75rem 1rem;margin-bottom:0.5rem;
                            opacity:0.8">
                    <div style="display:flex;justify-content:space-between;align-items:center">
                        <div>
                            <span style="font-size:1rem">{dec_icon}</span>
                            <strong style="color:#e2e8f0;font-size:0.9rem"> {area}, {city}</strong>
                            <span style="background:{color};color:white;padding:1px 6px;
                                         border-radius:4px;font-size:0.68rem;font-weight:600;margin-left:0.5rem">{level}</span>
                        </div>
                        <span style="background:{dec_color};color:white;padding:2px 8px;
                                     border-radius:6px;font-size:0.72rem;font-weight:600">
                            {existing['decision']}
                        </span>
                    </div>
                    <div style="font-size:0.75rem;color:#94a3b8;margin-top:0.3rem">
                        {existing.get('note','Decision recorded.')} — {existing.get('timestamp','')}
                    </div>
                </div>
                """, unsafe_allow_html=True)
                continue

            # Pending approval card
            with st.container():
                st.markdown(f"""
                <div style="background:#1a1d27;border:1px solid {color};border-top:3px solid {color};
                            border-radius:10px;padding:0.85rem 1rem;margin-bottom:0.4rem">
                    <div style="display:flex;justify-content:space-between;align-items:flex-start;flex-wrap:wrap;gap:0.5rem">
                        <div>
                            <div style="font-size:1rem;font-weight:700;color:#e2e8f0">
                                {fusion_h['priority_emoji']} {area}, {city}
                            </div>
                            <div style="font-size:0.75rem;color:#94a3b8">
                                Priority Score: <strong style="color:{color}">{score:.0f}/100 — {level}</strong>
                            </div>
                        </div>
                        <span style="background:rgba(234,179,8,0.2);border:1px solid #eab308;
                                     color:#eab308;padding:2px 8px;border-radius:6px;font-size:0.72rem;font-weight:600">
                            ⏳ PENDING HUMAN APPROVAL
                        </span>
                    </div>
                    <div style="background:#0f1117;border-radius:6px;padding:0.5rem 0.75rem;
                                margin:0.5rem 0;font-size:0.8rem;color:#e2e8f0">
                        <strong style="color:#a78bfa">🤖 AI RECOMMENDATION:</strong><br>
                        {action_h['title']}<br>
                        <span style="font-size:0.72rem;color:#94a3b8">{action_h['description'][:200]}…</span>
                    </div>
                    <div style="font-size:0.72rem;color:#64748b">
                        Urgency: <strong style="color:{color}">{action_h['urgency']}</strong>
                        &nbsp;|&nbsp; Action ID: {action_id}
                    </div>
                </div>
                """, unsafe_allow_html=True)

                note_key = f"di_note_{action_id}"
                if note_key not in st.session_state:
                    st.session_state[note_key] = ""

                note_col, btn_col1, btn_col2, btn_col3 = st.columns([2, 1, 1, 1])
                with note_col:
                    mod_note = st.text_input(
                        "Modification note (optional):",
                        key=note_key,
                        placeholder="e.g. Reduce scope to drainage only...",
                        label_visibility="collapsed",
                    )
                    st.markdown("""
                    <div style="font-size:0.68rem;color:#475569;margin-top:2px">
                        ✏️ Note — updates application state only. No real actions triggered.
                    </div>""", unsafe_allow_html=True)
                with btn_col1:
                    if st.button("✅ APPROVE", key=f"di_app_{action_id}", type="primary",
                                 use_container_width=True):
                        ts = datetime.now(timezone.utc).strftime("%H:%M UTC")
                        note_text = st.session_state.get(note_key, "") or "Human operator approved."
                        st.session_state.di_approved_actions[action_id] = {
                            "decision": "APPROVED", "note": note_text, "timestamp": ts,
                        }
                        audit.record(action_h, "APPROVED", "Operator", note_text)
                        st.rerun()
                with btn_col2:
                    if st.button("🔄 MODIFY", key=f"di_mod_{action_id}",
                                 use_container_width=True):
                        ts = datetime.now(timezone.utc).strftime("%H:%M UTC")
                        note_text = st.session_state.get(note_key, "") or "Action scope modified by operator."
                        st.session_state.di_approved_actions[action_id] = {
                            "decision": "MODIFIED", "note": note_text, "timestamp": ts,
                        }
                        audit.record(action_h, "MODIFIED", "Operator", note_text)
                        st.rerun()
                with btn_col3:
                    if st.button("❌ REJECT", key=f"di_rej_{action_id}",
                                 use_container_width=True):
                        ts = datetime.now(timezone.utc).strftime("%H:%M UTC")
                        note_text = st.session_state.get(note_key, "") or "Operator determined action not appropriate at this time."
                        st.session_state.di_approved_actions[action_id] = {
                            "decision": "REJECTED", "note": note_text, "timestamp": ts,
                        }
                        audit.record(action_h, "REJECTED", "Operator", note_text)
                        st.rerun()

    st.markdown("<br>", unsafe_allow_html=True)
    # Summary of decisions
    if st.session_state.di_approved_actions:
        n_app  = sum(1 for v in st.session_state.di_approved_actions.values() if v["decision"] == "APPROVED")
        n_rej  = sum(1 for v in st.session_state.di_approved_actions.values() if v["decision"] == "REJECTED")
        n_mod  = sum(1 for v in st.session_state.di_approved_actions.values() if v["decision"] == "MODIFIED")
        st.markdown(f"""
        <div style="background:#1a1d27;border:1px solid #2d3148;border-radius:8px;
                    padding:0.75rem 1rem;font-size:0.82rem;color:#94a3b8">
            <strong style="color:#e2e8f0">Session Summary:</strong>
            &nbsp; ✅ Approved: {n_app} &nbsp;|&nbsp; 🔄 Modified: {n_mod} &nbsp;|&nbsp; ❌ Rejected: {n_rej}
            &nbsp;|&nbsp; Total decisions: {len(st.session_state.di_approved_actions)}
        </div>
        """, unsafe_allow_html=True)


# ══════════════════════════════════════════════════════════════════════════════
# TAB 5 — AUDIT TRAIL
# ══════════════════════════════════════════════════════════════════════════════
with tab_audit:
    section_header("ACTION AUDIT TRAIL",
                   '<span style="background:#1e3a5f;color:#93c5fd;font-size:0.7rem;padding:2px 8px;border-radius:4px;font-weight:700;letter-spacing:0.04em">APPLICATION DECISION LOG</span>')
    st.markdown("""
    <div style="font-size:0.8rem;color:#94a3b8;margin-bottom:0.75rem">
        A record of every human decision made in this session.
        All entries are DEMO only — no real operational systems are updated.
    </div>
    """, unsafe_allow_html=True)

    entries = audit.get_all()
    if not entries:
        st.info("No audit entries yet. Use the Human-in-the-Loop tab to approve, modify, or reject recommendations.")
    else:
        # Header row
        st.markdown("""
        <div style="display:grid;grid-template-columns:120px 1fr 1fr 90px 100px 130px;gap:0.5rem;
                    padding:0.4rem 0.5rem;background:#1a1d27;border-radius:6px 6px 0 0;
                    font-size:0.7rem;font-weight:700;color:#94a3b8;text-transform:uppercase">
            <div>Zone</div>
            <div>AI Recommendation</div>
            <div>Human Decision</div>
            <div>Priority</div>
            <div>Timestamp</div>
            <div>Status</div>
        </div>
        """, unsafe_allow_html=True)

        for entry in entries:
            dec   = entry["human_decision"]
            dec_color = {
                "APPROVED": "#22c55e", "REJECTED": "#ef4444", "MODIFIED": "#f97316"
            }.get(dec, "#94a3b8")
            dec_icon  = {"APPROVED": "✅", "REJECTED": "❌", "MODIFIED": "🔄"}.get(dec, "•")
            lvl_color = COLORS.get(entry.get("priority_level", "LOW"), "#94a3b8")

            note_text = entry.get("modification_note", "")
            decision_text = (
                f"{dec_icon} {dec}" +
                (f" — {note_text}" if note_text else "")
            )

            st.markdown(f"""
            <div style="display:grid;grid-template-columns:120px 1fr 1fr 90px 100px 130px;
                        gap:0.5rem;padding:0.5rem;border-bottom:1px solid #2d3148;
                        font-size:0.78rem;align-items:start">
                <div style="color:#e2e8f0;font-weight:600">{entry['zone'][:18]}</div>
                <div style="color:#94a3b8">{entry['ai_recommendation'][:60]}…</div>
                <div style="color:{dec_color};font-weight:600">{decision_text[:60]}</div>
                <div>
                    <span style="background:{lvl_color};color:white;padding:1px 6px;
                                 border-radius:4px;font-size:0.65rem;font-weight:600">
                        {entry.get('priority_level','?')}
                    </span>
                </div>
                <div style="color:#64748b;font-size:0.72rem">{entry['timestamp'][11:19]}</div>
                <div>
                    <span style="background:#1a1d27;border:1px solid #2d3148;color:#94a3b8;
                                 padding:1px 6px;border-radius:4px;font-size:0.65rem">
                        {entry['status']}
                    </span>
                </div>
            </div>
            """, unsafe_allow_html=True)

        # Export + Clear buttons
        st.markdown("<br>", unsafe_allow_html=True)
        _dl_col, _cl_col = st.columns([1, 1])
        with _dl_col:
            # Build CSV for download
            import io as _io
            _csv_lines = ["Zone,AI Recommendation,Human Decision,Note,Priority,Timestamp,Status"]
            for _e in entries:
                def _esc(s): return '"' + str(s).replace('"', '""') + '"'
                _csv_lines.append(",".join([
                    _esc(_e.get("zone","")), _esc(_e.get("ai_recommendation","")),
                    _esc(_e.get("human_decision","")), _esc(_e.get("modification_note","")),
                    _esc(_e.get("priority_level","")), _esc(_e.get("timestamp","")),
                    _esc(_e.get("status","")),
                ]))
            _csv_data = "\n".join(_csv_lines)
            st.download_button(
                "📥 Export Audit Trail (CSV)",
                data=_csv_data,
                file_name=f"floodguard_audit_{datetime.now(timezone.utc).strftime('%Y%m%d_%H%M')}.csv",
                mime="text/csv",
                use_container_width=True,
            )
        with _cl_col:
            if st.button("🗑 Clear Audit Trail", key="di_clear_audit", use_container_width=True):
                audit.clear()
                st.session_state.di_approved_actions = {}
                st.rerun()

# ──────────────────────────────────────────────────────────────────────────────
# Footer
# ──────────────────────────────────────────────────────────────────────────────
st.markdown("---")
st.markdown(f"""
<div style="text-align:center;color:#475569;font-size:0.72rem;padding-bottom:1rem">
    FloodGuard AI — Decision Intelligence Center &nbsp;|&nbsp; HYBRID DATA: LIVE weather · MODEL predictions · USER SUBMITTED reports · DEMO infrastructure<br>
    Application priority scores are <strong>NOT</strong> scientifically validated emergency-response scores.<br>
    All AI recommendations require authorized human verification before any real-world implementation.
</div>
""", unsafe_allow_html=True)
