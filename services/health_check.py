"""
FloodGuard AI — System Health & Observability
===============================================
Provides a real-time health check for all system components.

Components checked:
  - Weather API (Open-Meteo)
  - Water Level Service
  - Database (SQLite)
  - IBM Granite / WatsonX
  - ML Model
  - Notification channels (Email / SMS / Webhook)
  - Alert Engine
  - Citizen Reports Store

Returns structured status dicts suitable for the observability panel.
"""
from __future__ import annotations

import time
from datetime import datetime, timezone
from typing import Any


def _check_weather_api() -> dict[str, Any]:
    """Check Open-Meteo weather API connectivity."""
    try:
        from services.live_data_manager import get_live_data_manager
        ldm = get_live_data_manager()
        status = ldm.get_status()
        if status.get("is_live"):
            last = status.get("last_updated", "")
            return {
                "name":    "Weather API (Open-Meteo)",
                "status":  "🟢 LIVE",
                "detail":  f"Connected — Last update: {last[:19] if last else 'Unknown'}",
                "ok":      True,
                "mode":    "LIVE",
            }
        else:
            reason = status.get("fallback_reason", "Unavailable")
            return {
                "name":    "Weather API (Open-Meteo)",
                "status":  "🟡 FALLBACK",
                "detail":  f"Using demo data — {reason}",
                "ok":      False,
                "mode":    "FALLBACK",
            }
    except Exception as exc:
        return {
            "name":    "Weather API (Open-Meteo)",
            "status":  "🔴 ERROR",
            "detail":  str(exc)[:120],
            "ok":      False,
            "mode":    "ERROR",
        }


def _check_water_level() -> dict[str, Any]:
    """Check water level service status."""
    try:
        from services.water_level_service import get_water_level_service
        svc = get_water_level_service()
        s   = svc.get_status_summary()
        live = s.get("live_sensor", False)
        return {
            "name":    "Water Level",
            "status":  "🟢 LIVE" if live else "🟡 ESTIMATED",
            "detail":  s.get("note", ""),
            "ok":      True,
            "mode":    "LIVE" if live else "ESTIMATED",
        }
    except Exception as exc:
        return {
            "name":    "Water Level",
            "status":  "🔴 ERROR",
            "detail":  str(exc)[:120],
            "ok":      False,
            "mode":    "ERROR",
        }


def _check_database() -> dict[str, Any]:
    """Check SQLite database connectivity."""
    try:
        from services.database import get_db_status
        db = get_db_status()
        if db.get("available"):
            return {
                "name":    "Database (SQLite)",
                "status":  "🟢 CONNECTED",
                "detail":  (
                    f"Alerts: {db.get('alert_count',0)} | "
                    f"Weather obs: {db.get('weather_count',0)} | "
                    f"Predictions: {db.get('prediction_count',0)}"
                ),
                "ok":      True,
                "mode":    "CONNECTED",
            }
        else:
            return {
                "name":    "Database (SQLite)",
                "status":  "🔴 ERROR",
                "detail":  db.get("error", "Unknown error"),
                "ok":      False,
                "mode":    "ERROR",
            }
    except Exception as exc:
        return {
            "name":    "Database (SQLite)",
            "status":  "🔴 ERROR",
            "detail":  str(exc)[:120],
            "ok":      False,
            "mode":    "ERROR",
        }


def _check_granite() -> dict[str, Any]:
    """Check IBM Granite / WatsonX connectivity."""
    try:
        from agents.granite_service import granite_status
        g = granite_status()
        if g.get("available"):
            return {
                "name":    "IBM Granite (WatsonX)",
                "status":  "🟢 LIVE",
                "detail":  f"Model: {g.get('model','unknown')}",
                "ok":      True,
                "mode":    "LIVE",
            }
        elif g.get("rate_limited"):
            return {
                "name":    "IBM Granite (WatsonX)",
                "status":  "🟠 RATE LIMITED",
                "detail":  "Rate limited — rule-based fallback active",
                "ok":      False,
                "mode":    "RATE_LIMITED",
            }
        elif g.get("config_error"):
            return {
                "name":    "IBM Granite (WatsonX)",
                "status":  "🔴 CONFIG ERROR",
                "detail":  "Check WATSONX_API_KEY + WATSONX_PROJECT_ID",
                "ok":      False,
                "mode":    "CONFIG_ERROR",
            }
        else:
            return {
                "name":    "IBM Granite (WatsonX)",
                "status":  "🟡 FALLBACK",
                "detail":  "Using rule-based fallback — configure WatsonX credentials",
                "ok":      False,
                "mode":    "FALLBACK",
            }
    except Exception as exc:
        return {
            "name":    "IBM Granite (WatsonX)",
            "status":  "🔴 ERROR",
            "detail":  str(exc)[:120],
            "ok":      False,
            "mode":    "ERROR",
        }


def _check_ml_model() -> dict[str, Any]:
    """Check ML model load status."""
    try:
        from ml.flood_risk_model import get_model
        model = get_model()
        if model.is_trained:
            return {
                "name":    "ML Model (Random Forest)",
                "status":  "🟢 LOADED",
                "detail":  "Trained model loaded from disk",
                "ok":      True,
                "mode":    "LOADED",
            }
        else:
            return {
                "name":    "ML Model (Random Forest)",
                "status":  "🟡 FALLBACK",
                "detail":  "Model not trained — using rule-based fallback",
                "ok":      False,
                "mode":    "FALLBACK",
            }
    except Exception as exc:
        return {
            "name":    "ML Model (Random Forest)",
            "status":  "🔴 ERROR",
            "detail":  str(exc)[:120],
            "ok":      False,
            "mode":    "ERROR",
        }


def _check_notifications() -> dict[str, Any]:
    """Check notification channel configuration."""
    try:
        from services.notification_service import get_notification_manager
        nm = get_notification_manager()
        ch = nm.get_channel_status()
        configured = sum(1 for v in ch.values() if isinstance(v, dict) and v.get("configured"))
        if configured > 0:
            channels = [k for k, v in ch.items() if isinstance(v, dict) and v.get("configured")]
            return {
                "name":    "Notifications",
                "status":  "🟢 CONFIGURED",
                "detail":  f"Active channels: {', '.join(channels)}",
                "ok":      True,
                "mode":    "CONFIGURED",
            }
        else:
            return {
                "name":    "Notifications",
                "status":  "🔴 NOT CONFIGURED",
                "detail":  "No notification channels configured (Email/SMS/Webhook)",
                "ok":      False,
                "mode":    "NOT_CONFIGURED",
            }
    except Exception as exc:
        return {
            "name":    "Notifications",
            "status":  "🔴 ERROR",
            "detail":  str(exc)[:120],
            "ok":      False,
            "mode":    "ERROR",
        }


def _check_alert_engine() -> dict[str, Any]:
    """Check flood alert engine status."""
    try:
        from services.flood_alert_engine import get_alert_engine
        engine = get_alert_engine()
        active = len(engine.get_active_alerts())
        return {
            "name":    "Alert Engine",
            "status":  "🟢 RUNNING",
            "detail":  f"{active} active alert(s)",
            "ok":      True,
            "mode":    "RUNNING",
        }
    except Exception as exc:
        return {
            "name":    "Alert Engine",
            "status":  "🔴 ERROR",
            "detail":  str(exc)[:120],
            "ok":      False,
            "mode":    "ERROR",
        }


def get_system_health() -> dict[str, Any]:
    """
    Run all health checks and return a consolidated status report.
    This is used by the observability panel in the UI.
    """
    t_start = time.time()
    checks = [
        _check_weather_api,
        _check_water_level,
        _check_database,
        _check_granite,
        _check_ml_model,
        _check_notifications,
        _check_alert_engine,
    ]

    results: list[dict] = []
    for fn in checks:
        try:
            results.append(fn())
        except Exception as exc:
            results.append({
                "name":   fn.__name__.replace("_check_", "").replace("_", " ").title(),
                "status": "🔴 ERROR",
                "detail": str(exc)[:120],
                "ok":     False,
                "mode":   "ERROR",
            })

    ok_count     = sum(1 for r in results if r.get("ok"))
    total_checks = len(results)
    elapsed      = round(time.time() - t_start, 2)

    return {
        "checks":            results,
        "ok_count":          ok_count,
        "total_checks":      total_checks,
        "health_pct":        round(ok_count / max(total_checks, 1) * 100),
        "checked_at":        datetime.now(timezone.utc).isoformat(),
        "check_duration_sec": elapsed,
    }
