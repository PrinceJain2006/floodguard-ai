"""
FloodGuard AI — Synthetic / Demo Dataset Generator
Produces realistic Ahmedabad and Surat flood scenario data.
All data is clearly labeled DEMO/SYNTHETIC and does not represent real government data.
"""
import json
import random
import uuid
from datetime import datetime, timedelta
from pathlib import Path

random.seed(42)

# ──────────────────────────────────────────────
# Geographic data — Ahmedabad & Surat areas
# ──────────────────────────────────────────────
AHMEDABAD_AREAS = [
    {"name": "Maninagar",       "lat": 22.9908, "lon": 72.6084, "elevation": 49, "density": 0.9},
    {"name": "Navrangpura",     "lat": 23.0395, "lon": 72.5616, "elevation": 53, "density": 0.7},
    {"name": "Naroda",          "lat": 23.0892, "lon": 72.6571, "elevation": 47, "density": 0.85},
    {"name": "Vatva",           "lat": 22.9518, "lon": 72.6401, "elevation": 45, "density": 0.75},
    {"name": "Gota",            "lat": 23.1187, "lon": 72.5574, "elevation": 55, "density": 0.6},
    {"name": "Chandkheda",      "lat": 23.1169, "lon": 72.5877, "elevation": 56, "density": 0.65},
    {"name": "Bopal",           "lat": 23.0239, "lon": 72.4705, "elevation": 58, "density": 0.55},
    {"name": "Satellite",       "lat": 23.0218, "lon": 72.5260, "elevation": 54, "density": 0.72},
    {"name": "Vejalpur",        "lat": 22.9995, "lon": 72.5191, "elevation": 51, "density": 0.68},
    {"name": "Isanpur",         "lat": 22.9726, "lon": 72.6226, "elevation": 46, "density": 0.88},
    {"name": "Nikol",           "lat": 23.0457, "lon": 72.6481, "elevation": 47, "density": 0.83},
    {"name": "Odhav",           "lat": 23.0057, "lon": 72.6601, "elevation": 46, "density": 0.78},
    {"name": "Piplaj",          "lat": 22.9478, "lon": 72.5641, "elevation": 48, "density": 0.65},
    {"name": "Ranip",           "lat": 23.0751, "lon": 72.5627, "elevation": 52, "density": 0.70},
    {"name": "Ambawadi",        "lat": 23.0278, "lon": 72.5521, "elevation": 53, "density": 0.72},
]

SURAT_AREAS = [
    {"name": "Adajan",          "lat": 21.2063, "lon": 72.8060, "elevation": 12, "density": 0.82},
    {"name": "Katargam",        "lat": 21.2253, "lon": 72.8317, "elevation": 10, "density": 0.90},
    {"name": "Rander",          "lat": 21.2371, "lon": 72.7734, "elevation": 11, "density": 0.78},
    {"name": "Udhna",           "lat": 21.1680, "lon": 72.8501, "elevation": 9,  "density": 0.87},
    {"name": "Limbayat",        "lat": 21.1817, "lon": 72.8611, "elevation": 10, "density": 0.85},
    {"name": "Vesu",            "lat": 21.1553, "lon": 72.7888, "elevation": 13, "density": 0.65},
    {"name": "Pal",             "lat": 21.1820, "lon": 72.7791, "elevation": 11, "density": 0.70},
    {"name": "Varachha",        "lat": 21.2100, "lon": 72.8606, "elevation": 10, "density": 0.92},
    {"name": "Bhatar",          "lat": 21.2326, "lon": 72.8591, "elevation": 11, "density": 0.75},
    {"name": "Piplod",          "lat": 21.1618, "lon": 72.8050, "elevation": 13, "density": 0.60},
    {"name": "Althan",          "lat": 21.1446, "lon": 72.7952, "elevation": 14, "density": 0.55},
    {"name": "Sarthana",        "lat": 21.2302, "lon": 72.8813, "elevation": 9,  "density": 0.88},
    {"name": "Dindoli",         "lat": 21.1451, "lon": 72.8388, "elevation": 10, "density": 0.80},
    {"name": "Kamrej",          "lat": 21.2638, "lon": 72.9278, "elevation": 12, "density": 0.60},
    {"name": "Sachin",          "lat": 21.0916, "lon": 72.8773, "elevation": 8,  "density": 0.70},
]

ALL_AREAS = {
    "Ahmedabad": AHMEDABAD_AREAS,
    "Surat": SURAT_AREAS,
}

DRAIN_TYPES = ["storm_drain", "open_channel", "culvert", "underground_pipe"]
TEAM_TYPES = ["pump_team", "emergency", "drainage", "traffic", "rapid_response"]
INCIDENT_CATEGORIES = ["waterlogging", "drain_overflow", "road_blockage",
                        "traffic_disruption", "property_flooding", "emergency_situation"]
SEVERITY_LEVELS = ["LOW", "MEDIUM", "HIGH", "CRITICAL"]


def _rnd_date(days_back=90):
    return (datetime.utcnow() - timedelta(days=random.randint(0, days_back))).isoformat()


def _jitter(lat, lon, scale=0.005):
    return lat + random.uniform(-scale, scale), lon + random.uniform(-scale, scale)


# ──────────────────────────────────────────────
# 1. Rainfall data
# ──────────────────────────────────────────────
def generate_rainfall_data(scenario="NORMAL"):
    multiplier = {"NORMAL": 1.0, "HEAVY": 3.0, "EXTREME": 6.0, "RECOVERY": 0.2}.get(scenario, 1.0)
    records = []
    for city, areas in ALL_AREAS.items():
        city_mult = 1.0 if city == "Ahmedabad" else 1.15   # Surat near coast — slightly wetter
        for area in areas:
            lat, lon = _jitter(area["lat"], area["lon"])
            base_1h = random.uniform(2, 18) * multiplier * city_mult
            records.append({
                "city": city,
                "area": area["name"],
                "latitude": round(lat, 5),
                "longitude": round(lon, 5),
                "rainfall_1h":  round(base_1h, 1),
                "rainfall_3h":  round(base_1h * random.uniform(2.5, 3.5), 1),
                "rainfall_6h":  round(base_1h * random.uniform(5.0, 7.0), 1),
                "rainfall_24h": round(base_1h * random.uniform(14, 22), 1),
                "recorded_at":  datetime.utcnow().isoformat(),
                "data_source":  "DEMO",
            })
    return records


# ──────────────────────────────────────────────
# 2. Drainage infrastructure
# ──────────────────────────────────────────────
def generate_drains():
    drains = []
    drain_counter = 1
    conditions = ["GOOD", "GOOD", "FAIR", "FAIR", "POOR", "CRITICAL"]
    for city, areas in ALL_AREAS.items():
        for area in areas:
            n_drains = random.randint(4, 8)
            for _ in range(n_drains):
                lat, lon = _jitter(area["lat"], area["lon"], 0.008)
                condition = random.choice(conditions)
                blockage_freq = {"GOOD": random.randint(0, 1), "FAIR": random.randint(1, 3),
                                 "POOR": random.randint(3, 7), "CRITICAL": random.randint(6, 12)}[condition]
                capacity = {"GOOD": random.uniform(75, 100), "FAIR": random.uniform(50, 75),
                            "POOR": random.uniform(25, 50), "CRITICAL": random.uniform(5, 25)}[condition]
                near_flood = random.random() < 0.35
                risk_score = round(
                    (100 - capacity) * 0.4 +
                    blockage_freq * 5.0 +
                    (30 if near_flood else 0) +
                    random.uniform(-5, 5), 1
                )
                risk_score = max(0, min(100, risk_score))
                priority = "CRITICAL" if risk_score >= 75 else "HIGH" if risk_score >= 50 else "MEDIUM" if risk_score >= 25 else "LOW"

                days_since_clean = random.randint(30, 365)
                last_cleaned = (datetime.utcnow() - timedelta(days=days_since_clean)).isoformat()

                drains.append({
                    "drain_id": f"D-{drain_counter:03d}",
                    "city": city,
                    "area": area["name"],
                    "latitude": round(lat, 5),
                    "longitude": round(lon, 5),
                    "drain_type": random.choice(DRAIN_TYPES),
                    "capacity_rating": round(capacity, 1),
                    "condition": condition,
                    "last_cleaned": last_cleaned,
                    "blockage_frequency": blockage_freq,
                    "near_flood_zone": near_flood,
                    "risk_score": risk_score,
                    "maintenance_priority": priority,
                    "status": "BLOCKED" if condition == "CRITICAL" and random.random() < 0.5 else "OPERATIONAL",
                })
                drain_counter += 1
    return drains


# ──────────────────────────────────────────────
# 3. Historical flood incidents
# ──────────────────────────────────────────────
def generate_flood_incidents():
    incidents = []
    inc_counter = 1
    for city, areas in ALL_AREAS.items():
        for area in areas:
            n_incidents = random.randint(1, 5)
            for _ in range(n_incidents):
                lat, lon = _jitter(area["lat"], area["lon"])
                severity = random.choices(SEVERITY_LEVELS, weights=[30, 35, 25, 10])[0]
                rainfall = {"LOW": random.uniform(20, 40), "MEDIUM": random.uniform(40, 70),
                            "HIGH": random.uniform(70, 100), "CRITICAL": random.uniform(100, 180)}[severity]
                reported_at = _rnd_date(180)
                resolved_at = (
                    datetime.fromisoformat(reported_at) + timedelta(hours=random.randint(2, 48))
                ).isoformat() if random.random() > 0.2 else None

                incidents.append({
                    "incident_id": f"INC-{inc_counter:04d}",
                    "city": city,
                    "area": area["name"],
                    "latitude": round(lat, 5),
                    "longitude": round(lon, 5),
                    "severity": severity,
                    "status": "RESOLVED" if resolved_at else "ACTIVE",
                    "rainfall_at_event": round(rainfall, 1),
                    "duration_hours": round(random.uniform(1, 36), 1),
                    "affected_population": random.randint(100, 15000),
                    "description": f"Urban flooding reported in {area['name']}, {city}. "
                                   f"Severity: {severity}. Rainfall: {rainfall:.1f} mm.",
                    "reported_at": reported_at,
                    "resolved_at": resolved_at,
                    "assigned_team": f"Team-{random.randint(1,5):02d}" if resolved_at else None,
                })
                inc_counter += 1
    return incidents


# ──────────────────────────────────────────────
# 4. ML training dataset
# ──────────────────────────────────────────────
def generate_ml_training_data(n_samples=5000):
    """
    Synthetic training data for flood risk ML model.
    Features match real hydrology research but values are SIMULATED.
    """
    data = []
    for _ in range(n_samples):
        city = random.choice(["Ahmedabad", "Surat"])
        area_list = ALL_AREAS[city]
        area = random.choice(area_list)

        rainfall_1h = random.uniform(0, 120)
        rainfall_3h = rainfall_1h * random.uniform(2.5, 3.5)
        rainfall_6h = rainfall_3h * random.uniform(1.8, 2.5)
        rainfall_24h = rainfall_6h * random.uniform(2, 4)
        drainage_capacity = random.uniform(10, 100)
        historical_flood_freq = random.randint(0, 12)
        water_level = random.uniform(0, 5)
        elevation = area["elevation"] + random.uniform(-3, 3)
        road_density = area["density"] + random.uniform(-0.1, 0.1)
        citizen_reports = random.randint(0, 80)

        # Composite risk score (domain-logic based labeling)
        risk = (
            rainfall_1h * 0.30 +
            (100 - drainage_capacity) * 0.20 +
            historical_flood_freq * 3.5 +
            water_level * 8.0 +
            (65 - elevation) * 0.5 +
            citizen_reports * 0.25
        ) / 100

        # Add noise
        risk += random.gauss(0, 0.05)
        risk = max(0, min(1, risk))

        # Categorize
        if risk >= 0.75:
            label = "CRITICAL"
        elif risk >= 0.50:
            label = "HIGH"
        elif risk >= 0.25:
            label = "MEDIUM"
        else:
            label = "LOW"

        data.append({
            "city": city,
            "area": area["name"],
            "rainfall_1h": round(rainfall_1h, 2),
            "rainfall_3h": round(rainfall_3h, 2),
            "rainfall_6h": round(rainfall_6h, 2),
            "rainfall_24h": round(rainfall_24h, 2),
            "drainage_capacity": round(drainage_capacity, 2),
            "historical_flood_freq": historical_flood_freq,
            "water_level": round(water_level, 2),
            "elevation": round(elevation, 2),
            "road_density": round(road_density, 3),
            "citizen_reports": citizen_reports,
            "risk_score": round(risk * 100, 2),
            "risk_label": label,
        })
    return data


# ──────────────────────────────────────────────
# 5. Response teams
# ──────────────────────────────────────────────
def generate_response_teams():
    teams = []
    team_counter = 1
    for city in ["Ahmedabad", "Surat"]:
        for ttype in TEAM_TYPES:
            for _ in range(random.randint(2, 4)):
                teams.append({
                    "team_id": f"TEAM-{team_counter:03d}",
                    "name": f"{city} {ttype.replace('_',' ').title()} #{team_counter}",
                    "city": city,
                    "team_type": ttype,
                    "status": random.choices(
                        ["AVAILABLE", "DEPLOYED", "STANDBY", "OFF_DUTY"],
                        weights=[50, 20, 20, 10]
                    )[0],
                    "current_area": None,
                    "contact": f"+91-9{random.randint(1000000000, 9999999999)}",
                    "capacity": random.randint(5, 20),
                })
                team_counter += 1
    return teams


# ──────────────────────────────────────────────
# 6. Citizen reports (seed data)
# ──────────────────────────────────────────────
SAMPLE_REPORTS = {
    "english": [
        "Water logging on the main road near {area} bus stand. Cars are stuck.",
        "The drain near {area} market is overflowing. Sewage on the street.",
        "Road is completely blocked due to flooding at {area} junction.",
        "My house in {area} is flooded. Water level rising.",
        "Emergency! People stranded in {area} due to chest-level water.",
    ],
    "hindi": [
        "{area} के पास मुख्य सड़क पर पानी भर गया है। गाड़ियां फंसी हैं।",
        "{area} बाजार के पास नाला उफान पर है। सड़क पर गंदा पानी बह रहा है।",
        "{area} चौक पर बाढ़ के कारण रास्ता बंद है।",
        "{area} में मेरा घर जलमग्न हो गया है, पानी का स्तर बढ़ रहा है।",
        "आपात स्थिति! {area} में सीने तक पानी भरने से लोग फंसे हैं।",
    ],
    "gujarati": [
        "{area} પાસે મુખ્ય રસ્તા પર પાણી ભરાઈ ગયું છે. ગાડીઓ ફસાઈ છે.",
        "{area} બજાર પાસે ગટર ઉભરાઈ રહી છે. રસ્તા પર ગંદુ પાણી વહી રહ્યું છે.",
        "{area} ચોક પર પૂરના કારણે રસ્તો બંધ છે.",
        "{area} માં મારું ઘર પૂરથી ભરાઈ ગયું છે, પાણી ઊંચું ચઢી રહ્યું છે.",
        "ઇમર્જન્સી! {area} માં છાતી સુધી પાણી ભરાવાથી લોકો ફસાઈ ગયા છે.",
    ],
}

CATEGORY_MAP = {
    0: "road_blockage",
    1: "drain_overflow",
    2: "road_blockage",
    3: "property_flooding",
    4: "emergency_situation",
}

SEVERITY_MAP = {
    0: "MEDIUM",
    1: "HIGH",
    2: "HIGH",
    3: "HIGH",
    4: "CRITICAL",
}


def generate_citizen_reports(n=200):
    reports = []
    counter = 1
    for _ in range(n):
        city = random.choice(["Ahmedabad", "Surat"])
        area = random.choice(ALL_AREAS[city])["name"]
        lang = random.choice(["english", "hindi", "gujarati"])
        msg_idx = random.randint(0, 4)
        text = SAMPLE_REPORTS[lang][msg_idx].format(area=area)
        severity = SEVERITY_MAP[msg_idx]
        category = CATEGORY_MAP[msg_idx]
        lat, lon = _jitter(
            next(a["lat"] for a in ALL_AREAS[city] if a["name"] == area),
            next(a["lon"] for a in ALL_AREAS[city] if a["name"] == area),
        )
        created = _rnd_date(30)
        reports.append({
            "report_id": f"RPT-{counter:05d}",
            "city": city,
            "area": area,
            "latitude": round(lat, 5),
            "longitude": round(lon, 5),
            "category": category,
            "severity": severity,
            "language": lang,
            "original_text": text,
            "translated_text": text if lang == "english" else f"[Translation] {text}",
            "status": random.choices(["OPEN", "ASSIGNED", "RESOLVED"], weights=[50, 30, 20])[0],
            "priority": {"CRITICAL": 9, "HIGH": 7, "MEDIUM": 5, "LOW": 3}[severity],
            "is_duplicate": False,
            "created_at": created,
        })
        counter += 1
    return reports


# ──────────────────────────────────────────────
# 7. Demo risk predictions (per scenario)
# ──────────────────────────────────────────────
def generate_risk_predictions(scenario="NORMAL"):
    predictions = []
    scenario_config = {
        "NORMAL":   {"multiplier": 1.0, "high_frac": 0.1, "crit_frac": 0.02},
        "HEAVY":    {"multiplier": 2.5, "high_frac": 0.35, "crit_frac": 0.15},
        "EXTREME":  {"multiplier": 5.0, "high_frac": 0.40, "crit_frac": 0.45},
        "CITIZEN_SURGE": {"multiplier": 2.0, "high_frac": 0.30, "crit_frac": 0.10},
        "EMERGENCY": {"multiplier": 4.5, "high_frac": 0.25, "crit_frac": 0.55},
    }
    cfg = scenario_config.get(scenario, scenario_config["NORMAL"])

    pred_counter = 1
    for city, areas in ALL_AREAS.items():
        for area in areas:
            r = random.random()
            if r < cfg["crit_frac"]:
                risk_score = random.uniform(76, 98)
                risk_level = "CRITICAL"
            elif r < cfg["crit_frac"] + cfg["high_frac"]:
                risk_score = random.uniform(51, 75)
                risk_level = "HIGH"
            elif r < 0.6:
                risk_score = random.uniform(26, 50)
                risk_level = "MEDIUM"
            else:
                risk_score = random.uniform(5, 25)
                risk_level = "LOW"

            lat, lon = _jitter(area["lat"], area["lon"])
            reasons = []
            if risk_score > 60:
                reasons.append("High rainfall intensity in last 3 hours")
            if risk_score > 70:
                reasons.append("Low drainage capacity in this zone")
            if risk_score > 50:
                reasons.append(f"Historical flooding frequency: {random.randint(2,8)} events/year")
            if area["density"] > 0.8:
                reasons.append("High road density — surface runoff risk")
            if random.random() > 0.5:
                reasons.append(f"{random.randint(5,45)} citizen reports in last 2 hours")

            action_map = {
                "CRITICAL": "Immediate deployment of emergency response. Evacuate low-lying areas.",
                "HIGH": "Deploy pump team. Inspect nearby drains. Issue public advisory.",
                "MEDIUM": "Monitor rainfall progression. Pre-position response team.",
                "LOW": "Continue monitoring. No immediate action required.",
            }
            predictions.append({
                "prediction_id": f"PRED-{pred_counter:04d}",
                "city": city,
                "area": area["name"],
                "latitude": round(lat, 5),
                "longitude": round(lon, 5),
                "risk_score": round(risk_score, 1),
                "risk_level": risk_level,
                "confidence": round(random.uniform(0.72, 0.97), 2),
                "predicted_time_window": "Next 0-3 hours",
                "main_reasons": reasons,
                "recommended_action": action_map[risk_level],
                "feature_importance": {
                    "rainfall_1h": round(random.uniform(0.25, 0.40), 3),
                    "drainage_capacity": round(random.uniform(0.15, 0.25), 3),
                    "historical_flood_freq": round(random.uniform(0.10, 0.20), 3),
                    "citizen_reports": round(random.uniform(0.08, 0.15), 3),
                    "elevation": round(random.uniform(0.05, 0.12), 3),
                },
                "scenario": scenario,
                "created_at": datetime.utcnow().isoformat(),
            })
            pred_counter += 1
    return predictions


# ──────────────────────────────────────────────
# Main seed writer
# ──────────────────────────────────────────────
def write_seed_data(output_dir: Path):
    output_dir.mkdir(parents=True, exist_ok=True)

    datasets = {
        "rainfall_normal.json":    generate_rainfall_data("NORMAL"),
        "rainfall_heavy.json":     generate_rainfall_data("HEAVY"),
        "rainfall_extreme.json":   generate_rainfall_data("EXTREME"),
        "drains.json":             generate_drains(),
        "flood_incidents.json":    generate_flood_incidents(),
        "ml_training_data.json":   generate_ml_training_data(5000),
        "citizen_reports.json":    generate_citizen_reports(200),
        "response_teams.json":     generate_response_teams(),
        "risk_normal.json":        generate_risk_predictions("NORMAL"),
        "risk_heavy.json":         generate_risk_predictions("HEAVY"),
        "risk_extreme.json":       generate_risk_predictions("EXTREME"),
        "risk_citizen_surge.json": generate_risk_predictions("CITIZEN_SURGE"),
        "risk_emergency.json":     generate_risk_predictions("EMERGENCY"),
    }

    for filename, data in datasets.items():
        path = output_dir / filename
        with open(path, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        print(f"  OK Written {len(data):>5} records -> {filename}")

    # Also write areas reference
    with open(output_dir / "areas.json", "w", encoding="utf-8") as f:
        json.dump(ALL_AREAS, f, ensure_ascii=False, indent=2)
    print(f"  OK Written areas reference -> areas.json")

    print(f"\n[DEMO DATA] All datasets written to {output_dir}")
    print("[NOTICE] This is synthetic demo data. It does not represent real government data.")


if __name__ == "__main__":
    import sys
    out = Path(sys.argv[1]) if len(sys.argv) > 1 else Path(__file__).parent.parent / "data"
    write_seed_data(out)
