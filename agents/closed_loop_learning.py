"""
FloodGuard AI — Closed-Loop Learning Store
Stores Prediction → Incident → Response → Outcome cycles
and provides prediction vs outcome comparison.
All data is DEMO/SIMULATED — not real operational data.
"""
import random
from datetime import datetime, timedelta
from typing import Any


class ClosedLoopLearning:
    """
    Tracks the full learning cycle:
      Prediction → Incident → Response Action → Outcome
    Compares predicted risk vs actual outcomes for model improvement tracking.
    DEMO: generates simulated history; in production would persist to DB.
    """

    def __init__(self):
        self._cycles: list[dict] = []
        self._initialized = False

    def _seed_demo_history(self, risk_predictions: list[dict], scenario: str):
        """Generate plausible demo history from current predictions."""
        self._cycles = []
        outcomes = ["RESOLVED", "ONGOING", "ESCALATED", "MITIGATED", "FALSE_ALARM"]
        outcome_weights = {
            "NORMAL":   [0.5, 0.2, 0.05, 0.2, 0.05],
            "HEAVY":    [0.3, 0.3, 0.15, 0.2, 0.05],
            "EXTREME":  [0.15, 0.2, 0.35, 0.25, 0.05],
            "CITIZEN_SURGE": [0.35, 0.25, 0.1, 0.25, 0.05],
            "EMERGENCY": [0.1, 0.15, 0.45, 0.25, 0.05],
        }
        weights = outcome_weights.get(scenario, [0.3, 0.25, 0.15, 0.25, 0.05])
        response_types = ["Pump deployed", "Drain cleared", "Road closed", "Team dispatched", "Shelter opened"]
        
        now = datetime.utcnow()

        for i, pred in enumerate(risk_predictions[:15]):
            t_pred = now - timedelta(hours=random.randint(1, 48))
            t_inc  = t_pred + timedelta(minutes=random.randint(10, 90))
            t_resp = t_inc  + timedelta(minutes=random.randint(5, 45))
            t_out  = t_resp + timedelta(minutes=random.randint(30, 180))

            predicted_score = pred["risk_score"]
            # Actual outcome score: correlated but with noise
            noise = random.uniform(-15, 15)
            actual_score = max(0, min(100, predicted_score + noise))
            
            outcome = random.choices(outcomes, weights=weights)[0]
            # Actual level from actual score
            if actual_score >= 75:   actual_level = "CRITICAL"
            elif actual_score >= 50: actual_level = "HIGH"
            elif actual_score >= 25: actual_level = "MEDIUM"
            else:                    actual_level = "LOW"

            accuracy = 100 - abs(predicted_score - actual_score)

            self._cycles.append({
                "cycle_id": f"CL-{i+1:04d}",
                "area": pred["area"],
                "city": pred["city"],
                # Prediction
                "predicted_risk_level": pred["risk_level"],
                "predicted_risk_score": round(predicted_score, 1),
                "prediction_time": t_pred.isoformat(),
                "prediction_confidence": pred.get("confidence", 0.80),
                # Incident
                "incident_detected": pred["risk_level"] in ("HIGH", "CRITICAL"),
                "incident_time": t_inc.isoformat(),
                "incident_category": random.choice(
                    ["waterlogging", "drain_overflow", "road_blockage", "property_flooding"]
                ),
                # Response
                "response_action": random.choice(response_types),
                "response_time": t_resp.isoformat(),
                "response_time_minutes": int((t_resp - t_inc).total_seconds() / 60),
                "resources_deployed": random.randint(1, 4),
                # Outcome
                "actual_risk_level": actual_level,
                "actual_risk_score": round(actual_score, 1),
                "outcome": outcome,
                "outcome_time": t_out.isoformat(),
                "resolution_time_minutes": int((t_out - t_inc).total_seconds() / 60),
                # Learning metrics
                "prediction_accuracy": round(accuracy, 1),
                "score_delta": round(actual_score - predicted_score, 1),
                "model_feedback": _derive_feedback(pred["risk_level"], actual_level, outcome),
                "data_label": "DEMO/SIMULATED",
            })

        self._initialized = True

    def record_cycle(self, cycle: dict):
        """Add a new learning cycle (in production would persist)."""
        self._cycles.append(cycle)

    def get_cycles(self, scenario: str = "NORMAL", risk_predictions: list[dict] | None = None) -> list[dict]:
        """Return all learning cycles, seeding demo data if needed."""
        if not self._initialized and risk_predictions:
            self._seed_demo_history(risk_predictions, scenario)
        return self._cycles

    def get_accuracy_summary(self) -> dict:
        """Compute overall prediction accuracy stats."""
        if not self._cycles:
            return {}
        
        correct_level = sum(
            1 for c in self._cycles
            if c["predicted_risk_level"] == c["actual_risk_level"]
        )
        avg_accuracy = sum(c["prediction_accuracy"] for c in self._cycles) / len(self._cycles)
        avg_delta = sum(c["score_delta"] for c in self._cycles) / len(self._cycles)
        avg_response_time = sum(c["response_time_minutes"] for c in self._cycles) / len(self._cycles)
        
        outcomes = {}
        for c in self._cycles:
            o = c["outcome"]
            outcomes[o] = outcomes.get(o, 0) + 1

        return {
            "total_cycles": len(self._cycles),
            "level_accuracy_pct": round(correct_level / len(self._cycles) * 100, 1),
            "avg_score_accuracy": round(avg_accuracy, 1),
            "avg_score_delta": round(avg_delta, 1),
            "avg_response_time_min": round(avg_response_time, 1),
            "outcome_distribution": outcomes,
            "data_label": "DEMO/SIMULATED",
        }


def _derive_feedback(predicted: str, actual: str, outcome: str) -> str:
    levels = ["LOW", "MEDIUM", "HIGH", "CRITICAL"]
    pi = levels.index(predicted) if predicted in levels else 1
    ai = levels.index(actual)    if actual    in levels else 1
    
    if pi == ai:
        return "✅ Accurate prediction"
    elif pi < ai:
        return f"⚠️ Under-predicted ({predicted} → actual {actual})"
    else:
        return f"📉 Over-predicted ({predicted} → actual {actual})"


# ──────────────────────────────────────────────
# Singleton
# ──────────────────────────────────────────────
_learning_store: ClosedLoopLearning | None = None


def get_learning_store() -> ClosedLoopLearning:
    global _learning_store
    if _learning_store is None:
        _learning_store = ClosedLoopLearning()
    return _learning_store
