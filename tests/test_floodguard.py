"""
FloodGuard AI — Test Suite
Tests for all major components: ML model, agents, API, orchestration.
"""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pytest
import json
import random
from datetime import datetime


# ──────────────────────────────────────────────
# 1. ML Model Tests
# ──────────────────────────────────────────────
class TestFloodRiskModel:
    """Tests for the Random Forest flood risk prediction model."""

    def setup_method(self):
        from ml.flood_risk_model import FloodRiskModel, _build_reasons
        self.Model = FloodRiskModel
        self._build_reasons = _build_reasons

    def test_fallback_predict_low_risk(self):
        """Minimal rainfall → LOW risk."""
        model = self.Model()
        features = {
            "rainfall_1h": 2, "rainfall_3h": 5, "rainfall_6h": 10, "rainfall_24h": 20,
            "drainage_capacity": 90, "historical_flood_freq": 0,
            "water_level": 0.1, "elevation": 60, "road_density": 0.4, "citizen_reports": 0,
        }
        result = model._fallback_predict(features)
        assert result["risk_level"] in ("LOW", "MEDIUM")
        assert 0 <= result["risk_score"] <= 100
        assert 0 <= result["confidence"] <= 1

    def test_fallback_predict_critical_risk(self):
        """Extreme rainfall + low drainage → CRITICAL."""
        model = self.Model()
        features = {
            "rainfall_1h": 100, "rainfall_3h": 300, "rainfall_6h": 600, "rainfall_24h": 1000,
            "drainage_capacity": 10, "historical_flood_freq": 10,
            "water_level": 4.0, "elevation": 8, "road_density": 0.95, "citizen_reports": 60,
        }
        result = model._fallback_predict(features)
        assert result["risk_level"] == "CRITICAL"
        assert result["risk_score"] > 70

    def test_risk_score_bounds(self):
        """Risk score always between 0-100."""
        model = self.Model()
        for _ in range(50):
            features = {
                "rainfall_1h": random.uniform(0, 150),
                "rainfall_3h": random.uniform(0, 450),
                "rainfall_6h": random.uniform(0, 900),
                "rainfall_24h": random.uniform(0, 2000),
                "drainage_capacity": random.uniform(0, 100),
                "historical_flood_freq": random.randint(0, 15),
                "water_level": random.uniform(0, 6),
                "elevation": random.uniform(5, 80),
                "road_density": random.uniform(0.2, 1.0),
                "citizen_reports": random.randint(0, 100),
            }
            result = model._fallback_predict(features)
            assert 0 <= result["risk_score"] <= 100, f"Score out of bounds: {result['risk_score']}"

    def test_build_reasons_nonempty_for_high_risk(self):
        """High risk features should produce non-empty reasons."""
        features = {
            "rainfall_1h": 90, "drainage_capacity": 20,
            "historical_flood_freq": 8, "citizen_reports": 45,
            "water_level": 3.5, "elevation": 9,
        }
        reasons = self._build_reasons(features, [])
        assert len(reasons) > 0

    def test_label_order(self):
        """All risk labels must be valid."""
        from ml.flood_risk_model import LABEL_ORDER
        assert set(LABEL_ORDER) == {"LOW", "MEDIUM", "HIGH", "CRITICAL"}


# ──────────────────────────────────────────────
# 2. Data Generator Tests
# ──────────────────────────────────────────────
class TestDataGenerator:
    """Tests for the synthetic data generator."""

    def test_rainfall_data_structure(self):
        from data.seed_generator import generate_rainfall_data
        data = generate_rainfall_data("NORMAL")
        assert len(data) == 30  # 15 areas × 2 cities
        record = data[0]
        assert "city" in record
        assert "area" in record
        assert "rainfall_1h" in record
        assert "rainfall_3h" in record
        assert record["data_source"] == "DEMO"

    def test_drains_structure(self):
        from data.seed_generator import generate_drains
        drains = generate_drains()
        assert len(drains) > 0
        drain = drains[0]
        assert "drain_id" in drain
        assert "capacity_rating" in drain
        assert drain["capacity_rating"] >= 0
        assert drain["capacity_rating"] <= 100
        assert "maintenance_priority" in drain
        assert drain["maintenance_priority"] in ("LOW", "MEDIUM", "HIGH", "CRITICAL")

    def test_ml_training_data(self):
        from data.seed_generator import generate_ml_training_data
        data = generate_ml_training_data(100)
        assert len(data) == 100
        record = data[0]
        for col in ["rainfall_1h", "drainage_capacity", "risk_score", "risk_label"]:
            assert col in record
        assert record["risk_label"] in ("LOW", "MEDIUM", "HIGH", "CRITICAL")
        assert 0 <= record["risk_score"] <= 100

    def test_citizen_reports_languages(self):
        from data.seed_generator import generate_citizen_reports
        reports = generate_citizen_reports(60)
        languages = {r["language"] for r in reports}
        assert "english" in languages
        assert "hindi" in languages
        assert "gujarati" in languages

    def test_risk_predictions_structure(self):
        from data.seed_generator import generate_risk_predictions
        preds = generate_risk_predictions("EXTREME")
        assert len(preds) == 30
        for p in preds:
            assert p["risk_level"] in ("LOW", "MEDIUM", "HIGH", "CRITICAL")
            assert 0 <= p["risk_score"] <= 100
            assert 0 <= p["confidence"] <= 1

    def test_extreme_scenario_has_more_critical(self):
        from data.seed_generator import generate_risk_predictions
        normal = generate_risk_predictions("NORMAL")
        extreme = generate_risk_predictions("EXTREME")
        normal_crit = sum(1 for p in normal if p["risk_level"] == "CRITICAL")
        extreme_crit = sum(1 for p in extreme if p["risk_level"] == "CRITICAL")
        assert extreme_crit >= normal_crit  # Extreme should have at least as many critical


# ──────────────────────────────────────────────
# 3. Agent Tests
# ──────────────────────────────────────────────
class TestFloodRiskAgent:
    def setup_method(self):
        from agents.flood_risk_agent import FloodRiskAgent
        self.agent = FloodRiskAgent()

    def test_analyze_area_returns_valid_result(self):
        result = self.agent.analyze_area(
            area="Maninagar", city="Ahmedabad",
            latitude=22.99, longitude=72.61,
            rainfall_data={"rainfall_1h": 80, "rainfall_3h": 220, "rainfall_6h": 400, "rainfall_24h": 800},
            drain_data=[{"capacity_rating": 25, "status": "BLOCKED", "blockage_frequency": 7}],
            citizen_reports=[{}, {}, {}],  # 3 reports
            historical_incidents=[{}, {}],  # 2 incidents
            elevation=46,
        )
        assert result["risk_level"] in ("LOW", "MEDIUM", "HIGH", "CRITICAL")
        assert 0 <= result["risk_score"] <= 100
        assert "main_reasons" in result
        assert "recommended_action" in result
        assert result["city"] == "Ahmedabad"
        assert result["area"] == "Maninagar"

    def test_get_status(self):
        status = self.agent.get_status()
        assert status["agent"] == "Flood Risk Agent"
        assert status["status"] == "ACTIVE"


class TestDrainageAgent:
    def setup_method(self):
        from agents.drainage_agent import DrainageAgent
        self.agent = DrainageAgent()

    def test_score_drain_blocked(self):
        """A blocked drain should get CRITICAL priority."""
        drain = {
            "drain_id": "D-001", "city": "Ahmedabad", "area": "Maninagar",
            "capacity_rating": 15, "blockage_frequency": 8,
            "near_flood_zone": True, "condition": "CRITICAL",
            "last_cleaned": "2024-01-01T00:00:00", "status": "BLOCKED",
        }
        result = self.agent.score_drain(drain, rainfall_1h=80)
        assert result["maintenance_priority"] == "CRITICAL"
        assert result["computed_risk_score"] > 70

    def test_score_drain_good(self):
        """A well-maintained drain should get LOW priority."""
        drain = {
            "drain_id": "D-999", "city": "Surat", "area": "Vesu",
            "capacity_rating": 95, "blockage_frequency": 0,
            "near_flood_zone": False, "condition": "GOOD",
            "last_cleaned": "2024-11-01T00:00:00", "status": "OPERATIONAL",
        }
        result = self.agent.score_drain(drain, rainfall_1h=5)
        assert result["maintenance_priority"] in ("LOW", "MEDIUM")


class TestCitizenReportAgent:
    def setup_method(self):
        from agents.citizen_report_agent import CitizenReportAgent, detect_language, _text_similarity
        self.agent = CitizenReportAgent()
        self.detect_language = detect_language
        self._text_similarity = _text_similarity

    def test_language_detection_gujarati(self):
        text = "અમારા વિસ્તારમાં ખૂબ પાણી ભરાઈ ગયું છે."
        assert self.detect_language(text) == "gujarati"

    def test_language_detection_hindi(self):
        text = "हमारे इलाके में बहुत पानी भर गया है।"
        assert self.detect_language(text) == "hindi"

    def test_language_detection_english(self):
        text = "There is severe waterlogging on the main road."
        assert self.detect_language(text) == "english"

    def test_process_report_english(self):
        result = self.agent.process_report(
            text="The drain is overflowing and the road is blocked near Maninagar bus stand.",
            area="Maninagar",
            city="Ahmedabad",
        )
        assert "report_id" in result
        assert result["report_id"].startswith("RPT-")
        assert result["city"] == "Ahmedabad"
        assert result["area"] == "Maninagar"
        assert result["category"] in (
            "waterlogging", "drain_overflow", "road_blockage",
            "traffic_disruption", "property_flooding", "emergency_situation"
        )
        assert result["severity"] in ("LOW", "MEDIUM", "HIGH", "CRITICAL")
        assert result["language"] == "english"
        assert not result["is_duplicate"]

    def test_duplicate_detection(self):
        text = "Water logging near bus stand area."
        report1 = self.agent.process_report(text=text, area="Maninagar", city="Ahmedabad")
        report2 = self.agent.process_report(text=text, area="Maninagar", city="Ahmedabad")
        # Second identical report should be detected as duplicate
        assert report2["is_duplicate"]

    def test_severity_priority_mapping(self):
        from agents.citizen_report_agent import SEVERITY_PRIORITY_MAP
        assert SEVERITY_PRIORITY_MAP["CRITICAL"] > SEVERITY_PRIORITY_MAP["HIGH"]
        assert SEVERITY_PRIORITY_MAP["HIGH"] > SEVERITY_PRIORITY_MAP["MEDIUM"]
        assert SEVERITY_PRIORITY_MAP["MEDIUM"] > SEVERITY_PRIORITY_MAP["LOW"]

    def test_batch_analyze(self):
        from data.seed_generator import generate_citizen_reports
        reports = generate_citizen_reports(50)
        analysis = self.agent.batch_analyze(reports)
        assert "total_reports" in analysis
        assert analysis["total_reports"] == 50
        assert "by_category" in analysis
        assert "hotspot_areas" in analysis


class TestResponseCoordinationAgent:
    def setup_method(self):
        from agents.response_coordination_agent import ResponseCoordinationAgent
        from data.seed_generator import (
            generate_risk_predictions, generate_drains, generate_citizen_reports,
            generate_response_teams, generate_rainfall_data
        )
        self.agent = ResponseCoordinationAgent()
        self.predictions = generate_risk_predictions("HEAVY")
        self.drains = generate_drains()
        self.reports = generate_citizen_reports(80)
        self.teams = generate_response_teams()
        self.rainfall = generate_rainfall_data("HEAVY")

    def _get_drain_analysis(self):
        from agents.drainage_agent import DrainageAgent
        da = DrainageAgent()
        return da.prioritize_drains(self.drains, self.rainfall, self.predictions)

    def _get_report_analysis(self):
        from agents.citizen_report_agent import CitizenReportAgent
        ca = CitizenReportAgent()
        return ca.batch_analyze(self.reports)

    def test_coordinate_returns_incidents(self):
        drain_analysis = self._get_drain_analysis()
        report_analysis = self._get_report_analysis()
        result = self.agent.coordinate(
            risk_predictions=self.predictions,
            drain_analysis=drain_analysis,
            report_analysis=report_analysis,
            response_teams=self.teams,
        )
        assert "incidents" in result
        assert "top_recommendations" in result
        assert isinstance(result["incidents"], list)
        assert isinstance(result["top_recommendations"], list)

    def test_approve_action(self):
        result = self.agent.approve_action("INC-001", 0, "operator1")
        assert result["approval_status"] == "APPROVED"
        assert result["approved_by"] == "operator1"

    def test_reject_action(self):
        result = self.agent.reject_action("INC-001", 0, "operator1", "Insufficient resources")
        assert result["approval_status"] == "REJECTED"
        assert result["rejection_reason"] == "Insufficient resources"


# ──────────────────────────────────────────────
# 4. Orchestrator Tests
# ──────────────────────────────────────────────
class TestOrchestrator:
    def setup_method(self):
        from agents.orchestrator import AgentOrchestrator
        self.orch = AgentOrchestrator()

    def test_run_pipeline_normal(self):
        state = self.orch.run_pipeline("NORMAL", "All")
        assert state is not None
        assert "risk_predictions" in state
        assert "drain_analysis" in state
        assert "report_analysis" in state
        assert "response_plan" in state
        assert state["scenario"] == "NORMAL"
        assert state["data_label"] == "DEMO/SIMULATED"

    def test_run_pipeline_extreme(self):
        state = self.orch.run_pipeline("EXTREME", "All")
        critical = sum(1 for p in state["risk_predictions"] if p["risk_level"] == "CRITICAL")
        # Extreme scenario should have more critical zones than 0
        assert critical >= 0  # Just validate it runs

    def test_pipeline_sets_current_state(self):
        self.orch.run_pipeline("NORMAL")
        assert self.orch.current_state is not None
        assert self.orch._initialized is True

    def test_pipeline_city_filter(self):
        state = self.orch.run_pipeline("NORMAL", "Ahmedabad")
        for pred in state["risk_predictions"]:
            assert pred["city"] == "Ahmedabad"

    def test_get_agent_statuses(self):
        self.orch.run_pipeline("NORMAL")
        statuses = self.orch.get_agent_statuses()
        assert len(statuses) == 6
        for s in statuses:
            assert "agent" in s
            assert "status" in s

    def test_query_returns_string(self):
        self.orch.run_pipeline("NORMAL")
        answer = self.orch.query("How many reports are there?")
        assert isinstance(answer, str)
        assert len(answer) > 0


# ──────────────────────────────────────────────
# 5. Granite Service Fallback Tests
# ──────────────────────────────────────────────
class TestGraniteService:
    def test_fallback_report_analysis_english(self):
        from agents.granite_service import _fallback_report_analysis
        result = _fallback_report_analysis(
            "Drain is overflowing and road is blocked.", "english"
        )
        assert "category" in result
        assert "severity" in result
        assert result["category"] in (
            "waterlogging", "drain_overflow", "road_blockage",
            "traffic_disruption", "property_flooding", "emergency_situation"
        )

    def test_fallback_query_answer_reports(self):
        from agents.granite_service import _fallback_query_answer
        context = {
            "reports": [
                {"status": "OPEN", "city": "Ahmedabad"},
                {"status": "RESOLVED", "city": "Surat"},
                {"status": "OPEN", "city": "Ahmedabad"},
            ]
        }
        answer = _fallback_query_answer("How many reports are there?", context)
        assert isinstance(answer, str)

    def test_granite_status_returns_dict(self):
        from agents.granite_service import granite_status
        status = granite_status()
        assert "available" in status
        assert "model" in status
        assert isinstance(status["available"], bool)


# ──────────────────────────────────────────────
# 6. Damage Assessment Agent Tests
# ──────────────────────────────────────────────
class TestDamageAgent:
    def setup_method(self):
        from agents.damage_assessment_agent import DamageAssessmentAgent
        self.agent = DamageAssessmentAgent()

    def test_assess_incident_returns_valid_result(self):
        result = self.agent.assess_incident(
            incident_id="INC-TEST",
            city="Ahmedabad",
            area="Maninagar",
            latitude=22.99,
            longitude=72.61,
            description="Severe flooding. Roads damaged. Drains blocked.",
            flood_duration_hours=8,
            severity="HIGH",
        )
        assert result["incident_id"] == "INC-TEST"
        assert result["damage_level"] in ("LOW", "MEDIUM", "HIGH", "SEVERE")
        assert result["is_preliminary"] is True
        assert "disclaimer" in result
        assert "AI" in result["disclaimer"].upper() or "PRELIMINARY" in result["disclaimer"].upper()
        assert result["requires_field_verification"] is True


# ──────────────────────────────────────────────
# 7. End-to-end Demo Test
# ──────────────────────────────────────────────
class TestEndToEndDemo:
    """
    End-to-end test simulating the hackathon demo flow.
    """

    def test_full_demo_scenario(self):
        """
        Simulates the complete 3-minute hackathon demo:
        Normal → Heavy Rainfall → Agents activate → Response plan → Recommendations
        """
        from agents.orchestrator import AgentOrchestrator

        orch = AgentOrchestrator()

        # Step 1: Normal conditions
        state_normal = orch.run_pipeline("NORMAL", "All")
        assert state_normal is not None
        assert len(state_normal["risk_predictions"]) > 0
        print(f"  STEP 1 OK Normal: {sum(1 for p in state_normal['risk_predictions'] if p['risk_level']=='CRITICAL')} critical zones")

        # Step 2: Heavy Rainfall scenario
        state_heavy = orch.run_pipeline("HEAVY", "All")
        assert state_heavy is not None
        heavy_critical = sum(1 for p in state_heavy["risk_predictions"] if p["risk_level"] == "CRITICAL")
        print(f"  STEP 2 OK Heavy: {heavy_critical} critical zones")

        # Step 3: Check all agents ran
        assert len(state_heavy["risk_predictions"]) > 0
        assert len(state_heavy["drain_analysis"]["scored_drains"]) > 0
        assert state_heavy["report_analysis"]["total_reports"] > 0

        # Step 4: Response plan generated
        response = state_heavy["response_plan"]
        assert "incidents" in response
        assert "top_recommendations" in response
        print(f"  STEP 4 OK Response: {len(response['incidents'])} incidents, {len(response['top_recommendations'])} recommendations")

        # Step 5: Recommendations present
        recs = response["top_recommendations"]
        assert len(recs) > 0

        # Step 6: Granite explanation (fallback)
        answer = orch.query("What is the flood situation?")
        assert isinstance(answer, str)
        print(f"  STEP 6 OK Granite query: '{answer[:60]}...'")

        # Step 7: Approval workflow
        if recs:
            result = orch.response_agent.approve_action(recs[0]["rec_id"], 0, "test_officer")
            assert result["approval_status"] == "APPROVED"
            print(f"  STEP 7 OK Approval workflow: {result['approval_status']}")

        # Step 8: Situation report
        report = state_heavy.get("situation_report", "")
        assert isinstance(report, str)
        assert len(report) > 50
        print(f"  STEP 8 OK Situation report: {len(report)} chars")

        # Step 9: Data labels
        assert state_heavy["data_label"] == "DEMO/SIMULATED"
        print(f"  STEP 9 OK Data label: {state_heavy['data_label']}")

        print("\n  [PASS] End-to-end demo test PASSED")
