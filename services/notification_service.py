"""
FloodGuard AI — Notification Service
======================================
Modular notification system for flood alerts.

Architecture:
    Alert Engine
        ↓
    Notification Manager
    ├── Dashboard (always active)
    ├── Email Adapter     (optional — requires SMTP config)
    ├── SMS Adapter       (optional — requires SMS_API_KEY)
    └── Webhook Adapter   (optional — requires WEBHOOK_URL)

IMPORTANT RULES:
  - All credentials come from environment variables / Streamlit secrets.
  - Never hard-code API keys, passwords, or phone numbers.
  - If a channel is not configured, show "NOT CONFIGURED" — do NOT pretend
    a notification was sent.
  - Simulation/test alerts must always include a "TEST ALERT" label.
  - Real notifications to government/emergency services require authorized
    integration — this system is decision support only.

Environment variables required per channel:

  Email:
    EMAIL_ENABLED=true
    SMTP_HOST=smtp.example.com
    SMTP_PORT=587
    SMTP_USERNAME=sender@example.com
    SMTP_PASSWORD=<secret>
    SMTP_FROM=FloodGuard AI <alerts@example.com>
    ALERT_RECIPIENTS=ops@example.com,manager@example.com

  SMS:
    SMS_ENABLED=true
    SMS_PROVIDER=twilio           (only 'twilio' currently supported)
    SMS_API_KEY=<secret>
    SMS_API_SECRET=<secret>       (Twilio account SID / auth token)
    SMS_SENDER=+1xxxxxxxxxx
    SMS_RECIPIENTS=+91xxxxxxxxxx,+91yyyyyyyyyy

  Webhook:
    WEBHOOK_ENABLED=true
    WEBHOOK_URL=https://your-system.example.com/flood-alert
    WEBHOOK_SECRET=<optional HMAC secret>

  Test mode:
    TEST_NOTIFICATION_MODE=true   (must be explicitly set to allow test sends)
"""
from __future__ import annotations

import hashlib
import hmac
import json
import os
import smtplib
import time
from datetime import datetime, timezone
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from typing import Any

# ─────────────────────────────────────────────────────────────────────────────
# Config helpers
# ─────────────────────────────────────────────────────────────────────────────

def _env(key: str, default: str = "") -> str:
    """Read from env / Streamlit secrets. Never crashes.

    st.secrets is only consulted when:
      1. Streamlit is already imported in sys.modules, AND
      2. An active ScriptRunContext exists for this thread.
    This prevents the "No secrets files found" warning that Streamlit emits
    when st.secrets is accessed outside a running app worker (e.g. on import,
    during pytest, or in background threads).
    """
    import sys
    try:
        _st = sys.modules.get("streamlit")
        if _st is None:
            raise LookupError("streamlit not imported")
        # Only access st.secrets inside an active Streamlit script-run thread
        _scriptrunner = sys.modules.get("streamlit.runtime.scriptrunner")
        if _scriptrunner is None:
            raise LookupError("scriptrunner not imported")
        _get_ctx = getattr(_scriptrunner, "get_script_run_ctx", None)
        if _get_ctx is None or _get_ctx() is None:
            raise LookupError("no active ScriptRunContext")
        val = _st.secrets.get(key, "")
        if val:
            return str(val)
    except Exception:
        pass
    return os.getenv(key, default)


def _bool_env(key: str, default: bool = False) -> bool:
    return _env(key, str(default)).lower() == "true"


def _int_env(key: str, default: int = 0) -> int:
    try:
        return int(_env(key, str(default)))
    except (ValueError, TypeError):
        return default


# ─────────────────────────────────────────────────────────────────────────────
# Delivery record
# ─────────────────────────────────────────────────────────────────────────────

class DeliveryRecord:
    """Track a single notification delivery attempt."""

    def __init__(self, channel: str, recipient: str):
        self.channel = channel
        self.recipient = recipient
        self.sent_at: str | None = None
        self.status: str = "PENDING"   # PENDING | SENT | FAILED | SKIPPED
        self.failure_reason: str = ""
        self.retry_count: int = 0

    def mark_sent(self):
        self.status = "SENT"
        self.sent_at = datetime.now(timezone.utc).isoformat()

    def mark_failed(self, reason: str):
        self.status = "FAILED"
        self.failure_reason = reason

    def mark_skipped(self, reason: str):
        self.status = "SKIPPED"
        self.failure_reason = reason

    def to_dict(self) -> dict:
        return {
            "channel": self.channel,
            "recipient": self.recipient,
            "sent_at": self.sent_at,
            "status": self.status,
            "failure_reason": self.failure_reason,
            "retry_count": self.retry_count,
        }


# ─────────────────────────────────────────────────────────────────────────────
# Email Adapter
# ─────────────────────────────────────────────────────────────────────────────

def _send_email(alert: dict, is_test: bool = False) -> list[DeliveryRecord]:
    """Send email notification. Returns list of DeliveryRecord."""
    records: list[DeliveryRecord] = []

    if not _bool_env("EMAIL_ENABLED"):
        r = DeliveryRecord("email", "N/A")
        r.mark_skipped("EMAIL_ENABLED is not set to 'true'")
        return [r]

    smtp_host = _env("SMTP_HOST")
    smtp_port = _int_env("SMTP_PORT", 587)
    smtp_user = _env("SMTP_USERNAME")
    smtp_pass = _env("SMTP_PASSWORD")
    smtp_from = _env("SMTP_FROM", smtp_user)
    recipients_str = _env("ALERT_RECIPIENTS")

    if not smtp_host or not smtp_user or not smtp_pass:
        r = DeliveryRecord("email", "N/A")
        r.mark_skipped("SMTP_HOST / SMTP_USERNAME / SMTP_PASSWORD not configured")
        return [r]

    recipients = [r.strip() for r in recipients_str.split(",") if r.strip()]
    if not recipients:
        r = DeliveryRecord("email", "N/A")
        r.mark_skipped("ALERT_RECIPIENTS not configured")
        return [r]

    test_prefix = "[TEST ALERT — NOT A REAL EMERGENCY] " if is_test else ""
    risk_level  = alert.get("risk_level", "UNKNOWN")
    location    = alert.get("location", "Unknown")
    subject     = f"{test_prefix}[{risk_level} FLOOD ALERT] {location}"

    # Build text body
    evidence_lines = "\n".join(
        f"  • {e}" for e in alert.get("evidence", [])
    ) or "  • No specific evidence provided"

    body_text = f"""
FloodGuard AI — Flood Alert Notification
{"=" * 50}
{f"⚠️  TEST ALERT — NOT A REAL EMERGENCY  ⚠️" if is_test else ""}

Location:         {location}
Risk Level:       {risk_level}
Risk Score:       {alert.get('risk_score', 'N/A')}/100
Expected Window:  {alert.get('expected_window', 'Unknown')}
Confidence:       {round(alert.get('confidence', 0) * 100, 0):.0f}%

Evidence:
{evidence_lines}

Recommended Action:
  {alert.get('recommended_action', 'Review dashboard for details.')}

Timestamp:    {alert.get('timestamp', datetime.now(timezone.utc).isoformat())}
Data Sources: {alert.get('data_sources', 'See dashboard')}
Alert ID:     {alert.get('event_id', 'N/A')}

{"=" * 50}
This alert was generated by FloodGuard AI decision-support system.
All AI recommendations require authorized human verification before
real-world emergency response actions are taken.
This system is a prototype and does not constitute an official
municipal emergency notification service.
"""

    for recipient in recipients:
        rec = DeliveryRecord("email", recipient)
        try:
            msg = MIMEMultipart("alternative")
            msg["Subject"] = subject
            msg["From"]    = smtp_from
            msg["To"]      = recipient
            msg.attach(MIMEText(body_text, "plain"))

            with smtplib.SMTP(smtp_host, smtp_port, timeout=15) as server:
                server.ehlo()
                server.starttls()
                server.login(smtp_user, smtp_pass)
                server.sendmail(smtp_from, [recipient], msg.as_string())

            rec.mark_sent()
        except Exception as exc:
            rec.mark_failed(f"SMTP error: {type(exc).__name__}: {exc}")
        records.append(rec)

    return records


# ─────────────────────────────────────────────────────────────────────────────
# SMS Adapter (Twilio)
# ─────────────────────────────────────────────────────────────────────────────

def _send_sms(alert: dict, is_test: bool = False) -> list[DeliveryRecord]:
    """Send SMS via Twilio. Returns list of DeliveryRecord."""
    records: list[DeliveryRecord] = []

    if not _bool_env("SMS_ENABLED"):
        r = DeliveryRecord("sms", "N/A")
        r.mark_skipped("SMS_ENABLED is not set to 'true'")
        return [r]

    provider   = _env("SMS_PROVIDER", "twilio").lower()
    api_key    = _env("SMS_API_KEY")    # Twilio Account SID
    api_secret = _env("SMS_API_SECRET") # Twilio Auth Token
    sender     = _env("SMS_SENDER")
    recip_str  = _env("SMS_RECIPIENTS")

    if not api_key or not api_secret or not sender:
        r = DeliveryRecord("sms", "N/A")
        r.mark_skipped("SMS_API_KEY / SMS_API_SECRET / SMS_SENDER not configured")
        return [r]

    recipients = [r.strip() for r in recip_str.split(",") if r.strip()]
    if not recipients:
        r = DeliveryRecord("sms", "N/A")
        r.mark_skipped("SMS_RECIPIENTS not configured")
        return [r]

    test_label = "TEST ALERT — NOT REAL. " if is_test else ""
    location   = alert.get("location", "Unknown")
    risk_level = alert.get("risk_level", "UNKNOWN")
    window     = alert.get("expected_window", "Unknown")
    evidence_short = "; ".join(alert.get("evidence", [])[:2])

    message = (
        f"{test_label}FloodGuard-AI ALERT: {risk_level} risk in {location}. "
        f"Expected risk window: {window}. "
        f"Reason: {evidence_short}. "
        "Check dashboard for details."
    )

    if provider != "twilio":
        r = DeliveryRecord("sms", "N/A")
        r.mark_skipped(f"SMS provider '{provider}' not supported — only 'twilio' implemented")
        return [r]

    for recipient in recipients:
        rec = DeliveryRecord("sms", recipient[-4:] + "****")  # mask number
        try:
            import httpx
            resp = httpx.post(
                f"https://api.twilio.com/2010-04-01/Accounts/{api_key}/Messages.json",
                auth=(api_key, api_secret),
                data={"From": sender, "To": recipient, "Body": message},
                timeout=15,
            )
            if resp.status_code in (200, 201):
                rec.mark_sent()
            else:
                rec.mark_failed(f"Twilio HTTP {resp.status_code}")
        except Exception as exc:
            rec.mark_failed(f"Twilio error: {type(exc).__name__}: {exc}")
        records.append(rec)

    return records


# ─────────────────────────────────────────────────────────────────────────────
# Webhook Adapter
# ─────────────────────────────────────────────────────────────────────────────

def _send_webhook(alert: dict, is_test: bool = False) -> list[DeliveryRecord]:
    """POST alert JSON to configured webhook. Returns list of DeliveryRecord."""
    rec = DeliveryRecord("webhook", "")

    if not _bool_env("WEBHOOK_ENABLED"):
        rec.mark_skipped("WEBHOOK_ENABLED is not set to 'true'")
        return [rec]

    webhook_url    = _env("WEBHOOK_URL")
    webhook_secret = _env("WEBHOOK_SECRET")

    if not webhook_url:
        rec.mark_skipped("WEBHOOK_URL not configured")
        return [rec]

    rec.recipient = webhook_url[:50] + "..."

    payload = {
        "event_id":           alert.get("event_id", ""),
        "location":           alert.get("location", ""),
        "risk_level":         alert.get("risk_level", ""),
        "risk_score":         alert.get("risk_score", 0),
        "expected_window":    alert.get("expected_window", ""),
        "confidence":         alert.get("confidence", 0),
        "evidence":           alert.get("evidence", []),
        "recommended_action": alert.get("recommended_action", ""),
        "timestamp":          alert.get("timestamp", datetime.now(timezone.utc).isoformat()),
        "is_test":            is_test,
    }
    if is_test:
        payload["test_label"] = "TEST ALERT — NOT A REAL EMERGENCY"

    body = json.dumps(payload)
    headers = {
        "Content-Type": "application/json",
        "X-FloodGuard-Source": "FloodGuard-AI",
    }

    if webhook_secret:
        sig = hmac.new(
            webhook_secret.encode(),
            body.encode(),
            hashlib.sha256,
        ).hexdigest()
        headers["X-FloodGuard-Signature"] = f"sha256={sig}"

    try:
        import httpx
        resp = httpx.post(webhook_url, content=body, headers=headers, timeout=10)
        if 200 <= resp.status_code < 300:
            rec.mark_sent()
        else:
            rec.mark_failed(f"Webhook HTTP {resp.status_code}: {resp.text[:200]}")
    except Exception as exc:
        rec.mark_failed(f"Webhook error: {type(exc).__name__}: {exc}")

    return [rec]


# ─────────────────────────────────────────────────────────────────────────────
# Notification Manager
# ─────────────────────────────────────────────────────────────────────────────

class NotificationManager:
    """
    Coordinates all notification channels.
    Call dispatch() to send an alert via all configured channels.
    """

    def dispatch(
        self,
        alert: dict,
        channels: list[str] | None = None,
        is_test: bool = False,
    ) -> dict[str, Any]:
        """
        Send alert across all configured channels.

        Parameters
        ----------
        alert    : structured alert dict from flood_alert_engine
        channels : subset of ['email','sms','webhook'] or None for all
        is_test  : if True, adds TEST ALERT label and only sends if
                   TEST_NOTIFICATION_MODE=true

        Returns
        -------
        Delivery summary dict
        """
        # Safety gate: refuse real notifications from simulation mode
        if not is_test and alert.get("is_simulation", False):
            return {
                "status":  "BLOCKED",
                "reason":  "Simulation alerts do not trigger real notifications",
                "records": [],
            }

        # Safety gate: test sends require explicit env opt-in
        if is_test and not _bool_env("TEST_NOTIFICATION_MODE"):
            return {
                "status":  "BLOCKED",
                "reason":  "TEST_NOTIFICATION_MODE is not enabled. Set TEST_NOTIFICATION_MODE=true to allow test sends.",
                "records": [],
            }

        all_channels = channels or ["email", "sms", "webhook"]
        all_records: list[dict] = []

        if "email" in all_channels:
            for r in _send_email(alert, is_test=is_test):
                all_records.append(r.to_dict())

        if "sms" in all_channels:
            for r in _send_sms(alert, is_test=is_test):
                all_records.append(r.to_dict())

        if "webhook" in all_channels:
            for r in _send_webhook(alert, is_test=is_test):
                all_records.append(r.to_dict())

        sent    = sum(1 for r in all_records if r["status"] == "SENT")
        failed  = sum(1 for r in all_records if r["status"] == "FAILED")
        skipped = sum(1 for r in all_records if r["status"] == "SKIPPED")

        return {
            "status":        "SENT" if sent > 0 else "SKIPPED" if skipped > 0 else "FAILED",
            "sent_count":    sent,
            "failed_count":  failed,
            "skipped_count": skipped,
            "records":       all_records,
            "dispatched_at": datetime.now(timezone.utc).isoformat(),
        }

    def get_channel_status(self) -> dict[str, Any]:
        """
        Return current configuration status for each channel.
        Used in the observability panel.
        """
        email_ok   = _bool_env("EMAIL_ENABLED") and bool(_env("SMTP_HOST")) and bool(_env("ALERT_RECIPIENTS"))
        sms_ok     = _bool_env("SMS_ENABLED") and bool(_env("SMS_API_KEY")) and bool(_env("SMS_RECIPIENTS"))
        webhook_ok = _bool_env("WEBHOOK_ENABLED") and bool(_env("WEBHOOK_URL"))
        test_mode  = _bool_env("TEST_NOTIFICATION_MODE")

        return {
            "email": {
                "enabled":    _bool_env("EMAIL_ENABLED"),
                "configured": email_ok,
                "status":     "🟢 CONFIGURED" if email_ok else "🔴 NOT CONFIGURED",
                "note":       "Set EMAIL_ENABLED + SMTP_HOST + SMTP_USERNAME + SMTP_PASSWORD + ALERT_RECIPIENTS",
            },
            "sms": {
                "enabled":    _bool_env("SMS_ENABLED"),
                "configured": sms_ok,
                "status":     "🟢 CONFIGURED" if sms_ok else "🔴 NOT CONFIGURED",
                "note":       "Set SMS_ENABLED + SMS_PROVIDER + SMS_API_KEY + SMS_API_SECRET + SMS_SENDER + SMS_RECIPIENTS",
            },
            "webhook": {
                "enabled":    _bool_env("WEBHOOK_ENABLED"),
                "configured": webhook_ok,
                "status":     "🟢 CONFIGURED" if webhook_ok else "🔴 NOT CONFIGURED",
                "note":       "Set WEBHOOK_ENABLED + WEBHOOK_URL",
            },
            "test_mode": test_mode,
        }


# Module-level singleton
_notification_manager: NotificationManager | None = None


def get_notification_manager() -> NotificationManager:
    global _notification_manager
    if _notification_manager is None:
        _notification_manager = NotificationManager()
    return _notification_manager
