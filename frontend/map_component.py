"""
FloodGuard AI — Interactive Geospatial Map
Folium-based map with flood risk zones, drains, reports, and teams.
"""
import folium
import pandas as pd
from datetime import datetime

RISK_COLORS = {
    "LOW":      "#22c55e",
    "MEDIUM":   "#eab308",
    "HIGH":     "#f97316",
    "CRITICAL": "#ef4444",
}

DRAIN_COLORS = {
    "CRITICAL": "#ef4444",
    "HIGH":     "#f97316",
    "MEDIUM":   "#eab308",
    "LOW":      "#22c55e",
}

CITY_CENTERS = {
    "Ahmedabad": [23.0225, 72.5714],
    "Surat":     [21.1702, 72.8311],
    "All":       [22.2587, 71.1924],
}


def build_flood_map(
    risk_predictions: list[dict],
    drain_data: list[dict],
    report_data: list[dict],
    team_data: list[dict],
    city: str = "All",
    zoom: int = 10,
) -> folium.Map:
    """
    Build a comprehensive Folium map for the FloodGuard dashboard.
    """
    center = CITY_CENTERS.get(city, CITY_CENTERS["All"])
    if city == "All":
        zoom = 8

    m = folium.Map(
        location=center,
        zoom_start=zoom,
        tiles="CartoDB dark_matter",
        attr="FloodGuard AI — DEMO DATA",
    )

    # ── Layer groups ──────────────────────────
    risk_layer   = folium.FeatureGroup(name="🌊 Flood Risk Zones", show=True)
    drain_layer  = folium.FeatureGroup(name="🔧 Drainage Status", show=True)
    report_layer = folium.FeatureGroup(name="📱 Citizen Reports", show=False)
    team_layer   = folium.FeatureGroup(name="🚒 Response Teams", show=False)

    # ── Risk zones ────────────────────────────
    for pred in risk_predictions:
        lat = pred.get("latitude")
        lon = pred.get("longitude")
        if not lat or not lon:
            continue

        level = pred.get("risk_level", "LOW")
        score = pred.get("risk_score", 0)
        color = RISK_COLORS.get(level, "#94a3b8")
        radius = max(300, score * 25)  # Scale circle by risk score

        # Circle overlay
        folium.Circle(
            location=[lat, lon],
            radius=radius,
            color=color,
            fill=True,
            fill_color=color,
            fill_opacity=0.25,
            weight=2,
            tooltip=f"{pred.get('area')} — {level}",
        ).add_to(risk_layer)

        # Marker
        icon_html = f"""
        <div style="background:{color};width:14px;height:14px;border-radius:50%;
                    border:2px solid white;box-shadow:0 0 6px {color}"></div>
        """
        popup_html = _risk_popup(pred)
        folium.Marker(
            location=[lat, lon],
            popup=folium.Popup(popup_html, max_width=300),
            tooltip=f"{pred.get('area')}, {pred.get('city')} — Risk: {level} ({score:.0f})",
            icon=folium.DivIcon(
                html=icon_html,
                icon_size=(14, 14),
                icon_anchor=(7, 7),
            ),
        ).add_to(risk_layer)

    # ── Drains ────────────────────────────────
    for drain in drain_data:
        lat = drain.get("latitude")
        lon = drain.get("longitude")
        if not lat or not lon:
            continue

        priority = drain.get("maintenance_priority", "LOW")
        color = DRAIN_COLORS.get(priority, "#94a3b8")
        status = drain.get("status", "OPERATIONAL")
        icon_char = "⚠" if status == "BLOCKED" else "●"

        icon_html = f"""
        <div style="background:{color};width:10px;height:10px;border-radius:2px;
                    border:1px solid rgba(255,255,255,0.5);font-size:6px;
                    display:flex;align-items:center;justify-content:center;color:white">
        </div>
        """
        popup_html = _drain_popup(drain)
        folium.Marker(
            location=[lat, lon],
            popup=folium.Popup(popup_html, max_width=260),
            tooltip=f"Drain {drain.get('drain_id')} — {priority} ({status})",
            icon=folium.DivIcon(
                html=icon_html,
                icon_size=(10, 10),
                icon_anchor=(5, 5),
            ),
        ).add_to(drain_layer)

    # ── Citizen reports ───────────────────────
    report_sev_colors = {
        "CRITICAL": "#ef4444", "HIGH": "#f97316",
        "MEDIUM":   "#eab308", "LOW":  "#22c55e",
    }
    for report in report_data[:100]:  # Cap to prevent map overload
        lat = report.get("latitude")
        lon = report.get("longitude")
        if not lat or not lon:
            continue

        sev = report.get("severity", "MEDIUM")
        color = report_sev_colors.get(sev, "#94a3b8")
        icon_html = f"""
        <div style="font-size:14px;line-height:1;filter:drop-shadow(0 0 3px {color})">📍</div>
        """
        popup_html = _report_popup(report)
        folium.Marker(
            location=[lat, lon],
            popup=folium.Popup(popup_html, max_width=260),
            tooltip=f"Report: {report.get('category','?').replace('_',' ').title()} — {sev}",
            icon=folium.DivIcon(
                html=icon_html,
                icon_size=(18, 18),
                icon_anchor=(9, 16),
            ),
        ).add_to(report_layer)

    # ── Response teams ────────────────────────
    team_icons = {
        "pump_team":      "💧",
        "emergency":      "🚨",
        "drainage":       "🔧",
        "traffic":        "🚦",
        "rapid_response": "⚡",
    }
    for team in team_data:
        lat = team.get("latitude")
        lon = team.get("longitude")
        if not lat or not lon:
            continue

        emoji = team_icons.get(team.get("team_type", ""), "🚒")
        status = team.get("status", "AVAILABLE")
        color = "#22c55e" if status == "AVAILABLE" else "#f97316" if status == "DEPLOYED" else "#94a3b8"
        icon_html = f"""
        <div style="font-size:16px;line-height:1;opacity:{'1.0' if status == 'DEPLOYED' else '0.7'}">{emoji}</div>
        """
        folium.Marker(
            location=[lat, lon],
            tooltip=f"{team.get('name')} — {status}",
            icon=folium.DivIcon(html=icon_html, icon_size=(20, 20), icon_anchor=(10, 10)),
        ).add_to(team_layer)

    # ── Legend ────────────────────────────────
    legend_html = """
    <div style="position:fixed;bottom:30px;right:10px;z-index:999;
                background:rgba(15,17,23,0.9);border:1px solid #2d3148;
                border-radius:8px;padding:10px 14px;font-family:sans-serif">
        <div style="color:#e2e8f0;font-weight:700;font-size:12px;margin-bottom:6px">FLOOD RISK LEVEL</div>
        <div style="display:flex;align-items:center;gap:6px;margin-bottom:4px">
            <div style="width:12px;height:12px;border-radius:50%;background:#ef4444"></div>
            <span style="color:#e2e8f0;font-size:11px">CRITICAL</span>
        </div>
        <div style="display:flex;align-items:center;gap:6px;margin-bottom:4px">
            <div style="width:12px;height:12px;border-radius:50%;background:#f97316"></div>
            <span style="color:#e2e8f0;font-size:11px">HIGH</span>
        </div>
        <div style="display:flex;align-items:center;gap:6px;margin-bottom:4px">
            <div style="width:12px;height:12px;border-radius:50%;background:#eab308"></div>
            <span style="color:#e2e8f0;font-size:11px">MEDIUM</span>
        </div>
        <div style="display:flex;align-items:center;gap:6px">
            <div style="width:12px;height:12px;border-radius:50%;background:#22c55e"></div>
            <span style="color:#e2e8f0;font-size:11px">LOW</span>
        </div>
        <div style="color:#94a3b8;font-size:9px;margin-top:6px">⚠️ DEMO/SIMULATED DATA</div>
    </div>
    """
    m.get_root().html.add_child(folium.Element(legend_html))

    # Add all layers
    risk_layer.add_to(m)
    drain_layer.add_to(m)
    report_layer.add_to(m)
    team_layer.add_to(m)

    folium.LayerControl(collapsed=False, position="topright").add_to(m)

    return m


def _risk_popup(pred: dict) -> str:
    level = pred.get("risk_level", "LOW")
    color = RISK_COLORS.get(level, "#94a3b8")
    reasons = pred.get("main_reasons", [])
    reasons_html = "".join(f"<li style='margin:2px 0'>{r}</li>" for r in reasons[:3])
    action = pred.get("recommended_action", "")
    rf = pred.get("input_features", {}).get("rainfall_1h", 0)

    return f"""
    <div style="font-family:sans-serif;font-size:12px;min-width:240px">
        <div style="background:{color};color:{'black' if level=='MEDIUM' else 'white'};
                    padding:6px 10px;border-radius:6px 6px 0 0;font-weight:700;font-size:13px">
            {pred.get('area')}, {pred.get('city')}
        </div>
        <div style="padding:8px 10px;background:#1a1d27;color:#e2e8f0;border-radius:0 0 6px 6px">
            <div style="margin-bottom:6px">
                <b>Risk Level:</b> <span style="color:{color}">{level}</span> &nbsp;
                <b>Score:</b> {pred.get('risk_score', 0):.0f}/100
            </div>
            <div style="margin-bottom:6px"><b>Rainfall:</b> {rf:.0f} mm/hr</div>
            <div style="margin-bottom:6px">
                <b>Confidence:</b> {pred.get('confidence', 0):.0%}
            </div>
            <div style="margin-bottom:6px"><b>Key Factors:</b><ul style="margin:2px 0;padding-left:16px">{reasons_html}</ul></div>
            <div style="background:rgba(255,255,255,0.05);padding:4px 6px;border-radius:4px;font-size:11px">
                <b>Action:</b> {action[:100]}
            </div>
            <div style="color:#7c3aed;font-size:10px;margin-top:4px">⚙ DEMO/SIMULATED DATA</div>
        </div>
    </div>
    """


def _drain_popup(drain: dict) -> str:
    priority = drain.get("maintenance_priority", "LOW")
    color = DRAIN_COLORS.get(priority, "#94a3b8")
    return f"""
    <div style="font-family:sans-serif;font-size:12px;min-width:220px">
        <div style="background:{color};color:{'black' if priority in ('LOW','MEDIUM') else 'white'};
                    padding:6px 10px;border-radius:6px 6px 0 0;font-weight:700">
            Drain {drain.get('drain_id')} — {priority}
        </div>
        <div style="padding:8px 10px;background:#1a1d27;color:#e2e8f0;border-radius:0 0 6px 6px">
            <div><b>Area:</b> {drain.get('area')}, {drain.get('city')}</div>
            <div><b>Type:</b> {drain.get('drain_type','').replace('_',' ').title()}</div>
            <div><b>Status:</b> {drain.get('status')}</div>
            <div><b>Condition:</b> {drain.get('condition')}</div>
            <div><b>Capacity:</b> {drain.get('capacity_rating', 0):.0f}%</div>
            <div><b>Blockages/yr:</b> {drain.get('blockage_frequency', 0)}</div>
            <div style="margin-top:4px;font-size:11px;color:#f97316">
                {drain.get('recommended_action', '')}
            </div>
        </div>
    </div>
    """


def _report_popup(report: dict) -> str:
    sev = report.get("severity", "MEDIUM")
    sev_colors = {"CRITICAL": "#ef4444", "HIGH": "#f97316", "MEDIUM": "#eab308", "LOW": "#22c55e"}
    color = sev_colors.get(sev, "#94a3b8")
    return f"""
    <div style="font-family:sans-serif;font-size:12px;min-width:200px">
        <div style="background:{color};color:{'black' if sev in ('MEDIUM','LOW') else 'white'};
                    padding:6px 10px;border-radius:6px 6px 0 0;font-weight:700">
            {report.get('category','').replace('_',' ').title()} — {sev}
        </div>
        <div style="padding:8px 10px;background:#1a1d27;color:#e2e8f0;border-radius:0 0 6px 6px">
            <div><b>Area:</b> {report.get('area')}, {report.get('city')}</div>
            <div><b>Language:</b> {report.get('language','').title()}</div>
            <div><b>Status:</b> {report.get('status')}</div>
            <div style="margin-top:4px;font-size:11px;font-style:italic;color:#94a3b8">
                "{report.get('original_text', '')[:80]}..."
            </div>
        </div>
    </div>
    """
