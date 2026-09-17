"""
FloodGuard AI — Page 1: Citizen Portal
Multilingual flood report submission and local status viewing.
"""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import streamlit as st
import pandas as pd
from datetime import datetime
from frontend.ui_utils import apply_global_css, header, metric_card, ai_disclaimer, card, risk_badge, demo_badge, live_badge
from agents.citizen_report_agent import get_citizen_agent, detect_language, ROUTING_MAP
from agents.orchestrator import get_orchestrator, SCENARIOS
from frontend.map_component import build_flood_map
from streamlit_folium import st_folium
from services.report_store import add_report, get_user_reports

st.set_page_config(page_title="Citizen Portal — FloodGuard AI", page_icon="📱", layout="wide")
apply_global_css()

# ──────────────────────────────────────────────
# Init orchestrator
# ──────────────────────────────────────────────
@st.cache_resource
def get_orch():
    orch = get_orchestrator()
    if not orch.current_state:
        orch.run_pipeline("NORMAL")
    return orch

orch = get_orch()

# Guard against double-submission within the same Streamlit session
if "last_submitted_fingerprint" not in st.session_state:
    st.session_state.last_submitted_fingerprint = None

# ──────────────────────────────────────────────
# Sidebar — language & city
# ──────────────────────────────────────────────
with st.sidebar:
    st.markdown("### 📱 Citizen Portal")
    st.markdown("---")
    lang_choice = st.selectbox("Language / भाषा / ભાષા", ["English", "हिन्दी", "ગુજરાતી"])
    city_choice = st.selectbox("City / शहर / શહેર", ["Ahmedabad", "Surat"])
    st.markdown("---")
    st.markdown("""
    <div style="font-size:0.75rem;color:#94a3b8">
    <strong>About this portal:</strong><br>
    Submit real flood reports. Reports are stored as USER SUBMITTED data.
    </div>
    """, unsafe_allow_html=True)

# ──────────────────────────────────────────────
# Header
# ──────────────────────────────────────────────
LABELS = {
    "English": {
        "title": "Citizen Flood Portal",
        "subtitle": "Report flooding • Track your complaint • Get safety alerts",
        "report_section": "📝 Submit a Flood Report",
        "text_label": "Describe the flood situation in your area:",
        "text_placeholder": "e.g. Water logging on main road near bus stand. Cars are stuck.",
        "area_label": "Your Area/Locality:",
        "submit": "Submit Report",
        "status_section": "📋 My Reports",
        "alerts_section": "🔔 Active Alerts",
        "local_risk": "🗺️ Local Flood Risk",
    },
    "हिन्दी": {
        "title": "नागरिक बाढ़ पोर्टल",
        "subtitle": "बाढ़ की रिपोर्ट करें • शिकायत ट्रैक करें • सुरक्षा अलर्ट पाएं",
        "report_section": "📝 बाढ़ रिपोर्ट दर्ज करें",
        "text_label": "अपने क्षेत्र की बाढ़ स्थिति का वर्णन करें:",
        "text_placeholder": "उदा. बस स्टैंड के पास मुख्य सड़क पर पानी भरा है।",
        "area_label": "आपका क्षेत्र/इलाका:",
        "submit": "रिपोर्ट जमा करें",
        "status_section": "📋 मेरी रिपोर्ट",
        "alerts_section": "🔔 सक्रिय अलर्ट",
        "local_risk": "🗺️ स्थानीय बाढ़ जोखिम",
    },
    "ગુજરાતી": {
        "title": "નાગરિક પૂર પોર્ટલ",
        "subtitle": "પૂરની જાણ કરો • ફરિયાદ ટ્રૅક કરો • સુરક્ષા સૂચનાઓ મેળવો",
        "report_section": "📝 પૂર અહેવાલ સબમિટ કરો",
        "text_label": "તમારા વિસ્તારની પૂર સ્થિતિ વર્ણવો:",
        "text_placeholder": "દા.ત. બસ સ્ટેન્ડ પાસે મુખ્ય રસ્તા પર પાણી ભરાઈ ગયું છે.",
        "area_label": "તમારો વિસ્તાર/મોહલ્લો:",
        "submit": "અહેવાલ સબમિટ કરો",
        "status_section": "📋 મારા અહેવાલ",
        "alerts_section": "🔔 સક્રિય ચેતવણીઓ",
        "local_risk": "🗺️ સ્થાનિક પૂર જોખમ",
    },
}

lbl = LABELS[lang_choice]
header(lbl["title"], lbl["subtitle"], "📱")

# Data status strip — truthful hybrid labels
_cp_is_live = orch.current_state.get("live_weather_status", {}).get("is_live", False) if orch.current_state else False
_cp_wx_label = '<strong style="color:#22c55e">LIVE</strong>' if _cp_is_live else '<strong style="color:#eab308">DEMO</strong>'
st.markdown(f"""
<div style="margin-bottom:1rem;display:flex;flex-wrap:wrap;gap:6px;align-items:center;font-size:0.72rem">
    <span style="background:#0f4c2a;color:#6ee7b7;padding:2px 8px;border-radius:4px;font-weight:700">HYBRID DATA</span>
    <span style="color:#64748b">🌧️ Weather: {_cp_wx_label}</span>
    <span style="color:#475569">·</span>
    <span style="color:#64748b">🌊 Flood Risk: <strong style="color:#3b82f6">MODEL</strong></span>
    <span style="color:#475569">·</span>
    <span style="color:#64748b">📱 Citizen Reports: <strong style="color:#f97316">USER SUBMITTED</strong></span>
    <span style="color:#475569">·</span>
    <span style="color:#64748b">🔧 Infrastructure: <strong style="color:#eab308">DEMO</strong></span>
</div>
""", unsafe_allow_html=True)

# ──────────────────────────────────────────────
# Active alerts strip
# ──────────────────────────────────────────────
alerts = orch.current_state.get("alerts", [])
citizen_alerts = [a for a in alerts if a.get("alert_type") == "citizen" and a.get("city") == city_choice]

if citizen_alerts:
    st.markdown(f"### {lbl['alerts_section']}")
    for alert in citizen_alerts[:3]:
        level = alert.get("alert_level", "INFO")
        cls = {"CRITICAL": "alert-critical", "HIGH": "alert-high", "WARNING": "alert-warning"}.get(level, "alert-info")
        st.markdown(f"""
        <div class="{cls}">
            <div style="font-weight:700;color:#e2e8f0">{alert.get('title')}</div>
            <div style="font-size:0.85rem;color:#cbd5e1;margin-top:0.2rem">{alert.get('message')}</div>
            <div style="font-size:0.7rem;color:#64748b;margin-top:0.3rem">MODEL GENERATED — Not a real emergency notification</div>
        </div>
        """, unsafe_allow_html=True)

# ──────────────────────────────────────────────
# Main columns
# ──────────────────────────────────────────────
col_form, col_map = st.columns([1, 1.4])

with col_form:
    st.markdown(f"### {lbl['report_section']}")

    # Report form
    with st.form("citizen_report_form", clear_on_submit=True):
        report_text = st.text_area(
            lbl["text_label"],
            placeholder=lbl["text_placeholder"],
            height=120,
        )

        # Area dropdown based on city
        from data.seed_generator import AHMEDABAD_AREAS, SURAT_AREAS
        area_list = [a["name"] for a in (AHMEDABAD_AREAS if city_choice == "Ahmedabad" else SURAT_AREAS)]
        area = st.selectbox(lbl["area_label"], area_list)

        category_hint = st.selectbox(
            "Issue Type / प्रकार / પ્રકાર",
            ["Waterlogging", "Drain Overflow", "Road Blockage",
             "Traffic Disruption", "Property Flooding", "Emergency Situation"],
        )

        image_upload = st.file_uploader(
            "Upload Photo (Optional / वैकल्पिक / વૈકલ્પિક)",
            type=["jpg", "jpeg", "png"],
            accept_multiple_files=False,
        )

        submitted = st.form_submit_button(lbl["submit"], use_container_width=True, type="primary")

    # ── Handle submission ────────────────────────────────────────────────────
    if submitted:
        if not report_text.strip():
            st.error("Please enter a description of the flood situation.")
        else:
            import hashlib as _hashlib
            # Session-level duplicate guard: same text+area+city within this session
            _submit_fp = _hashlib.sha256(
                f"{report_text.strip()}|{area}|{city_choice}".lower().encode()
            ).hexdigest()[:16]

            if st.session_state.last_submitted_fingerprint == _submit_fp:
                st.warning("This report was already submitted in this session.")
            else:
                with st.spinner("Processing your report..."):
                    agent = get_citizen_agent()
                    # Pass existing reports for fuzzy duplicate check
                    existing_user = get_user_reports()
                    existing_demo = orch.current_state.get("raw_reports", []) if orch.current_state else []
                    existing = existing_user + existing_demo
                    report = agent.process_report(
                        text=report_text,
                        area=area,
                        city=city_choice,
                        existing_reports=existing,
                        category_hint=category_hint,
                    )
                    # ── Persist to shared file store ──────────────────────────
                    saved, dedup_id = add_report(report)
                    if not saved:
                        report["is_duplicate"] = True
                        report["duplicate_of"] = dedup_id
                    else:
                        st.session_state.last_submitted_fingerprint = _submit_fp

                # ── Confirmation display ──────────────────────────────────────
                level_colors = {"CRITICAL": "#ef4444", "HIGH": "#f97316", "MEDIUM": "#eab308", "LOW": "#22c55e"}
                sev   = report.get("severity", "MEDIUM")
                color = level_colors.get(sev, "#94a3b8")
                cat   = report.get("category", "waterlogging")
                cat_display = cat.replace("_", " ").title()
                priority_map = {"CRITICAL": 1, "HIGH": 2, "MEDIUM": 3, "LOW": 4}
                priority = priority_map.get(sev, 3)
                is_dup = report.get("is_duplicate", False)

                if is_dup:
                    st.warning(
                        f"Possible duplicate — a similar report for {area} already exists. "
                        f"Reference ID: {report.get('duplicate_of', 'N/A')}"
                    )
                else:
                    st.success(f"Report submitted successfully! ID: {report['report_id']}")

                st.markdown(f"""
                <div style="background:rgba(34,197,94,0.1);border:1px solid #22c55e;
                            border-radius:8px;padding:1rem;margin-top:0.5rem">
                    <div style="display:grid;grid-template-columns:1fr 1fr;gap:0.3rem;
                                font-size:0.83rem;color:#e2e8f0;margin-bottom:0.5rem">
                        <div><b>Report ID:</b> {report['report_id']}</div>
                        <div><b>Category:</b> {cat_display}</div>
                        <div><b>Location:</b> {area}, {city_choice}</div>
                        <div><b>Severity:</b> <span style="color:{color};font-weight:700">{sev}</span></div>
                        <div><b>Priority:</b> #{priority} in queue</div>
                        <div><b>Routing to:</b> {report['assigned_team']}</div>
                        <div><b>Status:</b> <span style="color:#22c55e">OPEN</span></div>
                        <div><b>Source:</b> <span style="color:#fdba74;font-weight:700">USER SUBMITTED</span></div>
                    </div>
                    {"<div style='font-size:0.75rem;color:#ef4444;margin-top:0.3rem;padding:0.3rem 0.5rem;background:rgba(239,68,68,0.1);border-radius:4px'>Requires immediate action — emergency team alerted.</div>" if sev == "CRITICAL" else ""}
                    <div style="font-size:0.7rem;color:#64748b;margin-top:0.4rem">
                        USER SUBMITTED — Processed by FloodGuard AI. Not a real municipal emergency submission.
                    </div>
                </div>
                """, unsafe_allow_html=True)

                if image_upload:
                    st.image(image_upload, caption="Uploaded photo preview (not stored to disk)", width=200)

    # ── Quick stats ─────────────────────────────────────────────────────────
    st.markdown("---")
    # Merge demo seed reports with user-submitted for accurate stats
    demo_reports = orch.current_state.get("raw_reports", []) if orch.current_state else []
    user_reports = get_user_reports()
    all_reports  = user_reports + demo_reports
    city_reports = [r for r in all_reports if r.get("city") == city_choice]
    open_r       = sum(1 for r in city_reports if r.get("status") == "OPEN")
    critical_r   = sum(1 for r in city_reports if r.get("severity") == "CRITICAL")

    st.markdown(f"""
    <div style="margin-top:0.5rem">
        <div style="font-size:0.85rem;font-weight:700;color:#e2e8f0;margin-bottom:0.5rem">
            📊 {city_choice} Report Status
            <span style="background:#3a1a00;color:#fdba74;font-size:0.65rem;
                         padding:1px 5px;border-radius:3px;font-weight:700">
                USER SUBMITTED + DEMO SEED
            </span>
        </div>
    </div>
    """, unsafe_allow_html=True)

    mc1, mc2, mc3 = st.columns(3)
    with mc1: metric_card("Total Reports", str(len(city_reports)), color="#3b82f6", icon="📋")
    with mc2: metric_card("Open", str(open_r), color="#f97316", icon="🔴")
    with mc3: metric_card("Critical", str(critical_r), color="#ef4444", icon="🚨")

    # ── Recent reports table ─────────────────────────────────────────────────
    st.markdown("---")
    st.markdown(f"### {lbl['status_section']}")
    if city_reports:
        df = pd.DataFrame(city_reports[:20])
        # Ensure source column: USER SUBMITTED or DEMO/SYNTHETIC
        if "source" not in df.columns:
            df["source"] = "DEMO/SYNTHETIC"
        df["source"] = df["source"].fillna("DEMO/SYNTHETIC")
        # Use submitted_at if available, fall back to created_at
        ts_col = "submitted_at" if "submitted_at" in df.columns else "created_at"
        df_display = df[["report_id", "area", "category", "severity", "status", "source", ts_col]].copy()
        df_display.columns = ["ID", "Area", "Category", "Severity", "Status", "Source", "Submitted"]
        df_display["Category"] = df_display["Category"].str.replace("_", " ").str.title()
        df_display["Submitted"] = pd.to_datetime(df_display["Submitted"], errors="coerce").dt.strftime("%b %d %H:%M")
        st.dataframe(df_display, use_container_width=True, hide_index=True, height=220)

with col_map:
    st.markdown(f"### {lbl['local_risk']}")

    # Local flood risk map — merge user-submitted + demo reports
    _cp_state        = orch.current_state or {}
    city_preds       = [p for p in _cp_state.get("risk_predictions", []) if p.get("city") == city_choice]
    city_drains      = [d for d in _cp_state.get("raw_drains", []) if d.get("city") == city_choice]
    demo_map_reports = _cp_state.get("raw_reports", [])
    city_reports_map = [r for r in (get_user_reports() + demo_map_reports) if r.get("city") == city_choice]

    # Pass live weather map points so the legend shows LIVE when data is available,
    # consistent with Command Center and War Room maps.
    _cp_wx_points = _cp_state.get("live_weather_map_points", []) or None
    _cp_wx_live   = bool(_cp_wx_points) and _cp_is_live

    m = build_flood_map(
        risk_predictions=city_preds,
        drain_data=city_drains[:30],
        report_data=city_reports_map[:50],
        team_data=[],
        city=city_choice,
        zoom=12,
        weather_data=_cp_wx_points,
        is_live=_cp_wx_live,
    )
    st_folium(m, width="100%", height=450, key="citizen_map")

    # Risk summary for city
    critical_zones = sum(1 for p in city_preds if p["risk_level"] == "CRITICAL")
    high_zones = sum(1 for p in city_preds if p["risk_level"] == "HIGH")

    if critical_zones > 0:
        st.markdown(f"""
        <div class="alert-critical">
            <strong>{critical_zones} CRITICAL risk zone(s)</strong> in {city_choice}.
            Avoid low-lying areas and flooded roads.
        </div>
        """, unsafe_allow_html=True)
    elif high_zones > 0:
        st.markdown(f"""
        <div class="alert-high">
            <strong>{high_zones} HIGH risk zone(s)</strong> in {city_choice}.
            Exercise caution and stay updated.
        </div>
        """, unsafe_allow_html=True)
    else:
        st.markdown(f"""
        <div class="alert-info">
            No critical flood zones currently in {city_choice}. Continue monitoring.
        </div>
        """, unsafe_allow_html=True)

    st.markdown(
        '<div style="font-size:0.7rem;color:#64748b">FLOOD RISK: ML MODEL PREDICTION — '
        'Generated from available application inputs. Not an official municipal flood warning.</div>',
        unsafe_allow_html=True,
    )

# ──────────────────────────────────────────────
# Safety tips
# ──────────────────────────────────────────────
st.markdown("---")
st.markdown("""
<div style="background:#1a1d27;border:1px solid #2d3148;border-radius:8px;padding:1rem">
    <div style="font-weight:700;color:#e2e8f0;margin-bottom:0.5rem">Flood Safety Tips</div>
    <div style="display:grid;grid-template-columns:repeat(3,1fr);gap:0.5rem;font-size:0.8rem;color:#94a3b8">
        <div>• Avoid walking/driving through flooded areas</div>
        <div>• Move valuables and electronics to higher floors</div>
        <div>• Keep emergency kit ready (water, medicines, documents)</div>
        <div>• Disconnect electrical appliances if water enters</div>
        <div>• Contact emergency services: 1916 (AMC) / 1800 (SMC)</div>
        <div>• Follow official municipal announcements</div>
    </div>
    <div style="font-size:0.7rem;color:#475569;margin-top:0.5rem">
        Contact numbers are for reference only — this is a demo application.
    </div>
</div>
""", unsafe_allow_html=True)
