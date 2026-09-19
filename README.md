# 🌊 FloodGuard AI — AI-Powered Urban Flood Intelligence & Command Center

> **Agentic AI-powered decision-support system for urban flood risk prediction, evidence analysis, drainage intelligence, citizen reporting, and human-approved response planning.**

**Built for the IBM Hackathon — AI-Powered Urban Flood Management Challenge**

FloodGuard AI combines **Machine Learning, Multi-Agent AI, IBM Granite, Geospatial Intelligence, Citizen Reports, Evidence Fusion, and Human-in-the-Loop decision making** into one operational flood intelligence platform.

> **FloodGuard AI doesn't just predict flooding. It converts prediction + citizen reports + drainage information into prioritized actions.**

---

## 🎯 The Problem

Rapid urbanization and changing rainfall patterns can place significant pressure on urban drainage infrastructure.

During heavy rainfall, authorities need to answer several questions quickly:

* Which areas are at higher flood risk?
* Which drainage assets require attention?
* What are citizens reporting?
* Which incidents should be prioritized?
* Why is a particular zone considered high risk?
* What response should be considered?
* Should an AI-generated recommendation be approved by a human?

Traditional systems can provide individual data points, but the challenge is turning those signals into **clear, explainable and prioritized decision support**.

---

# 💡 Our Solution

FloodGuard AI brings these signals together into a unified AI Flood Command Center.

### Core intelligence flow

```text
Rainfall + Water Level + Drainage
                │
                ▼
        Machine Learning
        Flood Risk Prediction
                │
                ▼
        Multi-Agent Analysis
        ┌───────┼────────┐
        ▼       ▼        ▼
     Risk    Drainage  Citizen
     Agent    Agent     Agent
        └───────┼────────┘
                ▼
          Evidence Fusion
                │
                ▼
        Zone Prioritization
                │
                ▼
          IBM Granite
     Analysis & Recommendation
                │
                ▼
        Human-in-the-Loop
             Approval
                │
                ▼
       Civic Response Plan
                │
                ▼
           Audit Trail
```

The system is designed as **decision support**. It does not directly control real municipal emergency infrastructure.

---

# 🧠 What FloodGuard AI Does

## 1. Flood Risk Prediction

The existing ML pipeline uses a **Random Forest-based flood-risk model** to analyze available flood-related features and estimate risk.

Relevant inputs can include factors such as:

* Rainfall
* Water level
* Drainage capacity
* Historical flood information
* Other available application features

The model output is used by the Flood Risk Agent and downstream decision-intelligence components.

---

## 2. Multi-Agent AI

FloodGuard AI uses a multi-agent architecture where different agents focus on different parts of the flood-management workflow.

| Agent                          | Responsibility                           |
| ------------------------------ | ---------------------------------------- |
| 🌧️ Flood Risk Agent           | Flood-risk prediction                    |
| 🔧 Drainage Agent              | Drainage condition and priority analysis |
| 📱 Citizen Report Agent        | Citizen incident classification          |
| 🚨 Response Coordination Agent | Response-plan generation                 |
| 🧠 Chief Response Agent        | Unified action planning                  |
| 🏚️ Damage Assessment Agent    | Damage assessment/scoring                |

The agents are coordinated through the existing orchestration layer.

---

# 🤖 IBM Granite Integration

FloodGuard AI integrates **IBM Granite through watsonx** for AI-powered analysis where configured.

Granite can be used to work with application context such as:

```text
Flood Risk
+
Drainage Information
+
Citizen Reports
+
Incident Context
        ↓
IBM Granite
        ↓
Situation Analysis
        ↓
Explanation / Recommendation
```

The application distinguishes between:

### 🟢 IBM Granite Execution

When the configured IBM service is available.

### ⚙️ Demo / Fallback Execution

When the external IBM service is unavailable.

Fallback behavior is clearly identified rather than being presented as live Granite execution.

---

# 🗺️ Geospatial Flood Intelligence

FloodGuard AI includes a map-based visualization layer for flood intelligence.

The map can be used to communicate:

* Flood-risk areas
* Geographic context
* Incidents
* Response areas
* Relevant flood information

The application uses the existing geospatial implementation rather than claiming unconnected real-world municipal GIS infrastructure.

---

# 📱 Citizen Flood Reporting

The Citizen Portal allows users to submit flood-related reports.

Example:

> “Road par bahut pani bhar gaya hai, school ke paas traffic jam hai.”

The existing citizen-report pipeline processes the report and can classify relevant information such as:

* Incident type
* Severity
* Location/context
* Priority
* Suggested response

Where supported by the current implementation, multilingual reporting includes:

**English • Hindi • Gujarati**

The processed report can then become part of the broader command-center decision workflow.

---

# 🚨 AI Flood Command Center

The Command Center brings the major signals together in one operational view.

It provides visibility into areas such as:

### Flood Situation

* Flood risk
* Rainfall
* Water level
* Drainage status
* Affected zones
* Active incidents

### AI Intelligence

* Agent activity
* Risk analysis
* Evidence fusion
* Granite analysis
* Recommendations

### Response

* Priority incidents
* Recommended actions
* Human approval
* Audit information

The goal is to move from:

**“Where is flooding likely?”**

to:

**“What should be prioritized and why?”**

---

# 🌧️ Flood Scenario Simulator

FloodGuard AI includes a simulation environment for demonstrating changing flood conditions.

The simulator allows controlled scenario inputs such as:

* Rainfall
* Drainage capacity
* Water level
* Citizen reports

The scenario can then be processed through the application's existing risk and response logic.

This enables a judge/demo user to observe how changing conditions can affect:

```text
Scenario
   ↓
Risk Prediction
   ↓
Agent Analysis
   ↓
Evidence Fusion
   ↓
Priority
   ↓
Recommendation
```

The simulator is intended for demonstration and controlled experimentation, not as a claim of live municipal forecasting.

---

# 🔍 AI Explainability

Flood prediction should not simply produce a risk score.

FloodGuard AI therefore exposes available model-level information such as:

* Feature importance
* Risk-related input values
* Model prediction information

The system can answer the important question:

> **“Why is this zone considered high risk?”**

This makes the prediction easier to interpret and connect with operational information.

---

# 📊 ML Evaluation

The project includes an ML evaluation layer for the implemented Random Forest pipeline.

Where supported by the current model/evaluation pipeline, the application can expose metrics such as:

* Accuracy
* Precision
* Recall
* F1 Score
* Cross-validation information
* Feature importance
* Confusion matrix

### ⚠️ Data Transparency

The current project includes a **synthetic/demo training dataset**.

Therefore, model performance shown by the application should be interpreted as evaluation of the implemented demonstration dataset and **not as proof of real-world municipal flood prediction accuracy**.

No performance numbers should be interpreted as validation on live Ahmedabad or Surat municipal data.

---

# 🔧 Drainage Intelligence

Drainage information is incorporated into the flood-risk and decision-support workflow.

The system can identify drainage-related risk and support maintenance prioritization.

Where the simulator is used, drainage conditions can be changed to explore their effect on the application's calculated flood-risk state.

This supports the broader workflow:

```text
Flood Risk
    +
Drainage Condition
    +
Other Evidence
       ↓
Priority
       ↓
Recommended Action
```

---

# 🧩 Evidence Fusion & Decision Intelligence

A major part of FloodGuard AI is combining multiple signals instead of relying on a single prediction.

Conceptually:

```text
ML Risk Prediction
        +
Drainage Intelligence
        +
Citizen Reports
        +
Incident Information
        ↓
Evidence Fusion
        ↓
Zone Prioritization
        ↓
AI Recommendation
```

This creates a bridge between **prediction** and **operational decision support**.

---

# 👤 Human-in-the-Loop

FloodGuard AI does not treat an AI recommendation as an automatic real-world command.

The intended workflow is:

```text
AI Detects Risk
      ↓
Evidence Analysis
      ↓
Zone Prioritization
      ↓
AI Recommendation
      ↓
Human Review
      ↓
Approval / Modification / Rejection
      ↓
Response State
      ↓
Audit Trail
```

This provides an additional layer of human oversight for critical decisions.

---

# 🧾 Audit Trail

Decision-related information can be recorded through the application's audit functionality.

This supports traceability around:

* Decisions
* Human approvals
* Response recommendations
* Timestamps
* Decision context

The objective is to make the decision process more transparent and reviewable.

---

# 🏗️ System Architecture

```text
                    FLOODGUARD AI
                         │
        ┌────────────────┼────────────────┐
        │                │                │
        ▼                ▼                ▼
   Data / Reports     ML Model       Weather/Data
        │                │                │
        └────────────────┼────────────────┘
                         ▼
                 Multi-Agent Layer
                         │
        ┌────────────────┼─────────────────┐
        │        │       │       │         │
        ▼        ▼       ▼       ▼         ▼
      Risk   Drainage Citizen Response  Damage
      Agent   Agent    Agent    Agent   Assessment
        │        │       │       │         │
        └────────┴───────┼───────┴─────────┘
                         ▼
                  Evidence Fusion
                         │
                         ▼
                 Decision Intelligence
                         │
                         ▼
                  IBM Granite
                         │
                         ▼
               Human-in-the-Loop
                         │
                         ▼
                  Civic Response
                         │
                         ▼
                    Audit Trail
```

---

# 📂 Project Structure

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

# 🔬 Technology Stack

| Technology                  | Role                                                       |
| --------------------------- | ---------------------------------------------------------- |
| **Python**                  | Core application and AI/ML implementation                  |
| **Streamlit**               | Interactive application interface                          |
| **Machine Learning**        | Flood-risk prediction                                      |
| **Random Forest**           | Risk classification/regression pipeline                    |
| **Multi-Agent AI**          | Specialized flood intelligence tasks                       |
| **IBM Granite**             | AI analysis and recommendation generation where configured |
| **IBM watsonx**             | Granite integration                                        |
| **Geospatial Intelligence** | Flood and incident visualization                           |
| **Folium**                  | Interactive map visualization                              |
| **Pandas / NumPy**          | Data processing                                            |
| **Scikit-learn**            | ML implementation/evaluation                               |

---

# 🔄 End-to-End Decision Flow

The core FloodGuard AI story can be summarized as:

```text
DETECT
  ↓
PREDICT
  ↓
ANALYZE
  ↓
EXPLAIN
  ↓
EVIDENCE FUSION
  ↓
PRIORITIZE
  ↓
AI RECOMMENDATION
  ↓
HUMAN APPROVAL
  ↓
CIVIC RESPONSE
  ↓
AUDIT
```

This is the central idea behind the project:

> **Prediction becomes useful when it can be explained, combined with contextual evidence, prioritized, and converted into a human-reviewed action plan.**

---

# 🎬 Suggested Demonstration Flow

For a short project demonstration:

### 1. Start at the Command Center

Show the overall flood situation and system status.

### 2. Open the Flood Scenario Simulator

Change rainfall, drainage, water level or citizen-report inputs.

### 3. Run the Scenario

Show the application's risk calculation and resulting state changes.

### 4. Open the Risk Map

Show how flood-risk information is represented geographically.

### 5. Show Agent Activity

Demonstrate the multi-agent workflow.

### 6. Submit a Citizen Report

Use a realistic English, Hindi or Gujarati example supported by the application.

### 7. Show AI Analysis

Demonstrate the citizen-report processing and, when configured, IBM Granite analysis.

### 8. Show Decision Intelligence

Explain how evidence is combined and the zone is prioritized.

### 9. Human Approval

Show the human-in-the-loop decision stage.

### 10. Show Audit Trail

Finish by demonstrating that the decision process is traceable.

---

# ⚠️ Demo & Data Disclaimer

FloodGuard AI is a **hackathon demonstration and decision-support prototype**.

The project does **not** directly control municipal emergency infrastructure.

Unless explicitly connected to an external production data source:

* Flood data may be synthetic/demo data.
* Model training data may be synthetic.
* Simulation values are controlled by the application.
* IBM Granite availability depends on configuration and credentials.
* Recommendations are intended for demonstration and human review.

The system should not be interpreted as a production municipal emergency-management system.

---

# 🚀 Running the Project

Install dependencies:

```bash
pip install -r requirements.txt
```

Start the Streamlit application:

```bash
streamlit run app.py
```

The application opens as a Streamlit web application.

For IBM Granite functionality, configure the required IBM/watsonx environment variables according to the project's configuration.

If IBM services are unavailable, the application can use its existing fallback/demo behavior where supported.

---

# 👥 Team

### FloodGuard AI

**Prince Jain**
**Alka Raikbar**
**Aniket Jaiswal**

---

# 🏁 Project Vision

FloodGuard AI aims to demonstrate how **Agentic AI + Machine Learning + IBM Granite + Geospatial Intelligence + Human Oversight** can work together for urban flood decision support.

The key idea is simple:

> 🌊 **Don't stop at predicting the flood. Help decision-makers understand the situation, prioritize what matters, and decide what should happen next.**

**FloodGuard AI — From Flood Prediction to Decision Intelligence.**
