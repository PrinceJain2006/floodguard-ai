"""
FloodGuard AI — Streamlit UI Utilities
Shared styles, components, helpers.
"""
import streamlit as st
import plotly.graph_objects as go
import plotly.express as px
import pandas as pd
from datetime import datetime

# ──────────────────────────────────────────────
# Color palette
# ──────────────────────────────────────────────
COLORS = {
    "LOW":      "#22c55e",
    "MEDIUM":   "#eab308",
    "HIGH":     "#f97316",
    "CRITICAL": "#ef4444",
    "bg":       "#0a0d14",
    "surface":  "#131620",
    "border":   "#1e2440",
    "text":     "#e2e8f0",
    "muted":    "#94a3b8",
    "blue":     "#3b82f6",
    "purple":   "#7c3aed",
    "teal":     "#14b8a6",
}

RISK_EMOJI = {"LOW": "🟢", "MEDIUM": "🟡", "HIGH": "🟠", "CRITICAL": "🔴"}
RISK_BADGE = {
    "LOW":      "🟢 LOW",
    "MEDIUM":   "🟡 MEDIUM",
    "HIGH":     "🟠 HIGH",
    "CRITICAL": "🔴 CRITICAL",
}


def apply_global_css():
    st.markdown("""
    <style>
    /* ═══════════════════════════════════════════════════════════════════
       FloodGuard AI — Premium Command Center Global Styles
    ═══════════════════════════════════════════════════════════════════ */

    /* Global dark theme */
    .stApp { background-color: #0a0d14; color: #e2e8f0; }
    .main .block-container { padding-top: 1rem; padding-bottom: 2rem; max-width: 1440px; }

    /* ── Cards ─────────────────────────────────────────────────────── */
    .fg-card {
        background: #131620;
        border: 1px solid #1e2440;
        border-radius: 10px;
        padding: 1rem 1.2rem;
        margin-bottom: 0.75rem;
        transition: border-color 0.15s;
    }
    .fg-card:hover { border-color: #2d3a60; }
    .fg-card-danger {
        background: #150b0b;
        border: 1px solid #7f1d1d;
        border-radius: 10px;
        padding: 1rem 1.2rem;
        margin-bottom: 0.75rem;
    }
    .fg-card-warn {
        background: #141000;
        border: 1px solid #78350f;
        border-radius: 10px;
        padding: 1rem 1.2rem;
        margin-bottom: 0.75rem;
    }
    .fg-card-success {
        background: #071310;
        border: 1px solid #14532d;
        border-radius: 10px;
        padding: 1rem 1.2rem;
        margin-bottom: 0.75rem;
    }
    .fg-card-blue {
        background: #080f1e;
        border: 1px solid #1e3a5f;
        border-radius: 10px;
        padding: 1rem 1.2rem;
        margin-bottom: 0.75rem;
    }
    .fg-card-granite {
        background: linear-gradient(135deg, #0a0f1e, #0d1a2e);
        border: 1px solid #3b82f6;
        border-radius: 10px;
        padding: 1rem 1.2rem;
        margin-bottom: 0.75rem;
        position: relative;
        overflow: hidden;
    }
    .fg-card-granite::before {
        content: '';
        position: absolute; top: 0; left: 0; right: 0; height: 2px;
        background: linear-gradient(90deg, #3b82f6, #7c3aed);
    }

    /* ── Metric tiles ──────────────────────────────────────────────── */
    .fg-metric {
        background: #131620;
        border: 1px solid #1e2440;
        border-radius: 10px;
        padding: 1.1rem;
        text-align: center;
        transition: border-color 0.15s, transform 0.15s;
    }
    .fg-metric:hover { border-color: #3b82f6; transform: translateY(-1px); }
    .fg-metric-value { font-size: 1.9rem; font-weight: 800; line-height: 1; letter-spacing: -0.02em; }
    .fg-metric-label { font-size: 0.7rem; color: #64748b; margin-top: 0.3rem; text-transform: uppercase; letter-spacing: 0.07em; }
    .fg-metric-delta { font-size: 0.72rem; color: #94a3b8; margin-top: 0.15rem; }

    /* ── Risk indicator bar (used in zone details) ─────────────────── */
    .risk-bar-container {
        background: #1e2440;
        border-radius: 4px;
        height: 8px;
        overflow: hidden;
        margin: 4px 0;
    }

    /* ── Risk badges ───────────────────────────────────────────────── */
    .badge-critical { background: #ef4444; color: white; padding: 2px 9px; border-radius: 12px; font-size: 0.72rem; font-weight: 700; letter-spacing: 0.04em; }
    .badge-high     { background: #f97316; color: white; padding: 2px 9px; border-radius: 12px; font-size: 0.72rem; font-weight: 700; letter-spacing: 0.04em; }
    .badge-medium   { background: #eab308; color: #111; padding: 2px 9px; border-radius: 12px; font-size: 0.72rem; font-weight: 700; letter-spacing: 0.04em; }
    .badge-low      { background: #22c55e; color: white; padding: 2px 9px; border-radius: 12px; font-size: 0.72rem; font-weight: 700; letter-spacing: 0.04em; }

    /* ── Agent activity ────────────────────────────────────────────── */
    .agent-row {
        display: flex; align-items: center; gap: 0.75rem;
        padding: 0.55rem 0.7rem; border-bottom: 1px solid #1e2440;
        border-radius: 4px;
    }
    .agent-row:hover { background: #131620; }
    .agent-name { font-weight: 600; min-width: 180px; font-size: 0.86rem; }
    .agent-status { font-size: 0.8rem; color: #94a3b8; }

    /* ── Agent trace panel ─────────────────────────────────────────── */
    .agent-trace-step {
        background: #0d1020;
        border: 1px solid #1e2440;
        border-left: 3px solid #3b82f6;
        border-radius: 0 8px 8px 0;
        padding: 0.7rem 1rem;
        margin-bottom: 0.5rem;
        position: relative;
    }
    .agent-trace-step.complete { border-left-color: #22c55e; }
    .agent-trace-step.error { border-left-color: #ef4444; }
    .agent-trace-step.fallback { border-left-color: #eab308; }
    .agent-trace-step.granite { border-left-color: #7c3aed; background: #0a0d18; }

    /* ── Timeline ──────────────────────────────────────────────────── */
    .timeline-item {
        display: flex; gap: 1rem; padding: 0.5rem 0;
        border-left: 2px solid #1e2440; padding-left: 1rem;
        margin-left: 0.5rem;
    }
    .timeline-time { font-size: 0.72rem; color: #64748b; white-space: nowrap; }

    /* ── Alert banners ─────────────────────────────────────────────── */
    .alert-critical {
        background: rgba(239,68,68,0.12);
        border: 1px solid rgba(239,68,68,0.6);
        border-left: 4px solid #ef4444;
        border-radius: 6px; padding: 0.75rem 1rem; margin-bottom: 0.5rem;
    }
    .alert-high {
        background: rgba(249,115,22,0.12);
        border: 1px solid rgba(249,115,22,0.6);
        border-left: 4px solid #f97316;
        border-radius: 6px; padding: 0.75rem 1rem; margin-bottom: 0.5rem;
    }
    .alert-warning {
        background: rgba(234,179,8,0.10);
        border: 1px solid rgba(234,179,8,0.5);
        border-left: 4px solid #eab308;
        border-radius: 6px; padding: 0.75rem 1rem; margin-bottom: 0.5rem;
    }
    .alert-info {
        background: rgba(59,130,246,0.10);
        border: 1px solid rgba(59,130,246,0.5);
        border-left: 4px solid #3b82f6;
        border-radius: 6px; padding: 0.75rem 1rem; margin-bottom: 0.5rem;
    }

    /* ── Demo/data source labels ───────────────────────────────────── */
    .demo-label {
        background: #4c1d95; color: #ddd6fe; font-size: 0.68rem;
        padding: 2px 8px; border-radius: 4px; font-weight: 700;
        letter-spacing: 0.05em;
    }
    .simulated-label {
        background: #0f4c75; color: #7ec8e3; font-size: 0.68rem;
        padding: 2px 8px; border-radius: 4px; font-weight: 700;
    }

    /* ── Granite AI highlight ──────────────────────────────────────── */
    .granite-panel {
        background: linear-gradient(135deg, #06091a, #0a0d20);
        border: 1px solid #3b82f6;
        border-radius: 10px;
        padding: 1.2rem;
        margin-bottom: 0.75rem;
    }
    .granite-output {
        background: #050810;
        border: 1px solid #1e3a5f;
        border-radius: 6px;
        padding: 0.8rem 1rem;
        font-size: 0.85rem;
        color: #c7d2fe;
        line-height: 1.65;
        white-space: pre-wrap;
        font-family: 'Segoe UI', system-ui, sans-serif;
    }

    /* ── Approval buttons ──────────────────────────────────────────── */
    .approval-box {
        background: rgba(239,68,68,0.08);
        border: 1px solid rgba(239,68,68,0.4);
        border-radius: 8px;
        padding: 0.75rem 1rem;
        margin-top: 0.5rem;
    }

    /* ── Before/after comparison ───────────────────────────────────── */
    .before-box {
        background: rgba(239,68,68,0.08);
        border: 1px solid rgba(239,68,68,0.4);
        border-radius: 8px; padding: 0.9rem;
    }
    .after-box {
        background: rgba(34,197,94,0.08);
        border: 1px solid rgba(34,197,94,0.4);
        border-radius: 8px; padding: 0.9rem;
    }

    /* ── Buttons ───────────────────────────────────────────────────── */
    .stButton > button {
        border-radius: 8px;
        font-weight: 600;
        transition: all 0.2s;
        letter-spacing: 0.02em;
    }
    .stButton > button[kind="primary"] {
        background: linear-gradient(135deg, #1d4ed8, #1e40af);
        border: none;
    }

    /* ── Sidebar ───────────────────────────────────────────────────── */
    [data-testid="stSidebar"] { background: #0d1020; border-right: 1px solid #1e2440; }
    [data-testid="stSidebar"] .stMarkdown { color: #e2e8f0; }

    /* ── Tabs ──────────────────────────────────────────────────────── */
    .stTabs [data-baseweb="tab"] { color: #64748b; font-weight: 600; font-size: 0.85rem; }
    .stTabs [data-baseweb="tab"][aria-selected="true"] { color: #e2e8f0; }
    .stTabs [data-baseweb="tab-highlight"] { background-color: #3b82f6; height: 2px; }
    .stTabs [data-baseweb="tab-border"] { background-color: #1e2440; }

    /* ── Dividers ──────────────────────────────────────────────────── */
    hr { border-color: #1e2440; margin: 1rem 0; }

    /* ── Scrollbar ─────────────────────────────────────────────────── */
    ::-webkit-scrollbar { width: 5px; height: 5px; }
    ::-webkit-scrollbar-track { background: #0d1020; }
    ::-webkit-scrollbar-thumb { background: #1e2440; border-radius: 3px; }
    ::-webkit-scrollbar-thumb:hover { background: #2d3a60; }

    /* ── Dataframe ─────────────────────────────────────────────────── */
    .stDataFrame { border-radius: 8px; overflow: hidden; }

    /* ── Expander ──────────────────────────────────────────────────── */
    .streamlit-expanderHeader {
        background: #0d1020;
        border: 1px solid #1e2440;
        border-radius: 8px;
        color: #94a3b8;
        font-weight: 600;
        font-size: 0.85rem;
    }
    .streamlit-expanderContent {
        border: 1px solid #1e2440;
        border-top: none;
        border-radius: 0 0 8px 8px;
        background: #080c14;
    }

    /* ── Input widgets ─────────────────────────────────────────────── */
    .stSlider [data-testid="stThumb"] { background: #3b82f6; }
    .stSelectbox > div > div { background: #131620; border-color: #1e2440; }

    /* ── Progress bar ──────────────────────────────────────────────── */
    .stProgress > div > div { background: linear-gradient(90deg, #3b82f6, #7c3aed); }

    /* ── Info/success/warning/error boxes ──────────────────────────── */
    .stAlert { border-radius: 8px; }
    </style>
    """, unsafe_allow_html=True)


def header(title: str, subtitle: str = "", icon: str = ""):
    st.markdown(f"""
    <div style="margin-bottom:1.5rem">
        <h1 style="margin:0;font-size:1.8rem;font-weight:700;color:#e2e8f0">{icon} {title}</h1>
        {f'<p style="margin:0.25rem 0 0;color:#94a3b8;font-size:0.9rem">{subtitle}</p>' if subtitle else ''}
    </div>
    """, unsafe_allow_html=True)


def metric_card(label: str, value: str, delta: str = "", color: str = "#3b82f6", icon: str = ""):
    st.markdown(f"""
    <div class="fg-metric">
        <div class="fg-metric-value" style="color:{color}">{icon} {value}</div>
        <div class="fg-metric-label">{label}</div>
        {f'<div style="font-size:0.75rem;color:#94a3b8;margin-top:0.2rem">{delta}</div>' if delta else ''}
    </div>
    """, unsafe_allow_html=True)


def risk_badge(level: str) -> str:
    colors = {"LOW": "#22c55e", "MEDIUM": "#eab308", "HIGH": "#f97316", "CRITICAL": "#ef4444"}
    text_colors = {"LOW": "white", "MEDIUM": "#1a1d27", "HIGH": "white", "CRITICAL": "white"}
    c = colors.get(level, "#94a3b8")
    tc = text_colors.get(level, "white")
    return f'<span style="background:{c};color:{tc};padding:2px 8px;border-radius:12px;font-size:0.75rem;font-weight:600">{level}</span>'


def demo_badge():
    return '<span class="demo-label">DEMO DATA</span>'


def hybrid_badge():
    """Badge for hybrid mode: live weather + synthetic model data."""
    return (
        '<span style="background:#0f4c2a;color:#6ee7b7;font-size:0.7rem;'
        'padding:2px 8px;border-radius:4px;font-weight:700;letter-spacing:0.04em">'
        '🟢 HYBRID DATA</span>'
    )


def live_badge():
    """Badge for a fully-live data source."""
    return (
        '<span style="background:#14532d;color:#bbf7d0;font-size:0.7rem;'
        'padding:2px 8px;border-radius:4px;font-weight:700;letter-spacing:0.04em">'
        '🟢 LIVE</span>'
    )


def model_badge():
    """Badge marking ML-model / predicted data."""
    return (
        '<span style="background:#1e3a5f;color:#93c5fd;font-size:0.7rem;'
        'padding:2px 8px;border-radius:4px;font-weight:700;letter-spacing:0.04em">'
        '🔵 MODEL</span>'
    )


def simulated_badge():
    return '<span class="simulated-label">⚙ SIMULATED</span>'


def card(content: str, variant: str = "default"):
    variants = {
        "default": "fg-card",
        "danger":  "fg-card-danger",
        "warn":    "fg-card-warn",
        "success": "fg-card-success",
        "blue":    "fg-card-blue",
    }
    cls = variants.get(variant, "fg-card")
    st.markdown(f'<div class="{cls}">{content}</div>', unsafe_allow_html=True)


def section_header(title: str, badge: str = ""):
    st.markdown(f"""
    <div style="display:flex;align-items:center;gap:0.5rem;margin:1rem 0 0.75rem">
        <h3 style="margin:0;font-size:1rem;font-weight:700;color:#e2e8f0;text-transform:uppercase;letter-spacing:0.05em">{title}</h3>
        {badge}
    </div>
    """, unsafe_allow_html=True)


def ai_disclaimer():
    st.markdown("""
    <div style="background:rgba(124,58,237,0.1);border:1px solid #7c3aed;border-radius:8px;
                padding:0.6rem 1rem;font-size:0.78rem;color:#a78bfa;margin-bottom:1rem">
        🤖 <strong>AI Recommendations</strong> are decision-support suggestions and require
        authorized human verification before implementation.
        HYBRID DATA: 🟢 Live Weather · 🔵 ML Predictions · 🟠 User Reports · 🟡 Demo Infrastructure
    </div>
    """, unsafe_allow_html=True)


# ──────────────────────────────────────────────
# Chart helpers
# ──────────────────────────────────────────────

def risk_donut(counts: dict) -> go.Figure:
    labels = list(counts.keys())
    values = list(counts.values())
    colors_list = [COLORS.get(l, "#94a3b8") for l in labels]

    fig = go.Figure(go.Pie(
        labels=labels, values=values,
        hole=0.65,
        marker=dict(colors=colors_list),
        textinfo="value",
        hovertemplate="<b>%{label}</b>: %{value} zones<extra></extra>",
    ))
    fig.update_layout(
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        showlegend=True,
        legend=dict(orientation="v", font=dict(color="#e2e8f0", size=11)),
        margin=dict(t=20, b=20, l=20, r=20),
        height=220,
    )
    return fig


def rainfall_bar(data: list[dict], top_n: int = 10) -> go.Figure:
    df = pd.DataFrame(data).nlargest(top_n, "rainfall_1h")
    fig = go.Figure(go.Bar(
        x=df["rainfall_1h"],
        y=df["area"] + ", " + df["city"],
        orientation="h",
        marker=dict(
            color=df["rainfall_1h"],
            colorscale=[[0, "#22c55e"], [0.4, "#eab308"], [0.7, "#f97316"], [1, "#ef4444"]],
        ),
        hovertemplate="<b>%{y}</b><br>%{x:.1f} mm/hr<extra></extra>",
    ))
    fig.update_layout(
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        xaxis=dict(color="#94a3b8", title="Rainfall (mm/hr)"),
        yaxis=dict(color="#e2e8f0"),
        margin=dict(t=10, b=10, l=10, r=10),
        height=280,
    )
    return fig


def risk_gauge(score: float, label: str = "") -> go.Figure:
    color = (
        COLORS["CRITICAL"] if score >= 75 else
        COLORS["HIGH"]     if score >= 50 else
        COLORS["MEDIUM"]   if score >= 25 else
        COLORS["LOW"]
    )
    fig = go.Figure(go.Indicator(
        mode="gauge+number",
        value=score,
        domain=dict(x=[0, 1], y=[0, 1]),
        title=dict(text=label, font=dict(color="#e2e8f0", size=12)),
        gauge=dict(
            axis=dict(range=[0, 100], tickcolor="#94a3b8"),
            bar=dict(color=color),
            bgcolor="#1a1d27",
            bordercolor="#2d3148",
            steps=[
                dict(range=[0, 25],  color="#0f1a0f"),
                dict(range=[25, 50], color="#1a1500"),
                dict(range=[50, 75], color="#1a1000"),
                dict(range=[75, 100],color="#1a0f0f"),
            ],
        ),
        number=dict(font=dict(color=color, size=28)),
    ))
    fig.update_layout(
        paper_bgcolor="rgba(0,0,0,0)",
        margin=dict(t=20, b=20, l=20, r=20),
        height=180,
    )
    return fig


def timeline_chart(pipeline_log: list[dict]) -> go.Figure:
    if not pipeline_log:
        return go.Figure()
    steps = [l["step"] for l in pipeline_log]
    agents = [l["agent"] for l in pipeline_log]
    statuses = [l["status"] for l in pipeline_log]
    colors_list = ["#22c55e" if s == "COMPLETE" else "#3b82f6" if s == "RUNNING" else "#ef4444" for s in statuses]

    fig = go.Figure()
    for i, (step, agent, status, color) in enumerate(zip(steps, agents, statuses, colors_list)):
        fig.add_trace(go.Bar(
            x=[1], y=[step], orientation="h",
            marker_color=color,
            name=f"{agent}: {status}",
            showlegend=True,
            hovertemplate=f"<b>{step}</b><br>{agent}: {status}<extra></extra>",
        ))
    fig.update_layout(
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        barmode="stack",
        yaxis=dict(color="#e2e8f0"),
        xaxis=dict(visible=False),
        legend=dict(font=dict(color="#e2e8f0", size=10)),
        height=max(200, len(pipeline_log) * 25),
        margin=dict(t=10, b=10, l=10, r=10),
    )
    return fig


# ──────────────────────────────────────────────
# Agent trace / pipeline visualization helpers
# ──────────────────────────────────────────────

def render_agent_trace(pipeline_log: list[dict], granite_available: bool = False, granite_rate_limited: bool = False):
    """
    Render a visual agent activity trace from the pipeline log.
    Shows each agent step with status, input summary, and output.
    """
    if not pipeline_log:
        st.caption("No pipeline trace available — run a scenario first.")
        return

    AGENT_META = {
        "Flood Risk Agent":            {"icon": "🌊", "color": "#7c3aed", "desc": "ML flood-risk prediction"},
        "Drainage Agent":              {"icon": "🔧", "color": "#3b82f6", "desc": "Drainage analysis & scoring"},
        "Citizen Report Agent":        {"icon": "📱", "color": "#22c55e", "desc": "Multilingual NLP classification"},
        "Response Coordination Agent": {"icon": "⚡", "color": "#f97316", "desc": "Incident response planning"},
        "Chief Response Agent":        {"icon": "🎯", "color": "#ef4444", "desc": "Unified emergency action plan"},
        "IBM Granite":                 {"icon": "🧠", "color": "#a78bfa", "desc": "LLM reasoning & situation summary"},
        "Closed-Loop Learning":        {"icon": "🔄", "color": "#94a3b8", "desc": "Prediction-outcome feedback"},
        "Orchestrator":                {"icon": "⚙️", "color": "#475569", "desc": "Pipeline coordinator"},
        "LiveDataManager":             {"icon": "🌐", "color": "#14b8a6", "desc": "Live weather ingestion"},
    }

    # De-duplicate — keep only the last entry per agent
    seen: dict = {}
    for entry in pipeline_log:
        seen[entry.get("agent", "")] = entry

    ordered_agents = [
        "LiveDataManager", "Flood Risk Agent", "Drainage Agent",
        "Citizen Report Agent", "Response Coordination Agent",
        "IBM Granite", "Chief Response Agent", "Closed-Loop Learning",
    ]

    for ag_name in ordered_agents:
        entry = seen.get(ag_name)
        if not entry:
            continue
        meta = AGENT_META.get(ag_name, {"icon": "🤖", "color": "#94a3b8", "desc": ""})
        st_val = entry.get("status", "IDLE")
        detail = entry.get("details", "")
        ts = entry.get("timestamp", "")[:19].replace("T", " ")

        # Status color
        st_color = {
            "COMPLETE": "#22c55e", "RUNNING": "#3b82f6",
            "FALLBACK": "#eab308", "IDLE": "#475569",
            "ERROR": "#ef4444",
        }.get(st_val, "#94a3b8")

        # Special granite badge
        extra_badge = ""
        if ag_name == "IBM Granite":
            if granite_available:
                extra_badge = '<span style="background:#14532d;color:#bbf7d0;font-size:0.6rem;padding:1px 5px;border-radius:3px;font-weight:700;margin-left:4px">✅ LIVE</span>'
            elif granite_rate_limited:
                extra_badge = '<span style="background:#3a2e00;color:#fde68a;font-size:0.6rem;padding:1px 5px;border-radius:3px;font-weight:700;margin-left:4px">⏳ RATE LIMITED</span>'
            else:
                extra_badge = '<span style="background:#2a1a00;color:#fdba74;font-size:0.6rem;padding:1px 5px;border-radius:3px;font-weight:700;margin-left:4px">⚙ FALLBACK</span>'

        trace_class = "complete" if st_val == "COMPLETE" else "fallback" if st_val == "FALLBACK" else "error" if st_val == "ERROR" else ""
        if ag_name == "IBM Granite":
            trace_class += " granite"

        st.markdown(f"""
        <div class="agent-trace-step {trace_class}">
          <div style="display:flex;align-items:center;gap:0.5rem;margin-bottom:0.3rem">
            <span style="font-size:1.1rem">{meta['icon']}</span>
            <span style="font-size:0.85rem;font-weight:700;color:#e2e8f0">{ag_name}</span>
            {extra_badge}
            <span style="margin-left:auto;font-size:0.65rem;color:{st_color};font-weight:700;letter-spacing:0.04em">● {st_val}</span>
            <span style="font-size:0.62rem;color:#475569;margin-left:0.5rem">{ts}</span>
          </div>
          <div style="font-size:0.72rem;color:#64748b">{meta['desc']}</div>
          {f'<div style="font-size:0.78rem;color:#94a3b8;margin-top:0.3rem;padding-top:0.3rem;border-top:1px solid #1e2440">{detail}</div>' if detail else ''}
        </div>
        """, unsafe_allow_html=True)


def render_granite_panel(
    situation_report: str,
    granite_available: bool,
    granite_rate_limited: bool,
    scenario_label: str = "",
    input_summary: str = "",
):
    """Render a prominent IBM Granite AI panel with clear labelling."""
    if granite_available:
        badge = '<span style="background:#14532d;color:#bbf7d0;font-size:0.75rem;padding:2px 8px;border-radius:4px;font-weight:700">✅ IBM GRANITE LIVE</span>'
        note  = "Situation report and recommendations generated by IBM Granite 3-8b-instruct via WatsonX REST API."
        border_color = "#22c55e"
        bg = "linear-gradient(135deg,#060e10,#071210)"
    elif granite_rate_limited:
        badge = '<span style="background:#3a2e00;color:#fde68a;font-size:0.75rem;padding:2px 8px;border-radius:4px;font-weight:700">⏳ GRANITE RATE LIMITED</span>'
        note  = "WatsonX API is rate-limited (HTTP 429). Output generated by rule-based fallback — NOT Granite."
        border_color = "#eab308"
        bg = "linear-gradient(135deg,#0e0c00,#100d00)"
    else:
        badge = '<span style="background:#1a1a00;color:#94a3b8;font-size:0.75rem;padding:2px 8px;border-radius:4px;font-weight:700;border:1px solid #475569">⚙ GRANITE FALLBACK MODE</span>'
        note  = "IBM Granite is not connected (WATSONX_API_KEY not configured). Output is rule-based — clearly labelled as FALLBACK, NOT Granite."
        border_color = "#475569"
        bg = "linear-gradient(135deg,#0a0a0a,#0d0d0d)"

    st.markdown(f"""
    <div style="background:{bg};border:1px solid {border_color};
                border-radius:10px;padding:1rem 1.2rem;margin-bottom:1rem">
      <div style="display:flex;align-items:center;gap:0.75rem;margin-bottom:0.6rem;flex-wrap:wrap">
        <span style="font-size:1.4rem">🧠</span>
        <span style="font-size:1rem;font-weight:700;color:#e2e8f0">IBM GRANITE AI</span>
        {badge}
      </div>
      <div style="font-size:0.75rem;color:#64748b;margin-bottom:0.7rem">
        {note}
        {f' · Scenario: <strong style="color:#94a3b8">{scenario_label}</strong>' if scenario_label else ''}
      </div>
      {f'<div style="font-size:0.75rem;color:#475569;margin-bottom:0.5rem;padding:0.4rem 0.6rem;background:#080c14;border-radius:4px;border:1px solid #1e2440"><strong style="color:#64748b">INPUT CONTEXT:</strong> {input_summary}</div>' if input_summary else ''}
      <div class="granite-output">{situation_report or "No situation report available. Run a scenario to generate Granite analysis."}</div>
    </div>
    """, unsafe_allow_html=True)


def risk_level_indicator(level: str) -> str:
    """Return a rich risk level indicator HTML."""
    config = {
        "CRITICAL": ("🔴", "#ef4444", "rgba(239,68,68,0.12)"),
        "HIGH":     ("🟠", "#f97316", "rgba(249,115,22,0.10)"),
        "MEDIUM":   ("🟡", "#eab308", "rgba(234,179,8,0.08)"),
        "LOW":      ("🟢", "#22c55e", "rgba(34,197,94,0.08)"),
    }
    emoji, color, bg = config.get(level, ("⚪", "#94a3b8", "rgba(148,163,184,0.08)"))
    return (
        f'<span style="background:{bg};color:{color};'
        f'padding:3px 10px;border-radius:6px;font-size:0.82rem;'
        f'font-weight:700;border:1px solid {color}40;letter-spacing:0.04em">'
        f'{emoji} {level}</span>'
    )
