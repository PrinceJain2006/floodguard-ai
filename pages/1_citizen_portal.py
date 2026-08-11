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
from frontend.ui_utils import apply_global_css, header, metric_card, ai_disclaimer, card, risk_badge, demo_badge
from agents.citizen_report_agent import get_citizen_agent, detect_language, ROUTING_MAP
from agents.orchestrator import get_orchestrator, SCENARIOS
from frontend.map_component import build_flood_map
from streamlit_folium import st_folium

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
    <strong>Demo Users:</strong><br>
    Any user can submit reports in demo mode.
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

# Demo badge
st.markdown(f'<div style="margin-bottom:1rem">{demo_badge()}&nbsp;<span style="color:#64748b;font-size:0.8rem">All data is synthetic demo data — not real government data</span></div>', unsafe_allow_html=True)

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
            <div style="font-size:0.7rem;color:#64748b;margin-top:0.3rem">⚙ SIMULATED ALERT — Not a real emergency notification</div>
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

    if submitted:
        if not report_text.strip():
            st.error("Please enter a description of the flood situation.")
        else:
            with st.spinner("AI processing your report... 🤖"):
                agent = get_citizen_agent()
                existing = orch.current_state.get("raw_reports", [])
                report = agent.process_report(
                    text=report_text,
                    area=area,
                    city=city_choice,
                    existing_reports=existing,
                )

            detected_lang = detect_language(report_text)
            level_colors = {"CRITICAL": "#ef4444", "HIGH": "#f97316", "MEDIUM": "#eab308", "LOW": "#22c55e"}
            sev = report.get("severity", "MEDIUM")
            color = level_colors.get(sev, "#94a3b8")

            # Multilingual confirmation message
            confirm_msgs = {
                "english":  "✅ Report Submitted Successfully",
                "hindi":    "✅ रिपोर्ट सफलतापूर्वक जमा की गई",
                "gujarati": "✅ અહેવાल સફળતાપૂर्वक સbmit થयો",
            }
            conf_msg = confirm_msgs.get(detected_lang, confirm_msgs["english"])

            # Severity label multilingual
            sev_labels = {
                "CRITICAL": {"english": "CRITICAL", "hindi": "अत्यंत गंभीर", "gujarati": "અત્યંત ગhaber"},
                "HIGH":     {"english": "HIGH",     "hindi": "उच्च",         "gujarati": "ઉच्च"},
                "MEDIUM":   {"english": "MEDIUM",   "hindi": "मध्यम",        "gujarati": "મध્यમ"},
                "LOW":      {"english": "LOW",      "hindi": "कम",           "gujarati": "ઓchun"},
            }
            sev_label = sev_labels.get(sev, {}).get(detected_lang, sev)

            # Category label multilingual
            cat_labels = {
                "waterlogging":        {"hindi": "जलभराव",           "gujarati": "પाणी ભtrat"},
                "drain_overflow":      {"hindi": "नाली उफान",        "gujarati": "ગtrat ઉfan"},
                "road_blockage":       {"hindi": "सड़क अवरोध",       "gujarati": "gast Avrodh"},
                "property_flooding":   {"hindi": "संपत्ति में बाढ़", "gujarati": "ملکiyet purn"},
                "emergency_situation": {"hindi": "आपातकालीन स्थिति", "gujarati": "kटoकalIN sthiti"},
                "traffic_disruption":  {"hindi": "यातायात बाधा",     "gujarati": "Traffic bAdha"},
            }
            cat = report.get("category", "waterlogging")
            cat_display = cat.replace("_", " ").title()

            # Priority number
            priority_map = {"CRITICAL": 1, "HIGH": 2, "MEDIUM": 3, "LOW": 4}
            priority = priority_map.get(sev, 3)

            st.markdown(f"""
            <div style="background:rgba(34,197,94,0.1);border:1px solid #22c55e;
                        border-radius:8px;padding:1rem;margin-top:0.5rem">
                <div style="font-weight:700;color:#22c55e;margin-bottom:0.5rem;font-size:1rem">
                    {conf_msg}
                </div>
                <div style="display:grid;grid-template-columns:1fr 1fr;gap:0.3rem;font-size:0.83rem;color:#e2e8f0;margin-bottom:0.5rem">
                    <div><b>Report ID:</b> {report['report_id']}</div>
                    <div><b>Language:</b> {detected_lang.title()} / {report['language'].title()}</div>
                    <div><b>Category:</b> {cat_display}</div>
                    <div><b>Location:</b> {area}, {city_choice}</div>
                    <div><b>Severity:</b> <span style="color:{color};font-weight:700">{sev} ({sev_label})</span></div>
                    <div><b>Priority:</b> #{priority} in queue</div>
                    <div><b>Routing to:</b> {report['assigned_team']}</div>
                    <div><b>Status:</b> <span style="color:#22c55e">OPEN</span></div>
                </div>
                {f'<div style="font-size:0.75rem;color:#f97316;margin-top:0.3rem;padding:0.3rem 0.5rem;background:rgba(249,115,22,0.1);border-radius:4px">⚠️ Possible duplicate — similar report already filed for this area.</div>' if report.get('is_duplicate') else ''}
                {f'<div style="font-size:0.75rem;color:#ef4444;margin-top:0.3rem;padding:0.3rem 0.5rem;background:rgba(239,68,68,0.1);border-radius:4px">🚨 Requires immediate action — emergency team alerted.</div>' if sev == "CRITICAL" else ''}
                <div style="font-size:0.7rem;color:#64748b;margin-top:0.4rem">⚙ DEMO — Not a real municipal report submission</div>
            </div>
            """, unsafe_allow_html=True)

            if image_upload:
                st.image(image_upload, caption="Uploaded photo (Demo mode — not stored)", width=200)

    # ── Quick stats ─────────────────────────────
    st.markdown("---")
    city_reports = [r for r in orch.current_state.get("raw_reports", []) if r.get("city") == city_choice]
    open_r = sum(1 for r in city_reports if r.get("status") == "OPEN")
    critical_r = sum(1 for r in city_reports if r.get("severity") == "CRITICAL")

    st.markdown(f"""
    <div style="margin-top:0.5rem">
        <div style="font-size:0.85rem;font-weight:700;color:#e2e8f0;margin-bottom:0.5rem">
            📊 {city_choice} Report Status {demo_badge()}
        </div>
    </div>
    """, unsafe_allow_html=True)

    mc1, mc2, mc3 = st.columns(3)
    with mc1: metric_card("Total Reports", str(len(city_reports)), color="#3b82f6", icon="📋")
    with mc2: metric_card("Open", str(open_r), color="#f97316", icon="🔴")
    with mc3: metric_card("Critical", str(critical_r), color="#ef4444", icon="🚨")

    # ── Recent reports table ─────────────────────
    st.markdown("---")
    st.markdown(f"### {lbl['status_section']}")
    if city_reports:
        df = pd.DataFrame(city_reports[:20])
        df_display = df[["report_id", "area", "category", "severity", "status", "created_at"]].copy()
        df_display.columns = ["ID", "Area", "Category", "Severity", "Status", "Submitted"]
        df_display["Category"] = df_display["Category"].str.replace("_", " ").str.title()
        df_display["Submitted"] = pd.to_datetime(df_display["Submitted"]).dt.strftime("%b %d %H:%M")
        st.dataframe(df_display, use_container_width=True, hide_index=True, height=220)

with col_map:
    st.markdown(f"### {lbl['local_risk']}")

    # Local flood risk map
    city_preds = [p for p in orch.current_state.get("risk_predictions", []) if p.get("city") == city_choice]
    city_drains = [d for d in orch.current_state.get("raw_drains", []) if d.get("city") == city_choice]
    city_reports_map = [r for r in orch.current_state.get("raw_reports", []) if r.get("city") == city_choice]

    m = build_flood_map(
        risk_predictions=city_preds,
        drain_data=city_drains[:30],
        report_data=city_reports_map[:50],
        team_data=[],
        city=city_choice,
        zoom=12,
    )
    st_folium(m, width=700, height=450, key="citizen_map")

    # Risk summary for city
    critical_zones = sum(1 for p in city_preds if p["risk_level"] == "CRITICAL")
    high_zones = sum(1 for p in city_preds if p["risk_level"] == "HIGH")

    if critical_zones > 0:
        st.markdown(f"""
        <div class="alert-critical">
            🚨 <strong>{critical_zones} CRITICAL risk zone(s)</strong> in {city_choice}.
            Avoid low-lying areas and flooded roads.
        </div>
        """, unsafe_allow_html=True)
    elif high_zones > 0:
        st.markdown(f"""
        <div class="alert-high">
            ⚠️ <strong>{high_zones} HIGH risk zone(s)</strong> in {city_choice}.
            Exercise caution and stay updated.
        </div>
        """, unsafe_allow_html=True)
    else:
        st.markdown(f"""
        <div class="alert-info">
            ✅ No critical flood zones currently in {city_choice}. Continue monitoring.
        </div>
        """, unsafe_allow_html=True)
    
    st.markdown(f'<div style="font-size:0.7rem;color:#64748b">⚙ DEMO/SIMULATED DATA — Not real flood risk data</div>', unsafe_allow_html=True)

# ──────────────────────────────────────────────
# Safety tips
# ──────────────────────────────────────────────
st.markdown("---")
st.markdown("""
<div style="background:#1a1d27;border:1px solid #2d3148;border-radius:8px;padding:1rem">
    <div style="font-weight:700;color:#e2e8f0;margin-bottom:0.5rem">🛡️ Flood Safety Tips</div>
    <div style="display:grid;grid-template-columns:repeat(3,1fr);gap:0.5rem;font-size:0.8rem;color:#94a3b8">
        <div>• Avoid walking/driving through flooded areas</div>
        <div>• Move valuables and electronics to higher floors</div>
        <div>• Keep emergency kit ready (water, medicines, documents)</div>
        <div>• Disconnect electrical appliances if water enters</div>
        <div>• Contact emergency services: 1916 (AMC) / 1800 (SMC)</div>
        <div>• Follow official municipal announcements</div>
    </div>
    <div style="font-size:0.7rem;color:#475569;margin-top:0.5rem">Contact numbers are for reference only — this is a demo application.</div>
</div>
""", unsafe_allow_html=True)
