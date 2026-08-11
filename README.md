# FloodGuard AI 🌊
## Agentic AI for Predictive Urban Flood Management & Rapid Civic Response

> **Ahmedabad & Surat, Gujarat, India**  
> Built for the IBM Hackathon | Powered by IBM Granite + WatsonX

---

## ⚠️ Important Notice

> **DEMO/SIMULATED DATA** — FloodGuard AI uses synthetic datasets representing plausible flood scenarios for Ahmedabad and Surat. All data, predictions, and recommendations are for demonstration purposes only and do not represent real government operational data or guarantee actual flood prediction accuracy. AI recommendations require authorized human verification before any real-world implementation.

---

## Problem Statement

Urban flooding in Ahmedabad and Surat causes severe disruption annually. The Sabarmati River and Tapi River basins, combined with rapid urbanization, inadequate drainage infrastructure, and monsoon-intensity rainfall (often >100mm/hr), result in:

- **Loss of life and property** in low-lying areas (Maninagar, Vatva, Katargam, Udhna)
- **Traffic paralysis** for hours/days
- **Delayed emergency response** due to fragmented information
- **Overwhelmed drainage systems** leading to sewage overflow
- **Lack of real-time actionable intelligence** for municipal officers

**Current Gap:** Municipal teams operate reactively, with no unified system to predict, prioritize, and coordinate flood response before crises escalate.

---

## Solution

**FloodGuard AI** is an Agentic AI platform that:

1. **Predicts** flood risk per area using ML (Random Forest)
2. **Prioritizes** drainage maintenance automatically
3. **Processes** citizen reports in 3 languages (English, Hindi, Gujarati)
4. **Coordinates** emergency response with AI-generated action plans
5. **Explains** every recommendation using IBM Granite LLM
6. **Displays** everything on a real-time command-center dashboard

---

## Agent Architecture

```
DATA SOURCES
├── Rainfall (1h/3h/6h/24h) — Demo/Synthetic
├── Drainage Infrastructure
├── Historical Flood Incidents
├── Citizen Reports (EN/HI/GU)
└── Response Team Status
        ↓
AGENT ORCHESTRATOR
├── 🌊 Flood Risk Agent      → ML (Random Forest) flood risk scores
├── 🔧 Drainage Agent        → Maintenance priority queue
├── 📱 Citizen Report Agent  → Multilingual NLP classification
├── ⚡ Response Coord Agent   → Priority incident response plan
├── 📊 Dashboard Agent       → Real-time command center view
└── 🔍 Damage Agent          → Post-flood infrastructure assessment
        ↓
🧠 IBM Granite (WatsonX)
    ├── Multilingual report understanding
    ├── Incident classification
    ├── Situation report generation
    ├── Recommendation explanation
    └── Natural language queries
        ↓
AI RECOMMENDATIONS → HUMAN APPROVAL → ACTION LOGGED
        ↓
DASHBOARD + ALERTS + SITUATION REPORT
```

### Agent Descriptions

| Agent | Role | Technology |
|-------|------|-----------|
| **Flood Risk Agent** | Calculates per-area flood risk score (0-100) + level | Random Forest + rule fallback |
| **Drainage Agent** | Scores all drains, generates maintenance priority queue | Domain scoring algorithm |
| **Citizen Report Agent** | Classifies EN/HI/GU reports, detects duplicates, routes to teams | Granite NLP + rule fallback |
| **Response Coordination Agent** | Generates ranked incident response plans with approval gates | Priority queue + Granite |
| **Dashboard Agent** | Aggregates all agent outputs for command center display | Streamlit + Folium |
| **Damage Assessment Agent** | Classifies post-flood damage, generates preliminary reports | Granite + domain logic |

---

## IBM Granite Integration

Granite (`ibm/granite-3-8b-instruct`) via WatsonX is used for:

| Feature | Granite Role |
|---------|-------------|
| Citizen report understanding | Classify category, severity, extract location from EN/HI/GU text |
| Incident classification | Structured JSON extraction from unstructured reports |
| Situation report generation | Generate official-style flood situation reports |
| Recommendation explanation | Explain why each AI action was recommended |
| Natural language queries | Answer questions grounded in application data |
| Damage assessment | Classify post-flood infrastructure damage |

**Fallback:** All Granite features have rule-based fallbacks. The app works fully without a WatsonX API key (Demo Mode).

---

## IBM Cloud Architecture

```
IBM Cloud
├── WatsonX AI (Granite-3-8b-instruct)
│   └── Text generation API endpoint
├── Optional: IBM Event Streams (Kafka) for real-time IoT data
├── Optional: IBM Db2 (replace SQLite for production)
└── Optional: IBM Cloud Object Storage (for citizen images)

Local / App Deployment
├── Streamlit Frontend (app.py)
├── FastAPI Backend (backend/api.py)
├── SQLite Database (demo mode)
└── Agent Orchestrator
```

---

## Machine Learning Model

**Algorithm:** Random Forest (sklearn) — Classifier + Regressor

**Features:**
| Feature | Description |
|---------|-------------|
| `rainfall_1h` | 1-hour rainfall intensity (mm/hr) |
| `rainfall_3h` | 3-hour cumulative rainfall |
| `rainfall_6h` | 6-hour cumulative rainfall |
| `rainfall_24h` | 24-hour cumulative rainfall |
| `drainage_capacity` | Drainage system capacity rating (0-100%) |
| `historical_flood_freq` | Historical flooding events/year |
| `water_level` | Current water level (m) |
| `elevation` | Area elevation (m above MSL) |
| `road_density` | Road surface density (0-1) |
| `citizen_reports` | Recent citizen flood reports count |

**Output:** 
- `risk_score` (0-100 continuous)
- `risk_level` (LOW / MEDIUM / HIGH / CRITICAL)
- `confidence` (0-1)
- `feature_importance` dict

**Training:** 5,000 synthetic samples generated from domain-informed rules.  
**Architecture:** Plug-and-replace design — replace `ml/models/` with real trained models without code changes.

---

## Database Schema

| Table | Purpose |
|-------|---------|
| `users` | User accounts (citizen / operator / admin) |
| `citizen_reports` | Multilingual flood reports |
| `rainfall_data` | Rainfall readings per area |
| `flood_incidents` | Active and historical flood incidents |
| `drains` | Drainage infrastructure registry |
| `risk_predictions` | ML model output per area |
| `response_teams` | Team roster and availability |
| `alerts` | Generated alerts (citizen/operator/emergency) |
| `ai_recommendations` | AI recommendations with approval tracking |
| `damage_reports` | Post-disaster damage assessments |
| `audit_logs` | All system actions for accountability |

---

## API Documentation

### Base URL
```
http://localhost:8000
```

### Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| `GET` | `/` | API info |
| `GET` | `/health` | System health + Granite status |
| `POST` | `/auth/login` | Login (returns JWT) |
| `GET` | `/auth/me` | Current user info |
| `POST` | `/scenario/trigger` | Trigger demo scenario |
| `GET` | `/dashboard` | Full dashboard state |
| `GET` | `/flood-risk` | Risk predictions (filter by city/level) |
| `GET` | `/drains` | Drainage data (filter by city/priority) |
| `GET` | `/incidents` | Active incidents |
| `POST` | `/reports` | Submit citizen report |
| `GET` | `/reports` | Get reports (filter by city/status/severity) |
| `GET` | `/alerts` | Active alerts |
| `GET` | `/recommendations` | AI recommendations |
| `POST` | `/recommendations/{id}/approve` | Approve recommendation |
| `POST` | `/recommendations/{id}/reject` | Reject recommendation |
| `GET` | `/agents/status` | All agent statuses + pipeline log |
| `POST` | `/agent/analyze` | Natural language query |
| `POST` | `/damage/assess` | Post-flood damage assessment |

---

## Project Structure

```
floodguard/
├── app.py                          # Streamlit landing page
├── requirements.txt
├── .env.example                    # Environment variables template
│
├── pages/
│   ├── 1_citizen_portal.py        # Citizen flood report portal
│   ├── 2_command_center.py        # Municipal command center
│   ├── 3_agent_monitor.py         # AI agent activity monitor
│   └── 4_analytics.py             # Analytics & impact dashboard
│
├── agents/
│   ├── orchestrator.py            # Central agent orchestrator
│   ├── flood_risk_agent.py        # Agent 1: Flood risk prediction
│   ├── drainage_agent.py          # Agent 2: Drainage prioritization
│   ├── citizen_report_agent.py    # Agent 3: Report processing
│   ├── response_coordination_agent.py  # Agent 4: Response coordination
│   ├── damage_assessment_agent.py  # Agent 6: Post-disaster damage
│   └── granite_service.py         # IBM Granite integration
│
├── ml/
│   ├── flood_risk_model.py        # Random Forest ML model
│   └── models/                    # Saved model files (.pkl)
│
├── backend/
│   ├── api.py                     # FastAPI REST API
│   ├── config.py                  # Configuration management
│   └── models/
│       └── database.py            # SQLAlchemy DB models
│
├── frontend/
│   ├── ui_utils.py                # Streamlit UI components + CSS
│   ├── map_component.py           # Folium interactive map
│   └── auth.py                    # Authentication utilities
│
├── data/
│   ├── seed_generator.py          # Synthetic data generator
│   └── *.json                     # Generated seed datasets
│
└── tests/
    ├── conftest.py
    └── test_floodguard.py         # Comprehensive test suite
```

---

## Setup Instructions

### Prerequisites
- Python 3.11+
- pip

### 1. Clone / Navigate to Project

```bash
cd floodguard
```

### 2. Create Virtual Environment

```bash
python -m venv venv
# Windows:
venv\Scripts\activate
# Linux/Mac:
source venv/bin/activate
```

### 3. Install Dependencies

```bash
pip install -r requirements.txt
```

### 4. Configure Environment Variables

```bash
copy .env.example .env
```

Edit `.env` — for demo mode, no changes needed.  
For live IBM Granite: set `WATSONX_API_KEY` and `WATSONX_PROJECT_ID`.

### 5. Generate Demo Data + Train ML Model

```bash
# Generate synthetic datasets
python data/seed_generator.py

# Train the ML model
python ml/flood_risk_model.py
```

### 6. Run the Application

**Option A: Streamlit only (recommended for demo)**
```bash
streamlit run app.py
```

**Option B: With backend API**
```bash
# Terminal 1 — Backend
uvicorn backend.api:app --reload --port 8000

# Terminal 2 — Frontend
streamlit run app.py
```

### 7. Open in Browser
- Streamlit: `http://localhost:8501`
- API docs: `http://localhost:8000/docs`

---

## Environment Variables

| Variable | Required | Description |
|----------|----------|-------------|
| `WATSONX_API_KEY` | For Granite | IBM WatsonX API key |
| `WATSONX_PROJECT_ID` | For Granite | WatsonX project ID |
| `WATSONX_URL` | No | WatsonX endpoint (default: us-south) |
| `JWT_SECRET_KEY` | Prod only | JWT signing secret |
| `DATABASE_URL` | No | SQLAlchemy DB URL (default: SQLite) |
| `BACKEND_URL` | No | FastAPI backend URL |
| `DEMO_MODE` | No | Force demo data mode (default: true) |

---

## Demo Instructions

See [DEMO_SCRIPT.md](DEMO_SCRIPT.md) for the full 3-minute demo walkthrough.

**Quick demo:**
1. `streamlit run app.py`
2. Click **Municipal Command Center**
3. Click **"⛈️ Extreme Rainfall"** in the sidebar
4. Watch agents activate and risk map update
5. Go to **AI Recommendations** tab → approve/reject actions
6. Go to **AI Agent Monitor** → view pipeline execution
7. Use **Natural Language Command Center** to query the system

---

## Testing

```bash
# Run all tests
pytest tests/test_floodguard.py -v

# Run end-to-end demo test
pytest tests/test_floodguard.py::TestEndToEndDemo -v -s

# Run specific test class
pytest tests/test_floodguard.py::TestCitizenReportAgent -v
```

---

## Demo Credentials

| Role | Username | Password | Access |
|------|----------|----------|--------|
| Citizen | `citizen` | `citizen123` | Report submission, local alerts |
| Operator | `operator` | `operator123` | Command center, approvals |
| Admin | `admin` | `admin123` | Full access, audit logs |

---

## Limitations

1. **Synthetic data only** — Real deployment requires integration with IMD weather APIs, municipal IoT sensors, and official drainage GIS data
2. **Demo ML model** — Trained on synthetic data; production model requires real historical flood data from CWC/IMD
3. **Simulated alerts** — Alert notifications are displayed in-app; real deployment requires SMS/push notification integration
4. **No persistent storage** — Demo uses in-memory state; production requires configured database
5. **Granite fallback** — Without WatsonX credentials, rule-based NLP is used (still functional)
6. **Map accuracy** — Coordinates are approximate; real deployment requires accurate GIS data from AMC/SMC

---

## Future Improvements

1. **Real IoT integration** — Connect to actual river gauges, rain gauges, CCTV
2. **Mobile app** — Native Android/iOS citizen app with offline capability
3. **Multi-city expansion** — Vadodara, Rajkot, other Gujarat cities
4. **Advanced ML** — LSTM for rainfall time series, satellite imagery analysis
5. **WhatsApp integration** — Citizen reports via WhatsApp in Gujarati
6. **SMS alerts** — Real emergency SMS via BSNL/SMS gateway
7. **GIS integration** — Official AMC/SMC drainage and road network data
8. **Dashboard language support** — Full UI in Gujarati and Hindi

---

## Social Impact

| Metric | Potential Impact |
|--------|-----------------|
| Response time | ~35-45% faster through proactive prioritization |
| Drain maintenance | Pre-emptive vs reactive → fewer blockages during events |
| Citizen coordination | Multilingual reporting reduces underreporting |
| Officer decision-making | AI explanation → confident, informed decisions |
| Lives protected | Early warning for CRITICAL zones enables evacuation |

*All impact estimates are projections based on similar smart city flood management implementations globally.*

---

## Acknowledgments

- IBM WatsonX team for Granite LLM access
- Ahmedabad Municipal Corporation (AMC) and Surat Municipal Corporation (SMC) for publicly available urban data references
- OpenStreetMap contributors for geographic reference data

---

*FloodGuard AI v1.0 | Built for IBM Hackathon | © 2024*
