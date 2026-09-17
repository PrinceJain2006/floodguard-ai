"""
FloodGuard AI — Digital Twin Map Component
===========================================
Folium-based interactive map for Ahmedabad & Surat, Gujarat, India.

SCOPE: This map is exclusively scoped to Ahmedabad and Surat as per the
hackathon challenge "Smart Urban Flooding & Drainage Management System
for Ahmedabad–Surat". Gujarat geography is used only as minimal visual
context. All risk zones, drainage data, citizen reports, and response
intelligence are associated only with Ahmedabad or Surat.

Basemap: OpenStreetMap (no API key required).
No CartoDB dependency.

Source taxonomy (used consistently in layers, legend, and popups):
  • 🌊 Predicted Flood Risk  — MODEL       (ML/risk pipeline output)
  • 🌧️ Weather Evidence      — LIVE / DEMO (Open-Meteo API or synthetic fallback)
  • 🔧 Drainage Infrastructure — DEMO      (seeded synthetic data)
  • 📱 Citizen Reports        — USER / DEMO (USER SUBMITTED = persisted portal reports;
                                             DEMO/SYNTHETIC = seeded demonstration data)
  • 🚒 Response Teams         — DEMO       (seeded synthetic data)

City markers for Ahmedabad and Surat always visible.
"""
from __future__ import annotations

import folium

# ─────────────────────────────────────────────────────────────────────────────
# Scope constraint — ONLY Ahmedabad and Surat are in scope
# ─────────────────────────────────────────────────────────────────────────────
# Any data record whose "city" field is not one of these two cities is
# silently excluded from the map. Gujarat coordinates are accepted for the
# basemap context only — they do not imply the solution scope extends beyond
# these two cities.
_IN_SCOPE_CITIES = frozenset({"Ahmedabad", "Surat"})

# ─────────────────────────────────────────────────────────────────────────────
# Color palettes
# ─────────────────────────────────────────────────────────────────────────────
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

# ─────────────────────────────────────────────────────────────────────────────
# Geography constants  (verified against seed_generator.py)
# ─────────────────────────────────────────────────────────────────────────────
CITY_CENTERS = {
    "Ahmedabad": [23.0225, 72.5714],
    "Surat":     [21.1702, 72.8311],
    # Midpoint that keeps both cities comfortably in frame
    "All":       [22.25,   72.70],
}

DEFAULT_ZOOM = {
    "Ahmedabad": 12,
    "Surat":     12,
    "All":       9,
}

# Gujarat bounding box — used for basemap context and coordinate sanity-check.
# Accepting Gujarat-wide coordinates does NOT expand the solution scope;
# all data markers are additionally filtered by _IN_SCOPE_CITIES.
_LAT_MIN, _LAT_MAX = 20.0, 24.5
_LON_MIN, _LON_MAX = 68.0, 75.5

# Tight bounds encompassing both cities — always use this when city == "All"
_AHMEDABAD_SURAT_BOUNDS = [
    [20.90, 72.30],   # SW  (south of Surat, west of both)
    [23.35, 73.10],   # NE  (north of Ahmedabad, east of both)
]


# ─────────────────────────────────────────────────────────────────────────────
# Helpers
# ─────────────────────────────────────────────────────────────────────────────

def _valid_coord(lat, lon) -> bool:
    """Accept only coordinates within the Gujarat context region."""
    try:
        lat, lon = float(lat), float(lon)
    except (TypeError, ValueError):
        return False
    return _LAT_MIN <= lat <= _LAT_MAX and _LON_MIN <= lon <= _LON_MAX


def _in_scope_city(city: str) -> bool:
    """
    Return True only when the city is Ahmedabad or Surat.

    This enforces the hackathon scope constraint: all risk zones, weather
    evidence, drainage information, citizen reports, and response intelligence
    shown on the map MUST be associated with Ahmedabad or Surat only.
    Records tagged with any other city are silently excluded.
    """
    return city in _IN_SCOPE_CITIES


def _city_marker(lat: float, lon: float, name: str) -> folium.Marker:
    """
    Permanent city pin marker — small coloured dot with a visible tooltip.
    Replaced the old large opaque rectangular label which caused visual clutter.
    """
    dot_html = (
        '<div style="'
        'width:10px;height:10px;border-radius:50%;'
        'background:#3b82f6;border:2px solid #fff;'
        'box-shadow:0 0 4px rgba(59,130,246,0.7)'
        '"></div>'
    )
    return folium.Marker(
        location=[lat, lon],
        tooltip=f"<b>{name}</b>",
        icon=folium.DivIcon(html=dot_html, icon_size=(10, 10), icon_anchor=(5, 5)),
        z_index_offset=1000,
    )


# ─────────────────────────────────────────────────────────────────────────────
# Main builder
# ─────────────────────────────────────────────────────────────────────────────

def build_flood_map(
    risk_predictions: list[dict],
    drain_data: list[dict],
    report_data: list[dict],
    team_data: list[dict],
    city: str = "All",
    zoom: int | None = None,
    weather_data: list[dict] | None = None,
    is_live: bool = False,
) -> folium.Map:
    """
    Build the FloodGuard Digital Twin Map — Ahmedabad & Surat only.

    SCOPE ENFORCEMENT: All five data layers (risk zones, weather evidence,
    drainage, citizen reports, response teams) are filtered to records whose
    "city" field matches "Ahmedabad" or "Surat" exclusively. Records tagged
    with any other city are silently excluded before rendering.

    • OpenStreetMap basemap only — no CartoDB, no API key required.
    • City markers for Ahmedabad and Surat always pinned.
    • Auto-fits to valid Gujarat markers when data is present.
    • Invalid coordinates (outside Gujarat bounds) are silently skipped.
    • weather_data: optional list of rainfall/weather dicts with keys
      latitude, longitude, city, rainfall_1h, condition, source.
    • is_live: when True the legend marks the weather layer as LIVE;
      when False (default) it is marked DEMO to avoid false claims.
    """
    center     = CITY_CENTERS.get(city, CITY_CENTERS["All"])
    zoom_start = zoom if zoom is not None else DEFAULT_ZOOM.get(city, 9)

    # ── Base map — OpenStreetMap only, no API key required ────────────────
    m = folium.Map(
        location=center,
        zoom_start=zoom_start,
        tiles=None,
    )

    # Single tile layer: standard OpenStreetMap
    folium.TileLayer(
        tiles="https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png",
        attr='&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors',
        name="OpenStreetMap",
        max_zoom=18,
    ).add_to(m)

    # ── Permanent city markers (not toggleable) ───────────────────────────
    if city in ("All", "Ahmedabad"):
        _city_marker(23.0225, 72.5714, "📍 Ahmedabad").add_to(m)
    if city in ("All", "Surat"):
        _city_marker(21.1702, 72.8311, "📍 Surat").add_to(m)

    # ── Layer groups — named using the standard source taxonomy ──────────
    # Show report layer by default so user-submitted markers are immediately visible
    _has_user_reports = any(
        str(r.get("source", "")).upper() == "USER SUBMITTED" for r in report_data
    )
    _wx_layer_name = "🌧️ Weather Evidence — LIVE" if is_live else "🌧️ Weather Evidence — DEMO"
    risk_layer    = folium.FeatureGroup(name="🌊 Predicted Flood Risk — MODEL", show=True)
    weather_layer = folium.FeatureGroup(name=_wx_layer_name,                    show=True)
    drain_layer   = folium.FeatureGroup(name="🔧 Drainage Infrastructure — DEMO", show=False)
    report_layer  = folium.FeatureGroup(name="📱 Citizen Reports — USER / DEMO", show=_has_user_reports)
    team_layer    = folium.FeatureGroup(name="🚒 Response Teams — DEMO",         show=False)

    # Collect valid latlons from risk + drain markers for fit_bounds
    bounds_latlons: list[list[float]] = []

    # ── Predicted flood risk zones ────────────────────────────────────────
    for pred in risk_predictions:
        # Scope guard: only Ahmedabad or Surat
        if not _in_scope_city(pred.get("city", "")):
            continue
        lat = pred.get("latitude")
        lon = pred.get("longitude")
        if not _valid_coord(lat, lon):
            continue
        lat, lon = float(lat), float(lon)
        bounds_latlons.append([lat, lon])

        level  = pred.get("risk_level", "LOW")
        score  = pred.get("risk_score", 0)
        color  = RISK_COLORS.get(level, "#94a3b8")
        radius = max(250, min(score * 22, 2000))

        folium.Circle(
            location=[lat, lon],
            radius=radius,
            color=color,
            fill=True,
            fill_color=color,
            fill_opacity=0.22,
            weight=1.5,
            tooltip=f"{pred.get('area')} — {level} ({score:.0f})",
        ).add_to(risk_layer)

        dot_html = (
            f'<div style="'
            f'background:{color};'
            f'width:12px;height:12px;border-radius:50%;'
            f'border:2px solid white;'
            f'box-shadow:0 0 5px {color}'
            f'"></div>'
        )
        folium.Marker(
            location=[lat, lon],
            popup=folium.Popup(_risk_popup(pred), max_width=280),
            tooltip=f"{pred.get('area')}, {pred.get('city')} | {level} {score:.0f}/100",
            icon=folium.DivIcon(html=dot_html, icon_size=(12, 12), icon_anchor=(6, 6)),
        ).add_to(risk_layer)

    # ── Weather evidence layer ────────────────────────────────────────────
    # Accepts either explicit weather_data or falls back to rainfall from
    # risk_predictions (demo mode — clearly labeled)
    weather_points = weather_data if weather_data else _weather_from_predictions(risk_predictions)
    for wp in weather_points:
        # Scope guard: only Ahmedabad or Surat
        if not _in_scope_city(wp.get("city", "")):
            continue
        lat = wp.get("latitude")
        lon = wp.get("longitude")
        if not _valid_coord(lat, lon):
            continue
        lat, lon = float(lat), float(lon)

        rain       = wp.get("rainfall_1h", 0)
        cond       = wp.get("condition", "Rain")
        src        = wp.get("source", "DEMO")
        # Use per-point source to determine live status for this individual marker;
        # rename to _wp_is_live to avoid shadowing the function-level is_live parameter.
        _wp_is_live = str(src).upper() not in ("DEMO", "SYNTHETIC", "SIMULATED")

        w_color = (
            "#ef4444" if rain >= 80 else
            "#f97316" if rain >= 40 else
            "#eab308" if rain >= 15 else
            "#22c55e"
        )
        badge   = "LIVE" if _wp_is_live else "DEMO"
        badge_c = "#22c55e" if _wp_is_live else "#7c3aed"

        w_icon = (
            f'<div style="'
            f'background:rgba(15,17,23,0.75);'
            f'border:1px solid {w_color};'
            f'border-radius:4px;'
            f'padding:2px 4px;'
            f'font-size:10px;'
            f'font-weight:700;'
            f'color:{w_color};'
            f'white-space:nowrap'
            f'">🌧️ {rain:.0f}mm</div>'
        )
        folium.Marker(
            location=[lat, lon],
            popup=folium.Popup(_weather_popup(wp, _wp_is_live), max_width=240),
            tooltip=f"{wp.get('city','?')} | Rain: {rain:.0f} mm/hr | {badge}",
            icon=folium.DivIcon(html=w_icon, icon_size=(64, 20), icon_anchor=(32, 10)),
        ).add_to(weather_layer)

    # ── Drainage status ───────────────────────────────────────────────────
    for drain in drain_data:
        # Scope guard: only Ahmedabad or Surat
        if not _in_scope_city(drain.get("city", "")):
            continue
        lat = drain.get("latitude")
        lon = drain.get("longitude")
        if not _valid_coord(lat, lon):
            continue
        lat, lon = float(lat), float(lon)
        bounds_latlons.append([lat, lon])

        priority = drain.get("maintenance_priority", "LOW")
        color    = DRAIN_COLORS.get(priority, "#94a3b8")
        status   = drain.get("status", "OPERATIONAL")

        sq_html = (
            f'<div style="'
            f'background:{color};'
            f'width:9px;height:9px;border-radius:2px;'
            f'border:1px solid rgba(255,255,255,0.4)'
            f'"></div>'
        )
        folium.Marker(
            location=[lat, lon],
            popup=folium.Popup(_drain_popup(drain), max_width=240),
            tooltip=f"Drain {drain.get('drain_id')} — {priority} ({status})",
            icon=folium.DivIcon(html=sq_html, icon_size=(9, 9), icon_anchor=(4, 4)),
        ).add_to(drain_layer)

    # ── Citizen reports ───────────────────────────────────────────────────
    # USER SUBMITTED reports get a distinct 🟠 pin; demo/synthetic get 📍
    sev_colors = {
        "CRITICAL": "#ef4444", "HIGH": "#f97316",
        "MEDIUM":   "#eab308", "LOW":  "#22c55e",
    }
    for report in report_data[:80]:
        # Scope guard: only Ahmedabad or Surat
        if not _in_scope_city(report.get("city", "")):
            continue
        lat = report.get("latitude")
        lon = report.get("longitude")
        if not _valid_coord(lat, lon):
            continue
        lat, lon = float(lat), float(lon)
        sev   = report.get("severity", "MEDIUM")
        color = sev_colors.get(sev, "#94a3b8")
        is_user_submitted = str(report.get("source", "")).upper() == "USER SUBMITTED"
        pin_emoji = "🟠" if is_user_submitted else "📍"
        pin_html = (
            f'<div style="font-size:{"14" if is_user_submitted else "13"}px;line-height:1;'
            f'filter:drop-shadow(0 0 3px {color})">{pin_emoji}</div>'
        )
        source_label = "USER SUBMITTED" if is_user_submitted else "DEMO/SYNTHETIC"
        folium.Marker(
            location=[lat, lon],
            popup=folium.Popup(_report_popup(report), max_width=240),
            tooltip=f"[{source_label}] {report.get('category','?').replace('_',' ').title()} — {sev}",
            icon=folium.DivIcon(html=pin_html, icon_size=(16, 16), icon_anchor=(8, 14)),
        ).add_to(report_layer)

    # ── Response teams ────────────────────────────────────────────────────
    team_icons = {
        "pump_team":      "💧",
        "emergency":      "🚨",
        "drainage":       "🔧",
        "traffic":        "🚦",
        "rapid_response": "⚡",
    }
    for team in team_data:
        # Scope guard: only Ahmedabad or Surat
        if not _in_scope_city(team.get("city", "")):
            continue
        lat = team.get("latitude")
        lon = team.get("longitude")
        if not _valid_coord(lat, lon):
            continue
        lat, lon  = float(lat), float(lon)
        emoji     = team_icons.get(team.get("team_type", ""), "🚒")
        status    = team.get("status", "AVAILABLE")
        opacity   = "1.0" if status == "DEPLOYED" else "0.65"
        t_html    = (
            f'<div style="font-size:15px;line-height:1;opacity:{opacity}">{emoji}</div>'
        )
        folium.Marker(
            location=[lat, lon],
            tooltip=f"{team.get('name','Team')} — {status}",
            icon=folium.DivIcon(html=t_html, icon_size=(18, 18), icon_anchor=(9, 9)),
        ).add_to(team_layer)

    # ── Compact legend — top-left, clear of zoom controls and OSM attribution ─
    # Rendered inside Folium's iframe body so position:fixed is relative to the
    # iframe viewport.  Values are deliberately small to avoid covering markers.
    _wx_label = "LIVE" if is_live else "DEMO"
    _wx_color = "#6ee7b7" if is_live else "#c4b5fd"
    legend_html = f"""
    <div style="position:fixed;top:8px;left:8px;z-index:998;
                background:rgba(10,11,18,0.88);border:1px solid #2d3148;
                border-radius:6px;padding:5px 8px;font-family:sans-serif;
                font-size:9px;line-height:1.55;max-width:138px;
                pointer-events:none">
        <div style="color:#94a3b8;font-weight:700;letter-spacing:0.05em;
                    font-size:8px;margin-bottom:3px">FLOOD RISK</div>
        <div style="display:flex;align-items:center;gap:4px;margin-bottom:1px">
            <div style="width:8px;height:8px;border-radius:50%;background:#ef4444;flex-shrink:0"></div>
            <span style="color:#e2e8f0">CRITICAL</span>
        </div>
        <div style="display:flex;align-items:center;gap:4px;margin-bottom:1px">
            <div style="width:8px;height:8px;border-radius:50%;background:#f97316;flex-shrink:0"></div>
            <span style="color:#e2e8f0">HIGH</span>
        </div>
        <div style="display:flex;align-items:center;gap:4px;margin-bottom:1px">
            <div style="width:8px;height:8px;border-radius:50%;background:#eab308;flex-shrink:0"></div>
            <span style="color:#e2e8f0">MEDIUM</span>
        </div>
        <div style="display:flex;align-items:center;gap:4px;margin-bottom:3px">
            <div style="width:8px;height:8px;border-radius:50%;background:#22c55e;flex-shrink:0"></div>
            <span style="color:#e2e8f0">LOW</span>
        </div>
        <div style="border-top:1px solid #2d3148;margin:3px 0"></div>
        <div style="color:#94a3b8;font-weight:700;letter-spacing:0.05em;
                    font-size:8px;margin-bottom:3px">LAYERS &amp; SOURCES</div>
        <div style="color:{_wx_color};margin-bottom:1px">🌧️ Weather — <b>{_wx_label}</b></div>
        <div style="color:#93c5fd;margin-bottom:1px">🌊 Flood Risk — <b>MODEL</b></div>
        <div style="color:#c4b5fd;margin-bottom:1px">🔧 Drainage — <b>DEMO</b></div>
        <div style="color:#fdba74;margin-bottom:1px">🟠 Reports — <b>USER / DEMO</b></div>
        <div style="color:#c4b5fd">🚒 Teams — <b>DEMO</b></div>
    </div>
    """
    m.get_root().html.add_child(folium.Element(legend_html))

    # ── Add layers ────────────────────────────────────────────────────────
    risk_layer.add_to(m)
    weather_layer.add_to(m)
    drain_layer.add_to(m)
    report_layer.add_to(m)
    team_layer.add_to(m)

    # Layer control — collapsed, top-right, away from city markers
    folium.LayerControl(collapsed=True, position="topright").add_to(m)

    # ── Auto-fit bounds ───────────────────────────────────────────────────
    if city == "All":
        # Always use the pre-defined Ahmedabad+Surat bounds for the "All" view
        # so both cities are visible regardless of where markers fall.
        m.fit_bounds(_AHMEDABAD_SURAT_BOUNDS)
    elif len(bounds_latlons) >= 2:
        lats = [p[0] for p in bounds_latlons]
        lons = [p[1] for p in bounds_latlons]
        pad  = 0.08
        sw   = [max(min(lats) - pad, _LAT_MIN), max(min(lons) - pad, _LON_MIN)]
        ne   = [min(max(lats) + pad, _LAT_MAX), min(max(lons) + pad, _LON_MAX)]
        m.fit_bounds([sw, ne])

    return m


# ─────────────────────────────────────────────────────────────────────────────
# Weather evidence helper
# ─────────────────────────────────────────────────────────────────────────────

def _weather_from_predictions(risk_predictions: list[dict]) -> list[dict]:
    """
    Derive demo weather evidence points from existing risk prediction data.
    Uses one representative point per city (the highest-rainfall area).
    Clearly labeled DEMO — not real weather readings.
    """
    by_city: dict[str, dict] = {}
    for pred in risk_predictions:
        city = pred.get("city", "")
        rain = pred.get("input_features", {}).get("rainfall_1h", 0)
        if city not in by_city or rain > by_city[city].get("rainfall_1h", 0):
            by_city[city] = {
                "city":        city,
                "area":        pred.get("area", city),
                "latitude":    pred.get("latitude"),
                "longitude":   pred.get("longitude"),
                "rainfall_1h": rain,
                "rainfall_6h": pred.get("input_features", {}).get("rainfall_6h", rain * 5.5),
                "condition":   _rain_condition(rain),
                "source":      "DEMO",
                "recorded_at": "Demo scenario data",
            }
    return list(by_city.values())


def _rain_condition(rain_1h: float) -> str:
    if rain_1h >= 80:
        return "Extreme Rain"
    if rain_1h >= 40:
        return "Heavy Rain"
    if rain_1h >= 15:
        return "Moderate Rain"
    if rain_1h >= 5:
        return "Light Rain"
    return "Dry / Trace"


# ─────────────────────────────────────────────────────────────────────────────
# Popup builders
# ─────────────────────────────────────────────────────────────────────────────

def _risk_popup(pred: dict) -> str:
    level        = pred.get("risk_level", "LOW")
    color        = RISK_COLORS.get(level, "#94a3b8")
    txt_color    = "black" if level == "MEDIUM" else "white"
    score        = pred.get("risk_score", 0)
    rf           = pred.get("input_features", {}).get("rainfall_1h", 0)
    conf         = pred.get("confidence", 0)
    reasons      = pred.get("main_reasons", [])
    reasons_html = "".join(f"<li style='margin:1px 0'>{r}</li>" for r in reasons[:3])
    action       = pred.get("recommended_action", "")[:100]

    return (
        f'<div style="font-family:sans-serif;font-size:12px;min-width:220px;max-width:270px">'
        f'<div style="background:{color};color:{txt_color};padding:5px 9px;'
        f'border-radius:5px 5px 0 0;font-weight:700;font-size:12px">'
        f'{pred.get("area","")}, {pred.get("city","")}</div>'
        f'<div style="padding:7px 9px;background:#1a1d27;color:#e2e8f0;border-radius:0 0 5px 5px">'
        f'<div style="margin-bottom:4px"><b>Risk:</b> <span style="color:{color}">{level}</span>'
        f' &nbsp; <b>Score:</b> {score:.0f}/100</div>'
        f'<div style="margin-bottom:4px"><b>Rainfall:</b> {rf:.0f} mm/hr'
        f' &nbsp; <b>Conf:</b> {conf:.0%}</div>'
        f'<div style="margin-bottom:3px"><b>Evidence:</b>'
        f'<ul style="margin:2px 0;padding-left:14px">{reasons_html}</ul></div>'
        f'<div style="background:rgba(255,255,255,0.05);padding:3px 5px;'
        f'border-radius:3px;font-size:10px">{action}</div>'
        f'<div style="color:#93c5fd;font-size:9px;margin-top:3px">🌊 FLOOD RISK — MODEL</div>'
        f'</div></div>'
    )


def _weather_popup(wp: dict, is_live: bool) -> str:
    rain   = wp.get("rainfall_1h", 0)
    rain6  = wp.get("rainfall_6h", 0)
    cond   = wp.get("condition", "—")
    src    = wp.get("source", "DEMO")
    rec    = wp.get("recorded_at", "—")
    city   = wp.get("city", "—")
    area   = wp.get("area", "")
    badge  = "🟢 LIVE" if is_live else "⚙ DEMO"
    b_col  = "#22c55e" if is_live else "#a78bfa"

    src_tag = "🌧️ WEATHER — LIVE" if is_live else "🌧️ WEATHER — DEMO"
    return (
        f'<div style="font-family:sans-serif;font-size:12px;min-width:200px;max-width:240px">'
        f'<div style="background:#1e3a5f;color:#93c5fd;padding:5px 9px;'
        f'border-radius:5px 5px 0 0;font-weight:700">🌧️ {city} — Weather Evidence</div>'
        f'<div style="padding:7px 9px;background:#1a1d27;color:#e2e8f0;border-radius:0 0 5px 5px">'
        f'<div><b>Area:</b> {area}</div>'
        f'<div><b>Rainfall (1h):</b> {rain:.1f} mm/hr</div>'
        f'<div><b>Rainfall (6h):</b> {rain6:.1f} mm</div>'
        f'<div><b>Condition:</b> {cond}</div>'
        f'<div><b>Source:</b> {src}</div>'
        f'<div><b>Recorded:</b> {str(rec)[:19]}</div>'
        f'<div style="color:{b_col};font-size:9px;margin-top:3px;font-weight:700">{src_tag}</div>'
        f'</div></div>'
    )


def _drain_popup(drain: dict) -> str:
    priority  = drain.get("maintenance_priority", "LOW")
    color     = DRAIN_COLORS.get(priority, "#94a3b8")
    txt_color = "black" if priority in ("LOW", "MEDIUM") else "white"

    return (
        f'<div style="font-family:sans-serif;font-size:12px;min-width:200px;max-width:240px">'
        f'<div style="background:{color};color:{txt_color};padding:5px 9px;'
        f'border-radius:5px 5px 0 0;font-weight:700">'
        f'Drain {drain.get("drain_id","")} — {priority}</div>'
        f'<div style="padding:7px 9px;background:#1a1d27;color:#e2e8f0;border-radius:0 0 5px 5px">'
        f'<div><b>Zone:</b> {drain.get("area","")}, {drain.get("city","")}</div>'
        f'<div><b>Type:</b> {drain.get("drain_type","").replace("_"," ").title()}</div>'
        f'<div><b>Status:</b> {drain.get("status","")}</div>'
        f'<div><b>Condition:</b> {drain.get("condition","")}</div>'
        f'<div><b>Capacity:</b> {drain.get("capacity_rating",0):.0f}%</div>'
        f'<div><b>Blockages/yr:</b> {drain.get("blockage_frequency",0)}</div>'
        f'<div style="font-size:10px;color:#f97316;margin-top:3px">'
        f'{drain.get("recommended_action","")}</div>'
        f'<div style="color:#c4b5fd;font-size:9px;margin-top:2px;font-weight:700">🔧 DRAINAGE — DEMO</div>'
        f'</div></div>'
    )


def _report_popup(report: dict) -> str:
    sev       = report.get("severity", "MEDIUM")
    sev_c     = {"CRITICAL": "#ef4444", "HIGH": "#f97316", "MEDIUM": "#eab308", "LOW": "#22c55e"}
    color     = sev_c.get(sev, "#94a3b8")
    txt_color = "black" if sev in ("MEDIUM", "LOW") else "white"
    txt       = report.get("original_text", "")[:80]
    # Distinguish actual user-submitted reports from demo/synthetic seed data
    src            = str(report.get("source", "")).upper()
    is_user        = src == "USER SUBMITTED"
    src_color      = "#fdba74" if is_user else "#c4b5fd"
    src_label      = "🟠 USER SUBMITTED" if is_user else "🟡 DEMO/SYNTHETIC"
    submitted_at   = report.get("submitted_at", report.get("created_at", ""))[:16].replace("T", " ")

    # Derive the standard popup source tag from the already-computed src_label
    popup_tag = (
        "🟠 CITIZEN REPORT — USER SUBMITTED" if is_user
        else "📍 CITIZEN REPORT — DEMO/SYNTHETIC"
    )
    return (
        f'<div style="font-family:sans-serif;font-size:12px;min-width:190px;max-width:240px">'
        f'<div style="background:{color};color:{txt_color};padding:5px 9px;'
        f'border-radius:5px 5px 0 0;font-weight:700">'
        f'{report.get("category","").replace("_"," ").title()} — {sev}</div>'
        f'<div style="padding:7px 9px;background:#1a1d27;color:#e2e8f0;border-radius:0 0 5px 5px">'
        f'<div><b>Zone:</b> {report.get("area","")}, {report.get("city","")}</div>'
        f'<div><b>Report ID:</b> {report.get("report_id","")}</div>'
        f'<div><b>Language:</b> {report.get("language","").title()}</div>'
        f'<div><b>Status:</b> {report.get("status","OPEN")}</div>'
        f'<div><b>Time:</b> {submitted_at}</div>'
        f'<div style="font-size:10px;font-style:italic;color:#94a3b8;margin-top:3px">"{txt}…"</div>'
        f'<div style="color:{src_color};font-size:9px;font-weight:700;margin-top:2px">{popup_tag}</div>'
        f'</div></div>'
    )
