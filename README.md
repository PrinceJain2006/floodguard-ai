# 🌊 FloodGuard AI — AI Flood Command Center

> **IBM Hackathon Ready** · Agentic AI · IBM Granite · Random Forest ML · Human-in-the-Loop · Ahmedabad & Surat, Gujarat

[![Python](https://img.shields.io/badge/Python-3.11+-blue?logo=python)](https://python.org)
[![Streamlit](https://img.shields.io/badge/Streamlit-1.41-red?logo=streamlit)](https://streamlit.io)
[![IBM Granite](https://img.shields.io/badge/IBM-Granite_4_h_small-blue?logo=ibm)](https://ibm.com/watsonx)
[![scikit-learn](https://img.shields.io/badge/sklearn-1.5.2-orange)](https://scikit-learn.org)

---

## What It Does

FloodGuard AI is a **multi-agent, AI-powered urban flood management platform** for **Ahmedabad and Surat, Gujarat, India**. It combines ML flood-risk prediction, IBM Granite LLM reasoning, citizen intelligence, drainage analytics, and a human-in-the-loop emergency response workflow into a professional command-center interface.

> **Data Transparency:** Live weather data is fetched from Open-Meteo API. Flood-risk predictions use a Random Forest ML model trained on 5,000 synthetic records. Drainage infrastructure, response teams, and baseline flood incidents are clearly labelled **DEMO/SYNTHETIC data** — not real government or operational data.

---

## Architecture

```
 📡 DATA SOURCES (Live Weather · Synthetic Demo Data)
       ↓
 🌊 Flood Risk Agent (Random Forest ML)
       ↓
 🔧 Drainage Agent (Risk scoring · Maintenance prioritization)
       ↓
 📱 Citizen Report Agent (Multilingual NLP · EN/HI/GU)
       ↓
 ⚡ Response Coordination Agent (Incident plans)
       ↓
 🧠 IBM Granite AI (Situation summaries · Explanations · NL Q&A)
       ↓
 🎯 Chief Response Agent (Unified action plan)
       ↓
 👤 HUMAN APPROVAL (Municipal officer authorization)
       ↓
 ✅ RESPONSE (Simulated command-center state update)
```

**6 specialised agents** + IBM Granite reasoning layer + closed-loop learning feedback.

---

## Features

### 1. AI Flood Command Center Dashboard (`app.py`)
- Full landing page with portal navigation to all 8 modules
- Agent architecture overview with pipeline flow visualization
- IBM Granite integration status display
- Hybrid data transparency labels (LIVE / MODEL / DEMO)

### 2. Command Center (`pages/2_command_center.py`)
- **Live Risk Map** with Folium digital twin — Ahmedabad & Surat zones colored by risk level
- **Zone Detail Panel** — click/select any zone to see: risk score, rainfall, water level, drainage capacity, citizen reports, historical frequency, confidence, AI recommended action
- **Active Alerts** — CRITICAL/HIGH alerts from ML pipeline
- **IBM Granite AI Tab** — full situation summary, per-zone risk explanation, model confidence distribution
- **Agent Trace Tab** — live pipeline visualization with COMPLETE/RUNNING/FALLBACK status per agent
- **Incidents Tab** — active incidents with human approval buttons
- **AI Recommendations Tab** — per-recommendation APPROVE/REJECT workflow
- **Drainage Tab** — scored drains, maintenance schedule, top critical drains
- **Citizen Reports Tab** — merged USER SUBMITTED + demo reports
- **Response Teams Tab** — AVAILABLE/DEPLOYED/STANDBY status
- **Live Weather Tab** — Open-Meteo hourly/daily forecasts

### 3. Flood Scenario Simulator (`pages/6_simulator.py`)
- **6-slider What-If Simulator**: Rainfall intensity, Duration, Drainage capacity, Blocked drains, Water level, Citizen reports
- **RUN SIMULATION button** — calls actual Random Forest ML model for each zone
- **RESET SCENARIO button** — clears simulation state
- Live indicator: ML MODEL vs RULE-BASED (when model unavailable)
- **Forecast Timeline** — risk escalation heatmap (+0/+30/+60/+90/+120 min)
- **Drainage Before/After Simulator** — real DrainageAgent scoring with visual bar comparison
- **Resource Optimization** — team assignment matrix

### 4. Agent Monitor (`pages/3_agent_monitor.py`)
- Prominent **Pipeline Trace** with side-by-side agent status
- Per-agent cards: status, output summary, recent activity
- IBM Granite connection diagnostic (LIVE / RATE LIMITED / FALLBACK)
- Pipeline execution log table

### 5. Citizen Portal (`pages/1_citizen_portal.py`)
- Multilingual form (English / Hindi हिन्दी / Gujarati ગુજરાતી)
- Natural language flood report submission
- **Enhanced AI Classification Panel** after submission:
  - Incident type, Severity (🔴🟠🟡🟢), Priority, Language detected
  - Keywords extracted, AI summary (Granite or rule-based, clearly labelled)
  - Suggested response action
  - Processing pipeline flow: Citizen → Report Agent → IBM Granite → Command Center
- Local flood risk map per city
- Duplicate detection with fuzzy matching

### 6. Emergency War Room (`pages/5_war_room.py`)
- **HUMAN APPROVAL REQUIRED** panel — pending AI actions with Approve/Reject buttons
- **RESPONSE PLAN APPROVED** status when all actions are authorized
- Chief Response Agent action plan with per-action approval workflow
- Compact Resource Recommendations panel
- Agent Pipeline Trace in right column
- IBM Granite WHY explanation per zone (live Granite or fallback)
- Response Teams status + Active Incidents

### 7. Analytics & ML Evaluation (`pages/4_analytics.py`)
- **Model Info**: Random Forest · 5,000 synthetic samples · 4 classes · 10 features
- **Real computed metrics** (NOT hard-coded):
  - Accuracy, Precision, Recall, F1 Score (weighted)
  - Score MAE (regressor)
  - 3-fold cross-validation accuracy ± std
- **Per-class performance** table (LOW / MEDIUM / HIGH / CRITICAL)
- **Feature Importance** horizontal bar chart from actual Gini impurity values
- **WHY IS THIS ZONE HIGH RISK?** explainability section with feature value bars
- Risk trends, rainfall analysis, report analytics, damage assessment, scenario comparison

### 8. Decision Intelligence (`pages/8_decision_intelligence.py`)
- Evidence fusion from all agents
- Priority scoring and ranking
- Human-in-the-loop approval audit trail
- WHY explanations

---

## IBM Granite Integration

IBM Granite is integrated throughout the system:

| Feature | Granite Usage |
|---|---|
| Situation Report | Full scenario summary per pipeline run |
| Zone WHY Explanation | Per-zone risk factor explanation |
| Citizen Report Classification | Multilingual NLP analysis |
| Recommendation Explanation | Plain-language reasoning for AI actions |
| Natural Language Q&A | Free-text queries about flood state |

**Live mode:** Set `WATSONX_API_KEY` and `WATSONX_PROJECT_ID` in `.env`  
**Fallback mode:** Rule-based responses, clearly labelled `⚙ GRANITE FALLBACK MODE`  
**Never pretends** fallback output was generated by a live API.

---

## ML Model

- **Type:** Random Forest (classifier + regressor)
- **Features (10):** rainfall_1h, rainfall_3h, rainfall_6h, rainfall_24h, drainage_capacity, historical_flood_freq, water_level, elevation, road_density, citizen_reports
- **Classes:** LOW / MEDIUM / HIGH / CRITICAL
- **Training data:** 5,000 synthetic records (clearly labelled — not real government data)
- **Evaluation:** 20% held-out test split (1,000 samples), 3-fold cross-validation
- **All metrics calculated from actual model — never hard-coded**

### Actual computed metrics (on synthetic test set):

| Metric | Value |
|--------|-------|
| Accuracy | **90.7%** |
| Precision (weighted) | **90.0%** |
| Recall (weighted) | **90.7%** |
| F1 Score (weighted) | **90.1%** |
| 3-fold CV Accuracy | **~90% ± std** |

### Feature importance (Gini, from trained model):

| Feature | Importance |
|---------|------------|
| historical_flood_freq | 0.1948 |
| water_level | 0.1850 |
| elevation | 0.1418 |
| citizen_reports | 0.0822 |
| rainfall_1h | 0.0774 |
| rainfall_3h | 0.0746 |
| rainfall_6h | 0.0736 |
| drainage_capacity | 0.0718 |
| rainfall_24h | 0.0542 |
| road_density | 0.0446 |

> **Note:** These metrics are computed on synthetic data. Real-world performance will differ when trained on actual sensor/municipal data.

---

## Tech Stack

| Layer | Technology |
|---|---|
| Frontend | Streamlit 1.41 |
| Maps | Folium + streamlit-folium |
| Charts | Plotly |
| ML | scikit-learn 1.5 (Random Forest) |
| AI/LLM | IBM Granite via WatsonX REST API |
| Live Weather | Open-Meteo API (free, no key needed) |
| Data | Synthetic demo (5,000 training + seed data) |
| Report Store | JSON file persistence (cross-page state) |

---

## Quick Start

```bash
# 1. Clone and navigate
cd floodguard-ai

# 2. Create and activate virtualenv
python -m venv .venv
source .venv/bin/activate  # Windows: .venv\Scripts\activate

# 3. Install dependencies
pip install -r requirements.txt

# 4. Configure IBM Granite (optional — fallback works without it)
cp .env.example .env
# Edit .env and add WATSONX_API_KEY and WATSONX_PROJECT_ID

# 5. Run
streamlit run app.py
```

The app opens at `http://localhost:8501`.

---

## Environment Variables

```env
# IBM WatsonX / Granite (optional — fallback mode works without)
WATSONX_API_KEY=your_api_key_here
WATSONX_PROJECT_ID=your_project_id_here
WATSONX_URL=https://us-south.ml.cloud.ibm.com

# Optional — override default model
WATSONX_MODEL_ID=ibm/granite-4-h-small
```

---

## 3-Minute Hackathon Demo Flow

1. **Landing Page** — Show the AI Flood Command Center with 8 portals and agent architecture
2. **Command Center → Live Risk Map** — Show Ahmedabad + Surat map, select a zone to see detail panel
3. **Flood Simulator** — Increase rainfall to 150mm/hr, reduce drainage to 20%, add 80 citizen reports → **RUN SIMULATION** — watch risk scores update using the ML model
4. **Agent Trace Tab** — Show the 6-agent pipeline status with IBM Granite highlighted
5. **IBM Granite AI Tab** — Show the situation summary generated by Granite
6. **Emergency War Room** — Run EXTREME scenario, show critical zones, pending approvals → **APPROVE** an action
7. **Drainage Simulation** — Select a critical drain, show BEFORE (high risk) → adjust capacity → show AFTER (lower risk)
8. **Analytics → ML Evaluation** — Show real computed accuracy, feature importance chart
9. **Citizen Portal** — Submit a Hindi flood report, show AI classification panel
10. **Agent Monitor** — Show all 6 agents COMPLETE with IBM Granite live

---

## Deployment

### Local
```bash
streamlit run app.py
```

### Docker
```bash
docker build -t floodguard-ai .
docker run -p 8501:8501 -e WATSONX_API_KEY=xxx floodguard-ai
```

### IBM Cloud Code Engine
```bash
./ibm-ce-deploy.sh
```

---

## Data Transparency & Limitations

| Data Source | Status |
|---|---|
| Weather (Open-Meteo) | 🟢 LIVE (free API, no key) |
| Flood Risk Prediction | 🔵 ML MODEL (Random Forest) |
| Drainage Infrastructure | 🟡 DEMO/SYNTHETIC |
| Response Teams | 🟡 DEMO/SYNTHETIC |
| Citizen Reports | 🟠 USER SUBMITTED (via portal) + 🟡 DEMO seed |
| IBM Granite | 🟢 LIVE (when configured) / ⚙ FALLBACK |

**This is a hackathon demonstration.** It does not connect to real municipal emergency systems. AI recommendations require authorized human verification before any real-world implementation.

---

## Project Structure

```
floodguard-ai/
├── app.py                    # Landing page / AI Command Center hub
├── pages/
│   ├── 1_citizen_portal.py   # Multilingual citizen reporting
│   ├── 2_command_center.py   # Main command center + Granite + Agent trace
│   ├── 3_agent_monitor.py    # Agent pipeline monitor
│   ├── 4_analytics.py        # Analytics + ML evaluation + explainability
│   ├── 5_war_room.py         # Emergency war room + human approval
│   ├── 6_simulator.py        # What-if + drainage before/after
│   ├── 7_learning_loop.py    # Closed-loop prediction accuracy
│   └── 8_decision_intelligence.py  # Evidence fusion + audit
├── agents/
│   ├── orchestrator.py       # Multi-agent pipeline coordinator
│   ├── flood_risk_agent.py   # Agent 1: ML risk prediction
│   ├── drainage_agent.py     # Agent 2: Drain analysis
│   ├── citizen_report_agent.py  # Agent 3: NLP classification
│   ├── response_coordination_agent.py  # Agent 4: Incident plans
│   ├── chief_response_agent.py  # Agent 5: Unified action plan
│   ├── damage_assessment_agent.py  # Agent 6: Damage scoring
│   ├── granite_service.py    # IBM Granite WatsonX integration
│   ├── evidence_fusion.py    # Decision intelligence
│   └── closed_loop_learning.py  # Prediction-outcome tracking
├── ml/
│   ├── flood_risk_model.py   # Random Forest classifier + regressor
│   └── models/               # Saved trained model artifacts
├── frontend/
│   ├── ui_utils.py           # Global CSS + shared UI helpers
│   └── map_component.py      # Folium digital twin map
├── data/
│   ├── seed_generator.py     # Synthetic demo data generation
│   └── ml_training_data.json # 5,000 training samples
├── services/
│   ├── report_store.py       # Citizen report persistence
│   ├── live_data_manager.py  # Open-Meteo weather ingestion
│   └── weather_dashboard.py  # Weather display helpers
└── requirements.txt
```

---

## Author

Built for the IBM Hackathon — AI-Powered Urban Flood Management Challenge.  
FloodGuard AI demonstrates agentic AI, IBM Granite integration, ML explainability, and human-in-the-loop emergency response for Ahmedabad and Surat, Gujarat, India.
