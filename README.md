# 🌊 FloodGuard AI

## AI-Powered Urban Flood Intelligence & Decision Support System

FloodGuard AI is an **agentic AI platform** for urban flood emergency management, built for Ahmedabad and Surat, Gujarat.
It combines ML flood-risk prediction, multi-agent analysis, IBM Granite reasoning, citizen intelligence, geospatial mapping, evidence fusion, and human-in-the-loop decision support into a single operational workflow.

> **FloodGuard AI doesn't just predict flooding — it converts prediction + citizen reports + drainage intelligence into prioritized, explainable, human-approved civic actions.**

---

## ⚡ End-to-End Decision Workflow

```text
DATA SOURCES
 Live Weather (Open-Meteo) · Citizen Reports · Drainage · Incidents
        │
        ▼
 ML FLOOD-RISK PREDICTION  (Random Forest — 5,000 synthetic training samples)
        │
        ▼
 MULTI-AGENT ANALYSIS
 Flood Risk Agent → Drainage Agent → Citizen Report Agent → Response Coord Agent
        │
        ▼
 IBM GRANITE REASONING (ibm/granite-4-h-small via WatsonX API)
        │
        ▼
 EVIDENCE FUSION  (ML 35% · Rainfall 20% · Drainage 18% · Reports 12% · History 10% · Water Level 5%)
        │
        ▼
 ZONE PRIORITIZATION  +  WHY THIS ZONE / WHY NOW
        │
        ▼
 AI RECOMMENDATION
        │
        ▼
 HUMAN APPROVAL  (APPROVE / MODIFY / REJECT with modification notes)
        │
        ▼
 CIVIC ACTION LOG  +  AUDIT TRAIL
```

---

## 🖥️ Application Pages (8 Modules)

| Page | Module | Key Features |
|------|---------|-------------|
| Landing | FloodGuard AI Hub | 8-page portal · 6-agent architecture visualization · IBM Granite status |
| 1 | Citizen Portal | EN/हिं/ગુ multilingual reporting · 7-step pipeline · Zone risk context |
| 2 | Command Center | Live map · ACTIVE FLOOD EVENT header · Zone risk cards · Data source strip |
| 3 | Agent Monitor | INPUT→PROCESS→OUTPUT per agent · Pipeline execution log · NL query |
| 4 | Analytics & ML | Risk trends · Confusion matrix · Feature importance · Scenario comparison |
| 5 | Emergency War Room | HITL approve/modify/reject · Civic Action Log · Granite WHY |
| 6 | Flood Simulator | BEFORE/AFTER scenario · What-if sliders · Drainage simulation · Forecast |
| 7 | Learning Loop | Prediction vs outcome · Accuracy tracking · Closed-loop feedback |
| 8 | Decision Intelligence | Evidence fusion · Why This Zone/Why Now · Agent trace · Audit trail |

---

## 🤖 6-Agent Architecture

```text
📡 DATA SOURCES → 🌊 Flood Risk Agent → 🔧 Drainage Agent → 📱 Citizen Report Agent
→ ⚡ Response Coord Agent → 🧠 IBM Granite → 🎯 Chief Response Agent → 👤 HUMAN APPROVAL
```

### Agent Details

| Agent | Responsibility |
|-------|---------------|
| **Flood Risk Agent** | Random Forest ML prediction per zone — 10 input features |
| **Drainage Agent** | Drain maintenance priority scoring using actual DrainageAgent formula |
| **Citizen Report Agent** | Multilingual NLP classification of citizen-submitted flood reports |
| **Response Coord Agent** | Incident response plan + resource recommendations |
| **Chief Response Agent** | Unified emergency action plan requiring human approval |
| **Damage Assessment Agent** | Post-event damage scoring and assessment |

---

## 🧠 Machine Learning

**Model:** Random Forest (classifier + regressor)  
**Training data:** 5,000 synthetic samples (realistic Gujarat flood parameter distributions)  
**Features (10):** rainfall_1h, rainfall_3h, rainfall_6h, rainfall_24h, drainage_capacity, historical_flood_freq, water_level, elevation, road_density, citizen_reports  
**Classes:** LOW / MEDIUM / HIGH / CRITICAL  
**Artifacts:** Saved to `ml/models/` (classifier.pkl, regressor.pkl)

All ML metrics (accuracy, precision, recall, F1, confusion matrix, feature importance) are **computed from the actual model on a real 20% held-out test split** — never hard-coded.

> **Data transparency:** Training data is synthetic — not real government sensor measurements. Clearly disclosed throughout the application.

---

## 🔍 Evidence Fusion & Explainability

FloodGuard AI fuses evidence from all agents before producing priority scores:

| Evidence Source | Weight | Data Status |
|----------------|--------|-------------|
| ML Risk Score | 35% | 🔵 MODEL |
| Rainfall Intensity | 20% | 🟢 LIVE (Open-Meteo) or 🟡 DEMO |
| Drainage Status | 18% | 🟡 DEMO |
| Citizen Reports | 12% | 🟠 USER SUBMITTED or 🟡 DEMO |
| Historical Vulnerability | 10% | 🟡 DEMO |
| Water Level Proxy | 5% | 🟡 DEMO |

The **WHY THIS ZONE** explanation shows actual evidence values, ML feature importances, and significant fused factors with source badges (LIVE/DEMO/MODEL).

The **WHY NOW** comparison shows score deltas between scenarios with urgency flags.

---

## 🔐 Human-in-the-Loop

Every AI recommendation requiring intervention goes through human review:

```text
AI Recommendation (priority_level + urgency)
        ↓
Human Decision  →  APPROVE / MODIFY / REJECT
        ↓        ↑
Modification note (optional)
        ↓
Application state updated
        ↓
Civic Action Log entry
        ↓
Audit Trail record
```

HITL is available in both the **Emergency War Room** (quick approval panel) and **Decision Intelligence** (full approval workflow). Both write to the **same shared audit trail** (`agents/evidence_fusion.py` → `get_audit_trail()`).

> AI approval buttons update application state only — no real emergency services are contacted.

---

## ☁️ IBM Granite Integration

**Model:** `ibm/granite-4-h-small` via WatsonX API (`us-south.ml.cloud.ibm.com`)  
**Configure:** Set `WATSONX_API_KEY` + `WATSONX_PROJECT_ID` in `.env`

The Granite layer provides:
- Situation report generation
- WHY this zone is risky explanations  
- Incident classification
- Natural language Q&A over application data

**Status transparency:**
- 🟢 **IBM GRANITE — LIVE**: Real WatsonX generation confirmed
- ⚠️ **RATE LIMITED**: 429 backoff active — credentials valid  
- 🟡 **GRANITE FALLBACK**: Rule-based responses (WatsonX inactive/unavailable)

Fallback output is **never** presented as Granite-generated. The application remains fully functional without Granite.

---

## 🌐 Live Data

| Source | API | Status |
|--------|-----|--------|
| Weather | Open-Meteo (open-meteo.com) | 🟢 LIVE when reachable |
| Rainfall blend | Live values overlaid on synthetic for NORMAL scenario | 🟢 LIVE → 🟡 DEMO fallback |
| Drainage assets | Synthetic seed data | 🟡 DEMO |
| Response teams | Synthetic seed data | 🟡 DEMO |
| Citizen reports | User-submitted via portal + demo seed | 🟠 USER + 🟡 DEMO |

---

## 🌧️ Flood Scenario Simulator

The simulator supports five scenarios:

| Scenario | Rainfall Multiplier | Use |
|----------|--------------------|----|
| Normal Rain | 1.0× | Baseline monitoring |
| Heavy Rainfall | 2.5× | Elevated risk |
| Extreme Rainfall | 5.0× | CRITICAL zones |
| Citizen Surge | 2.0× | High report volume |
| Emergency Response | 4.5× | Maximum deployment |

For each scenario, the app shows:
- **BEFORE** state snapshot
- **SCENARIO** applied
- **AFTER** state: critical/high zones, drains, reports, teams
- Agent analysis outputs  
- Granite situation report (LIVE or FALLBACK badge)
- **SIMULATION MODE** label

The **Drainage Simulation** tab uses the real `DrainageAgent.score_drain()` formula for both before and after scores — no hard-coded improvement values.

---

## 📱 Citizen Pipeline

```text
Citizen Report  (EN / हिं / ગુ)
        ↓
VALIDATE (format + severity check)
        ↓
CLASSIFY (NLP category + priority)
        ↓
IBM GRANITE / FALLBACK (analysis)
        ↓
EVIDENCE FUSION (zone risk updated)
        ↓
ZONE RISK UPDATE (ML pipeline re-incorporates report count)
        ↓
COMMAND CENTER (operator notified)
```

---

## 🗺️ Geospatial Intelligence

Interactive Folium map in Command Center:
- Colour-coded risk zones (CRITICAL/HIGH/MEDIUM/LOW)
- Live weather overlay points (when Open-Meteo is active)
- Drainage asset markers
- Citizen report locations

---

## 📊 Analytics & ML Evaluation

**Tab 1 — Risk Trends:** Horizontal bar chart by zone, risk level distribution donut, simulated risk trend

**Tab 2 — Rainfall Analysis:** City-level rainfall comparison, zone-level breakdown

**Tab 3 — Report Analytics:** Report category distribution, resolution rates

**Tab 4 — Damage Assessment:** Incident severity, damage cost estimates

**Tab 5 — Scenario Comparison:** Simulated reference bars + live pipeline annotation

**Tab 6 — ML Model & Explainability:**
- Accuracy, Precision, Recall, F1, MAE, 3-fold CV — all computed from real model
- Per-class performance table
- Normalized confusion matrix heatmap
- Feature importance bar chart (Gini impurity from Random Forest)
- Zone-level feature value vs importance visualization
- Class probability bars (predict_proba output)

---

## 🔄 Closed-Loop Learning

Tracks prediction → incident → response → outcome for each zone:
- Predicted vs actual risk score scatter plot
- Outcome distribution (RESOLVED / MITIGATED / ONGOING / ESCALATED / FALSE_ALARM)
- Accuracy by risk level (CRITICAL / HIGH / MEDIUM / LOW)
- Score delta (prediction error) distribution
- Average response time by outcome

> Data is demo/simulated for the hackathon environment.

---

## 🏗️ Project Structure

```text
floodguard-ai/
├── app.py                          # Landing page (Streamlit entry point)
├── pages/
│   ├── 1_citizen_portal.py         # Citizen flood reporting
│   ├── 2_command_center.py         # Main command dashboard + live map
│   ├── 3_agent_monitor.py          # Agent pipeline monitor + NL query + pipeline log
│   ├── 4_analytics.py              # Analytics + ML evaluation
│   ├── 5_war_room.py               # Emergency HITL + Civic Action Log
│   ├── 6_simulator.py              # Scenario simulator + drainage before/after
│   ├── 7_learning_loop.py          # Prediction vs outcome tracking
│   └── 8_decision_intelligence.py  # Evidence fusion + WHY + audit trail
├── agents/
│   ├── orchestrator.py             # Central pipeline coordinator
│   ├── flood_risk_agent.py         # ML flood risk per zone
│   ├── drainage_agent.py           # Drain scoring + maintenance priority
│   ├── citizen_report_agent.py     # NLP report classification
│   ├── response_coordination_agent.py  # Response plan generation
│   ├── chief_response_agent.py     # Unified emergency action plan
│   ├── damage_assessment_agent.py  # Post-event damage scoring
│   ├── evidence_fusion.py          # Evidence fusion + audit trail
│   ├── granite_service.py          # IBM Granite / WatsonX integration
│   └── closed_loop_learning.py     # Prediction-outcome tracking
├── ml/
│   ├── flood_risk_model.py         # Random Forest classifier + regressor
│   └── models/                     # Saved model artifacts (PKL)
├── frontend/
│   ├── ui_utils.py                 # Global CSS, metric cards, badges, charts
│   └── map_component.py            # Folium flood map
├── services/
│   ├── live_data_manager.py        # Open-Meteo live weather integration
│   ├── report_store.py             # Persistent citizen report storage
│   └── weather_dashboard.py        # Weather display helpers
├── data/
│   └── seed_generator.py           # Synthetic data generation
├── tests/                          # 133 tests — pytest
├── requirements.txt
└── .env.example                    # WATSONX_API_KEY, WATSONX_PROJECT_ID
```

---

## 🛠️ Setup

### Requirements

```bash
pip install -r requirements.txt
```

### Configuration

Copy `.env.example` to `.env` and configure:

```env
WATSONX_API_KEY=your_ibm_cloud_api_key
WATSONX_PROJECT_ID=your_watsonx_project_id
```

> IBM Granite is **optional** — the application runs fully in fallback mode without credentials.

### Run

```bash
cd floodguard-ai
streamlit run app.py
```

### Tests

```bash
cd floodguard-ai
python -m pytest tests/ -q
```

Expected: **133 tests pass**

---

## 📊 Data Transparency

All data in FloodGuard AI is clearly labelled:

| Badge | Meaning |
|-------|---------|
| 🟢 **LIVE** | Live data from Open-Meteo API |
| 🔵 **MODEL** | ML Random Forest predictions |
| 🟠 **USER SUBMITTED** | Real citizen reports entered via portal |
| 🟡 **DEMO / SIMULATED** | Synthetic seed data (drains, teams, incidents) |

The application never presents demo data as live government data.

---

## ⚠️ Disclaimer

FloodGuard AI is a **hackathon demonstration system**.

- AI recommendations are decision-support tools only — not authorised emergency orders
- Human approval buttons update application state only — no real emergency services are contacted
- Drainage/team/incident data is synthetic — not real municipal infrastructure data
- ML training data is synthetic — not real government sensor measurements
- The system is not validated for operational emergency response use

---

## 🏆 Hackathon Features Summary

| Feature | Status | Notes |
|---------|--------|-------|
| ML Flood Risk Prediction | ✅ | Random Forest, 5k synthetic samples, real metrics |
| 6-Agent Multi-Agent System | ✅ | Orchestrator + 6 specialised agents |
| IBM Granite Integration | ✅ | Live WatsonX + graceful fallback |
| Evidence Fusion | ✅ | 6-source weighted fusion with explanations |
| WHY THIS ZONE / WHY NOW | ✅ | Feature importance + delta comparison |
| Human-in-the-Loop | ✅ | Approve/Modify/Reject + modification notes |
| Audit Trail | ✅ | Shared across War Room + Decision Intelligence |
| Civic Action Log | ✅ | Timeline view of all HITL decisions |
| Citizen Pipeline | ✅ | EN/हिं/ગુ + 7-step pipeline visualization |
| Live Weather | ✅ | Open-Meteo blended into NORMAL scenario |
| Flood Simulator | ✅ | 5 scenarios + before/after + drainage sim |
| Drainage Before/After | ✅ | Real DrainageAgent scoring formula |
| Forecast Timeline | ✅ | +0/30/60/90/120 min heatmap |
| Geospatial Map | ✅ | Folium with risk zones + weather overlay |
| Agent Execution Log | ✅ | Live pipeline trace in Agent Monitor |
| ML Evaluation | ✅ | Confusion matrix, F1, CV, feature importance |
| Closed-Loop Learning | ✅ | Prediction vs outcome tracking |
| Data Source Transparency | ✅ | LIVE/MODEL/USER/DEMO badges throughout |

---

*FloodGuard AI — Agentic AI for Urban Flood Management | Ahmedabad & Surat, Gujarat*
