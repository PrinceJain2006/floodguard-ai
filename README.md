# 🌊 FloodGuard AI

## AI-Powered Urban Flood Intelligence & Decision Support System

**FloodGuard AI** is an AI-powered urban flood intelligence platform designed to support flood-risk analysis, multi-agent decision making, citizen incident reporting, drainage assessment, and human-reviewed emergency response planning for **Ahmedabad and Surat, Gujarat**.

The system combines **Machine Learning, Multi-Agent AI, IBM Granite, Geospatial Intelligence, Evidence Fusion, and Human-in-the-Loop decision making** into a unified flood command workflow.

> **FloodGuard AI doesn't just predict flooding. It converts prediction + citizen reports + drainage information into prioritized actions.**

---

## ⚡ Decision Intelligence

```text
┌──────────────────────┐
│ Rainfall & Weather   │
│ Drainage Conditions  │
│ Historical Floods    │
│ Citizen Reports      │
└──────────┬───────────┘
           ↓
┌──────────────────────┐
│   ML Flood Risk      │
│     Prediction       │
└──────────┬───────────┘
           ↓
┌──────────────────────┐
│   Multi-Agent AI     │
│ Risk • Drainage      │
│ Citizen • Response   │
└──────────┬───────────┘
           ↓
┌──────────────────────┐
│   Evidence Fusion    │
│ + Zone Prioritization│
└──────────┬───────────┘
           ↓
┌──────────────────────┐
│    IBM Granite       │
│ Analysis & Reasoning │
└──────────┬───────────┘
           ↓
┌──────────────────────┐
│ AI Recommendation    │
└──────────┬───────────┘
           ↓
┌──────────────────────┐
│   Human Approval     │
└──────────┬───────────┘
           ↓
┌──────────────────────┐
│ Civic Response Plan  │
│      + Audit Trail   │
└──────────────────────┘
```

---

## 🖥️ AI Flood Command Center

FloodGuard AI provides a centralized operational view for monitoring flood risk, incidents, drainage conditions, citizen reports, agent activity, and AI-generated decision support.

<!-- Add your actual Command Center screenshot here -->

<p align="center">
  <img src="assets/command-center.png" width="950" alt="FloodGuard AI Command Center">
</p>

---

## 🎯 Problem

Rapid urbanization and changing rainfall patterns can put pressure on existing urban drainage infrastructure.

During heavy rainfall, authorities need to understand multiple signals simultaneously:

* Where is flood risk increasing?
* Which zones require immediate attention?
* Which drainage assets are vulnerable?
* What are citizens reporting?
* What response should be prioritized?
* Why was a particular zone classified as high risk?
* Where should human decision-makers intervene?

FloodGuard AI addresses this as a **decision-intelligence problem**, rather than treating flood prediction as an isolated ML task.

---

## 💡 Solution

FloodGuard AI brings together multiple intelligence layers:

| Layer                           | Purpose                                                     |
| ------------------------------- | ----------------------------------------------------------- |
| **Machine Learning**            | Predict flood risk from available features                  |
| **Flood Risk Agent**            | Interprets and processes flood-risk predictions             |
| **Drainage Agent**              | Identifies drainage-related vulnerabilities                 |
| **Citizen Report Agent**        | Processes and classifies citizen incidents                  |
| **Response Coordination Agent** | Generates response recommendations                          |
| **Chief Response Agent**        | Helps unify the response plan                               |
| **Damage Assessment Agent**     | Supports damage assessment                                  |
| **IBM Granite**                 | Situation analysis, reasoning and recommendation generation |
| **Evidence Fusion**             | Combines multiple signals for decision support              |
| **Human Approval**              | Keeps critical response decisions under human control       |
| **Audit Trail**                 | Records decision activity                                   |

---

# 🤖 Multi-Agent Architecture

FloodGuard AI uses a six-agent architecture coordinated through an orchestration layer.

### 01 — Flood Risk Agent

Uses the ML flood-risk model to analyze flood-related inputs and produce risk information.

### 02 — Drainage Agent

Analyzes drainage conditions and identifies maintenance-related priorities.

### 03 — Citizen Report Agent

Processes citizen-submitted flood incidents and supports multilingual incident classification.

### 04 — Response Coordination Agent

Converts analyzed incidents and risk information into response recommendations.

### 05 — Chief Response Agent

Provides a unified response-oriented decision layer across the system.

### 06 — Damage Assessment Agent

Supports post-event damage assessment and scoring.

### Agent Orchestration

```text
Data Inputs
    │
    ▼
Agent Orchestrator
    │
    ├── Flood Risk Agent
    ├── Drainage Agent
    ├── Citizen Report Agent
    ├── Response Coordination Agent
    ├── Chief Response Agent
    └── Damage Assessment Agent
              │
              ▼
       Evidence Fusion
              │
              ▼
       Decision Intelligence
```

---

# 🧠 Machine Learning

FloodGuard AI includes a **Random Forest-based flood-risk modelling pipeline**.

The project contains:

* Random Forest classification
* Random Forest regression components
* Saved model artifacts
* Feature importance / explainability
* Model evaluation functionality
* Training data generation for the demonstration environment

The current repository includes **5,000 synthetic training samples** for demonstration purposes.

> **Data transparency:** The current demonstration environment uses synthetic/demo data where applicable. These values should not be interpreted as live municipal or government flood data.

---

# 🔍 Explainable Flood Risk

FloodGuard AI does not treat a risk score as a black box.

The system can expose model-related factors and feature importance to help explain why flood risk changes.

Conceptually:

```text
Rainfall
     +
Drainage Condition
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
Explainability / Feature Importance
```

This supports the key decision question:

> **Why is this zone considered high risk?**

---

# 🗺️ Geospatial Intelligence

The application includes a map-based flood intelligence layer using the project's existing geographical implementation.

Risk information can be visualized by zone and connected with relevant flood, drainage, and incident information available to the application.

<!-- Add your actual Risk Map screenshot here -->

<p align="center">
  <img src="assets/risk-map.png" width="950" alt="FloodGuard AI Risk Map">
</p>

---

# 📱 Citizen Flood Reporting

FloodGuard AI includes a citizen-facing reporting workflow.

A citizen can submit a flood-related incident, which is then processed through the application's citizen-report pipeline.

```text
Citizen Report
      ↓
Citizen Report Agent
      ↓
Incident Classification
      ↓
Severity / Context
      ↓
Command Center
      ↓
Response Recommendation
```

The project supports multilingual citizen-report processing where implemented, including **English, Hindi and Gujarati** capabilities.

<!-- Add your actual Citizen Portal screenshot here -->

<p align="center">
  <img src="assets/citizen-portal.png" width="950" alt="FloodGuard AI Citizen Portal">
</p>

---

# ☁️ IBM Granite Integration

FloodGuard AI integrates an IBM Granite / watsonx service layer through:

```text
agents/granite_service.py
```

Granite is used within the application's AI reasoning layer for tasks such as:

* Situation understanding
* Contextual analysis
* Incident summarization
* Recommendation generation

The application also contains fallback/demo behavior for environments where external IBM services are unavailable.

### Execution transparency

```text
IBM Granite Available
        │
        ▼
IBM Granite Execution
        │
        ▼
Generated AI Analysis
```

or, when external execution is unavailable:

```text
IBM Granite Unavailable
        │
        ▼
Existing Demo / Fallback Logic
```

The application does **not** treat fallback output as live Granite execution.

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

This is the core distinction between a simple prediction dashboard and a broader **decision-support system**.

---

# 🚨 Human-in-the-Loop

FloodGuard AI is designed around human-reviewed response planning.

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

AI recommendations are not presented as autonomous control of real municipal infrastructure.

> **Human approval remains an important control point for critical response decisions.**

---

# 🌧️ Flood Scenario Simulation

The project includes a simulator for demonstrating flood scenarios and system responses.

The simulator allows controlled changes to available scenario inputs and demonstrates how the application's risk and decision-support pipeline responds.

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

This provides a controlled environment for demonstrating the system without claiming live municipal deployment.

<!-- Add your actual Simulator screenshot here -->

<p align="center">
  <img src="assets/simulator.png" width="950" alt="FloodGuard AI Flood Scenario Simulator">
</p>

---

# 📊 Analytics & Decision Intelligence

The application includes dedicated views for:

* Flood-risk analytics
* ML evaluation
* Feature importance
* Agent monitoring
* Emergency analysis
* Decision intelligence
* Audit information
* Closed-loop learning

<!-- Add actual Analytics screenshot -->

<p align="center">
  <img src="assets/analytics.png" width="950" alt="FloodGuard AI Analytics">
</p>

---

# 🔄 Closed-Loop Learning

FloodGuard AI includes a closed-loop learning component for tracking prediction outcomes and supporting future improvement of the decision pipeline.

```text
Prediction
    ↓
Observed Outcome
    ↓
Comparison
    ↓
Learning Signal
    ↓
Future Model Improvement
```

---

# 🖥️ Application Modules

| Page                      | Purpose                                           |
| ------------------------- | ------------------------------------------------- |
| **Landing / Command Hub** | Entry point and system overview                   |
| **Citizen Portal**        | Multilingual citizen reporting                    |
| **Command Center**        | Central flood intelligence and Granite/agent view |
| **Agent Monitor**         | Multi-agent pipeline monitoring                   |
| **Analytics**             | ML analytics, evaluation and explainability       |
| **War Room**              | Emergency response and human approval             |
| **Simulator**             | Flood scenario and drainage simulation            |
| **Learning Loop**         | Prediction/outcome tracking                       |
| **Decision Intelligence** | Evidence fusion, prioritization and audit         |

---

# 🏗️ Technical Architecture

```text
                         FLOODGUARD AI
                              │
          ┌───────────────────┴───────────────────┐
          │                                       │
      DATA LAYER                              ML LAYER
          │                                       │
 Weather / Reports                       Random Forest Model
 Drainage / Incidents                    Risk Prediction
 Historical Information                  Explainability
          │                                       │
          └───────────────────┬───────────────────┘
                              │
                       AGENTIC AI LAYER
                              │
                  ┌───────────┼───────────┐
                  │           │           │
                Risk      Drainage     Citizen
                Agent       Agent       Agent
                  │           │           │
                  └───────────┼───────────┘
                              │
                     Response Agents
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

### AI / ML

* Python
* Scikit-learn
* Random Forest
* Machine Learning Explainability
* Multi-Agent AI

### IBM Technology

* IBM Granite
* IBM watsonx integration
* IBM AI ecosystem

### Application

* Streamlit
* Python
* Folium
* Streamlit-Folium

### Data / Services

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

### 1. Clone the repository

```bash
git clone https://github.com/PrinceJain2006/floodguard-ai.git
cd floodguard-ai
```

### 2. Install dependencies

```bash
pip install -r requirements.txt
```

### 3. Start the Streamlit application

```bash
streamlit run app.py
```

The application will open in the local Streamlit environment.

---

# 🎬 Recommended Demonstration Flow

For a concise technical demonstration:

```text
01  Start Command Center
          ↓
02  Introduce current flood-risk state
          ↓
03  Run a controlled flood scenario
          ↓
04  Observe risk / zone changes
          ↓
05  Show agent processing
          ↓
06  Submit a citizen flood report
          ↓
07  Show incident classification
          ↓
08  Show evidence fusion / prioritization
          ↓
09  Show IBM Granite analysis when connected
          ↓
10  Show AI recommendation
          ↓
11  Human reviews / approves response
          ↓
12  Show audit / decision record
```

The demonstration should clearly distinguish **model output, agent processing, Granite-generated analysis, and simulated/demo values**.

---

# ⚠️ Demonstration & Data Disclaimer

FloodGuard AI is a **hackathon demonstration and decision-support prototype**.

The current system may use synthetic/demo data and controlled simulations. It should not be interpreted as a live municipal emergency-management platform.

The application does not directly control real emergency infrastructure.

AI-generated recommendations require appropriate human verification before any real-world implementation.

---

# 👥 Team

### FloodGuard AI

Built for the **AI-Powered Urban Flood Management** challenge.

The project focuses on combining:

**Machine Learning + Agentic AI + IBM Granite + Geospatial Intelligence + Evidence Fusion + Human-in-the-Loop Decision Support**

for urban flood-management scenarios.

---

## 🌊 FloodGuard AI

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
