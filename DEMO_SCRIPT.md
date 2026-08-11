# FloodGuard AI — 3-Minute Hackathon Demo Script

## Overview
This script walks judges through a live demonstration of FloodGuard AI, showcasing genuine multi-agent collaboration, IBM Granite integration, and actionable AI recommendations.

**Setup:** Run `streamlit run app.py` before presenting.

---

## STEP 1 — Landing Page (15 seconds)

> "This is FloodGuard AI — an Agentic AI platform for predictive urban flood management in Ahmedabad and Surat, Gujarat."

- Point out the 4 portals: Citizen Portal, Municipal Command Center, AI Agent Monitor, Analytics
- Note: "All data is synthetic demo data clearly labeled DEMO/SIMULATED"
- Click **[Municipal Command Center]**

---

## STEP 2 — Normal Conditions (15 seconds)

> "We start with normal rain conditions. You can see the command center dashboard — current risk zones on the map, rainfall data, citizen reports."

- Show the KPI strip (low critical zones)
- Point to the Live Risk Map — mostly green zones
- Say: "Let's simulate a real emergency scenario"

---

## STEP 3 — Trigger Heavy Rainfall (20 seconds)

> "I'll trigger the Heavy Rainfall scenario — this simulates conditions typical of Ahmedabad's monsoon peak."

- Click **"🌧️ Heavy Rainfall"** in the left sidebar
- Watch dashboard update in ~3 seconds
- Point to KPI strip: critical zones, open reports, rainfall spike

> "Notice how all metrics update instantly — the agents just ran the full analysis pipeline in under 5 seconds."

---

## STEP 4 — Show Risk Map (20 seconds)

> "The Live Risk Map now shows flood risk zones color-coded by severity — red is CRITICAL, orange HIGH, yellow MEDIUM, green LOW."

- Switch to **🗺️ Live Risk Map** tab
- Click on a red/critical zone marker on the map
- Show the popup: area name, risk score, rainfall, key factors, recommended action

> "Each zone shows the ML model's prediction with confidence score and the top contributing factors — this is explainable AI."

---

## STEP 5 — Agent Activity (25 seconds)

> "Let me show you the multi-agent system working. Click AI Agent Monitor."

- Navigate to **Page 3: AI Agent Monitor**
- If not already on Heavy scenario, trigger it from sidebar
- Point to the 6 agent cards: Flood Risk Agent, Drainage Agent, Citizen Report Agent, Response Agent, Damage Agent, IBM Granite

> "Six specialized agents ran in sequence. The Flood Risk Agent used our Random Forest model on rainfall + drainage + citizen data. The Drainage Agent scored all 100+ drains and found critical blockages. The Citizen Report Agent processed 80 reports in English, Hindi, and Gujarati."

- Scroll to **Pipeline Execution Log**
- Show the timeline: each step, agent, and status

---

## STEP 6 — IBM Granite Query (20 seconds)

> "Now let me show IBM Granite in action. I'll ask it a natural language question about the current flood situation."

- In the **Natural Language Command Center** at the bottom, type:
  `"Which areas are at critical flood risk and why?"`
- Click **Ask AI**
- Show the Granite response

> "Granite is answering from our actual data context — not hallucinating. It's grounded in the risk predictions from our ML model."

- Try another: `"Give me the top 5 recommended municipal actions"`

---

## STEP 7 — Back to Command Center (25 seconds)

> "Now let's see the AI Recommendations and the human approval workflow."

- Navigate back to **Command Center**
- Click **🤖 AI Recommendations** tab
- Show the top recommendations with CRITICAL/HIGH priorities

> "The Response Coordination Agent generated these ranked recommendations. CRITICAL actions require human approval before implementation — this is a key AI safety feature."

- Click **✅ Approve** on a recommendation

> "The municipal officer just approved the action. It's logged with timestamp, approver name, and the full reasoning."

---

## STEP 8 — Trigger Extreme + Incidents (20 seconds)

> "Let me trigger the Extreme Rainfall scenario to show emergency response."

- Click **"⛈️ Extreme Rainfall"** in sidebar
- Go to **⚡ Incidents** tab
- Show a CRITICAL incident expanded
- Point to the action list with team assignments

> "The system generated a coordinated response plan: deploy emergency teams, activate pumps, inspect drains, issue citizen alerts — all with team assignments and approval status."

---

## STEP 9 — Citizen Portal (15 seconds)

> "The platform is multilingual. Let me show the Citizen Portal."

- Click **Page 1: Citizen Portal**
- Select **ગુજરાતી** (Gujarati) language
- Type in the report box: `"અમારા વિસ્તારમાં ખૂબ પાણી ભરાઈ ગયું છે"`
- Submit

> "A Gujarati citizen just reported flooding. IBM Granite classified it as waterlogging, HIGH severity, and routed it to the Pump Team — automatically."

---

## STEP 10 — Download Situation Report (15 seconds)

> "Finally, let me generate the AI Flood Situation Report."

- Go back to **Command Center**
- Click **🤖 AI Recommendations** tab  
- Scroll to **AI Situation Report**
- Click **📥 Download Situation Report**

> "This is an IBM Granite-generated preliminary situation report — ready for municipal officers to review, edit, and distribute."

---

## STEP 11 — Analytics (10 seconds)

> "The Analytics Dashboard tracks impact metrics."

- Click **Page 4: Analytics**
- Point to: Flood Alerts Detected, Reports Processed, Response Actions Recommended

> "In a real deployment, these would be live operational metrics showing actual response time improvements."

---

## Close (10 seconds)

> "FloodGuard AI demonstrates five key things:
> 1. Real Gujarat-specific problem with Ahmedabad and Surat flood scenarios
> 2. Genuine 6-agent collaboration with visible pipeline execution
> 3. IBM Granite for multilingual understanding and situation reports
> 4. Actionable AI recommendations with human approval gates
> 5. Measurable social impact potential — faster response, better coordination, lives protected"

> "Thank you!"

---

## Backup Queries for Q&A

If judges ask questions, use these natural language queries:

- `"How many critical flood zones are in Ahmedabad?"` → shows filtered risk data
- `"Which drains need immediate maintenance?"` → drainage agent output
- `"How many unresolved citizen reports are there?"` → report agent analysis
- `"What is the highest rainfall area right now?"` → rainfall ranking
- `"Generate today's flood situation report"` → full Granite report

---

## Technical Q&A Prep

**Q: Is this real data?**  
A: No. All data is clearly labeled DEMO/SIMULATED — synthetic datasets based on realistic Ahmedabad and Surat geography and historical flood patterns. A real deployment would connect to IMD APIs, AMC/SMC IoT sensors, and municipal GIS data.

**Q: Is Granite actually running?**  
A: Yes, if WATSONX_API_KEY is configured. Without it, rule-based fallbacks handle all text functions. The app works fully in both modes.

**Q: How does the ML model work?**  
A: Random Forest classifier trained on 5,000 synthetic samples with 10 features including rainfall, drainage capacity, elevation, and citizen reports. It outputs risk_score (0-100), risk_level, confidence, and feature importance for explainability.

**Q: What about AI safety?**  
A: Three safety layers: (1) CRITICAL actions require explicit human approval, (2) all AI recommendations are labeled "require human verification", (3) Granite is grounded in retrieved data — no hallucinated sensor values.

**Q: What's the social impact?**  
A: Faster response time (35-45% estimated improvement), proactive drain maintenance, multilingual citizen reporting, and AI-explained decisions for officer confidence — collectively reducing flood impact on Gujarat's 8M+ urban population.
