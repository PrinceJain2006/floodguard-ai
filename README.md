# 🌊 FloodGuard AI

## AI-Assisted Urban Flood-Risk and Decision-Support System

FloodGuard AI is an **AI-assisted urban flood-risk and decision-support prototype** for Ahmedabad and Surat, Gujarat. It combines live weather data, ML flood-risk prediction, a multi-agent AI pipeline, IBM Granite reasoning, citizen intelligence, structured alerts, and human-in-the-loop decision support into a single operational workflow.

> **Technical honesty notice:** FloodGuard AI is a hackathon prototype and does not constitute an official municipal emergency system. All AI recommendations require authorized human verification before real-world implementation.

---

## ⚡ End-to-End Decision Workflow

```
DATA SOURCES
 🟢 Live Weather (Open-Meteo API — free, no key required)
 🟡 Water Level (rainfall-derived estimate — no live sensor available)
 🟠 Drainage (configured demo infrastructure data)
 USER Citizen Reports (real user-submitted + demo seed data)
        │
        ▼
 ML FLOOD-RISK PREDICTION  (Random Forest — 5,000 SYNTHETIC training samples)
 🟡 SYNTHETIC VALIDATION — not real government sensor data
        │
        ▼
 MULTI-AGENT ANALYSIS PIPELINE
 Flood Risk Agent
     → Drainage Agent
         → Citizen Report Agent
             → Damage Assessment Agent  ← properly integrated
                 → Response Coordination Agent
        │
        ▼
 IBM GRANITE REASONING (ibm/granite-4-h-small via WatsonX API)
 🟢 LIVE when WATSONX_API_KEY configured | 🟡 Rule-based FALLBACK otherwise
        │
        ▼
 CHIEF RESPONSE AGENT  →  FLOOD ALERT ENGINE
        │                      │
        ▼                      ▼
 EVIDENCE FUSION          STRUCTURED ALERTS
 (Prototype weights)      Expected Risk Window
        │                      │
        ▼                      ▼
 ZONE PRIORITIZATION   NOTIFICATION DISPATCH
 WHY THIS ZONE         (Email / SMS / Webhook)
        │
        ▼
 HUMAN APPROVAL  (Approve / Modify / Reject)
        │
        ▼
 CIVIC ACTION LOG + AUDIT TRAIL + SQLite PERSISTENCE
```

---

## 🖥️ Application Pages (9 Modules)

| Page | Module | Key Features |
|------|---------|-------------|
| Landing | FloodGuard AI Hub | 9-page portal · 7-agent architecture · IBM Granite status |
| 1 | Citizen Portal | EN/हिं/ગુ multilingual reporting · Zone risk context |
| 2 | Command Center | Live map · Active alerts panel · Data source strip |
| 3 | Agent Monitor | INPUT→PROCESS→OUTPUT per agent · Pipeline execution log · NL query |
| 4 | Analytics & ML | Risk trends · Model metadata · Synthetic validation notice · Confusion matrix |
| 5 | Emergency War Room | HITL approve/modify/reject · Civic Action Log · Granite WHY |
| 6 | Flood Simulator | BEFORE/AFTER what-if · Scenario sliders · **Clearly labelled SIMULATION** |
| 7 | Learning Loop | **Prediction-to-outcome feedback tracking** (not automated retraining) |
| 8 | Decision Intelligence | Evidence fusion · Why This Zone/Why Now · Agent trace · Audit trail |
| 9 | Alert History | Alert database · Notification status · HITL controls · Test alerts |

---

## 🤖 6-Agent AI Architecture (Updated Pipeline)

```
📡 DATA SOURCES
    → 🌊 Flood Risk Agent      (ML prediction per zone)
    → 🔧 Drainage Agent        (drain maintenance priority)
    → 📱 Citizen Report Agent  (multilingual NLP)
    → 🔍 Damage Assessment Agent  ← NOW PROPERLY INTEGRATED
    → ⚡ Response Coord Agent  (incident response plan)
    → 🧠 IBM Granite           (AI reasoning layer)
    → 🎯 Chief Response Agent  (unified action plan)
    → 👤 HUMAN APPROVAL
    → ✅ ALERT + RESPONSE
```

| Agent | Responsibility | Data Type |
|-------|---------------|-----------|
| **Flood Risk Agent** | Random Forest ML prediction per zone | ML prediction |
| **Drainage Agent** | Drain maintenance priority scoring | Rule-based domain logic |
| **Citizen Report Agent** | Multilingual NLP classification | Agent orchestration |
| **Damage Assessment Agent** | Post-event damage scoring | AI-assisted + rule-based |
| **Response Coord Agent** | Incident response plan + resource recommendations | Agent orchestration |
| **IBM Granite** | Situation summary · risk explanation · recommendations | AI reasoning |
| **Chief Response Agent** | Unified emergency action plan (requires human approval) | Orchestration |

---

## 📡 Data Sources & Status

| Source | Status | Description |
|--------|--------|-------------|
| **Open-Meteo** | 🟢 LIVE (no API key required) | Live weather/rainfall for 10 Gujarat cities |
| **Water Level** | 🟡 ESTIMATED | Rainfall-derived proxy — no live sensor available for AHM/SRT |
| **Drainage** | 🟠 STATIC/DEMO | Configured demo infrastructure data |
| **Citizen Reports** | 🟢 REAL (user) + 🟡 DEMO (seed) | Real user submissions + labelled demo data |
| **ML Model** | 🟡 SYNTHETIC VALIDATION | Trained on 5,000 synthetic samples |
| **IBM Granite** | 🟢 LIVE / 🟡 FALLBACK | Live when WatsonX credentials configured |
| **Database** | 🟢 SQLite | Persistent storage for alerts, predictions, feedback |

---

## 🚨 Flood Alert Engine

The Flood Alert Engine combines all evidence sources into structured alerts:

- **Risk levels**: GREEN / YELLOW / ORANGE / RED
- **Expected flood-risk window**: heuristic estimate (NOT a precise hydrological prediction)
- **De-duplication**: 30-minute cooldown per location/level
- **Evidence fusion weights**: labelled as PROTOTYPE — not calibrated with real historical data
- **Notifications**: Email / SMS (Twilio) / Webhook — all require explicit configuration

### Alert wording discipline
- ✅ "Expected flood-risk window: 14:00–17:00 IST"
- ❌ ~~"Flood will definitely occur at 3 PM"~~
- ✅ "Alert generated — notification dispatched to configured channels"
- ❌ ~~"Government authorities have been alerted"~~ (unless authorized integration exists)

---

## 🔧 Environment Variables

Copy `.env.example` to `.env` and configure:

### Required (for IBM Granite)
```
WATSONX_API_KEY=your_api_key
WATSONX_PROJECT_ID=your_project_id
WATSONX_URL=https://us-south.ml.cloud.ibm.com
```

### Optional — Notifications
```
# Email (SMTP)
EMAIL_ENABLED=true
SMTP_HOST=smtp.gmail.com
SMTP_PORT=587
SMTP_USERNAME=your_email@gmail.com
SMTP_PASSWORD=your_app_password
ALERT_RECIPIENTS=ops@example.com,manager@example.com

# SMS (Twilio)
SMS_ENABLED=true
SMS_PROVIDER=twilio
SMS_API_KEY=your_twilio_account_sid
SMS_API_SECRET=your_twilio_auth_token
SMS_SENDER=+1xxxxxxxxxx
SMS_RECIPIENTS=+91xxxxxxxxxx

# Webhook
WEBHOOK_ENABLED=true
WEBHOOK_URL=https://your-system.example.com/flood-alert

# Test mode (demo only — never in production)
TEST_NOTIFICATION_MODE=false
```

### Weather & Alerts
```
DEMO_MODE=true          # Set false to use live weather
LIVE_WEATHER_ENABLED=true
ALERT_THRESHOLD_RED=75  # Risk score threshold for RED alert
ALERT_COOLDOWN_SECONDS=1800
```

---

## 🚀 Running Locally

```bash
cd floodguard-ai
pip install -r requirements.txt
cp .env.example .env
# Edit .env with your credentials
streamlit run app.py
```

### On Streamlit Cloud
Set secrets via App settings → Secrets (same keys as .env).

---

## 🏗️ Architecture

```
floodguard-ai/
├── app.py                          # Landing page + navigation
├── pages/
│   ├── 1_citizen_portal.py         # Multilingual citizen reporting
│   ├── 2_command_center.py         # Live command center + alerts
│   ├── 3_agent_monitor.py          # Agent pipeline monitor
│   ├── 4_analytics.py              # Analytics + ML evaluation
│   ├── 5_war_room.py               # Emergency war room (HITL)
│   ├── 6_simulator.py              # What-if scenario simulator
│   ├── 7_learning_loop.py          # Prediction-to-outcome feedback
│   ├── 8_decision_intelligence.py  # Evidence fusion + explainability
│   └── 9_alert_history.py          # Alert history + notifications
├── agents/
│   ├── orchestrator.py             # 11-step multi-agent pipeline
│   ├── flood_risk_agent.py         # Agent 1: ML flood prediction
│   ├── drainage_agent.py           # Agent 2: drainage prioritization
│   ├── citizen_report_agent.py     # Agent 3: NLP report analysis
│   ├── damage_assessment_agent.py  # Agent 4: damage scoring (now in pipeline)
│   ├── response_coordination_agent.py # Agent 5: response planning
│   ├── chief_response_agent.py     # Agent 6: unified action plan
│   ├── granite_service.py          # IBM Granite / WatsonX integration
│   ├── evidence_fusion.py          # Decision intelligence layer
│   └── closed_loop_learning.py     # Prediction-outcome feedback
├── services/
│   ├── live_weather.py             # Open-Meteo API client
│   ├── live_data_manager.py        # Live data cache + fallback
│   ├── water_level_service.py      # Water level abstraction (NEW)
│   ├── flood_alert_engine.py       # Alert generation + dedup (NEW)
│   ├── notification_service.py     # Email/SMS/Webhook dispatch (NEW)
│   ├── database.py                 # SQLite persistence layer (NEW)
│   ├── health_check.py             # System observability (NEW)
│   ├── report_store.py             # Citizen report persistence
│   └── weather_dashboard.py        # Weather UI components
├── ml/
│   ├── flood_risk_model.py         # Random Forest model
│   └── models/                     # Serialised model files
├── data/
│   ├── seed_generator.py           # Synthetic demo data
│   ├── user_reports.json           # Persisted citizen reports
│   └── *.json                      # Demo scenario data
├── backend/
│   └── config.py                   # Credential resolution (env/secrets)
├── frontend/
│   ├── ui_utils.py                 # UI components + styling
│   └── map_component.py            # Folium map builder
├── .env.example                    # All env vars documented
├── .gitignore                      # Protects .env + secrets
└── requirements.txt
```

---

## 🔬 ML Model Details

| Attribute | Value |
|-----------|-------|
| Algorithm | Random Forest (classifier + regressor) |
| Training data | **5,000 SYNTHETIC samples** (not real sensor data) |
| Validation | **Synthetic validation only** |
| Features | 10 (rainfall, drainage, water level, elevation, historical frequency, citizen reports) |
| Classes | LOW / MEDIUM / HIGH / CRITICAL |
| Status | DEMO — must be retrained on verified historical data for operational use |

**⚠️ Do NOT claim real-world accuracy from synthetic test metrics.**

---

## ⚖️ Evidence Fusion Weights (Prototype)

```
ML Risk Score:            35%  ← Random Forest prediction
Rainfall Intensity:       20%  ← Current/forecast rainfall
Water Level Stress:       15%  ← River/channel level
Drainage Stress:          15%  ← Capacity/blockage
Citizen Report Signals:   10%  ← Report volume & severity
Historical Vulnerability:  5%  ← Historical flood frequency
```

**⚠️ These are PROTOTYPE weights** — not scientifically calibrated with real historical data.

---

## 📋 Known Limitations

1. **Water level**: No live river/drainage sensor API available for Ahmedabad/Surat. Values are rainfall-derived estimates.
2. **ML model**: Trained on synthetic data. Real-world accuracy is unknown until verified historical data is used.
3. **Evidence fusion weights**: Prototype values — require calibration with historical flood data.
4. **Risk window timing**: Heuristic estimate only. Not a physically accurate hydrological/hydraulic model.
5. **Drainage data**: Demo infrastructure data, not real municipal sensor readings.
6. **No government integration**: System generates alerts but does NOT contact emergency services unless an authorized integration is explicitly configured.
7. **Database persistence**: SQLite — ephemeral on Streamlit Cloud between deployments.

---

## 🔮 Future Scope

- [ ] Connect to CWC (Central Water Commission) official flood forecasts when API access is available
- [ ] Integrate GloFAS river discharge forecasts for major rivers
- [ ] Retrain ML model on verified IMD/AMC/SMC historical flood data
- [ ] Calibrate evidence fusion weights with historical flood outcomes
- [ ] Replace drainage demo data with actual municipal infrastructure data
- [ ] Integrate authorized government notification systems
- [ ] Add IoT sensor feed support in `water_level_service.py`
- [ ] PostgreSQL / Supabase for production persistence
- [ ] Hydraulic model integration for physically accurate flood timing

---

## 🔐 Security

- All credentials stored in `.env` / Streamlit secrets — never in code
- `.env` is in `.gitignore` — never committed
- No hard-coded API keys, tokens, or passwords in source code
- Notification credentials fetched at call-time (not module-level cached)

---

*FloodGuard AI is an AI-assisted urban flood-risk and decision-support prototype. It does not constitute an official government emergency management system. All recommendations require human verification.*
