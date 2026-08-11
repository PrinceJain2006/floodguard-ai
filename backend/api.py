"""
FloodGuard AI — FastAPI Backend
Provides REST API endpoints for all agent functionality.
"""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import uuid
from datetime import datetime, timedelta
from typing import Any, Optional
from fastapi import FastAPI, HTTPException, Depends, status, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field
from jose import JWTError, jwt
from passlib.context import CryptContext

from backend.config import JWT_SECRET_KEY, JWT_ALGORITHM, JWT_ACCESS_TOKEN_EXPIRE_MINUTES
from backend.models.database import create_tables
from agents.orchestrator import get_orchestrator, SCENARIOS

# ──────────────────────────────────────────────
app = FastAPI(
    title="FloodGuard AI API",
    description="Agentic AI for Predictive Urban Flood Management — Ahmedabad & Surat",
    version="1.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Create DB tables on startup
@app.on_event("startup")
async def startup():
    create_tables()

# ──────────────────────────────────────────────
# Auth helpers
# ──────────────────────────────────────────────
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/auth/token", auto_error=False)

# Demo users (replace with DB in production)
DEMO_USERS = {
    "citizen": {"username": "citizen", "role": "citizen",   "password": "citizen123",   "name": "Citizen User"},
    "operator": {"username": "operator","role": "operator", "password": "operator123",  "name": "Municipal Operator"},
    "admin":    {"username": "admin",   "role": "admin",    "password": "admin123",      "name": "Administrator"},
}


def create_token(data: dict) -> str:
    to_encode = data.copy()
    to_encode["exp"] = datetime.utcnow() + timedelta(minutes=JWT_ACCESS_TOKEN_EXPIRE_MINUTES)
    return jwt.encode(to_encode, JWT_SECRET_KEY, algorithm=JWT_ALGORITHM)


def get_current_user(token: str = Depends(oauth2_scheme)) -> dict | None:
    if not token:
        return None
    try:
        payload = jwt.decode(token, JWT_SECRET_KEY, algorithms=[JWT_ALGORITHM])
        username = payload.get("sub")
        return DEMO_USERS.get(username)
    except JWTError:
        return None


def require_operator(user: dict = Depends(get_current_user)) -> dict:
    if not user or user["role"] not in ("operator", "admin"):
        raise HTTPException(status_code=403, detail="Operator or admin role required")
    return user


# ──────────────────────────────────────────────
# Request / Response models
# ──────────────────────────────────────────────
class LoginRequest(BaseModel):
    username: str
    password: str


class CitizenReportRequest(BaseModel):
    text: str = Field(..., min_length=5, max_length=2000)
    area: str
    city: str = "Ahmedabad"
    latitude: float | None = None
    longitude: float | None = None


class ScenarioRequest(BaseModel):
    scenario: str = "NORMAL"
    city: str = "All"


class QueryRequest(BaseModel):
    question: str = Field(..., min_length=3, max_length=500)


class ApprovalRequest(BaseModel):
    approver: str
    reason: str | None = None


# ──────────────────────────────────────────────
# Auth endpoints
# ──────────────────────────────────────────────
@app.post("/auth/token")
async def login(form_data: OAuth2PasswordRequestForm = Depends()):
    user = DEMO_USERS.get(form_data.username)
    if not user or form_data.password not in (
        user["password"], pwd_context.hash(user["password"])
    ):
        # Simple plaintext check for demo
        if user and form_data.password == user["password"]:
            pass
        else:
            raise HTTPException(status_code=401, detail="Invalid credentials")
    token = create_token({"sub": user["username"], "role": user["role"]})
    return {"access_token": token, "token_type": "bearer", "role": user["role"], "name": user["name"]}


@app.post("/auth/login")
async def login_json(req: LoginRequest):
    user = DEMO_USERS.get(req.username)
    if not user or req.password != user["password"]:
        raise HTTPException(status_code=401, detail="Invalid credentials")
    token = create_token({"sub": user["username"], "role": user["role"]})
    return {"access_token": token, "token_type": "bearer", "role": user["role"], "name": user["name"]}


@app.get("/auth/me")
async def me(user: dict = Depends(get_current_user)):
    if not user:
        raise HTTPException(status_code=401, detail="Not authenticated")
    return {k: v for k, v in user.items() if k != "password"}


# ──────────────────────────────────────────────
# Core API endpoints
# ──────────────────────────────────────────────

@app.get("/")
async def root():
    return {
        "app": "FloodGuard AI",
        "version": "1.0.0",
        "status": "running",
        "description": "Agentic AI for Urban Flood Management — Ahmedabad & Surat",
    }


@app.get("/health")
async def health():
    orch = get_orchestrator()
    from agents.granite_service import granite_status
    return {
        "status": "healthy",
        "granite": granite_status(),
        "pipeline_initialized": orch._initialized,
        "current_scenario": orch.current_scenario,
        "timestamp": datetime.utcnow().isoformat(),
    }


# ── Scenario trigger ──────────────────────────
@app.post("/scenario/trigger")
async def trigger_scenario(req: ScenarioRequest):
    """Trigger a demo scenario — runs the full agent pipeline."""
    if req.scenario not in SCENARIOS:
        raise HTTPException(status_code=400, detail=f"Unknown scenario. Valid: {list(SCENARIOS.keys())}")
    orch = get_orchestrator()
    state = orch.run_pipeline(scenario=req.scenario, city=req.city)
    return {
        "scenario": req.scenario,
        "city": req.city,
        "elapsed_seconds": state["elapsed_seconds"],
        "summary": {
            "critical_zones": state["response_plan"]["summary"]["critical_zones"],
            "high_zones": state["response_plan"]["summary"]["high_zones"],
            "citizen_reports": state["response_plan"]["summary"]["citizen_reports"],
            "incidents": len(state["response_plan"]["incidents"]),
            "recommendations": len(state["response_plan"]["top_recommendations"]),
        },
        "data_label": "DEMO/SIMULATED",
    }


# ── Dashboard ─────────────────────────────────
@app.get("/dashboard")
async def dashboard():
    """Return current full dashboard state."""
    orch = get_orchestrator()
    if not orch.current_state:
        orch.run_pipeline("NORMAL")
    state = orch.current_state
    return {
        "scenario": state["scenario"],
        "city": state["city"],
        "last_updated": state["last_updated"],
        "risk_summary": {
            "critical": sum(1 for p in state["risk_predictions"] if p["risk_level"] == "CRITICAL"),
            "high":     sum(1 for p in state["risk_predictions"] if p["risk_level"] == "HIGH"),
            "medium":   sum(1 for p in state["risk_predictions"] if p["risk_level"] == "MEDIUM"),
            "low":      sum(1 for p in state["risk_predictions"] if p["risk_level"] == "LOW"),
        },
        "drain_summary": state["drain_analysis"]["priority_summary"],
        "report_summary": {
            "total":    state["report_analysis"]["total_reports"],
            "open":     state["report_analysis"]["open_reports"],
            "critical": state["report_analysis"]["critical_count"],
        },
        "alerts": state["alerts"],
        "situation_report": state["situation_report"],
        "data_label": "DEMO/SIMULATED",
    }


# ── Flood risk ────────────────────────────────
@app.get("/flood-risk")
async def get_flood_risk(city: str | None = None, level: str | None = None):
    orch = get_orchestrator()
    if not orch.current_state:
        orch.run_pipeline("NORMAL")
    preds = orch.current_state["risk_predictions"]
    if city:
        preds = [p for p in preds if p["city"] == city]
    if level:
        preds = [p for p in preds if p["risk_level"] == level.upper()]
    return {"predictions": preds, "count": len(preds), "data_label": "DEMO/SIMULATED"}


# ── Drains ────────────────────────────────────
@app.get("/drains")
async def get_drains(city: str | None = None, priority: str | None = None):
    orch = get_orchestrator()
    if not orch.current_state:
        orch.run_pipeline("NORMAL")
    drains = orch.current_state["drain_analysis"]["scored_drains"]
    if city:
        drains = [d for d in drains if d["city"] == city]
    if priority:
        drains = [d for d in drains if d["maintenance_priority"] == priority.upper()]
    return {"drains": drains, "count": len(drains), "data_label": "DEMO/SIMULATED"}


# ── Incidents ─────────────────────────────────
@app.get("/incidents")
async def get_incidents(city: str | None = None):
    orch = get_orchestrator()
    if not orch.current_state:
        orch.run_pipeline("NORMAL")
    incidents = orch.current_state["response_plan"]["incidents"]
    if city:
        incidents = [i for i in incidents if i["city"] == city]
    return {"incidents": incidents, "count": len(incidents), "data_label": "DEMO/SIMULATED"}


# ── Reports ───────────────────────────────────
@app.post("/reports")
async def submit_report(req: CitizenReportRequest):
    """Submit a new citizen flood report."""
    from agents.citizen_report_agent import get_citizen_agent
    agent = get_citizen_agent()
    orch = get_orchestrator()
    existing = orch.current_state["raw_reports"] if orch.current_state else []
    report = agent.process_report(
        text=req.text,
        area=req.area,
        city=req.city,
        latitude=req.latitude,
        longitude=req.longitude,
        existing_reports=existing,
    )
    return {"report": report, "message": "Report submitted successfully [DEMO]"}


@app.get("/reports")
async def get_reports(city: str | None = None, status: str | None = None, severity: str | None = None):
    orch = get_orchestrator()
    if not orch.current_state:
        orch.run_pipeline("NORMAL")
    reports = orch.current_state["raw_reports"]
    if city:
        reports = [r for r in reports if r["city"] == city]
    if status:
        reports = [r for r in reports if r.get("status", "").upper() == status.upper()]
    if severity:
        reports = [r for r in reports if r.get("severity", "").upper() == severity.upper()]
    return {"reports": reports, "count": len(reports), "data_label": "DEMO/SIMULATED"}


# ── Alerts ────────────────────────────────────
@app.get("/alerts")
async def get_alerts():
    orch = get_orchestrator()
    if not orch.current_state:
        orch.run_pipeline("NORMAL")
    return {
        "alerts": orch.current_state["alerts"],
        "count": len(orch.current_state["alerts"]),
        "note": "SIMULATED alerts — not real emergency notifications",
    }


# ── Recommendations ───────────────────────────
@app.get("/recommendations")
async def get_recommendations():
    orch = get_orchestrator()
    if not orch.current_state:
        orch.run_pipeline("NORMAL")
    recs = orch.current_state["response_plan"]["top_recommendations"]
    return {"recommendations": recs, "count": len(recs), "data_label": "DEMO/SIMULATED"}


@app.post("/recommendations/{rec_id}/approve")
async def approve_recommendation(rec_id: str, req: ApprovalRequest, user: dict = Depends(require_operator)):
    orch = get_orchestrator()
    result = orch.response_agent.approve_action(rec_id, 0, req.approver or user.get("username", "operator"))
    return {"status": "approved", "result": result}


@app.post("/recommendations/{rec_id}/reject")
async def reject_recommendation(rec_id: str, req: ApprovalRequest, user: dict = Depends(require_operator)):
    orch = get_orchestrator()
    result = orch.response_agent.reject_action(
        rec_id, 0, req.approver or user.get("username", "operator"),
        req.reason or "Rejected by operator"
    )
    return {"status": "rejected", "result": result}


# ── Agent monitor ─────────────────────────────
@app.get("/agents/status")
async def agent_status():
    orch = get_orchestrator()
    return {
        "agents": orch.get_agent_statuses(),
        "pipeline_log": orch.pipeline_log[-15:],
        "current_scenario": orch.current_scenario,
    }


# ── Natural language query ────────────────────
@app.post("/agent/analyze")
async def agent_query(req: QueryRequest):
    """Answer a natural language question using application data."""
    orch = get_orchestrator()
    if not orch.current_state:
        orch.run_pipeline("NORMAL")
    answer = orch.query(req.question)
    return {
        "question": req.question,
        "answer": answer,
        "data_source": "DEMO/SIMULATED",
        "note": "Answer grounded in demo data. Not real-time government data.",
    }


# ── Damage assessment ─────────────────────────
@app.post("/damage/assess")
async def assess_damage(incident_id: str, city: str, area: str, description: str):
    from agents.damage_assessment_agent import get_damage_agent
    agent = get_damage_agent()
    result = agent.assess_incident(
        incident_id=incident_id,
        city=city,
        area=area,
        latitude=0,
        longitude=0,
        description=description,
    )
    return result


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000, reload=True)
