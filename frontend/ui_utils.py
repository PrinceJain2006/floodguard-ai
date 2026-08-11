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
    "bg":       "#0f1117",
    "surface":  "#1a1d27",
    "border":   "#2d3148",
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
    /* Global dark theme */
    .stApp { background-color: #0f1117; color: #e2e8f0; }
    .main .block-container { padding-top: 1rem; padding-bottom: 2rem; max-width: 1400px; }

    /* Cards */
    .fg-card {
        background: #1a1d27;
        border: 1px solid #2d3148;
        border-radius: 10px;
        padding: 1rem 1.2rem;
        margin-bottom: 0.75rem;
    }
    .fg-card-danger {
        background: #1a0f0f;
        border: 1px solid #ef4444;
        border-radius: 10px;
        padding: 1rem 1.2rem;
        margin-bottom: 0.75rem;
    }
    .fg-card-warn {
        background: #1a1500;
        border: 1px solid #eab308;
        border-radius: 10px;
        padding: 1rem 1.2rem;
        margin-bottom: 0.75rem;
    }
    .fg-card-success {
        background: #0f1a0f;
        border: 1px solid #22c55e;
        border-radius: 10px;
        padding: 1rem 1.2rem;
        margin-bottom: 0.75rem;
    }
    .fg-card-blue {
        background: #0f1420;
        border: 1px solid #3b82f6;
        border-radius: 10px;
        padding: 1rem 1.2rem;
        margin-bottom: 0.75rem;
    }

    /* Metric tiles */
    .fg-metric {
        background: #1a1d27;
        border: 1px solid #2d3148;
        border-radius: 10px;
        padding: 1.2rem;
        text-align: center;
    }
    .fg-metric-value { font-size: 2rem; font-weight: 700; line-height: 1; }
    .fg-metric-label { font-size: 0.75rem; color: #94a3b8; margin-top: 0.3rem; text-transform: uppercase; letter-spacing: 0.05em; }

    /* Risk badges */
    .badge-critical { background: #ef4444; color: white; padding: 2px 8px; border-radius: 12px; font-size: 0.75rem; font-weight: 600; }
    .badge-high     { background: #f97316; color: white; padding: 2px 8px; border-radius: 12px; font-size: 0.75rem; font-weight: 600; }
    .badge-medium   { background: #eab308; color: #1a1d27; padding: 2px 8px; border-radius: 12px; font-size: 0.75rem; font-weight: 600; }
    .badge-low      { background: #22c55e; color: white; padding: 2px 8px; border-radius: 12px; font-size: 0.75rem; font-weight: 600; }

    /* Agent activity */
    .agent-row {
        display: flex; align-items: center; gap: 0.75rem;
        padding: 0.5rem 0; border-bottom: 1px solid #2d3148;
    }
    .agent-name { font-weight: 600; min-width: 180px; font-size: 0.875rem; }
    .agent-status { font-size: 0.8rem; color: #94a3b8; }

    /* Timeline */
    .timeline-item {
        display: flex; gap: 1rem; padding: 0.5rem 0;
        border-left: 2px solid #2d3148; padding-left: 1rem;
        margin-left: 0.5rem;
    }
    .timeline-time { font-size: 0.75rem; color: #94a3b8; white-space: nowrap; }

    /* Alert banners */
    .alert-critical { background: rgba(239,68,68,0.15); border: 1px solid #ef4444; border-radius: 8px; padding: 0.75rem 1rem; margin-bottom: 0.5rem; }
    .alert-high     { background: rgba(249,115,22,0.15); border: 1px solid #f97316; border-radius: 8px; padding: 0.75rem 1rem; margin-bottom: 0.5rem; }
    .alert-warning  { background: rgba(234,179,8,0.15);  border: 1px solid #eab308; border-radius: 8px; padding: 0.75rem 1rem; margin-bottom: 0.5rem; }
    .alert-info     { background: rgba(59,130,246,0.15); border: 1px solid #3b82f6; border-radius: 8px; padding: 0.75rem 1rem; margin-bottom: 0.5rem; }

    /* Demo label */
    .demo-label {
        background: #7c3aed; color: white; font-size: 0.7rem;
        padding: 2px 8px; border-radius: 4px; font-weight: 700;
        letter-spacing: 0.05em;
    }
    .simulated-label {
        background: #0f4c75; color: #7ec8e3; font-size: 0.7rem;
        padding: 2px 8px; border-radius: 4px; font-weight: 700;
    }

    /* Buttons */
    .stButton > button {
        border-radius: 8px;
        font-weight: 600;
        transition: all 0.2s;
    }

    /* Sidebar */
    [data-testid="stSidebar"] { background: #1a1d27; }
    [data-testid="stSidebar"] .stMarkdown { color: #e2e8f0; }

    /* Tabs */
    .stTabs [data-baseweb="tab"] { color: #94a3b8; }
    .stTabs [data-baseweb="tab"][aria-selected="true"] { color: #e2e8f0; }
    .stTabs [data-baseweb="tab-highlight"] { background-color: #3b82f6; }
    .stTabs [data-baseweb="tab-border"] { background-color: #2d3148; }

    /* Dividers */
    hr { border-color: #2d3148; }

    /* Scrollbar */
    ::-webkit-scrollbar { width: 6px; height: 6px; }
    ::-webkit-scrollbar-track { background: #1a1d27; }
    ::-webkit-scrollbar-thumb { background: #2d3148; border-radius: 3px; }
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
        authorized human verification before implementation. All data is DEMO/SIMULATED.
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
