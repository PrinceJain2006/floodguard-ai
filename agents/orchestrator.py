"""
FloodGuard AI — Agent Orchestrator
Central coordinator that runs all agents in sequence
and produces a unified system state for the dashboard.
Implements the multi-agent workflow pipeline.
"""
import json
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

try:
    from agents.flood_risk_agent import get_flood_risk_agent
    from agents.drainage_agent import get_drainage_agent
    from agents.citizen_report_agent import get_citizen_agent
    from agents.response_coordination_agent import get_response_agent
    from agents.damage_assessment_agent import get_damage_agent
    from agents.granite_service import (
        generate_situation_report, answer_query, granite_status,
        invalidate_granite_status_cache,
    )
    from agents.chief_response_agent import get_chief_agent
    from agents.closed_loop_learning import get_learning_store
    from data.seed_generator import (
        generate_rainfall_data, generate_drains, generate_flood_incidents,
        generate_citizen_reports, generate_response_teams, generate_risk_predictions, ALL_AREAS
    )
    from services.live_data_manager import get_live_data_manager
except ImportError:
    from flood_risk_agent import get_flood_risk_agent
    from drainage_agent import get_drainage_agent
    from citizen_report_agent import get_citizen_agent
    from response_coordination_agent import get_response_agent
    from damage_assessment_agent import get_damage_agent
    from granite_service import (
        generate_situation_report, answer_query, granite_status,
        invalidate_granite_status_cache,
    )
    from chief_response_agent import get_chief_agent
    from closed_loop_learning import get_learning_store
    try:
        from services.live_data_manager import get_live_data_manager
    except ImportError:
        get_live_data_manager = None  # type: ignore[assignment]


SCENARIOS = {
    "NORMAL":        {"label": "Normal Rain",       "emoji": "🌦️",  "rainfall_mult": 1.0},
    "HEAVY":         {"label": "Heavy Rainfall",    "emoji": "🌧️",  "rainfall_mult": 2.5},
    "EXTREME":       {"label": "Extreme Rainfall",  "emoji": "⛈️",  "rainfall_mult": 5.0},
    "CITIZEN_SURGE": {"label": "Citizen Surge",     "emoji": "📱",  "rainfall_mult": 2.0},
    "EMERGENCY":     {"label": "Emergency Response","emoji": "🚨",  "rainfall_mult": 4.5},
}


class AgentOrchestrator:
    """
    Central orchestrator for the FloodGuard AI multi-agent system.
    Manages agent lifecycle, data flow, and state updates.
    """

    def __init__(self):
        self.flood_agent  = get_flood_risk_agent()
        self.drain_agent  = get_drainage_agent()
        self.citizen_agent = get_citizen_agent()
        self.response_agent = get_response_agent()
        self.damage_agent = get_damage_agent()
        self.chief_agent  = get_chief_agent()
        self.learning_store = get_learning_store()

        self.current_scenario = "NORMAL"
        self.current_state: dict | None = None
        self.pipeline_log: list[dict] = []
        self._initialized = False

    def _log_step(self, step: str, agent: str, status: str, details: str = ""):
        self.pipeline_log.append({
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "step": step,
            "agent": agent,
            "status": status,
            "details": details,
        })
        if len(self.pipeline_log) > 100:
            self.pipeline_log = self.pipeline_log[-100:]

    def run_pipeline(self, scenario: str = "NORMAL", city: str = "All") -> dict:
        """
        Execute the full agent pipeline for a given scenario.
        
        Flow:
          Data Sources
          → Flood Risk Agent
          → Drainage Agent  
          → Citizen Report Agent
          → Response Coordination Agent
          → Granite Reasoning Layer
          → Unified State
        """
        self.current_scenario = scenario
        t_start = time.time()
        self._log_step("PIPELINE_START", "Orchestrator", "RUNNING", f"Scenario={scenario}, City={city}")

        # ── Step 1: Load data ──────────────────────────────────
        self._log_step("DATA_LOAD", "Orchestrator", "RUNNING", "Loading scenario data")
        rainfall = generate_rainfall_data(scenario)
        drains   = generate_drains()
        incidents = generate_flood_incidents()
        reports  = generate_citizen_reports(200 if scenario == "CITIZEN_SURGE" else 80)
        teams    = generate_response_teams()

        # Filter by city if specified
        if city != "All":
            rainfall  = [r for r in rainfall  if r["city"] == city]
            drains    = [d for d in drains    if d["city"] == city]
            incidents = [i for i in incidents if i["city"] == city]
            reports   = [r for r in reports   if r["city"] == city]
            teams     = [t for t in teams     if t["city"] == city]

        # ── Step 1b: Overlay live weather rainfall (if available) ──────────
        # For NORMAL scenario: blend live rainfall with synthetic data so the
        # ML model receives real current weather signals.
        # For non-NORMAL scenarios (HEAVY/EXTREME/etc.): preserve the synthetic
        # scenario-multiplied rainfall to keep the demo meaningful — live weather
        # is still fetched for the weather tab display but does NOT override
        # scenario-scaled rainfall used for risk prediction.
        live_weather_status = {"data_mode": "DEMO", "is_live": False, "fallback_reason": "not attempted"}
        live_weather_records: list[dict] = []
        live_weather_map_points: list[dict] = []
        try:
            if get_live_data_manager is not None:
                ldm = get_live_data_manager()
                ldm.refresh()
                live_weather_status = ldm.get_status()
                live_rf = ldm.get_rainfall_records(city_filter=city)
                if live_rf:
                    live_weather_records = live_rf
                    live_weather_map_points = ldm.weather_to_map_points(city_filter=city)

                    # Only blend live rainfall into risk-model input for NORMAL scenario.
                    # Non-NORMAL scenarios use scenario-scaled synthetic rainfall so that
                    # HEAVY/EXTREME/EMERGENCY produce meaningfully different risk outputs.
                    if scenario == "NORMAL":
                        live_lookup = {r["city"]: r for r in live_rf}
                        blended = []
                        for rec in rainfall:
                            live_rec = live_lookup.get(rec.get("city", ""))
                            if live_rec:
                                live_r1h  = live_rec["rainfall_1h"]
                                synth_r1h = rec.get("rainfall_1h", 1.0) or 1.0
                                scale     = max(0.1, min(live_r1h / synth_r1h, 10.0))
                                blended.append({
                                    **rec,
                                    "rainfall_1h":  round(live_r1h, 1),
                                    "rainfall_3h":  round(rec.get("rainfall_3h", 0) * scale, 1),
                                    "rainfall_6h":  round(rec.get("rainfall_6h", 0) * scale, 1),
                                    "rainfall_24h": round(rec.get("rainfall_24h", 0) * scale, 1),
                                    "data_source":  "Open-Meteo (LIVE, blended)",
                                    "is_live":      True,
                                })
                            else:
                                blended.append(rec)
                        rainfall = blended
                        self._log_step(
                            "LIVE_WEATHER", "LiveDataManager", "COMPLETE",
                            f"Live rainfall blended for NORMAL scenario ({len(live_rf)} city observations)"
                        )
                    else:
                        # Non-NORMAL: live weather fetched for display only; scenario
                        # rainfall multipliers drive the risk model.
                        self._log_step(
                            "LIVE_WEATHER", "LiveDataManager", "COMPLETE",
                            f"Live weather fetched for display; {scenario} scenario rainfall preserved"
                        )
        except Exception as exc:
            live_weather_status = {
                "data_mode": "DEMO",
                "is_live": False,
                "fallback_reason": f"Live weather error: {exc}",
            }
            self._log_step("LIVE_WEATHER", "LiveDataManager", "FALLBACK", str(exc))

        self._log_step("DATA_LOAD", "Orchestrator", "COMPLETE",
                       f"{len(rainfall)} areas, {len(drains)} drains, {len(reports)} reports")

        # ── Step 2: Flood Risk Agent ───────────────────────────
        self._log_step("FLOOD_RISK", "Flood Risk Agent", "RUNNING", "Analyzing rainfall and risk")
        risk_predictions = self.flood_agent.analyze_all_areas(
            rainfall_records=rainfall,
            drain_records=drains,
            report_records=reports,
            incident_records=incidents,
            area_meta=ALL_AREAS,
        )
        critical_count = sum(1 for p in risk_predictions if p["risk_level"] == "CRITICAL")
        high_count     = sum(1 for p in risk_predictions if p["risk_level"] == "HIGH")
        self._log_step("FLOOD_RISK", "Flood Risk Agent", "COMPLETE",
                       f"Analyzed {len(risk_predictions)} areas — {critical_count} CRITICAL, {high_count} HIGH")

        # ── Step 3: Drainage Agent ─────────────────────────────
        self._log_step("DRAINAGE", "Drainage Agent", "RUNNING", "Prioritizing drainage maintenance")
        drain_analysis = self.drain_agent.prioritize_drains(
            drains=drains,
            rainfall_records=rainfall,
            risk_predictions=risk_predictions,
        )
        self._log_step("DRAINAGE", "Drainage Agent", "COMPLETE",
                       f"Identified {len(drain_analysis['requires_immediate_action'])} critical drains")

        # ── Step 4: Citizen Report Agent ──────────────────────
        self._log_step("CITIZEN_REPORTS", "Citizen Report Agent", "RUNNING", "Analyzing citizen reports")
        report_analysis = self.citizen_agent.batch_analyze(reports)
        self._log_step("CITIZEN_REPORTS", "Citizen Report Agent", "COMPLETE",
                       f"Processed {report_analysis['total_reports']} reports, "
                       f"{report_analysis['open_reports']} open")

        # ── Step 5: Damage Assessment Agent ───────────────────
        # Runs BEFORE the response agent so damage intelligence informs response planning.
        self._log_step("DAMAGE_ASSESSMENT", "Damage Assessment Agent", "RUNNING",
                       "Assessing damage from incident reports")
        damage_assessment_result: dict = {"assessments": [], "summary": {}, "is_preliminary": True}
        try:
            active_incidents = [
                inc for inc in incidents
                if inc.get("status") in ("ACTIVE", "RESOLVED")
            ]
            if active_incidents:
                damage_assessment_result = self.damage_agent.batch_assess(active_incidents)
                severe_count = damage_assessment_result["summary"].get("severe_count", 0)
                total_assessed = damage_assessment_result["summary"].get("total_assessed", 0)
                self._log_step("DAMAGE_ASSESSMENT", "Damage Assessment Agent", "COMPLETE",
                               f"Assessed {total_assessed} incidents — {severe_count} severe/high damage")
            else:
                self._log_step("DAMAGE_ASSESSMENT", "Damage Assessment Agent", "COMPLETE",
                               "No active/resolved incidents to assess")
        except Exception as exc:
            self._log_step("DAMAGE_ASSESSMENT", "Damage Assessment Agent", "ERROR", str(exc))

        # ── Step 6: Response Coordination Agent ───────────────
        self._log_step("RESPONSE", "Response Coordination Agent", "RUNNING", "Generating response plan")
        response_plan = self.response_agent.coordinate(
            risk_predictions=risk_predictions,
            drain_analysis=drain_analysis,
            report_analysis=report_analysis,
            response_teams=teams,
            city=city,
        )
        self._log_step("RESPONSE", "Response Coordination Agent", "COMPLETE",
                       f"Generated {len(response_plan['incidents'])} incidents, "
                       f"{len(response_plan['top_recommendations'])} recommendations")

        # ── Step 7: Granite reasoning layer ───────────────────
        # generate_situation_report uses the module-level generation cache so
        # repeated pipeline runs with the same scenario / zone counts won't fire
        # duplicate Granite requests.  We call granite_status() AFTER the
        # generation attempt so the status accurately reflects whether generation
        # succeeded (the status probe result is cached for _STATUS_CACHE_TTL).
        self._log_step("GRANITE", "IBM Granite", "RUNNING", "Generating situation summary")
        situation_report = generate_situation_report(
            city=city if city != "All" else "Ahmedabad & Surat",
            scenario=scenario,
            summary_data=response_plan["summary"],
        )
        # Invalidate the status cache so the next call reflects the generation
        # outcome (either LIVE if the call succeeded, or RATE_LIMITED/FALLBACK).
        invalidate_granite_status_cache()
        g_status = granite_status()
        self._log_step(
            "GRANITE", "IBM Granite", "COMPLETE",
            "🟢 Live — IBM Granite generation" if g_status["available"]
            else "🟠 Rate limited — rule-based fallback" if g_status["rate_limited"]
            else "⚙ Fallback mode (configure WatsonX credentials)",
        )

        # ── Step 8: Chief Response Agent ──────────────────────
        self._log_step("CHIEF_RESPONSE", "Chief Response Agent", "RUNNING",
                       "Generating unified emergency action plan")
        action_plan = self.chief_agent.generate_action_plan(
            risk_predictions=risk_predictions,
            drain_analysis=drain_analysis,
            report_analysis=report_analysis,
            response_plan=response_plan,
            teams=teams,
            scenario=scenario,
        )
        resource_recs = self.chief_agent.get_resource_recommendations(
            risk_predictions=risk_predictions,
            teams=teams,
            scenario=scenario,
        )
        self._log_step("CHIEF_RESPONSE", "Chief Response Agent", "COMPLETE",
                       f"{action_plan['total_actions']} actions, {action_plan['approval_needed']} need approval")

        # ── Step 9: Closed-loop learning ──────────────────────
        self._log_step("LEARNING", "Closed-Loop Learning", "RUNNING",
                       "Seeding prediction-outcome cycles")
        # Reset learning store on each new pipeline run
        self.learning_store._initialized = False
        learning_cycles = self.learning_store.get_cycles(
            scenario=scenario,
            risk_predictions=risk_predictions,
        )
        self._log_step("LEARNING", "Closed-Loop Learning", "COMPLETE",
                       f"{len(learning_cycles)} cycles recorded")

        # ── Step 10: Build alerts (legacy simple alerts) ──────
        alerts = _generate_alerts(risk_predictions, response_plan, scenario)

        # ── Step 11: Flood Alert Engine ───────────────────────
        # The alert engine runs risk fusion and generates structured alerts
        # with de-duplication, expected risk window, and notification dispatch.
        alert_engine = None
        rich_alerts: list[dict] = []
        try:
            from services.flood_alert_engine import get_alert_engine
            alert_engine = get_alert_engine()
            rich_alerts = alert_engine.process_pipeline_output(
                state={
                    "risk_predictions": risk_predictions,
                    "drain_analysis": drain_analysis,
                    "report_analysis": report_analysis,
                    "rainfall_data": rainfall,
                    "scenario": scenario,
                },
                is_simulation=(scenario != "NORMAL"),
            )
            self._log_step(
                "ALERT_ENGINE", "Flood Alert Engine", "COMPLETE",
                f"Generated {len(rich_alerts)} new alert(s). "
                f"Active: {len(alert_engine.get_active_alerts())}",
            )
        except Exception as exc:
            self._log_step("ALERT_ENGINE", "Flood Alert Engine", "ERROR", str(exc))

        # ── Assemble state ─────────────────────────────────────
        elapsed = round(time.time() - t_start, 2)
        self.current_state = {
            "scenario": scenario,
            "city": city,
            "risk_predictions": risk_predictions,
            "drain_analysis": drain_analysis,
            "report_analysis": report_analysis,
            "damage_assessment": damage_assessment_result,
            "response_plan": response_plan,
            "situation_report": situation_report,
            "action_plan": action_plan,
            "resource_recommendations": resource_recs,
            "learning_cycles": learning_cycles,
            "alerts": alerts,
            "rich_alerts": alert_engine.get_active_alerts() if alert_engine else [],
            "teams": teams,
            "rainfall_data": rainfall,
            "raw_reports": reports,
            "raw_drains": drains,
            "granite_status": g_status,
            "pipeline_log": self.pipeline_log[-20:],
            "elapsed_seconds": elapsed,
            "data_label": "DEMO/SIMULATED",
            "last_updated": datetime.now(timezone.utc).isoformat(),
            # Live weather intelligence
            "live_weather_status":      live_weather_status,
            "live_weather_records":     live_weather_records,
            "live_weather_map_points":  live_weather_map_points,
        }

        self._log_step("PIPELINE_COMPLETE", "Orchestrator", "COMPLETE",
                       f"Pipeline finished in {elapsed}s")
        self._initialized = True
        return self.current_state

    def get_agent_statuses(self) -> list[dict]:
        """Return current status of all agents.

        Uses the cached granite_status() result — does NOT fire a new probe on
        every call.  The cache is refreshed after each pipeline run.
        """
        # Single call — result is module-level cached for _STATUS_CACHE_TTL
        g_st = granite_status()
        g_avail       = g_st["available"]
        g_rate        = g_st.get("rate_limited", False)
        g_config_err  = g_st.get("config_error", False)

        if g_avail:
            g_status_label = "LIVE"
        elif g_rate:
            g_status_label = "RATE LIMITED"
        elif g_config_err:
            g_status_label = "CONFIG ERROR"
        else:
            g_status_label = "FALLBACK"

        recent: list[str] = [f"Model: {g_st['model']}"]
        if g_avail:
            recent.append("🟢 IBM Granite — Live generation")
        elif g_rate:
            recent.append("🟠 Rate limited — rule-based fallback active")
        elif g_config_err:
            recent.append("🔴 Configuration error — check credentials")
        else:
            recent.append("⚙ Rule-based fallback — configure WatsonX credentials")

        return [
            self.flood_agent.get_status(),
            self.drain_agent.get_status(),
            self.citizen_agent.get_status(),
            self.response_agent.get_status(),
            self.damage_agent.get_status(),
            self.chief_agent.get_status(),
            {
                "agent": "IBM Granite",
                "status": g_status_label,
                "last_run": self.current_state.get("last_updated") if self.current_state else None,
                "recent_activity": recent,
            },
        ]

    def query(self, question: str) -> str:
        """Answer a natural language query using current state."""
        if not self.current_state:
            return "Please run an analysis scenario first."

        context = {
            "predictions": self.current_state.get("risk_predictions", [])[:10],
            "drains": self.current_state.get("raw_drains", [])[:20],
            "reports": self.current_state.get("raw_reports", [])[:20],
            "rainfall": self.current_state.get("rainfall_data", [])[:10],
            "scenario": self.current_state.get("scenario"),
            "city": self.current_state.get("city"),
        }
        return answer_query(question, context)


def _generate_alerts(
    risk_predictions: list[dict],
    response_plan: dict,
    scenario: str,
) -> list[dict]:
    alerts = []
    counter = 1

    critical = [p for p in risk_predictions if p["risk_level"] == "CRITICAL"]
    high = [p for p in risk_predictions if p["risk_level"] == "HIGH"]

    for area_risk in critical[:3]:
        alerts.append({
            "alert_id": f"ALT-{counter:04d}",
            "alert_level": "CRITICAL",
            "alert_type": "citizen",
            "city": area_risk["city"],
            "area": area_risk["area"],
            "title": f"🚨 FLOOD ALERT: {area_risk['area']}",
            "message": (
                f"CRITICAL flood risk in {area_risk['area']}, {area_risk['city']}. "
                f"Rainfall: {area_risk.get('input_features', {}).get('rainfall_1h', 0):.0f} mm/hr. "
                "Avoid low-lying areas. Move valuables to higher ground. Follow municipal instructions."
            ),
            "is_simulated": True,
            "created_at": datetime.now(timezone.utc).isoformat(),
        })
        counter += 1

    for area_risk in high[:2]:
        alerts.append({
            "alert_id": f"ALT-{counter:04d}",
            "alert_level": "HIGH",
            "alert_type": "operator",
            "city": area_risk["city"],
            "area": area_risk["area"],
            "title": f"⚠️ HIGH RISK: {area_risk['area']}",
            "message": (
                f"High flood risk detected in {area_risk['area']}, {area_risk['city']}. "
                "Flood risk score: " + str(area_risk["risk_score"]) + "/100. "
                "Pre-position response teams."
            ),
            "is_simulated": True,
            "created_at": datetime.now(timezone.utc).isoformat(),
        })
        counter += 1

    if response_plan.get("requires_emergency_protocol"):
        alerts.append({
            "alert_id": f"ALT-{counter:04d}",
            "alert_level": "CRITICAL",
            "alert_type": "emergency",
            "city": response_plan["city"],
            "area": None,
            "title": "🚨 EMERGENCY PROTOCOL ACTIVATED",
            "message": (
                f"Emergency flood protocol activated for {response_plan['city']}. "
                "All response teams on high alert. Senior officers notified. "
                "Human authorization required for emergency actions."
            ),
            "is_simulated": True,
            "created_at": datetime.now(timezone.utc).isoformat(),
        })

    return alerts


# ──────────────────────────────────────────────
# Singleton
# ──────────────────────────────────────────────
_orchestrator: AgentOrchestrator | None = None


def get_orchestrator() -> AgentOrchestrator:
    global _orchestrator
    if _orchestrator is None:
        _orchestrator = AgentOrchestrator()
    return _orchestrator
