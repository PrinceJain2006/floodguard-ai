# 🌊 FloodGuard AI

## AI-Powered Urban Flood Intelligence & Decision Support System

FloodGuard AI is an AI-powered urban flood intelligence platform designed to support **flood-risk prediction, drainage analysis, citizen incident processing, multi-agent decision making, explainable AI, and human-reviewed emergency response planning** for urban flood scenarios in Ahmedabad and Surat, Gujarat.

The platform combines **Machine Learning, Multi-Agent AI, IBM Granite, Geospatial Intelligence, Evidence Fusion, and Human-in-the-Loop decision support** into a unified operational workflow.

> **FloodGuard AI doesn't just predict flooding. It converts prediction + citizen reports + drainage information into prioritized actions.**

---

## ⚡ Decision Intelligence Workflow

```text
Weather & Flood Signals
        │
        ▼
┌─────────────────────────┐
│   ML Flood Risk Model   │
│     Random Forest       │
└────────────┬────────────┘
             │
             ▼
┌─────────────────────────┐
│    Multi-Agent Layer    │
│ Risk • Drainage •       │
│ Citizen • Response      │
└────────────┬────────────┘
             │
             ▼
┌─────────────────────────┐
│     Evidence Fusion     │
│  + Zone Prioritization  │
└────────────┬────────────┘
             │
             ▼
┌─────────────────────────┐
│      IBM Granite        │
│ Analysis & Reasoning    │
└────────────┬────────────┘
             │
             ▼
┌─────────────────────────┐
│   AI Recommendation     │
└────────────┬────────────┘
             │
             ▼
┌─────────────────────────┐
│     Human Approval      │
└────────────┬────────────┘
             │
             ▼
┌─────────────────────────┐
│   Civic Response Plan   │
│      + Audit Trail      │
└─────────────────────────┘
```

---

# 🖥️ AI Flood Command Center

FloodGuard AI provides a centralized operational interface for monitoring flood risk, incidents, drainage conditions, citizen reports, agent activity, and AI-supported decisions.

<p align="center">
  <img src="assets/command-center.png" width="950" alt="FloodGuard AI Command Center">
</p>

---

# 🎯 Problem

Urban flooding requires decision-makers to evaluate multiple signals at the same time.

During heavy rainfall, important questions include:

* Which areas are becoming high risk?
* Which drainage assets require attention?
* What are citizens reporting?
* Which incidents should be prioritized?
* What response should be recommended?
* Why is a particular zone considered high risk?
* Where should human decision-makers intervene?

FloodGuard AI approaches this as a **decision-intelligence problem**, rather than treating flood prediction as an isolated machine-learning task.

---

# 💡 Solution

FloodGuard AI connects prediction, agentic analysis and decision support into one workflow.

| Intelligence Layer              | Role                                              |
| ------------------------------- | ------------------------------------------------- |
| **Machine Learning**            | Flood-risk prediction                             |
| **Flood Risk Agent**            | Processes flood-risk information                  |
| **Drainage Agent**              | Analyzes drainage conditions                      |
| **Citizen Report Agent**        | Processes citizen incidents                       |
| **Response Coordination Agent** | Generates response recommendations                |
| **Chief Response Agent**        | Unifies response-oriented decisions               |
| **Damage Assessment Agent**     | Supports damage assessment                        |
| **IBM Granite**                 | Contextual analysis and recommendation generation |
| **Evidence Fusion**             | Combines available decision signals               |
| **Human Approval**              | Keeps critical response decisions human-reviewed  |
| **Audit Trail**                 | Records decision activity                         |

---

# 🤖 Multi-Agent Architecture

FloodGuard AI uses a six-agent architecture coordinated through an orchestration layer.

### 01 — Flood Risk Agent

Uses the project's ML flood-risk model and available inputs to produce flood-risk information.

### 02 — Drainage Agent

Analyzes drainage-related conditions and identifies maintenance priorities.

### 03 — Citizen Report Agent

Processes citizen-submitted flood reports and supports multilingual incident classification where implemented.

### 04 — Response Coordination Agent

Uses analyzed incident and risk information to generate response recommendations.

### 05 — Chief Response Agent

Provides a unified response-oriented decision layer.

### 06 — Damage Assessment Agent

Supports post-event damage assessment and scoring.

### Agent Orchestration

```text
                         ┌─────────────────────┐
                         │   Input Signals      │
                         │ Weather / Reports    │
                         │ Drainage / Incidents │
                         └──────────┬──────────┘
                                    │
                                    ▼
                         ┌─────────────────────┐
                         │  Agent Orchestrator │
                         └──────────┬──────────┘
                                    │
              ┌─────────────────────┼─────────────────────┐
              ▼                     ▼                     ▼
       Flood Risk Agent      Drainage Agent      Citizen Report Agent
              │                     │                     │
              └─────────────────────┼─────────────────────┘
                                    │
                         ┌──────────▼──────────┐
                         │ Response Agents     │
                         └──────────┬──────────┘
                                    │
                                    ▼
                           Evidence Fusion
                                    │
                                    ▼
                        Decision Intelligence
```

---

# 🧠 Machine Learning

FloodGuard AI contains a **Random Forest-based flood-risk modelling pipeline**.

The ML layer includes:

* Random Forest classification
* Random Forest regression components
* Saved trained model artifacts
* Feature importance
* Model evaluation functionality
* Training-data generation for the demonstration environment

The repository currently contains **5,000 synthetic training samples** for the demonstration environment.

> **Data transparency:** Synthetic/demo data is used where applicable. These values should not be interpreted as live municipal or government flood data.

---

# 🔍 Explainable Flood Risk

FloodGuard AI is designed to provide more context than a single risk score.

The system can expose model-related factors and feature importance to help explain changes in predicted flood risk.

```text
Rainfall
    +
Drainage Conditions
    +
Water Level
    +
Historical Flood Information
    +
Other Available Features
          │
          ▼
   Random Forest Model
          │
          ▼
   Flood Risk Prediction
          │
          ▼
 Feature Importance /
   Explainability
```

### Key Decision Question

> **Why is this zone considered high risk?**

The explainability layer helps connect model output with the available input factors.

---

# 🗺️ Geospatial Intelligence

FloodGuard AI includes a map-based flood intelligence layer using the project's existing geographical implementation.

Risk information can be visualized by zone and connected with relevant flood, drainage and incident information available to the application.

<p align="center">
  <img src="assets/risk-map.png" width="950" alt="FloodGuard AI Risk Map">
</p>

---

# 📱 Citizen Flood Reporting

FloodGuard AI includes a citizen-facing reporting workflow.

A submitted flood incident enters the application's processing pipeline and can be surfaced in the command-center workflow.

```text
Citizen Report
      │
      ▼
Citizen Report Agent
      │
      ▼
Incident Classification
      │
      ▼
Severity / Context
      │
      ▼
Command Center
      │
      ▼
Response Recommendation
```

The project supports multilingual citizen-report processing where implemented, including **English, Hindi and Gujarati**.

<p align="center">
  <img src="assets/citizen-portal.png" width="950" alt="FloodGuard AI Citizen Portal">
</p>

---

# ☁️ IBM Granite Integration

FloodGuard AI contains an IBM Granite / watsonx service layer:

```text
agents/granite_service.py
```

The Granite layer supports AI-assisted tasks such as:

* Situation understanding
* Contextual analysis
* Incident summarization
* Recommendation generation

### Execution Transparency

When IBM Granite is available:

```text
Application Context
        ↓
IBM Granite
        ↓
AI Analysis
        ↓
Generated Summary / Recommendation
```

When the external IBM service is unavailable:

```text
IBM Granite Unavailable
        ↓
Existing Demo / Fallback Logic
```

The application distinguishes between live Granite execution and fallback/demo behavior.

> **Fallback output is never presented as live IBM Granite execution.**

---

# 🧩 Evidence Fusion & Decision Intelligence

FloodGuard AI combines multiple available signals before producing decision support.

```text
ML Risk Prediction
        +
Drainage Intelligence
        +
Citizen Reports
        +
Incident Context
        +
Geospatial Information
        │
        ▼
   Evidence Fusion
        │
        ▼
 Zone Prioritization
        │
        ▼
 AI Recommendation
        │
        ▼
 Human Decision
```

This provides a decision-support layer around the underlying flood-risk prediction.

---

# 🚨 Human-in-the-Loop

Critical response recommendations are designed around human review.

```text
Risk Detected
      ↓
Evidence Analysis
      ↓
Zone Prioritized
      ↓
AI Recommendation
      ↓
Human Approval
      ↓
Response Plan
      ↓
Audit Trail
```

AI recommendations do **not** represent autonomous control of real municipal emergency infrastructure.

> **Human approval remains a control point for critical response decisions.**

---

# 🌧️ Flood Scenario Simulation

The application includes a controlled flood-scenario simulation environment.

Scenario inputs can be adjusted to demonstrate how the application's risk and decision-support pipeline responds.

```text
Scenario Input
      ↓
Risk Recalculation
      ↓
Agent Processing
      ↓
Evidence Fusion
      ↓
Recommendation
```

<p align="center">
  <img src="assets/simulator.png" width="950" alt="FloodGuard AI Flood Scenario Simulator">
</p>

---

# 📊 Analytics & Explainability

The analytics layer provides visibility into:

* Flood-risk analysis
* ML evaluation
* Feature importance
* Prediction behaviour
* Decision-support information
* Agent-related analysis
* Closed-loop learning information

<p align="center">
  <img src="assets/analytics.png" width="950" alt="FloodGuard AI Analytics">
</p>

---

# 🔄 Closed-Loop Learning

FloodGuard AI includes a closed-loop learning component for tracking prediction outcomes and supporting future improvement.

```text
Prediction
    ↓
Observed Outcome
    ↓
Comparison
    ↓
Learning Signal
    ↓
Future Improvement
```

Implementation details are handled through:

```text
agents/closed_loop_learning.py
```

---

# 🧭 Decision Intelligence

The decision-intelligence layer connects model outputs, agent analysis and available evidence into a structured decision workflow.

Core sequence:

```text
DETECT
  ↓
PREDICT
  ↓
ANALYZE
  ↓
EXPLAIN
  ↓
PRIORITIZE
  ↓
HUMAN APPROVAL
  ↓
CIVIC RESPONSE
  ↓
AUDIT
```

This is the central operational story of FloodGuard AI.

---

# 🖥️ Application Modules

| Module                    | Purpose                                    |
| ------------------------- | ------------------------------------------ |
| **Landing / Command Hub** | System entry point and overview            |
| **Citizen Portal**        | Citizen flood reporting                    |
| **Command Center**        | Central flood intelligence and AI analysis |
| **Agent Monitor**         | Multi-agent pipeline monitoring            |
| **Analytics**             | ML analytics and explainability            |
| **War Room**              | Emergency response and human approval      |
| **Simulator**             | Flood scenario and drainage simulation     |
| **Learning Loop**         | Prediction/outcome tracking                |
| **Decision Intelligence** | Evidence fusion, prioritization and audit  |

---

# 🏗️ Technical Architecture

```text
                         FLOODGUARD AI
                              │
        ┌─────────────────────┴─────────────────────┐
        │                                           │
     DATA LAYER                                  ML LAYER
        │                                           │
 Weather / Reports                         Random Forest Model
 Drainage / Incidents                      Risk Prediction
 Historical Information                    Explainability
        │                                           │
        └─────────────────────┬─────────────────────┘
                              │
                       AGENTIC AI LAYER
                              │
        ┌─────────────┬───────┴────────┬─────────────┐
        │             │                │             │
      Risk        Drainage         Citizen       Response
      Agent        Agent            Agent          Agents
        │             │                │             │
        └─────────────┴────────────────┴─────────────┘
                              │
                              ▼
                       Evidence Fusion
                              │
                              ▼
                    IBM Granite / AI Layer
                              │
                              ▼
                    Decision Intelligence
                              │
                              ▼
                       Human Approval
                              │
                              ▼
                       Response Plan
                              │
                              ▼
                         Audit Trail
```

---

# 🛠️ Technology Stack

### Artificial Intelligence & Machine Learning

* Python
* Scikit-learn
* Random Forest
* Machine Learning Explainability
* Multi-Agent AI

### IBM Technology

* IBM Granite
* IBM watsonx integration

### Application

* Streamlit
* Python
* Folium
* Streamlit-Folium

### Data & Services

* SQLite / application persistence
* Synthetic demonstration data
* Open-Meteo weather ingestion where configured

---

# 📁 Project Structure

```text
floodguard-ai/
│
├── app.py
│
├── pages/
│   ├── 1_citizen_portal.py
│   ├── 2_command_center.py
│   ├── 3_agent_monitor.py
│   ├── 4_analytics.py
│   ├── 5_war_room.py
│   ├── 6_simulator.py
│   ├── 7_learning_loop.py
│   └── 8_decision_intelligence.py
│
├── agents/
│   ├── orchestrator.py
│   ├── flood_risk_agent.py
│   ├── drainage_agent.py
│   ├── citizen_report_agent.py
│   ├── response_coordination_agent.py
│   ├── chief_response_agent.py
│   ├── damage_assessment_agent.py
│   ├── granite_service.py
│   ├── evidence_fusion.py
│   └── closed_loop_learning.py
│
├── ml/
│   ├── flood_risk_model.py
│   └── models/
│
├── frontend/
│   ├── ui_utils.py
│   └── map_component.py
│
├── data/
│   ├── seed_generator.py
│   └── ml_training_data.json
│
├── services/
│   ├── report_store.py
│   ├── live_data_manager.py
│   └── weather_dashboard.py
│
└── requirements.txt
```

---

# 🚀 Run Locally

### Clone

```bash
git clone https://github.com/PrinceJain2006/floodguard-ai.git
cd floodguard-ai
```

### Install Dependencies

```bash
pip install -r requirements.txt
```

### Launch

```bash
streamlit run app.py
```

---

# 🎬 Demonstration Flow

A concise demonstration can follow the complete decision pipeline:

```text
01  Start Command Center
        ↓
02  Review current flood-risk state
        ↓
03  Run controlled flood scenario
        ↓
04  Observe risk / zone changes
        ↓
05  Monitor agent processing
        ↓
06  Submit citizen flood report
        ↓
07  Process incident classification
        ↓
08  Review evidence fusion / prioritization
        ↓
09  Review IBM Granite analysis
        ↓
10  Generate AI recommendation
        ↓
11  Human reviews / approves response
        ↓
12  Review decision / audit information
```

The demonstration should clearly distinguish:

* ML-generated values
* Deterministic application logic
* Agent processing
* IBM Granite output
* Demo/synthetic data
* Human-approved recommendations

---

# ⚠️ Project Status & Data Transparency

FloodGuard AI is a **hackathon demonstration and decision-support prototype**.

The current system uses synthetic/demo data and controlled simulations where applicable. External data integrations are only represented as available/configured in the application.

The system does **not** directly control real municipal emergency infrastructure.

AI-generated recommendations require appropriate human verification before any real-world implementation.

---

# 🌊 FloodGuard AI

### From Flood Prediction → Decision Intelligence

```text
DETECT
   ↓
PREDICT
   ↓
ANALYZE
   ↓
EXPLAIN
   ↓
PRIORITIZE
   ↓
HUMAN APPROVAL
   ↓
CIVIC RESPONSE
   ↓
AUDIT
```

> **Turning flood signals into explainable, prioritized decision support.**
