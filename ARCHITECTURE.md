# FloodGuard AI — Architecture Reference

## High-Level Architecture

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                          FLOODGUARD AI PLATFORM                             │
│                   (Ahmedabad & Surat, Gujarat, India)                       │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                              │
│  ┌──────────────────────────────────────────────────────────────────────┐   │
│  │                      DATA LAYER (Demo/Synthetic)                     │   │
│  │  Rainfall · Drainage · Incidents · Reports · Teams · Areas           │   │
│  └──────────────────────┬───────────────────────────────────────────────┘   │
│                         │                                                    │
│  ┌──────────────────────▼───────────────────────────────────────────────┐   │
│  │                    AGENT ORCHESTRATOR                                │   │
│  │  ┌──────────────────────────────────────────────────────────────┐    │   │
│  │  │  PIPELINE: Data → Risk → Drainage → Reports → Coordination   │    │   │
│  │  └──────────────────────────────────────────────────────────────┘    │   │
│  │                                                                       │   │
│  │  ┌───────────────┐  ┌───────────────┐  ┌───────────────┐             │   │
│  │  │  🌊 Flood     │  │  🔧 Drainage  │  │  📱 Citizen   │             │   │
│  │  │  Risk Agent   │  │  Agent        │  │  Report Agent │             │   │
│  │  │  (ML/RF)      │  │  (Scoring)    │  │  (NLP)        │             │   │
│  │  └───────┬───────┘  └───────┬───────┘  └───────┬───────┘             │   │
│  │          │                  │                   │                     │   │
│  │  ┌───────▼───────────────────▼───────────────────▼──────────────┐    │   │
│  │  │              ⚡ Response Coordination Agent                   │    │   │
│  │  │    Priority Queue · Incident Generator · Approval Gates       │    │   │
│  │  └──────────────────────────┬───────────────────────────────────┘    │   │
│  │                              │                                        │   │
│  │  ┌───────────────────────────▼──────────────────────────────────┐    │   │
│  │  │              🧠 IBM Granite Reasoning Layer                   │    │   │
│  │  │   ibm/granite-3-8b-instruct via WatsonX API                  │    │   │
│  │  │   · Report classification  · Situation reports               │    │   │
│  │  │   · NL explanations        · Query answering                 │    │   │
│  │  └──────────────────────────────────────────────────────────────┘    │   │
│  └──────────────────────┬───────────────────────────────────────────────┘   │
│                         │                                                    │
│  ┌──────────────────────▼───────────────────────────────────────────────┐   │
│  │                    APPLICATION LAYER                                 │   │
│  │  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐  ┌────────────┐  │   │
│  │  │  FastAPI    │  │  Streamlit  │  │  SQLite DB  │  │  Auth/JWT  │  │   │
│  │  │  REST API   │  │  Dashboard  │  │  (demo)     │  │  RBAC      │  │   │
│  │  └─────────────┘  └─────────────┘  └─────────────┘  └────────────┘  │   │
│  └──────────────────────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────────────────────┘
```

## Component Descriptions

### 1. Data Layer
**Files:** `data/seed_generator.py`, `data/*.json`  
Synthetic data for demonstration. In production, replace with:
- IMD OpenAPI weather feeds
- AMC/SMC IoT sensor data
- Municipal GIS drainage database
- Real historical flood records from NDMA/CWC

### 2. Agent Orchestrator
**File:** `agents/orchestrator.py`  
Central coordinator managing agent lifecycle and data flow.

Pipeline execution order:
1. Load scenario data
2. Run Flood Risk Agent (per area)
3. Run Drainage Agent (per drain)
4. Run Citizen Report Agent (batch)
5. Run Response Coordination Agent
6. Call Granite for situation report
7. Generate alerts
8. Return unified state

### 3. Flood Risk Agent (Agent 1)
**File:** `agents/flood_risk_agent.py`  
Uses Random Forest (sklearn) to predict risk score (0-100) and level (LOW/MEDIUM/HIGH/CRITICAL) per area.

ML features: rainfall_1h, rainfall_3h, rainfall_6h, rainfall_24h, drainage_capacity, historical_flood_freq, water_level, elevation, road_density, citizen_reports

### 4. Drainage Agent (Agent 2)
**File:** `agents/drainage_agent.py`  
Domain-scoring algorithm for drainage maintenance prioritization.

Score formula:
```
drain_risk = (100 - capacity) × 0.25
           + blockage_freq × 8 × 0.25
           + flood_zone_flag × 80 × 0.15
           + (100 - condition_score) × 0.20
           + days_since_cleaned/3 × 0.10
           + rainfall_factor × 0.05
           + blocked_bonus
```

### 5. Citizen Report Agent (Agent 3)
**File:** `agents/citizen_report_agent.py`  
Processes multilingual reports:
1. Language detection (Devanagari/Gujarati unicode ranges)
2. Granite NLP classification → category, severity, location
3. Text fingerprinting for duplicate detection
4. Fuzzy matching (>80% similarity threshold)
5. Team routing based on category

### 6. Response Coordination Agent (Agent 4)
**File:** `agents/response_coordination_agent.py`  
Combines all agent outputs into a ranked incident response plan:
1. Identifies critical areas from flood risk predictions
2. Finds nearby critical drains
3. Counts citizen reports per area
4. Generates action list per incident
5. Flags CRITICAL actions for human approval
6. Generates system-level recommendations

### 7. IBM Granite Service
**File:** `agents/granite_service.py`  
WatsonX REST API integration:
- IAM token management with 55-minute cache
- Structured JSON extraction from LLM responses
- Complete rule-based fallback for all functions

### 8. Damage Assessment Agent (Agent 6)
**File:** `agents/damage_assessment_agent.py`  
Post-disaster damage classification with:
- Infrastructure type identification (road/drainage/property/public)
- Duration-adjusted damage scoring
- Mandatory AI disclaimer on all outputs
- Field verification requirement flags

### 9. FastAPI Backend
**File:** `backend/api.py`  
REST API with JWT authentication and RBAC (citizen/operator/admin).  
All endpoints return `data_label: "DEMO/SIMULATED"`.

### 10. Streamlit Frontend
Multi-page application:
| Page | File | Role |
|------|------|------|
| Landing | `app.py` | Portal selection hub |
| Citizen Portal | `pages/1_citizen_portal.py` | Multilingual report submission |
| Command Center | `pages/2_command_center.py` | Operator dashboard |
| Agent Monitor | `pages/3_agent_monitor.py` | Pipeline visibility |
| Analytics | `pages/4_analytics.py` | Trends and impact metrics |

## Data Flow

```
Scenario Trigger
      │
      ▼
generate_rainfall_data(scenario)
generate_drains()
generate_citizen_reports()
generate_response_teams()
      │
      ▼
FloodRiskAgent.analyze_all_areas()
  → RandomForest.predict() per area
  → risk_score + risk_level per area
      │
      ▼
DrainageAgent.prioritize_drains()
  → score_drain() per drain
  → maintenance_schedule
      │
      ▼
CitizenReportAgent.batch_analyze()
  → hotspot_areas
  → category/severity breakdown
      │
      ▼
ResponseCoordinationAgent.coordinate()
  → incidents[] with recommended_actions[]
  → top_recommendations[]
      │
      ▼
granite.generate_situation_report()
  → situationReport (text)
      │
      ▼
_generate_alerts()
  → alerts[] (citizen/operator/emergency)
      │
      ▼
Unified State → Dashboard
```

## AI Safety Design

1. **No autonomous actions** — All CRITICAL recommendations require explicit human approval
2. **Transparency** — Every recommendation shows reasoning and confidence
3. **Data labeling** — All demo/simulated data explicitly labeled
4. **Granite grounding** — LLM uses retrieved context, not hallucinated values
5. **Preliminary disclaimers** — Damage assessments explicitly marked as unverified
6. **Fallback safety** — Rule-based fallbacks prevent system failure

## Security Design

1. **No secrets in code** — All credentials via environment variables
2. **JWT authentication** — Stateless auth with configurable expiry
3. **RBAC** — citizen < operator < admin role hierarchy
4. **Input validation** — Pydantic models on all API inputs
5. **CORS** — Configurable in production
6. **No frontend exposure** — WatsonX credentials never reach browser

## Scaling Path (Production)

```
Demo (Current)          → Production
─────────────────────────────────────
SQLite                  → IBM Db2 / PostgreSQL
In-memory state         → Redis cache
Synthetic data          → IMD + IoT real-time feeds
Demo SMS               → BSNL SMS API
Folium map             → Mapbox GL / ArcGIS
Single process         → Kubernetes + autoscaling
Basic auth             → SSO + Aadhaar integration
Rule ML model          → LSTM/GNN + satellite imagery
```
