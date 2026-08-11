"""
FloodGuard AI — Page 7: Closed-Loop Learning & Analytics
Feature 10: Store Prediction → Incident → Response → Outcome, show prediction vs outcome.
All data is DEMO/SIMULATED.
"""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import streamlit as st
import plotly.graph_objects as go
import plotly.express as px
import pandas as pd
from datetime import datetime
from frontend.ui_utils import (
    apply_global_css, header, metric_card, demo_badge,
    simulated_badge, section_header, COLORS, ai_disclaimer
)
from agents.orchestrator import get_orchestrator, SCENARIOS

st.set_page_config(
    page_title="Learning Loop — FloodGuard AI",
    page_icon="🔄",
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
    st.markdown("## 🔄 Learning Loop")
    st.markdown("---")
    for sc_id, sc_info in SCENARIOS.items():
        if st.button(f"{sc_info['emoji']} {sc_info['label']}", key=f"sc_{sc_id}",
                     use_container_width=True,
                     type="primary" if orch.current_scenario == sc_id else "secondary"):
            with st.spinner(f"Running {sc_info['label']}..."):
                orch.run_pipeline(scenario=sc_id)
            st.rerun()
    st.markdown("---")
    st.markdown(f'<div style="font-size:0.75rem;color:#94a3b8">{demo_badge()} Synthetic data only</div>', unsafe_allow_html=True)

# ──────────────────────────────────────────────
# Header
# ──────────────────────────────────────────────
header("Closed-Loop Learning", "Prediction → Incident → Response → Outcome tracking", "🔄")

st.markdown(f"""
<div style="background:rgba(124,58,237,0.1);border:1px solid #7c3aed;border-radius:8px;
            padding:0.5rem 0.9rem;margin-bottom:1rem;font-size:0.78rem;color:#a78bfa">
    {simulated_badge()} All cycles are <strong>DEMO/SIMULATED</strong> data generated from the current scenario.
    In production, this would store real prediction → outcome data for continuous model improvement.
</div>
""", unsafe_allow_html=True)

# Get learning data
learning_cycles = state.get("learning_cycles", [])
predictions = state.get("risk_predictions", [])
scenario = state.get("scenario", "NORMAL")

# If no learning data yet, seed it
if not learning_cycles and predictions:
    store = orch.learning_store
    store._initialized = False
    learning_cycles = store.get_cycles(scenario=scenario, risk_predictions=predictions)

if not learning_cycles:
    st.info("Run a scenario to generate learning cycle data.")
    st.stop()

# ──────────────────────────────────────────────
# Accuracy summary
# ──────────────────────────────────────────────
accuracy_summary = orch.learning_store.get_accuracy_summary()

k1,k2,k3,k4,k5,k6 = st.columns(6)
with k1: metric_card("Total Cycles",      str(accuracy_summary.get("total_cycles", 0)), color="#3b82f6", icon="🔄")
with k2: metric_card("Level Accuracy",    f"{accuracy_summary.get('level_accuracy_pct',0):.0f}%", color="#22c55e", icon="🎯")
with k3: metric_card("Avg Score Accuracy",f"{accuracy_summary.get('avg_score_accuracy',0):.0f}/100", color="#3b82f6", icon="📊")
with k4: metric_card("Avg Score Delta",   f"{accuracy_summary.get('avg_score_delta',0):+.1f}", color="#f97316", icon="📈")
with k5: metric_card("Avg Response Time", f"~{accuracy_summary.get('avg_response_time_min',0):.0f} min", color="#7c3aed", icon="⏱️")
with k6: metric_card("Scenarios Tracked", str(len(SCENARIOS)), color="#14b8a6", icon="🎬")

st.markdown("<br>", unsafe_allow_html=True)

# ──────────────────────────────────────────────
# Tabs
# ──────────────────────────────────────────────
tab1, tab2, tab3 = st.tabs([
    "📊 Prediction vs Outcome",
    "🔄 Cycle Log",
    "📈 Model Feedback",
])

# ── Tab 1: Prediction vs Outcome ─────────────
with tab1:
    section_header("PREDICTION VS ACTUAL OUTCOME", simulated_badge())

    col_chart, col_stats = st.columns([1.4, 1])

    with col_chart:
        # Scatter: predicted score vs actual score
        df_cycles = pd.DataFrame(learning_cycles)

        fig_scatter = go.Figure()
        level_colors = {"CRITICAL": "#ef4444", "HIGH": "#f97316", "MEDIUM": "#eab308", "LOW": "#22c55e"}

        for level in ["CRITICAL", "HIGH", "MEDIUM", "LOW"]:
            df_l = df_cycles[df_cycles["predicted_risk_level"] == level]
            if not df_l.empty:
                fig_scatter.add_trace(go.Scatter(
                    x=df_l["predicted_risk_score"],
                    y=df_l["actual_risk_score"],
                    mode="markers",
                    name=f"Predicted {level}",
                    marker=dict(color=level_colors[level], size=8, opacity=0.8),
                    text=df_l["area"] + ", " + df_l["city"],
                    hovertemplate="<b>%{text}</b><br>Predicted: %{x:.0f}<br>Actual: %{y:.0f}<extra></extra>",
                ))

        # Perfect prediction line
        fig_scatter.add_trace(go.Scatter(
            x=[0, 100], y=[0, 100],
            mode="lines",
            name="Perfect Prediction",
            line=dict(color="#3b82f6", dash="dash", width=1),
        ))

        fig_scatter.update_layout(
            paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
            xaxis=dict(color="#94a3b8", title="Predicted Risk Score", range=[0, 105]),
            yaxis=dict(color="#94a3b8", title="Actual Risk Score",    range=[0, 105]),
            legend=dict(font=dict(color="#e2e8f0", size=10)),
            height=380, margin=dict(t=10, b=10, l=10, r=10),
        )
        st.plotly_chart(fig_scatter, use_container_width=True, config={"displayModeBar": False})
        st.markdown('<div style="font-size:0.7rem;color:#64748b">⚙ SIMULATED — dashed line = perfect prediction. Points cluster near it = good accuracy.</div>', unsafe_allow_html=True)

    with col_stats:
        # Outcome distribution
        outcomes = accuracy_summary.get("outcome_distribution", {})
        if outcomes:
            section_header("OUTCOME DISTRIBUTION")
            outcome_colors = {
                "RESOLVED": "#22c55e", "MITIGATED": "#14b8a6",
                "ONGOING": "#eab308", "ESCALATED": "#ef4444", "FALSE_ALARM": "#94a3b8",
            }
            fig_out = go.Figure(go.Pie(
                labels=list(outcomes.keys()),
                values=list(outcomes.values()),
                hole=0.55,
                marker=dict(colors=[outcome_colors.get(k, "#3b82f6") for k in outcomes]),
                textinfo="percent+label",
            ))
            fig_out.update_layout(
                paper_bgcolor="rgba(0,0,0,0)",
                legend=dict(font=dict(color="#e2e8f0", size=10)),
                height=250, margin=dict(t=10, b=10, l=10, r=10),
                showlegend=False,
            )
            st.plotly_chart(fig_out, use_container_width=True, config={"displayModeBar": False})

        st.markdown("---")
        # Prediction accuracy by level
        section_header("ACCURACY BY RISK LEVEL")
        for level in ["CRITICAL", "HIGH", "MEDIUM", "LOW"]:
            level_cycles = [c for c in learning_cycles if c["predicted_risk_level"] == level]
            if not level_cycles:
                continue
            correct = sum(1 for c in level_cycles if c["predicted_risk_level"] == c["actual_risk_level"])
            acc = correct / len(level_cycles) * 100
            p_color = level_colors.get(level, "#94a3b8")
            st.markdown(f"""
            <div style="display:flex;align-items:center;gap:0.75rem;margin-bottom:0.3rem">
                <div style="min-width:70px;font-size:0.78rem;color:{p_color};font-weight:600">{level}</div>
                <div style="flex:1;background:#1a1d27;border-radius:4px;height:16px;overflow:hidden;border:1px solid #2d3148">
                    <div style="width:{acc:.0f}%;background:{p_color};height:100%;border-radius:4px"></div>
                </div>
                <div style="min-width:40px;font-size:0.78rem;color:#e2e8f0">{acc:.0f}%</div>
                <div style="font-size:0.72rem;color:#64748b">{len(level_cycles)} pts</div>
            </div>
            """, unsafe_allow_html=True)

# ── Tab 2: Cycle Log ─────────────────────────
with tab2:
    section_header("LEARNING CYCLE LOG", simulated_badge())
    st.markdown("""
    <div style="font-size:0.8rem;color:#94a3b8;margin-bottom:0.75rem">
        Each row represents one complete cycle: prediction made → incident detected → response deployed → outcome recorded.
    </div>
    """, unsafe_allow_html=True)

    df_log = pd.DataFrame(learning_cycles)
    if not df_log.empty:
        display_cols = [
            "cycle_id", "area", "city",
            "predicted_risk_level", "predicted_risk_score",
            "actual_risk_level", "actual_risk_score",
            "prediction_accuracy", "score_delta",
            "response_time_minutes", "resolution_time_minutes",
            "outcome", "model_feedback",
        ]
        available_cols = [c for c in display_cols if c in df_log.columns]
        df_display = df_log[available_cols].copy()
        df_display.columns = [c.replace("_", " ").title() for c in available_cols]

        st.dataframe(df_display, use_container_width=True, hide_index=True, height=450)

        # Download
        csv_data = df_log[available_cols].to_csv(index=False)
        st.download_button(
            "📥 Download Cycle Log (CSV)",
            data=csv_data,
            file_name=f"floodguard_learning_cycles_{datetime.utcnow().strftime('%Y%m%d')}.csv",
            mime="text/csv",
        )

# ── Tab 3: Model Feedback ────────────────────
with tab3:
    section_header("MODEL FEEDBACK SUMMARY", simulated_badge())

    col_fb1, col_fb2 = st.columns([1, 1])

    with col_fb1:
        # Score delta distribution
        df_cycles2 = pd.DataFrame(learning_cycles)
        if not df_cycles2.empty and "score_delta" in df_cycles2.columns:
            section_header("PREDICTION ERROR DISTRIBUTION")
            fig_hist = go.Figure(go.Histogram(
                x=df_cycles2["score_delta"],
                nbinsx=20,
                marker_color="#3b82f6",
                opacity=0.8,
            ))
            fig_hist.add_vline(x=0, line_dash="dash", line_color="#22c55e", annotation_text="Perfect")
            fig_hist.update_layout(
                paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
                xaxis=dict(color="#94a3b8", title="Actual − Predicted Score"),
                yaxis=dict(color="#94a3b8", title="Count"),
                height=260, margin=dict(t=10, b=10, l=10, r=10),
            )
            st.plotly_chart(fig_hist, use_container_width=True, config={"displayModeBar": False})
            st.markdown('<div style="font-size:0.7rem;color:#64748b">⚙ Centred near 0 = well-calibrated model</div>', unsafe_allow_html=True)

    with col_fb2:
        # Feedback categories
        section_header("FEEDBACK BREAKDOWN")
        feedback_counts: dict[str, int] = {}
        for c in learning_cycles:
            fb = c.get("model_feedback", "Unknown")
            # Shorten key
            if "Accurate" in fb:
                key = "✅ Accurate"
            elif "Under" in fb:
                key = "⚠️ Under-predicted"
            else:
                key = "📉 Over-predicted"
            feedback_counts[key] = feedback_counts.get(key, 0) + 1

        for key, count in sorted(feedback_counts.items(), key=lambda x: -x[1]):
            pct = count / max(len(learning_cycles), 1) * 100
            fb_color = "#22c55e" if "Accurate" in key else "#f97316" if "Under" in key else "#3b82f6"
            st.markdown(f"""
            <div style="display:flex;align-items:center;gap:0.75rem;margin-bottom:0.4rem">
                <div style="min-width:160px;font-size:0.78rem;color:{fb_color}">{key}</div>
                <div style="flex:1;background:#1a1d27;border-radius:4px;height:18px;overflow:hidden;border:1px solid #2d3148">
                    <div style="width:{pct:.0f}%;background:{fb_color};height:100%;border-radius:4px"></div>
                </div>
                <div style="min-width:60px;font-size:0.78rem;color:#e2e8f0">{count} ({pct:.0f}%)</div>
            </div>
            """, unsafe_allow_html=True)

        # Response time by outcome
        st.markdown("---")
        section_header("AVG RESPONSE TIME BY OUTCOME")
        if learning_cycles:
            by_outcome: dict[str, list] = {}
            for c in learning_cycles:
                out = c.get("outcome", "UNKNOWN")
                by_outcome.setdefault(out, []).append(c.get("response_time_minutes", 0))
            avg_by_outcome = {k: sum(v)/len(v) for k, v in by_outcome.items()}

            outcome_colors_list = ["#22c55e", "#14b8a6", "#eab308", "#ef4444", "#94a3b8"]
            fig_rt = go.Figure(go.Bar(
                x=list(avg_by_outcome.keys()),
                y=list(avg_by_outcome.values()),
                marker=dict(color=outcome_colors_list[:len(avg_by_outcome)]),
            ))
            fig_rt.update_layout(
                paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
                xaxis=dict(color="#94a3b8"),
                yaxis=dict(color="#94a3b8", title="Avg Minutes"),
                height=220, margin=dict(t=10, b=10, l=10, r=10),
            )
            st.plotly_chart(fig_rt, use_container_width=True, config={"displayModeBar": False})

# ──────────────────────────────────────────────
# Footer
# ──────────────────────────────────────────────
st.markdown("---")
st.markdown(f"""
<div style="text-align:center;color:#475569;font-size:0.72rem;padding-bottom:1rem">
    FloodGuard AI | Closed-Loop Learning | {simulated_badge()} All data is DEMO/SIMULATED.<br>
    In production: connects to real prediction store and incident database for continuous improvement.
</div>
""", unsafe_allow_html=True)
