"""
FloodGuard AI — SQLite Persistence Layer
=========================================
Provides a lightweight, file-based persistence store for:
  - weather observations
  - flood-risk predictions
  - citizen reports
  - agent outputs
  - alerts
  - response decisions
  - prediction-outcome feedback
  - timestamps / source metadata

Design:
  - SQLite via stdlib sqlite3 — zero external dependency.
  - Thread-safe via connection-per-call pattern.
  - Graceful failure: every write error is caught and logged.
  - Abstraction allows future switch to PostgreSQL/Supabase.
  - Never exposes raw connection objects to callers.

On Streamlit Cloud:
  - SQLite writes to a temp path under /tmp or the working directory.
  - Data is ephemeral between deployments — acceptable for a prototype.
  - For production use, swap DB_PATH to a Supabase / PG connection string
    via DATABASE_URL secret.
"""
from __future__ import annotations

import json
import sqlite3
import threading
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

# ─────────────────────────────────────────────────────────────────────────────
# Database path
# ─────────────────────────────────────────────────────────────────────────────
_HERE = Path(__file__).parent.parent          # floodguard-ai/
_DB_PATH = _HERE / "data" / "floodguard.db"
_DB_PATH.parent.mkdir(parents=True, exist_ok=True)

_lock = threading.Lock()


# ─────────────────────────────────────────────────────────────────────────────
# Schema
# ─────────────────────────────────────────────────────────────────────────────
_SCHEMA_SQL = """
CREATE TABLE IF NOT EXISTS weather_observations (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    city        TEXT    NOT NULL,
    source      TEXT    NOT NULL,
    data_mode   TEXT    NOT NULL,
    rainfall_1h REAL,
    temperature REAL,
    humidity    REAL,
    wind_speed  REAL,
    condition   TEXT,
    raw_json    TEXT,
    recorded_at TEXT,
    created_at  TEXT    NOT NULL
);

CREATE TABLE IF NOT EXISTS flood_risk_predictions (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    area        TEXT    NOT NULL,
    city        TEXT    NOT NULL,
    risk_level  TEXT    NOT NULL,
    risk_score  REAL    NOT NULL,
    confidence  REAL,
    scenario    TEXT,
    raw_json    TEXT,
    created_at  TEXT    NOT NULL
);

CREATE TABLE IF NOT EXISTS citizen_reports (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    report_id   TEXT    UNIQUE,
    city        TEXT    NOT NULL,
    area        TEXT,
    description TEXT,
    severity    TEXT,
    status      TEXT,
    source      TEXT,
    raw_json    TEXT,
    created_at  TEXT    NOT NULL
);

CREATE TABLE IF NOT EXISTS alerts (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    event_id        TEXT    UNIQUE NOT NULL,
    location        TEXT    NOT NULL,
    risk_level      TEXT    NOT NULL,
    risk_score      REAL,
    expected_window TEXT,
    confidence      REAL,
    evidence_json   TEXT,
    recommended_action TEXT,
    notification_status TEXT,
    alert_state     TEXT    DEFAULT 'NEW',
    acknowledged_at TEXT,
    resolved_at     TEXT,
    final_outcome   TEXT,
    created_at      TEXT    NOT NULL
);

CREATE TABLE IF NOT EXISTS prediction_feedback (
    id                  INTEGER PRIMARY KEY AUTOINCREMENT,
    prediction_id       TEXT,
    area                TEXT,
    city                TEXT,
    predicted_level     TEXT,
    predicted_score     REAL,
    predicted_at        TEXT,
    actual_outcome      TEXT,
    outcome_recorded_at TEXT,
    error_delta         REAL,
    confidence          REAL,
    notes               TEXT,
    created_at          TEXT    NOT NULL
);

CREATE TABLE IF NOT EXISTS agent_outputs (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    agent_name  TEXT    NOT NULL,
    run_id      TEXT,
    output_json TEXT,
    status      TEXT,
    elapsed_sec REAL,
    created_at  TEXT    NOT NULL
);

CREATE TABLE IF NOT EXISTS system_events (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    event_type  TEXT    NOT NULL,
    message     TEXT,
    severity    TEXT    DEFAULT 'INFO',
    created_at  TEXT    NOT NULL
);
"""


# ─────────────────────────────────────────────────────────────────────────────
# Connection helper
# ─────────────────────────────────────────────────────────────────────────────

def _get_conn() -> sqlite3.Connection:
    conn = sqlite3.connect(str(_DB_PATH), check_same_thread=False)
    conn.row_factory = sqlite3.Row
    return conn


def _init_db() -> bool:
    """Create tables if they don't exist. Returns True on success."""
    try:
        with _lock:
            conn = _get_conn()
            conn.executescript(_SCHEMA_SQL)
            conn.commit()
            conn.close()
        return True
    except Exception as exc:
        print(f"[DB] Schema init error: {exc}")
        return False


# Initialise on import
_db_ok = _init_db()


def is_available() -> bool:
    """Return True if the database connection is working."""
    return _db_ok


# ─────────────────────────────────────────────────────────────────────────────
# Generic write helper
# ─────────────────────────────────────────────────────────────────────────────

def _execute(sql: str, params: tuple = ()) -> bool:
    """Execute a write SQL statement. Returns True on success."""
    try:
        with _lock:
            conn = _get_conn()
            conn.execute(sql, params)
            conn.commit()
            conn.close()
        return True
    except Exception as exc:
        print(f"[DB] Write error: {exc}")
        return False


def _query(sql: str, params: tuple = ()) -> list[dict]:
    """Execute a read SQL statement. Returns list of row dicts."""
    try:
        with _lock:
            conn = _get_conn()
            cur = conn.execute(sql, params)
            rows = [dict(r) for r in cur.fetchall()]
            conn.close()
            return rows
    except Exception as exc:
        print(f"[DB] Query error: {exc}")
        return []


# ─────────────────────────────────────────────────────────────────────────────
# Public API — Weather Observations
# ─────────────────────────────────────────────────────────────────────────────

def save_weather_observation(city: str, data: dict) -> bool:
    """Persist a weather observation record."""
    now = datetime.now(timezone.utc).isoformat()
    return _execute(
        """INSERT INTO weather_observations
           (city, source, data_mode, rainfall_1h, temperature, humidity,
            wind_speed, condition, raw_json, recorded_at, created_at)
           VALUES (?,?,?,?,?,?,?,?,?,?,?)""",
        (
            city,
            data.get("source", "Unknown"),
            data.get("data_mode", "DEMO"),
            data.get("rainfall_1h", 0.0),
            data.get("temperature"),
            data.get("humidity"),
            data.get("wind_speed"),
            data.get("condition"),
            json.dumps(data),
            data.get("recorded_at", now),
            now,
        ),
    )


def get_latest_weather(city: str) -> dict | None:
    """Return the most recent weather observation for a city."""
    rows = _query(
        "SELECT * FROM weather_observations WHERE city=? ORDER BY id DESC LIMIT 1",
        (city,),
    )
    if rows:
        r = rows[0]
        try:
            return json.loads(r.get("raw_json", "{}"))
        except Exception:
            return dict(r)
    return None


# ─────────────────────────────────────────────────────────────────────────────
# Public API — Flood Risk Predictions
# ─────────────────────────────────────────────────────────────────────────────

def save_prediction(prediction: dict) -> bool:
    """Persist a flood-risk prediction record."""
    now = datetime.now(timezone.utc).isoformat()
    return _execute(
        """INSERT INTO flood_risk_predictions
           (area, city, risk_level, risk_score, confidence, scenario, raw_json, created_at)
           VALUES (?,?,?,?,?,?,?,?)""",
        (
            prediction.get("area", ""),
            prediction.get("city", ""),
            prediction.get("risk_level", "LOW"),
            prediction.get("risk_score", 0.0),
            prediction.get("confidence", 0.0),
            prediction.get("scenario", ""),
            json.dumps(prediction),
            now,
        ),
    )


def get_recent_predictions(limit: int = 50) -> list[dict]:
    """Return the N most recent predictions."""
    return _query(
        "SELECT * FROM flood_risk_predictions ORDER BY id DESC LIMIT ?",
        (limit,),
    )


# ─────────────────────────────────────────────────────────────────────────────
# Public API — Alerts
# ─────────────────────────────────────────────────────────────────────────────

def save_alert(alert: dict) -> bool:
    """Persist an alert record. Uses INSERT OR REPLACE on event_id."""
    now = datetime.now(timezone.utc).isoformat()
    return _execute(
        """INSERT OR REPLACE INTO alerts
           (event_id, location, risk_level, risk_score, expected_window,
            confidence, evidence_json, recommended_action, notification_status,
            alert_state, acknowledged_at, resolved_at, final_outcome, created_at)
           VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
        (
            alert.get("event_id", ""),
            alert.get("location", ""),
            alert.get("risk_level", ""),
            alert.get("risk_score", 0.0),
            alert.get("expected_window", ""),
            alert.get("confidence", 0.0),
            json.dumps(alert.get("evidence", [])),
            alert.get("recommended_action", ""),
            json.dumps(alert.get("notification_status", {})),
            alert.get("alert_state", "NEW"),
            alert.get("acknowledged_at"),
            alert.get("resolved_at"),
            alert.get("final_outcome"),
            alert.get("created_at", now),
        ),
    )


def get_alerts(state_filter: str | None = None, limit: int = 100) -> list[dict]:
    """Return alerts, optionally filtered by state."""
    if state_filter:
        rows = _query(
            "SELECT * FROM alerts WHERE alert_state=? ORDER BY id DESC LIMIT ?",
            (state_filter, limit),
        )
    else:
        rows = _query(
            "SELECT * FROM alerts ORDER BY id DESC LIMIT ?",
            (limit,),
        )
    # Deserialise JSON fields
    for r in rows:
        try:
            r["evidence"] = json.loads(r.get("evidence_json") or "[]")
        except Exception:
            r["evidence"] = []
        try:
            r["notification_status"] = json.loads(r.get("notification_status") or "{}")
        except Exception:
            r["notification_status"] = {}
    return rows


def update_alert_state(event_id: str, new_state: str, extra: dict | None = None) -> bool:
    """Update the state of an existing alert."""
    now = datetime.now(timezone.utc).isoformat()
    extra = extra or {}
    ack = extra.get("acknowledged_at") if new_state == "ACKNOWLEDGED" else None
    res = extra.get("resolved_at") if new_state == "RESOLVED" else None
    outcome = extra.get("final_outcome")
    return _execute(
        """UPDATE alerts SET alert_state=?, acknowledged_at=COALESCE(?,acknowledged_at),
           resolved_at=COALESCE(?,resolved_at), final_outcome=COALESCE(?,final_outcome)
           WHERE event_id=?""",
        (new_state, ack, res, outcome, event_id),
    )


# ─────────────────────────────────────────────────────────────────────────────
# Public API — Prediction Feedback
# ─────────────────────────────────────────────────────────────────────────────

def save_prediction_feedback(feedback: dict) -> bool:
    """Store prediction-to-outcome feedback record."""
    now = datetime.now(timezone.utc).isoformat()
    return _execute(
        """INSERT INTO prediction_feedback
           (prediction_id, area, city, predicted_level, predicted_score,
            predicted_at, actual_outcome, outcome_recorded_at,
            error_delta, confidence, notes, created_at)
           VALUES (?,?,?,?,?,?,?,?,?,?,?,?)""",
        (
            feedback.get("prediction_id", ""),
            feedback.get("area", ""),
            feedback.get("city", ""),
            feedback.get("predicted_level", ""),
            feedback.get("predicted_score", 0.0),
            feedback.get("predicted_at", ""),
            feedback.get("actual_outcome", ""),
            feedback.get("outcome_recorded_at", now),
            feedback.get("error_delta", 0.0),
            feedback.get("confidence", 0.0),
            feedback.get("notes", ""),
            now,
        ),
    )


def get_prediction_feedback(limit: int = 100) -> list[dict]:
    """Return the N most recent feedback records."""
    return _query(
        "SELECT * FROM prediction_feedback ORDER BY id DESC LIMIT ?",
        (limit,),
    )


# ─────────────────────────────────────────────────────────────────────────────
# Public API — System Events
# ─────────────────────────────────────────────────────────────────────────────

def log_event(event_type: str, message: str, severity: str = "INFO") -> bool:
    """Log a system event."""
    now = datetime.now(timezone.utc).isoformat()
    return _execute(
        "INSERT INTO system_events (event_type, message, severity, created_at) VALUES (?,?,?,?)",
        (event_type, message, severity, now),
    )


def get_recent_events(limit: int = 50) -> list[dict]:
    """Return recent system events."""
    return _query(
        "SELECT * FROM system_events ORDER BY id DESC LIMIT ?",
        (limit,),
    )


def get_db_status() -> dict:
    """Return database health status for observability panel."""
    try:
        conn = _get_conn()
        cur = conn.execute("SELECT COUNT(*) as n FROM alerts")
        alert_count = cur.fetchone()["n"]
        cur = conn.execute("SELECT COUNT(*) as n FROM weather_observations")
        weather_count = cur.fetchone()["n"]
        cur = conn.execute("SELECT COUNT(*) as n FROM flood_risk_predictions")
        pred_count = cur.fetchone()["n"]
        conn.close()
        return {
            "available": True,
            "db_path": str(_DB_PATH),
            "alert_count": alert_count,
            "weather_count": weather_count,
            "prediction_count": pred_count,
        }
    except Exception as exc:
        return {"available": False, "error": str(exc)}
