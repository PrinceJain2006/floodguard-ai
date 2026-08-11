"""
FloodGuard AI — Flood Risk ML Model
Random Forest classifier + regressor for flood risk prediction.
Model is trained on synthetic data; replace with real data for production.

Features:
  rainfall_1h, rainfall_3h, rainfall_6h, rainfall_24h,
  drainage_capacity, historical_flood_freq, water_level,
  elevation, road_density, citizen_reports

Target:
  risk_label (LOW / MEDIUM / HIGH / CRITICAL)
  risk_score (0-100 continuous)
"""
import json
import joblib
import numpy as np
import pandas as pd
from pathlib import Path
from sklearn.ensemble import RandomForestClassifier, RandomForestRegressor
from sklearn.model_selection import train_test_split
from sklearn.preprocessing import LabelEncoder
from sklearn.metrics import classification_report, mean_absolute_error

FEATURE_COLS = [
    "rainfall_1h", "rainfall_3h", "rainfall_6h", "rainfall_24h",
    "drainage_capacity", "historical_flood_freq", "water_level",
    "elevation", "road_density", "citizen_reports",
]

LABEL_ORDER = ["LOW", "MEDIUM", "HIGH", "CRITICAL"]

BASE_DIR = Path(__file__).parent
MODELS_DIR = BASE_DIR / "models"
MODELS_DIR.mkdir(exist_ok=True)


class FloodRiskModel:
    """
    Wraps a Random Forest classifier (risk level) and regressor (risk score).
    Provides prediction with feature importance / explanation.
    """

    def __init__(self):
        self.classifier: RandomForestClassifier | None = None
        self.regressor: RandomForestRegressor | None = None
        self.label_encoder: LabelEncoder = LabelEncoder()
        self.is_trained = False

    # ──────────────────────────────────────
    # Training
    # ──────────────────────────────────────
    def train(self, df: pd.DataFrame) -> dict:
        X = df[FEATURE_COLS].values
        y_label = df["risk_label"].values
        y_score = df["risk_score"].values

        # Encode labels maintaining order
        self.label_encoder.classes_ = np.array(LABEL_ORDER)
        y_enc = self.label_encoder.transform(y_label)

        X_train, X_test, yl_train, yl_test, ys_train, ys_test = train_test_split(
            X, y_enc, y_score, test_size=0.2, random_state=42, stratify=y_enc
        )

        # Classifier
        self.classifier = RandomForestClassifier(
            n_estimators=200, max_depth=12, random_state=42, n_jobs=-1
        )
        self.classifier.fit(X_train, yl_train)

        # Regressor
        self.regressor = RandomForestRegressor(
            n_estimators=200, max_depth=12, random_state=42, n_jobs=-1
        )
        self.regressor.fit(X_train, ys_train)

        self.is_trained = True

        # Evaluation
        yl_pred = self.classifier.predict(X_test)
        ys_pred = self.regressor.predict(X_test)
        report_text = classification_report(
            yl_test, yl_pred,
            target_names=LABEL_ORDER,
            zero_division=0
        )
        mae = mean_absolute_error(ys_test, ys_pred)

        return {
            "classification_report": report_text,
            "score_mae": round(mae, 3),
            "n_train": len(X_train),
            "n_test": len(X_test),
        }

    # ──────────────────────────────────────
    # Prediction
    # ──────────────────────────────────────
    def predict(self, features: dict) -> dict:
        """
        features: dict with keys matching FEATURE_COLS
        Returns risk_score, risk_level, confidence, feature_importance
        """
        if not self.is_trained:
            return self._fallback_predict(features)

        row = np.array([[features.get(f, 0.0) for f in FEATURE_COLS]])

        # Score
        score = float(np.clip(self.regressor.predict(row)[0], 0, 100))

        # Label + probabilities
        proba = self.classifier.predict_proba(row)[0]
        label_idx = int(np.argmax(proba))
        label = LABEL_ORDER[label_idx]
        confidence = float(proba[label_idx])

        # Feature importance
        fi = {
            feat: round(float(imp), 4)
            for feat, imp in zip(FEATURE_COLS, self.classifier.feature_importances_)
        }
        top_features = sorted(fi.items(), key=lambda x: -x[1])[:5]

        reasons = _build_reasons(features, top_features)

        return {
            "risk_score": round(score, 1),
            "risk_level": label,
            "confidence": round(confidence, 3),
            "probabilities": {
                LABEL_ORDER[i]: round(float(p), 3) for i, p in enumerate(proba)
            },
            "feature_importance": fi,
            "top_features": top_features,
            "main_reasons": reasons,
        }

    def _fallback_predict(self, features: dict) -> dict:
        """Rule-based fallback when model is not trained."""
        r1h = features.get("rainfall_1h", 0)
        dc = features.get("drainage_capacity", 50)
        hff = features.get("historical_flood_freq", 0)
        cr = features.get("citizen_reports", 0)
        wl = features.get("water_level", 0)

        score = (r1h * 0.40 + (100 - dc) * 0.25 + hff * 3 + cr * 0.2 + wl * 8) * 0.85
        score = max(0, min(100, score))

        level = (
            "CRITICAL" if score >= 75 else
            "HIGH" if score >= 50 else
            "MEDIUM" if score >= 25 else
            "LOW"
        )
        return {
            "risk_score": round(score, 1),
            "risk_level": level,
            "confidence": 0.70,
            "probabilities": {},
            "feature_importance": {},
            "top_features": [],
            "main_reasons": [f"Rule-based estimate (model not loaded). Score: {score:.0f}"],
        }

    # ──────────────────────────────────────
    # Persistence
    # ──────────────────────────────────────
    def save(self, path: Path | None = None):
        path = path or MODELS_DIR
        joblib.dump(self.classifier, path / "classifier.pkl")
        joblib.dump(self.regressor, path / "regressor.pkl")
        joblib.dump(self.label_encoder, path / "label_encoder.pkl")
        print(f"[ML] Models saved to {path}")

    def load(self, path: Path | None = None) -> bool:
        path = path or MODELS_DIR
        try:
            self.classifier = joblib.load(path / "classifier.pkl")
            self.regressor = joblib.load(path / "regressor.pkl")
            self.label_encoder = joblib.load(path / "label_encoder.pkl")
            self.is_trained = True
            return True
        except FileNotFoundError:
            return False


# ──────────────────────────────────────────────
# Singleton instance
# ──────────────────────────────────────────────
_model_instance: FloodRiskModel | None = None


def get_model() -> FloodRiskModel:
    global _model_instance
    if _model_instance is None:
        _model_instance = FloodRiskModel()
        loaded = _model_instance.load()
        if not loaded:
            print("[ML] No saved model found. Training on synthetic data...")
            _train_and_save(_model_instance)
    return _model_instance


def _train_and_save(model: FloodRiskModel):
    """Train the model from synthetic data file."""
    data_path = Path(__file__).parent.parent / "data" / "ml_training_data.json"
    if not data_path.exists():
        print("[ML] Training data not found. Generating...")
        from data.seed_generator import generate_ml_training_data
        data = generate_ml_training_data(5000)
        data_path.parent.mkdir(exist_ok=True)
        with open(data_path, "w") as f:
            json.dump(data, f)

    with open(data_path) as f:
        data = json.load(f)

    df = pd.DataFrame(data)
    metrics = model.train(df)
    model.save()
    print(f"[ML] Training complete. MAE={metrics['score_mae']:.2f}")
    print(metrics["classification_report"])


# ──────────────────────────────────────────────
# Helpers
# ──────────────────────────────────────────────
def _build_reasons(features: dict, top_features: list) -> list[str]:
    reasons = []
    r1h = features.get("rainfall_1h", 0)
    dc = features.get("drainage_capacity", 50)
    hff = features.get("historical_flood_freq", 0)
    cr = features.get("citizen_reports", 0)
    wl = features.get("water_level", 0)
    elev = features.get("elevation", 50)

    if r1h > 50:
        reasons.append(f"Extreme rainfall intensity: {r1h:.1f} mm/hr")
    elif r1h > 25:
        reasons.append(f"High rainfall intensity: {r1h:.1f} mm/hr")

    if dc < 30:
        reasons.append(f"Critically low drainage capacity: {dc:.0f}%")
    elif dc < 60:
        reasons.append(f"Reduced drainage capacity: {dc:.0f}%")

    if hff >= 5:
        reasons.append(f"Frequent historical flooding: {hff} events/year")
    elif hff >= 2:
        reasons.append(f"Moderate historical flooding: {hff} events/year")

    if cr >= 30:
        reasons.append(f"High number of citizen flood reports: {int(cr)}")
    elif cr >= 10:
        reasons.append(f"Multiple citizen reports received: {int(cr)}")

    if wl >= 3:
        reasons.append(f"Dangerously high water level: {wl:.1f}m")
    elif wl >= 1.5:
        reasons.append(f"Elevated water level: {wl:.1f}m")

    if elev < 15:
        reasons.append(f"Very low elevation: {elev:.0f}m (high inundation risk)")
    elif elev < 30:
        reasons.append(f"Low elevation zone: {elev:.0f}m")

    return reasons[:5] if reasons else ["Within normal parameters."]


# ──────────────────────────────────────────────
# CLI entry point
# ──────────────────────────────────────────────
if __name__ == "__main__":
    print("[ML] FloodGuard AI — Flood Risk Model Trainer")
    print("[NOTICE] Using synthetic demo data.")
    model = FloodRiskModel()
    _train_and_save(model)

    # Quick smoke test
    test_features = {
        "rainfall_1h": 85,
        "rainfall_3h": 230,
        "rainfall_6h": 420,
        "rainfall_24h": 900,
        "drainage_capacity": 25,
        "historical_flood_freq": 7,
        "water_level": 2.8,
        "elevation": 10,
        "road_density": 0.88,
        "citizen_reports": 42,
    }
    result = model.predict(test_features)
    print(f"\n[ML] Smoke test prediction:")
    print(f"  Risk: {result['risk_level']} ({result['risk_score']:.1f}/100)")
    print(f"  Confidence: {result['confidence']:.1%}")
    print(f"  Top reasons: {result['main_reasons'][:3]}")
