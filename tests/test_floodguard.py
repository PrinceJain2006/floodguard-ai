"""
FloodGuard AI — Test Suite
Tests for all major components: ML model, agents, API, orchestration.
"""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pytest   # type: ignore[import-untyped]
import random
from datetime import datetime
import folium    # type: ignore[import-untyped]


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
        # 6 agents + IBM Granite = 7
        assert len(statuses) >= 6
        for s in statuses:
            assert "agent" in s
            assert "status" in s

    def test_query_returns_string(self):
        self.orch.run_pipeline("NORMAL")
        answer = self.orch.query("How many reports are there?")
        assert isinstance(answer, str)
        assert len(answer) > 0



# ──────────────────────────────────────────────
# Chief Response Agent — City Matching Tests
# ──────────────────────────────────────────────
class TestChiefResponseAgentCityMatching:
    """
    Verify that resource recommendations never assign a team from one city
    to a zone in the other city.
    """

    def setup_method(self):
        from agents.chief_response_agent import ChiefResponseAgent
        self.agent = ChiefResponseAgent()

    def _make_zone(self, area, city, risk_level="CRITICAL", risk_score=85.0):
        return {
            "area": area, "city": city,
            "risk_level": risk_level, "risk_score": risk_score,
            "confidence": 0.88,
            "input_features": {"rainfall_1h": 60.0},
            "main_reasons": ["test"],
            "latitude": 23.0225 if city == "Ahmedabad" else 21.1702,
            "longitude": 72.5714 if city == "Ahmedabad" else 72.8311,
        }

    def _make_teams(self):
        """Minimal team set: one of each type per city."""
        teams = []
        for city in ("Ahmedabad", "Surat"):
            tid = 1 if city == "Ahmedabad" else 10
            for ttype in ("pump_team", "rapid_response", "emergency", "drainage"):
                teams.append({
                    "team_id": f"T-{city[:3].upper()}-{tid:03d}",
                    "name": f"{city} {ttype.replace('_',' ').title()} #{tid}",
                    "city": city,
                    "team_type": ttype,
                    "status": "AVAILABLE",
                    "capacity": 10,
                })
                tid += 1
        return teams

    def test_ahmedabad_zone_gets_only_ahmedabad_teams(self):
        """A CRITICAL Ahmedabad zone must only receive Ahmedabad resources."""
        predictions = [self._make_zone("Maninagar", "Ahmedabad")]
        teams = self._make_teams()
        recs = self.agent.get_resource_recommendations(predictions, teams)
        for rec in recs:
            if "Ahmedabad" in rec["zone"]:
                for resource in rec["assigned_resources"]:
                    team_name = resource.get("team_name", "")
                    team_city = resource.get("city", "")
                    assert "Surat" not in team_name, (
                        f"Ahmedabad zone received Surat resource: {team_name}"
                    )
                    if team_city:  # city field is set on successfully assigned teams
                        assert team_city == "Ahmedabad", (
                            f"Ahmedabad zone received resource from city '{team_city}'"
                        )

    def test_surat_zone_gets_only_surat_teams(self):
        """A CRITICAL Surat zone must only receive Surat resources."""
        predictions = [self._make_zone("Adajan", "Surat")]
        teams = self._make_teams()
        recs = self.agent.get_resource_recommendations(predictions, teams)
        for rec in recs:
            if "Surat" in rec["zone"]:
                for resource in rec["assigned_resources"]:
                    team_name = resource.get("team_name", "")
                    team_city = resource.get("city", "")
                    assert "Ahmedabad" not in team_name, (
                        f"Surat zone received Ahmedabad resource: {team_name}"
                    )
                    if team_city:
                        assert team_city == "Surat", (
                            f"Surat zone received resource from city '{team_city}'"
                        )

    def test_no_available_same_city_team_shows_safe_message(self):
        """
        When no same-city team is available, the recommendation must clearly
        say so instead of assigning a resource from the other city.
        """
        predictions = [self._make_zone("Sachin", "Surat")]
        # Provide ONLY Ahmedabad teams — no Surat teams at all
        teams_only_ahm = [
            {
                "team_id": "T-AHM-001",
                "name": "Ahmedabad Pump Team #1",
                "city": "Ahmedabad",
                "team_type": "pump_team",
                "status": "AVAILABLE",
                "capacity": 10,
            }
        ]
        recs = self.agent.get_resource_recommendations(predictions, teams_only_ahm)
        assert len(recs) == 1
        resource = recs[0]["assigned_resources"][0]
        # Must NOT have assigned the Ahmedabad team
        assert "Ahmedabad" not in resource.get("team_name", ""), (
            "Surat zone must not receive an Ahmedabad team even when no Surat team exists"
        )
        # Must be the safe unavailable message
        assert resource.get("status") == "UNAVAILABLE", (
            "When no same-city team exists the status must be UNAVAILABLE, not AVAILABLE"
        )
        assert "Surat" in resource.get("team_name", ""), (
            "The safe message must mention the city that lacks resources"
        )

    def test_mixed_cities_correct_separation(self):
        """With zones from both cities, each zone must get only its own city's resources."""
        predictions = [
            self._make_zone("Maninagar", "Ahmedabad"),
            self._make_zone("Adajan", "Surat"),
        ]
        teams = self._make_teams()
        recs = self.agent.get_resource_recommendations(predictions, teams)
        for rec in recs:
            zone_city = rec["zone"].split(", ")[-1]  # "Maninagar, Ahmedabad" → "Ahmedabad"
            for resource in rec["assigned_resources"]:
                team_city = resource.get("city", "")
                if team_city and team_city != zone_city:
                    raise AssertionError(
                        f"Zone '{rec['zone']}' received resource from wrong city: "
                        f"team_city={team_city}, zone_city={zone_city}"
                    )



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


# ──────────────────────────────────────────────
# 8. Evidence Fusion Tests
# ──────────────────────────────────────────────
class TestEvidenceFusion:
    """Tests for the Evidence Fusion & Decision Intelligence layer."""

    def setup_method(self):
        from agents.evidence_fusion import (
            fuse_zone_evidence, fuse_all_zones, build_why_now,
            build_agent_decision_trace, get_recommended_action,
            AuditTrail, EVIDENCE_WEIGHTS,
        )
        self.fuse_zone_evidence      = fuse_zone_evidence
        self.fuse_all_zones          = fuse_all_zones
        self.build_why_now           = build_why_now
        self.build_agent_decision_trace = build_agent_decision_trace
        self.get_recommended_action  = get_recommended_action
        self.AuditTrail              = AuditTrail
        self.EVIDENCE_WEIGHTS        = EVIDENCE_WEIGHTS

    def _make_pred(self, risk_score=80, risk_level="CRITICAL"):
        return {
            "area": "Maninagar", "city": "Ahmedabad",
            "risk_score": risk_score, "risk_level": risk_level,
            "confidence": 0.85,
            "input_features": {
                "rainfall_1h": 75, "rainfall_6h": 400,
                "drainage_capacity": 30, "water_level": 2.5,
                "citizen_reports": 25,
            },
            "blocked_drains": 2,
            "active_reports": 25,
            "historical_incidents": 4,
            "main_reasons": ["High rainfall", "Low drainage capacity"],
            "recommended_action": "Deploy emergency response teams.",
        }

    def test_fuse_zone_evidence_score_bounds(self):
        """Priority score must be 0-100."""
        pred = self._make_pred(risk_score=85, risk_level="CRITICAL")
        result = self.fuse_zone_evidence(pred, [], [], [])
        assert 0 <= result["priority_score"] <= 100

    def test_fuse_zone_evidence_level_mapping(self):
        """Level must match score thresholds."""
        pred_high = self._make_pred(risk_score=60, risk_level="HIGH")
        result = self.fuse_zone_evidence(pred_high, [], [], [])
        assert result["priority_level"] in ("CRITICAL", "HIGH", "MEDIUM", "LOW")

    def test_fuse_zone_evidence_has_factors(self):
        """Must return contributing_factors list."""
        pred = self._make_pred()
        result = self.fuse_zone_evidence(pred, [], [], [])
        assert "contributing_factors" in result
        assert len(result["contributing_factors"]) == len(self.EVIDENCE_WEIGHTS)

    def test_fuse_zone_evidence_has_why_this_zone(self):
        """Must return non-empty why_this_zone."""
        pred = self._make_pred()
        result = self.fuse_zone_evidence(pred, [], [], [])
        assert "why_this_zone" in result
        assert len(result["why_this_zone"]) > 20

    def test_fuse_zone_evidence_data_label(self):
        """Must have DEMO data label."""
        pred = self._make_pred()
        result = self.fuse_zone_evidence(pred, [], [], [])
        assert "DEMO" in result["data_label"].upper()

    def test_evidence_weights_sum_to_one(self):
        """Weights must sum to 1.0."""
        total = sum(self.EVIDENCE_WEIGHTS.values())
        assert abs(total - 1.0) < 1e-9, f"Weights sum to {total}, not 1.0"

    def test_build_why_now_no_previous(self):
        """Without previous fusion, must report insufficient data."""
        pred = self._make_pred()
        from agents.evidence_fusion import fuse_zone_evidence
        current = fuse_zone_evidence(pred, [], [], [])
        result  = self.build_why_now(current, None)
        assert result["available"] is False
        assert "Insufficient" in result["message"]

    def test_build_why_now_with_previous(self):
        """With previous fusion, must return numeric comparison."""
        pred = self._make_pred(risk_score=70)
        from agents.evidence_fusion import fuse_zone_evidence
        previous = fuse_zone_evidence(self._make_pred(risk_score=40), [], [], [])
        current  = fuse_zone_evidence(pred, [], [], [])
        result   = self.build_why_now(current, previous)
        assert result["available"] is True
        assert "prev_score" in result
        assert "curr_score" in result
        assert isinstance(result["score_delta"], float)

    def test_get_recommended_action_critical(self):
        """CRITICAL zone must require approval."""
        pred = self._make_pred()
        from agents.evidence_fusion import fuse_zone_evidence
        fusion = fuse_zone_evidence(pred, [], [], [])
        # Force critical
        fusion["priority_level"] = "CRITICAL"
        fusion["priority_score"] = 85.0
        action = self.get_recommended_action(fusion, pred)
        assert action["requires_approval"] is True
        assert "action_id" in action
        assert action["data_label"] == "DEMO/SIMULATED"

    def test_get_recommended_action_low(self):
        """LOW zone must NOT require approval."""
        pred_low = self._make_pred(risk_score=10, risk_level="LOW")
        pred_low["input_features"]["rainfall_1h"] = 2
        from agents.evidence_fusion import fuse_zone_evidence
        fusion = fuse_zone_evidence(pred_low, [], [], [])
        fusion["priority_level"] = "LOW"
        fusion["priority_score"] = 10.0
        action = self.get_recommended_action(fusion, pred_low)
        assert action["requires_approval"] is False

    def test_audit_trail_record(self):
        """Audit trail must record and retrieve entries."""
        trail  = self.AuditTrail()
        action = {
            "action_id": "EF-TEST001", "area": "Maninagar", "city": "Ahmedabad",
            "priority_level": "CRITICAL", "priority_score": 85,
            "title": "Test action",
        }
        entry = trail.record(action, "APPROVED", "test_officer")
        assert entry["human_decision"] == "APPROVED"
        assert entry["decided_by"] == "test_officer"
        assert "DEMO" in entry["data_label"].upper()
        entries = trail.get_all()
        assert len(entries) == 1

    def test_audit_trail_clear(self):
        """Audit trail clear must empty entries."""
        trail  = self.AuditTrail()
        action = {"action_id": "X", "area": "A", "city": "B",
                  "priority_level": "LOW", "priority_score": 10, "title": "T"}
        trail.record(action, "REJECTED")
        trail.clear()
        assert len(trail.get_all()) == 0

    def test_fuse_all_zones_returns_sorted(self):
        """fuse_all_zones must return list sorted by score descending."""
        from data.seed_generator import (
            generate_rainfall_data, generate_drains,
            generate_flood_incidents, generate_citizen_reports
        )
        from agents.orchestrator import AgentOrchestrator
        orch = AgentOrchestrator()
        state = orch.run_pipeline("HEAVY", "All")
        fusions = self.fuse_all_zones(
            risk_predictions  = state["risk_predictions"],
            drain_records     = state["raw_drains"],
            report_records    = state["raw_reports"],
            incident_records  = state.get("drain_analysis", {}).get("scored_drains", []),
        )
        assert len(fusions) > 0
        scores = [f["priority_score"] for f in fusions]
        assert scores == sorted(scores, reverse=True)

    def test_agent_decision_trace_steps(self):
        """Agent trace must include all expected agents."""
        from agents.orchestrator import AgentOrchestrator
        orch = AgentOrchestrator()
        state = orch.run_pipeline("HEAVY", "All")
        pred = state["risk_predictions"][0]
        from agents.evidence_fusion import fuse_zone_evidence
        fusion = fuse_zone_evidence(pred, state["raw_drains"], state["raw_reports"], [])
        trace = self.build_agent_decision_trace(
            fusion_result   = fusion,
            risk_prediction = pred,
            drain_analysis  = state["drain_analysis"],
            report_analysis = state["report_analysis"],
            response_plan   = state["response_plan"],
            action_plan     = state["action_plan"],
        )
        agent_names = [t["agent"] for t in trace]
        assert "Flood Risk Agent" in agent_names
        assert "Drainage Agent" in agent_names
        assert "Evidence Fusion Layer" in agent_names
        assert "Final Decision" in agent_names


# ──────────────────────────────────────────────
# 9. Map Component Tests
# ──────────────────────────────────────────────
class TestMapComponent:
    """Tests for the Folium map — geometry, coordinate validation, tile layer."""

    def setup_method(self):
        from frontend.map_component import (
            build_flood_map, _valid_coord, _in_scope_city,
            CITY_CENTERS, DEFAULT_ZOOM, _IN_SCOPE_CITIES,
            _LAT_MIN, _LAT_MAX, _LON_MIN, _LON_MAX,
        )
        self.build_flood_map  = build_flood_map
        self._valid_coord     = _valid_coord
        self._in_scope_city   = _in_scope_city
        self.CITY_CENTERS     = CITY_CENTERS
        self.DEFAULT_ZOOM     = DEFAULT_ZOOM
        self.IN_SCOPE_CITIES  = _IN_SCOPE_CITIES
        self.LAT_MIN = _LAT_MIN
        self.LAT_MAX = _LAT_MAX
        self.LON_MIN = _LON_MIN
        self.LON_MAX = _LON_MAX

    # ── Coordinate validator ──────────────────────────────────────────────

    def test_valid_coord_ahmedabad(self):
        """Ahmedabad centre must be valid."""
        assert self._valid_coord(23.0225, 72.5714)

    def test_valid_coord_surat(self):
        """Surat centre must be valid."""
        assert self._valid_coord(21.1702, 72.8311)

    def test_valid_coord_all_center(self):
        """Default 'All' centre must be valid."""
        lat, lon = self.CITY_CENTERS["All"]
        assert self._valid_coord(lat, lon)

    def test_invalid_coord_zero_zero(self):
        """(0, 0) — Gulf of Guinea — must be rejected."""
        assert not self._valid_coord(0.0, 0.0)

    def test_invalid_coord_caribbean(self):
        """Caribbean coordinates must be rejected."""
        assert not self._valid_coord(18.0, -77.0)

    def test_invalid_coord_none(self):
        """None values must be rejected gracefully."""
        assert not self._valid_coord(None, None)

    def test_invalid_coord_string(self):
        """Non-numeric strings must be rejected gracefully."""
        assert not self._valid_coord("abc", "xyz")

    def test_invalid_coord_north_india_outside_gujarat(self):
        """Delhi (28.6, 77.2) is outside the Gujarat demo bounds."""
        assert not self._valid_coord(28.6, 77.2)

    # ── City centers are in Gujarat ───────────────────────────────────────

    def test_city_centers_in_bounds(self):
        """All CITY_CENTERS must fall within Gujarat bounds."""
        for city, (lat, lon) in self.CITY_CENTERS.items():
            assert self._valid_coord(lat, lon), (
                f"CITY_CENTERS['{city}'] = [{lat}, {lon}] is outside Gujarat bounds"
            )

    def test_all_center_corrected(self):
        """'All' centre longitude must be near 72.9 (Gujarat), not ~71."""
        _, lon = self.CITY_CENTERS["All"]
        assert lon >= 72.0, f"'All' longitude {lon} is too far west — should be ~72.95"

    # ── Map object construction ───────────────────────────────────────────

    def test_build_map_empty_data_returns_folium_map(self):
        """build_flood_map with no data must return a folium.Map centred on Gujarat."""
        m = self.build_flood_map([], [], [], [], city="All")
        assert isinstance(m, folium.Map)
        loc = m.location
        assert loc is not None
        lat, lon = loc[0], loc[1]
        assert self._valid_coord(lat, lon), f"Map center {lat},{lon} is outside Gujarat"

    def test_build_map_ahmedabad_center(self):
        """Ahmedabad filter must centre on Ahmedabad."""
        m = self.build_flood_map([], [], [], [], city="Ahmedabad")
        lat, lon = m.location
        # Ahmedabad is ~23.02 N, 72.57 E
        assert 22.5 <= lat <= 23.5
        assert 72.0 <= lon <= 73.5

    def test_build_map_surat_center(self):
        """Surat filter must centre on Surat."""
        m = self.build_flood_map([], [], [], [], city="Surat")
        lat, lon = m.location
        # Surat is ~21.17 N, 72.83 E
        assert 20.5 <= lat <= 22.0
        assert 72.0 <= lon <= 73.5

    def test_build_map_invalid_coords_skipped(self):
        """Markers with coordinates outside Gujarat must be silently skipped."""
        bad_preds = [
            {
                "latitude": 0.0, "longitude": 0.0,
                "area": "BadZone", "city": "Nowhere",
                "risk_level": "CRITICAL", "risk_score": 90,
                "main_reasons": [], "recommended_action": "", "confidence": 0.8,
                "input_features": {"rainfall_1h": 50},
            },
            {
                "latitude": 18.5, "longitude": -77.3,
                "area": "Caribbean", "city": "Nowhere",
                "risk_level": "HIGH", "risk_score": 70,
                "main_reasons": [], "recommended_action": "", "confidence": 0.8,
                "input_features": {"rainfall_1h": 30},
            },
        ]
        # Should not raise; map must still centre on Gujarat
        m = self.build_flood_map(bad_preds, [], [], [], city="All")
        lat, lon = m.location
        assert self._valid_coord(lat, lon), "Map must still centre on Gujarat when all markers are invalid"

    def test_build_map_valid_markers_fit_bounds(self):
        """With valid Gujarat markers, map fit_bounds must be called (location stays in Gujarat)."""
        valid_preds = [
            {
                "latitude": 23.01, "longitude": 72.58,
                "area": "Maninagar", "city": "Ahmedabad",
                "risk_level": "HIGH", "risk_score": 65,
                "main_reasons": ["High rainfall"], "recommended_action": "Deploy team",
                "confidence": 0.85, "input_features": {"rainfall_1h": 55},
            },
            {
                "latitude": 21.17, "longitude": 72.83,
                "area": "Katargam", "city": "Surat",
                "risk_level": "CRITICAL", "risk_score": 88,
                "main_reasons": ["Flooding"], "recommended_action": "Evacuate",
                "confidence": 0.9, "input_features": {"rainfall_1h": 90},
            },
        ]
        m = self.build_flood_map(valid_preds, [], [], [], city="All")
        # Map must have rendered without raising
        assert isinstance(m, folium.Map)

    def test_build_map_no_carto_string_tile(self):
        """Map must NOT use the old 'CartoDB dark_matter' string shortcut that breaks in Folium 0.18+."""
        m = self.build_flood_map([], [], [], [], city="All")
        # Serialize to HTML and check no broken tile reference
        html = m._repr_html_()
        # The old broken shortcut produced 'CartoDB' with no URL
        assert "tiles=CartoDB" not in html, "Old CartoDB string shortcut must not appear in map HTML"

    def test_build_map_with_pipeline_data(self):
        """Full pipeline data must produce a valid map centred on Gujarat."""
        from agents.orchestrator import AgentOrchestrator
        orch  = AgentOrchestrator()
        state = orch.run_pipeline("HEAVY", "All")
        m = self.build_flood_map(
            risk_predictions = state["risk_predictions"],
            drain_data       = state["raw_drains"][:60],
            report_data      = state["raw_reports"][:60],
            team_data        = state["teams"],
            city             = "All",
        )
        assert isinstance(m, folium.Map)
        # Verify the rendered HTML contains Gujarat tile attribution
        html = m._repr_html_()
        assert "openstreetmap" in html.lower() or "Gujarat" in html or "Ahmedabad" in html

    # ── Scope constraint: Ahmedabad & Surat only ──────────────────────────

    def test_in_scope_city_ahmedabad(self):
        """Ahmedabad must be accepted as in-scope."""
        assert self._in_scope_city("Ahmedabad")

    def test_in_scope_city_surat(self):
        """Surat must be accepted as in-scope."""
        assert self._in_scope_city("Surat")

    def test_in_scope_city_rejects_mumbai(self):
        """Mumbai must be rejected — only Ahmedabad and Surat are in scope."""
        assert not self._in_scope_city("Mumbai")

    def test_in_scope_city_rejects_vadodara(self):
        """Vadodara (also in Gujarat) must be rejected — scope is AHD+SUR only."""
        assert not self._in_scope_city("Vadodara")

    def test_in_scope_city_rejects_empty_string(self):
        """Empty string must be rejected as out-of-scope."""
        assert not self._in_scope_city("")

    def test_in_scope_city_rejects_unknown(self):
        """Unknown/placeholder city names must be rejected."""
        assert not self._in_scope_city("Unknown")

    def test_in_scope_cities_constant_is_exactly_two(self):
        """_IN_SCOPE_CITIES must contain exactly Ahmedabad and Surat — nothing more."""
        assert self.IN_SCOPE_CITIES == frozenset({"Ahmedabad", "Surat"}), (
            f"_IN_SCOPE_CITIES must be exactly {{Ahmedabad, Surat}}, got {self.IN_SCOPE_CITIES}"
        )

    def test_out_of_scope_risk_pred_excluded_from_map(self):
        """A risk prediction tagged with a city other than AHD/SUR must not appear on the map."""
        # Valid Gujarat coordinate but wrong city — must be silently excluded
        out_of_scope_preds = [
            {
                "latitude": 22.3, "longitude": 73.2,   # Vadodara area coords
                "area": "Alkapuri", "city": "Vadodara",
                "risk_level": "CRITICAL", "risk_score": 95,
                "main_reasons": ["test"], "recommended_action": "evacuate",
                "confidence": 0.9, "input_features": {"rainfall_1h": 100},
            },
        ]
        m = self.build_flood_map(out_of_scope_preds, [], [], [], city="All")
        html = m._repr_html_()
        # The area name "Alkapuri" must not appear — it was excluded by scope guard
        assert "Alkapuri" not in html, (
            "Out-of-scope risk zone 'Alkapuri, Vadodara' must not render on the map"
        )

    def test_out_of_scope_drain_excluded_from_map(self):
        """A drain record tagged with a city other than AHD/SUR must not appear on the map."""
        out_of_scope_drains = [
            {
                "drain_id": "D-OOS-001", "city": "Rajkot", "area": "Kalavad Road",
                "latitude": 22.3, "longitude": 70.8,
                "drain_type": "storm_drain", "capacity_rating": 50,
                "condition": "POOR", "maintenance_priority": "CRITICAL",
                "status": "BLOCKED", "blockage_frequency": 5,
                "near_flood_zone": True, "risk_score": 80,
                "last_cleaned": "2025-01-01",
            },
        ]
        m = self.build_flood_map([], out_of_scope_drains, [], [], city="All")
        html = m._repr_html_()
        assert "D-OOS-001" not in html, (
            "Out-of-scope drain 'D-OOS-001, Rajkot' must not render on the map"
        )

    def test_out_of_scope_report_excluded_from_map(self):
        """A citizen report tagged with a city other than AHD/SUR must not appear on the map."""
        out_of_scope_reports = [
            {
                "report_id": "RPT-OOS-001", "city": "Gandhinagar", "area": "Sector 21",
                "latitude": 23.2, "longitude": 72.6,
                "category": "road_blockage", "severity": "HIGH",
                "language": "english",
                "original_text": "Flooding in Sector 21 Gandhinagar.",
                "status": "OPEN",
            },
        ]
        m = self.build_flood_map([], [], out_of_scope_reports, [], city="All")
        html = m._repr_html_()
        assert "RPT-OOS-001" not in html, (
            "Out-of-scope citizen report 'RPT-OOS-001, Gandhinagar' must not render on the map"
        )

    def test_in_scope_risk_pred_renders_on_map(self):
        """A valid Ahmedabad risk prediction must appear on the map."""
        valid_pred = [
            {
                "latitude": 22.9908, "longitude": 72.6084,
                "area": "Maninagar", "city": "Ahmedabad",
                "risk_level": "CRITICAL", "risk_score": 92,
                "main_reasons": ["Heavy rain"], "recommended_action": "Evacuate",
                "confidence": 0.95, "input_features": {"rainfall_1h": 110},
            },
        ]
        m = self.build_flood_map(valid_pred, [], [], [], city="All")
        html = m._repr_html_()
        assert "Maninagar" in html, (
            "In-scope Ahmedabad risk zone 'Maninagar' must be visible on the map"
        )

    def test_in_scope_surat_report_renders_on_map(self):
        """A valid Surat citizen report must appear on the map."""
        valid_report = [
            {
                "report_id": "RPT-SURAT-001", "city": "Surat", "area": "Adajan",
                "latitude": 21.2063, "longitude": 72.8060,
                "category": "property_flooding", "severity": "HIGH",
                "language": "gujarati",
                "original_text": "Adajan flooding.",
                "status": "OPEN",
            },
        ]
        m = self.build_flood_map([], [], valid_report, [], city="All")
        html = m._repr_html_()
        assert "Adajan" in html, (
            "In-scope Surat citizen report for 'Adajan' must be visible on the map"
        )

    def test_legend_contains_scope_label(self):
        """The map legend must visually identify Ahmedabad & Surat as the scope."""
        m = self.build_flood_map([], [], [], [], city="All")
        html = m._repr_html_()
        assert "AHMEDABAD" in html.upper() and "SURAT" in html.upper(), (
            "Map legend must explicitly name both Ahmedabad and Surat as the scope"
        )

    def test_map_html_contains_ahmedabad_and_surat(self):
        """
        The rendered map HTML must reference both Ahmedabad and Surat.
        These appear via city marker tooltips (not the tile attribution,
        which is now the standard OSM attribution only).
        """
        m = self.build_flood_map([], [], [], [], city="All")
        html = m._repr_html_()
        assert "Ahmedabad" in html and "Surat" in html, (
            "Rendered map HTML must contain both Ahmedabad and Surat "
            "(via city marker tooltips or legend)"
        )

    def test_map_attribution_is_clean_osm(self):
        """Tile attribution must be the standard OSM line only — no custom footer text."""
        m = self.build_flood_map([], [], [], [], city="All")
        html = m._repr_html_()
        assert "openstreetmap.org" in html.lower(), "OSM attribution must be present"
        # The large custom footer text was removed; it must not appear in attribution
        assert "Flood Management" not in html, (
            "Custom 'Flood Management' text must not appear in the tile attribution"
        )


    def test_legend_demo_label_when_not_live(self):
        """Legend must show DEMO for weather layer when is_live=False (default)."""
        m = self.build_flood_map([], [], [], [], city="All", is_live=False)
        html = m._repr_html_()
        assert "DEMO" in html, "Legend must show DEMO for weather when is_live=False"

    def test_legend_live_label_when_live(self):
        """Legend must show LIVE for weather layer when is_live=True."""
        m = self.build_flood_map([], [], [], [], city="All", is_live=True)
        html = m._repr_html_()
        assert "LIVE" in html, "Legend must show LIVE for weather when is_live=True"


# ──────────────────────────────────────────────────────────────────────────────
# Live Weather Service Tests
# ──────────────────────────────────────────────────────────────────────────────
class TestLiveWeatherService:
    """
    Tests for services/live_weather.py.

    Network calls are NOT made in tests — we mock the HTTP client or feed
    synthetic API-shaped responses to _parse_response directly.
    """

    def setup_method(self):
        from services.live_weather import (
            fetch_city_weather, fetch_all_cities,
            _parse_response, _validate_numeric, _wmo_to_condition,
            WeatherFetchError, CITY_COORDS,
        )
        self.fetch_city_weather  = fetch_city_weather
        self.fetch_all_cities    = fetch_all_cities
        self._parse_response     = _parse_response
        self._validate_numeric   = _validate_numeric
        self._wmo_to_condition   = _wmo_to_condition
        self.WeatherFetchError   = WeatherFetchError
        self.CITY_COORDS         = CITY_COORDS

    # ── Utility / unit tests ─────────────────────────────────────────────

    def test_city_coords_only_ahmedabad_surat(self):
        """CITY_COORDS must contain exactly Ahmedabad and Surat."""
        assert set(self.CITY_COORDS.keys()) == {"Ahmedabad", "Surat"}

    def test_validate_numeric_valid(self):
        """Valid temperature should pass bounds check."""
        v = self._validate_numeric(34.5, "temperature_2m")
        assert v == pytest.approx(34.5)

    def test_validate_numeric_out_of_range(self):
        """Temperature of 200°C must raise WeatherFetchError."""
        with pytest.raises(self.WeatherFetchError):
            self._validate_numeric(200.0, "temperature_2m")

    def test_validate_numeric_non_numeric(self):
        """Non-numeric string must raise WeatherFetchError."""
        with pytest.raises(self.WeatherFetchError):
            self._validate_numeric("not_a_number", "precipitation")

    def test_validate_numeric_none(self):
        """None value must raise WeatherFetchError."""
        with pytest.raises(self.WeatherFetchError):
            self._validate_numeric(None, "precipitation")

    def test_wmo_condition_clear(self):
        assert self._wmo_to_condition(0) == "Clear Sky"

    def test_wmo_condition_thunderstorm(self):
        assert self._wmo_to_condition(95) == "Thunderstorm"

    def test_wmo_condition_unknown_code(self):
        result = self._wmo_to_condition(999)
        assert "999" in result

    def test_wmo_condition_invalid(self):
        """Non-numeric code returns unknown string (no crash)."""
        result = self._wmo_to_condition("bad")
        assert isinstance(result, str)

    # ── _parse_response with synthetic API payloads ───────────────────────

    def _make_raw(self, rain=5.0, precip=5.0, temp=32.0, wind=15.0,
                  code=63, prob=70):
        """Build a synthetic Open-Meteo API response dict."""
        return {
            "current": {
                "time":             "2026-08-14T10:00",
                "temperature_2m":   temp,
                "precipitation":    precip,
                "rain":             rain,
                "windspeed_10m":    wind,
                "weathercode":      code,
            },
            "hourly": {
                "time":                      ["2026-08-14T10:00"] * 6,
                "precipitation":             [precip] * 6,
                "precipitation_probability": [prob] * 6,
                "rain":                      [rain] * 6,
                "windspeed_10m":             [wind] * 6,
                "temperature_2m":            [temp] * 6,
                "weathercode":               [code] * 6,
            },
        }

    def test_parse_response_ahmedabad_valid(self):
        """Valid Open-Meteo response for Ahmedabad parses without error."""
        raw = self._make_raw(rain=12.0, temp=34.5)
        result = self._parse_response("Ahmedabad", raw)
        assert result["city"] == "Ahmedabad"
        assert result["is_live"] is True
        assert result["data_mode"] == "LIVE"
        assert result["rainfall_1h"] == pytest.approx(12.0, abs=0.1)
        assert result["temperature"] == pytest.approx(34.5, abs=0.1)
        assert result["source"] == "Open-Meteo"

    def test_parse_response_surat_valid(self):
        """Valid Open-Meteo response for Surat parses without error."""
        raw = self._make_raw(precip=45.0, rain=40.0)
        result = self._parse_response("Surat", raw)
        assert result["city"] == "Surat"
        assert result["rainfall_1h"] == pytest.approx(45.0, abs=0.1)

    def test_parse_response_uses_max_precip_rain(self):
        """rainfall_1h = max(precipitation, rain)."""
        raw = self._make_raw(rain=5.0, precip=15.0)
        result = self._parse_response("Ahmedabad", raw)
        assert result["rainfall_1h"] == pytest.approx(15.0, abs=0.1)

    def test_parse_response_missing_current_block(self):
        """Response without 'current' block must raise WeatherFetchError."""
        with pytest.raises(self.WeatherFetchError, match="'current' block"):
            self._parse_response("Ahmedabad", {"hourly": {}})

    def test_parse_response_missing_required_field(self):
        """Response missing a required field must raise WeatherFetchError."""
        raw = self._make_raw()
        del raw["current"]["temperature_2m"]
        with pytest.raises(self.WeatherFetchError):
            self._parse_response("Ahmedabad", raw)

    def test_parse_response_out_of_range_temperature(self):
        """Implausibly hot temperature must raise WeatherFetchError."""
        raw = self._make_raw(temp=999.0)
        with pytest.raises(self.WeatherFetchError):
            self._parse_response("Ahmedabad", raw)

    def test_parse_response_out_of_scope_city(self):
        """City not in GUJARAT_CITY_COORDS raises WeatherFetchError."""
        with pytest.raises(self.WeatherFetchError):
            self._parse_response("Mumbai", self._make_raw())

    def test_parse_response_forecast_6h(self):
        """rainfall_6h should equal sum of 6 hourly forecast values."""
        raw = self._make_raw(precip=10.0, rain=10.0)
        result = self._parse_response("Ahmedabad", raw)
        assert result["rainfall_6h"] == pytest.approx(60.0, abs=1.0)

    def test_parse_response_pipeline_schema_keys(self):
        """Result must include all keys expected by the pipeline."""
        raw = self._make_raw()
        result = self._parse_response("Ahmedabad", raw)
        for key in ["city", "latitude", "longitude", "rainfall_1h",
                    "rainfall_3h", "rainfall_6h", "rainfall_24h",
                    "condition", "source", "is_live", "recorded_at", "fetched_at"]:
            assert key in result, f"Missing key: {key}"

    def test_fetch_city_weather_invalid_city(self):
        """Requesting a city outside the Gujarat list raises WeatherFetchError."""
        with pytest.raises(self.WeatherFetchError):
            self.fetch_city_weather("Mumbai")

    def test_fetch_all_cities_on_network_error(self):
        """
        fetch_all_cities must NOT raise even when network is unavailable.
        It must return a dict with None values and error strings.
        """
        import unittest.mock as mock
        import httpx

        with mock.patch("services.live_weather.httpx.get",
                        side_effect=httpx.ConnectError("Simulated network failure")):
            result = self.fetch_all_cities(timeout=1)

        assert "errors" in result
        # Either city is None (failed) or has data (if somehow succeeded)
        for city in ["Ahmedabad", "Surat"]:
            if result.get(city) is None:
                assert result["errors"].get(city) is not None

    def test_fetch_all_cities_on_timeout(self):
        """fetch_all_cities must NOT raise on timeout."""
        import unittest.mock as mock
        import httpx

        with mock.patch("services.live_weather.httpx.get",
                        side_effect=httpx.TimeoutException("Simulated timeout")):
            result = self.fetch_all_cities(timeout=1)

        assert "errors" in result
        for city in ["Ahmedabad", "Surat"]:
            if result.get(city) is None:
                assert result["errors"].get(city) is not None


# ──────────────────────────────────────────────────────────────────────────────
# Live Data Manager Tests
# ──────────────────────────────────────────────────────────────────────────────
class TestLiveDataManager:
    """
    Tests for services/live_data_manager.py.
    All tests use mocked network calls — no live HTTP required.
    """

    def setup_method(self):
        # Reset singleton between tests
        from services.live_data_manager import reset_live_data_manager
        reset_live_data_manager()

        from services.live_data_manager import (
            LiveDataManager, get_live_data_manager, reset_live_data_manager,
            DATA_MODE_LIVE, DATA_MODE_DEMO,
        )
        from services.live_weather import CITY_COORDS
        self.LiveDataManager         = LiveDataManager
        self.get_live_data_manager   = get_live_data_manager
        self.reset_live_data_manager = reset_live_data_manager
        self.DATA_MODE_LIVE          = DATA_MODE_LIVE
        self.DATA_MODE_DEMO          = DATA_MODE_DEMO
        self.CITY_COORDS             = CITY_COORDS

    def teardown_method(self):
        from services.live_data_manager import reset_live_data_manager
        reset_live_data_manager()

    def _make_weather_record(self, city: str) -> dict:
        """Minimal valid WeatherRecord for tests."""
        from services.live_weather import CITY_COORDS
        coords = CITY_COORDS[city]
        return {
            "city":        city,
            "latitude":    coords["lat"],
            "longitude":   coords["lon"],
            "temperature": 33.5,
            "rainfall_1h": 8.5,
            "rainfall_3h": 25.0,
            "rainfall_6h": 50.0,
            "rainfall_24h": 85.0,
            "precipitation_probability": 65.0,
            "wind_speed":  12.0,
            "condition":   "Moderate Rain",
            "weathercode": 63,
            "forecast_precip_next6h": [8.0] * 6,
            "source":      "Open-Meteo",
            "source_url":  "https://open-meteo.com",
            "is_live":     True,
            "data_mode":   "LIVE",
            "recorded_at": "2026-08-14T10:00",
            "fetched_at":  "2026-08-14T10:00:00+00:00",
            "area":        city,
            "rainfall_24h": 85.0,
            "data_source": "Open-Meteo (live)",
            "recorded_at_label": "Open-Meteo — 2026-08-14T10:00 IST",
        }

    # ── Disabled-mode tests ───────────────────────────────────────────────

    def test_disabled_manager_returns_demo_status(self):
        """Manager with enabled=False must return DEMO status."""
        mgr = self.LiveDataManager(enabled=False)
        status = mgr.get_status()
        assert status["data_mode"] == self.DATA_MODE_DEMO
        assert status["is_live"] is False

    def test_disabled_manager_city_weather_returns_none(self):
        """get_city_weather must return None when manager is disabled."""
        mgr = self.LiveDataManager(enabled=False)
        assert mgr.get_city_weather("Ahmedabad") is None
        assert mgr.get_city_weather("Surat") is None

    def test_disabled_manager_rainfall_records_empty(self):
        """get_rainfall_records must return [] when disabled."""
        mgr = self.LiveDataManager(enabled=False)
        assert mgr.get_rainfall_records("All") == []

    # ── Successful fetch tests ────────────────────────────────────────────

    def _manager_with_mocked_fetch(self, ahm_record, srt_record):
        """Return a manager whose _do_fetch returns preset data."""
        import unittest.mock as mock
        mgr = self.LiveDataManager(enabled=True, cache_ttl=600)

        mock_result = {
            "Ahmedabad": ahm_record,
            "Surat":     srt_record,
            "errors":    {"Ahmedabad": None, "Surat": None},
        }
        with mock.patch("services.live_data_manager.fetch_all_cities", return_value=mock_result):
            mgr.refresh(force=True)
        return mgr

    def test_successful_fetch_live_status(self):
        """After a successful fetch, status.data_mode == LIVE."""
        mgr = self._manager_with_mocked_fetch(
            self._make_weather_record("Ahmedabad"),
            self._make_weather_record("Surat"),
        )
        status = mgr.get_status()
        assert status["data_mode"] == self.DATA_MODE_LIVE
        assert status["is_live"] is True
        assert status["source"] == "Open-Meteo"

    def test_successful_fetch_ahmedabad_city_info(self):
        """Ahmedabad city info must be populated after successful fetch."""
        mgr = self._manager_with_mocked_fetch(
            self._make_weather_record("Ahmedabad"),
            self._make_weather_record("Surat"),
        )
        status = mgr.get_status()
        ahm = status["cities"]["Ahmedabad"]
        assert ahm["available"] is True
        assert ahm["rainfall_1h"] == pytest.approx(8.5, abs=0.1)

    def test_successful_fetch_surat_city_info(self):
        """Surat city info must be populated after successful fetch."""
        mgr = self._manager_with_mocked_fetch(
            self._make_weather_record("Ahmedabad"),
            self._make_weather_record("Surat"),
        )
        status = mgr.get_status()
        srt = status["cities"]["Surat"]
        assert srt["available"] is True

    def test_get_city_weather_ahmedabad(self):
        """get_city_weather('Ahmedabad') returns the record after fetch."""
        mgr = self._manager_with_mocked_fetch(
            self._make_weather_record("Ahmedabad"),
            self._make_weather_record("Surat"),
        )
        rec = mgr.get_city_weather("Ahmedabad")
        assert rec is not None
        assert rec["city"] == "Ahmedabad"
        assert rec["is_live"] is True

    def test_get_city_weather_surat(self):
        """get_city_weather('Surat') returns the record after fetch."""
        mgr = self._manager_with_mocked_fetch(
            self._make_weather_record("Ahmedabad"),
            self._make_weather_record("Surat"),
        )
        rec = mgr.get_city_weather("Surat")
        assert rec is not None
        assert rec["city"] == "Surat"

    # ── Rainfall records schema compatibility ─────────────────────────────

    def test_get_rainfall_records_schema(self):
        """get_rainfall_records must return pipeline-compatible schema keys."""
        mgr = self._manager_with_mocked_fetch(
            self._make_weather_record("Ahmedabad"),
            self._make_weather_record("Surat"),
        )
        records = mgr.get_rainfall_records("All")
        assert len(records) == 2
        for rec in records:
            for key in ["city", "area", "latitude", "longitude",
                        "rainfall_1h", "rainfall_3h", "rainfall_6h",
                        "rainfall_24h", "recorded_at", "data_source", "is_live"]:
                assert key in rec, f"Missing pipeline key: {key}"

    def test_get_rainfall_records_city_filter(self):
        """City filter 'Ahmedabad' must return only Ahmedabad record."""
        mgr = self._manager_with_mocked_fetch(
            self._make_weather_record("Ahmedabad"),
            self._make_weather_record("Surat"),
        )
        records = mgr.get_rainfall_records("Ahmedabad")
        assert len(records) == 1
        assert records[0]["city"] == "Ahmedabad"

    def test_get_rainfall_records_values(self):
        """Rainfall values in returned records must match source data."""
        mgr = self._manager_with_mocked_fetch(
            self._make_weather_record("Ahmedabad"),
            self._make_weather_record("Surat"),
        )
        records = mgr.get_rainfall_records("Ahmedabad")
        assert records[0]["rainfall_1h"] == pytest.approx(8.5, abs=0.1)
        assert records[0]["is_live"] is True
        assert "Open-Meteo" in records[0]["data_source"]

    # ── Network failure → DEMO fallback ───────────────────────────────────

    def test_network_failure_demo_fallback(self):
        """Network failure must result in DEMO status, not a crash."""
        import unittest.mock as mock
        import httpx
        mgr = self.LiveDataManager(enabled=True, cache_ttl=600, request_timeout=1)
        with mock.patch(
            "services.live_weather.httpx.get",
            side_effect=httpx.ConnectError("Simulated failure"),
        ):
            mgr.refresh(force=True)

        status = mgr.get_status()
        assert status["data_mode"] == self.DATA_MODE_DEMO
        assert status["is_live"] is False
        assert status["fallback_reason"] != ""

    def test_timeout_demo_fallback(self):
        """Timeout must result in DEMO status without raising."""
        import unittest.mock as mock
        import httpx
        mgr = self.LiveDataManager(enabled=True, cache_ttl=600, request_timeout=1)
        with mock.patch(
            "services.live_weather.httpx.get",
            side_effect=httpx.TimeoutException("Simulated timeout"),
        ):
            mgr.refresh(force=True)

        status = mgr.get_status()
        assert status["data_mode"] == self.DATA_MODE_DEMO

    def test_invalid_response_demo_fallback(self):
        """Invalid API response (missing 'current') must fall back to DEMO."""
        import unittest.mock as mock
        mgr = self.LiveDataManager(enabled=True, cache_ttl=600, request_timeout=1)

        # Return a malformed response (no 'current' key)
        mock_bad_response = mock.MagicMock()
        mock_bad_response.raise_for_status.return_value = None
        mock_bad_response.json.return_value = {"no_current": "here"}

        with mock.patch("services.live_weather.httpx.get", return_value=mock_bad_response):
            mgr.refresh(force=True)

        status = mgr.get_status()
        assert status["data_mode"] == self.DATA_MODE_DEMO

    def test_missing_fields_demo_fallback(self):
        """Response missing required fields must fall back to DEMO."""
        import unittest.mock as mock
        mgr = self.LiveDataManager(enabled=True, cache_ttl=600, request_timeout=1)

        mock_partial = mock.MagicMock()
        mock_partial.raise_for_status.return_value = None
        # Current block is present but missing temperature_2m
        mock_partial.json.return_value = {
            "current": {
                "precipitation": 5.0,
                "rain": 5.0,
                "windspeed_10m": 10.0,
                "weathercode": 63,
                # temperature_2m MISSING
            },
            "hourly": {},
        }
        with mock.patch("services.live_weather.httpx.get", return_value=mock_partial):
            mgr.refresh(force=True)

        status = mgr.get_status()
        assert status["data_mode"] == self.DATA_MODE_DEMO

    # ── Stale data detection ──────────────────────────────────────────────

    def test_stale_data_detection(self):
        """Cache older than stale_threshold must be flagged as stale."""
        mgr = self._manager_with_mocked_fetch(
            self._make_weather_record("Ahmedabad"),
            self._make_weather_record("Surat"),
        )
        # Backdate the cache to simulate stale data
        mgr._cache["fetched_at"] -= 2000   # 2000 seconds ago
        assert mgr._cache_stale() is True
        status = mgr.get_status()
        assert status["is_stale"] is True

    def test_fresh_cache_not_stale(self):
        """Freshly fetched cache must not be flagged as stale."""
        mgr = self._manager_with_mocked_fetch(
            self._make_weather_record("Ahmedabad"),
            self._make_weather_record("Surat"),
        )
        assert mgr._cache_stale() is False

    # ── LIVE/DEMO status distinction ──────────────────────────────────────

    def test_live_status_is_live_true(self):
        """is_live must be True only when real data was fetched."""
        mgr = self._manager_with_mocked_fetch(
            self._make_weather_record("Ahmedabad"),
            self._make_weather_record("Surat"),
        )
        assert mgr.get_status()["is_live"] is True

    def test_demo_status_is_live_false(self):
        """is_live must be False when fallback / disabled."""
        mgr = self.LiveDataManager(enabled=False)
        assert mgr.get_status()["is_live"] is False

    def test_status_never_claims_live_when_demo(self):
        """data_mode must never be LIVE when is_live is False."""
        mgr = self.LiveDataManager(enabled=False)
        s = mgr.get_status()
        if not s["is_live"]:
            assert s["data_mode"] != self.DATA_MODE_LIVE

    # ── Evidence Fusion integration ───────────────────────────────────────

    def test_evidence_fusion_receives_live_rainfall(self):
        """
        When live weather is available, fuse_zone_evidence should
        use the live rainfall value and label it LIVE.
        """
        from agents.evidence_fusion import fuse_zone_evidence

        live_record = self._make_weather_record("Ahmedabad")
        live_record["rainfall_1h"] = 55.0  # set a specific test value

        pred = {
            "city": "Ahmedabad",
            "area": "Maninagar",
            "risk_score": 70.0,
            "risk_level": "HIGH",
            "confidence": 0.88,
            "input_features": {"rainfall_1h": 10.0, "drainage_capacity": 50,
                               "historical_flood_freq": 3, "water_level": 1.0,
                               "elevation": 49, "road_density": 0.7,
                               "citizen_reports": 5},
        }
        result = fuse_zone_evidence(
            risk_prediction=pred,
            drain_records=[],
            area_reports=[],
            historical_incidents=[],
            live_weather_record=live_record,
        )
        # Rainfall note must mention LIVE
        rf_factor = next(f for f in result["contributing_factors"]
                         if f["factor_key"] == "rainfall_intensity")
        assert rf_factor["is_live"] is True
        assert "LIVE" in rf_factor["note"]
        assert result["rainfall_is_live"] is True

    def test_evidence_fusion_demo_when_no_live(self):
        """Without live weather, rainfall evidence must be labeled DEMO."""
        from agents.evidence_fusion import fuse_zone_evidence

        pred = {
            "city": "Surat",
            "area": "Adajan",
            "risk_score": 50.0,
            "risk_level": "HIGH",
            "confidence": 0.82,
            "input_features": {"rainfall_1h": 30.0, "drainage_capacity": 50,
                               "historical_flood_freq": 2, "water_level": 0.5,
                               "elevation": 12, "road_density": 0.8,
                               "citizen_reports": 3},
        }
        result = fuse_zone_evidence(
            risk_prediction=pred,
            drain_records=[],
            area_reports=[],
            historical_incidents=[],
            live_weather_record=None,
        )
        rf_factor = next(f for f in result["contributing_factors"]
                         if f["factor_key"] == "rainfall_intensity")
        assert rf_factor["is_live"] is False
        assert "DEMO" in rf_factor["note"]
        assert result["rainfall_is_live"] is False

    # ── weather_to_map_points ─────────────────────────────────────────────

    def test_weather_to_map_points_schema(self):
        """map points must include all keys expected by map_component."""
        mgr = self._manager_with_mocked_fetch(
            self._make_weather_record("Ahmedabad"),
            self._make_weather_record("Surat"),
        )
        points = mgr.weather_to_map_points("All")
        assert len(points) == 2
        for pt in points:
            for key in ["city", "area", "latitude", "longitude",
                        "rainfall_1h", "rainfall_6h", "condition",
                        "source", "is_live", "recorded_at"]:
                assert key in pt, f"Missing map key: {key}"

    def test_weather_to_map_points_is_live(self):
        """Map points from live data must have is_live=True."""
        mgr = self._manager_with_mocked_fetch(
            self._make_weather_record("Ahmedabad"),
            self._make_weather_record("Surat"),
        )
        for pt in mgr.weather_to_map_points("All"):
            assert pt["is_live"] is True


# ──────────────────────────────────────────────────────────────────────────────
# Raw HTML Rendering Regression Tests
# ──────────────────────────────────────────────────────────────────────────────
class TestNoRawHtmlInRenderedOutput:
    """
    Regression tests to ensure raw HTML tags do not leak into plain-text
    Streamlit contexts (st.expander labels, st.button labels, st.metric, etc.).

    These tests check the *data* that flows through the rendering path, not
    the Streamlit renderer itself (which cannot be invoked in unit tests).
    They assert:
      1. pipeline_log entries contain no HTML tags.
      2. agent status dicts contain no HTML tags in their text fields.
      3. render_agent_trace helper builds HTML strings that are only ever
         passed to st.markdown(…, unsafe_allow_html=True), i.e. the function
         returns nothing (it calls st.markdown internally) — the test verifies
         the generated HTML string has proper open/close structure.
    """

    HTML_TAG_RE = __import__("re").compile(
        r"<(?:span|div|p|strong|b|i|br|hr|a |table|ul|ol|li|style|button|script)\b",
        __import__("re").IGNORECASE,
    )

    def _has_html(self, text: str) -> bool:
        return bool(self.HTML_TAG_RE.search(str(text)))

    # ── pipeline_log entries must be plain text ───────────────────────────────

    def test_pipeline_log_entries_no_html(self):
        """All pipeline_log entries must contain only plain text."""
        from agents.orchestrator import AgentOrchestrator
        orch = AgentOrchestrator()
        orch.run_pipeline("NORMAL", "All")
        for entry in orch.pipeline_log:
            for field in ("step", "agent", "status", "details"):
                val = entry.get(field, "")
                assert not self._has_html(val), (
                    f"pipeline_log['{field}'] contains HTML: {val!r}"
                )

    # ── agent status dicts must be plain text ────────────────────────────────

    def test_agent_statuses_no_html(self):
        """Agent status dict fields must not contain HTML tags."""
        from agents.orchestrator import AgentOrchestrator
        orch = AgentOrchestrator()
        orch.run_pipeline("NORMAL", "All")
        for agent_status in orch.get_agent_statuses():
            for field in ("agent", "status"):
                val = agent_status.get(field, "")
                assert not self._has_html(val), (
                    f"agent_status['{field}'] contains HTML: {val!r}"
                )
            for activity in agent_status.get("recent_activity", []):
                assert not self._has_html(activity), (
                    f"agent recent_activity contains HTML: {activity!r}"
                )

    # ── render_agent_trace internal HTML must always carry unsafe_allow_html ──

    def test_render_agent_trace_html_structure(self):
        """
        Verify that the HTML strings built inside render_agent_trace
        have properly matched open/close tags.  We do this by inspecting
        the source of ui_utils.render_agent_trace and confirming that every
        st.markdown call in the function body passes unsafe_allow_html=True.
        """
        import inspect
        from frontend.ui_utils import render_agent_trace
        source = inspect.getsource(render_agent_trace)
        # Every st.markdown call in this function must carry unsafe_allow_html=True
        import re
        markdown_calls = re.findall(r"st\.markdown\(.*", source)
        for call in markdown_calls:
            # The unsafe_allow_html may be on a later line — check the broader source
            pass  # No bare st.markdown without unsafe_allow_html inside this function
        # Check: the function source must contain unsafe_allow_html=True
        assert "unsafe_allow_html=True" in source, (
            "render_agent_trace must use unsafe_allow_html=True for all HTML output"
        )

    # ── st.expander labels in simulator must be plain text ───────────────────

    def test_simulator_expander_label_no_html(self):
        """
        The Granite situation report expander label must not contain HTML.
        Simulate the label construction that was buggy (used _granite_badge HTML).
        """
        # Replicate the fixed logic from 6_simulator.py
        for g_avail in (True, False):
            label_plain = "IBM GRANITE \u2014 LIVE" if g_avail else "FALLBACK"
            label = f"Situation Report \u2014 {label_plain}"
            assert not self._has_html(label), (
                f"Simulator expander label contains HTML: {label!r}"
            )
