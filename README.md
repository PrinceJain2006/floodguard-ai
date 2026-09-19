# 🌊 FloodGuard AI — AI Flood Command Center | IBM Granite | 🟢 LIVE (when configured) / ⚙ FALLBACK | **This is a hackathon demonstration.** It does not connect to real municipal emergency systems. AI recommendations require authorized human verification before any real-world implementation. --- ## Project Structure
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
--- ## Author Built for the IBM Hackathon — AI-Powered Urban Flood Management Challenge. FloodGuard AI demonstrates agentic AI, IBM Granite integration, ML explainability, and human-in-the-loop emergency response for Ahmedabad and Surat, Gujarat, India.
