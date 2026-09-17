"""
FloodGuard AI — Shared Persistent Report Store
File-based persistence for USER SUBMITTED citizen reports.

This module provides the single source of truth for user-submitted reports
that must survive Streamlit page navigation and reruns.  Demo/synthetic seed
data is kept separate and managed by data/seed_generator.py.

Storage: floodguard-ai/data/user_reports.json  (newline-delimited JSON records)

Thread/rerun safety:
  - Reads always load fresh from disk (no in-process cache).
  - Writes use an atomic rename pattern to avoid partial writes.
  - Duplicate detection is file-level (fingerprint) so clicking Submit
    twice quickly still only creates one record.
"""
import json
import hashlib
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

# Location of the persistence file — relative to this module's directory
_HERE = Path(__file__).parent
_STORE_PATH = _HERE.parent / "data" / "user_reports.json"


# ─────────────────────────────────────────────────────────────────────────────
# Internal helpers
# ─────────────────────────────────────────────────────────────────────────────

def _fingerprint(text: str, area: str, city: str) -> str:
    """
    Stable content fingerprint used for duplicate detection.
    Normalise whitespace + lowercase before hashing so minor edits
    or capitalisation differences are still caught.
    """
    norm = " ".join(text.lower().split())
    key = f"{norm}|{area.lower()}|{city.lower()}"
    return hashlib.sha256(key.encode()).hexdigest()[:16]


def _load_raw() -> list[dict]:
    """Load all records from disk.  Returns [] if file is absent or corrupt."""
    if not _STORE_PATH.exists():
        return []
    try:
        with _STORE_PATH.open("r", encoding="utf-8") as fh:
            data = json.load(fh)
            if isinstance(data, list):
                return data
    except (json.JSONDecodeError, OSError):
        pass
    return []


def _save_raw(records: list[dict]) -> None:
    """Atomically write records list to disk."""
    _STORE_PATH.parent.mkdir(parents=True, exist_ok=True)
    tmp = _STORE_PATH.with_suffix(".tmp")
    with tmp.open("w", encoding="utf-8") as fh:
        json.dump(records, fh, ensure_ascii=False, indent=2)
    # Atomic replace (works on both Windows and POSIX)
    try:
        tmp.replace(_STORE_PATH)
    except OSError:
        # Windows fallback: remove target first
        if _STORE_PATH.exists():
            os.remove(_STORE_PATH)
        tmp.rename(_STORE_PATH)


# ─────────────────────────────────────────────────────────────────────────────
# Public API
# ─────────────────────────────────────────────────────────────────────────────

def get_user_reports() -> list[dict]:
    """
    Return all persisted USER SUBMITTED reports, newest first.
    Each call reads fresh from disk — safe to call on every Streamlit rerun.
    """
    records = _load_raw()
    # Sort newest-first for display
    records.sort(key=lambda r: r.get("submitted_at", ""), reverse=True)
    return records


def add_report(report: dict) -> tuple[bool, str]:
    """
    Persist a new user-submitted report.

    Deduplication: if a report with the same content fingerprint already
    exists in the store, the call is a no-op and returns (False, existing_id).

    Returns:
        (True, report_id)   — report was saved
        (False, existing_id) — duplicate, not saved
    """
    text  = report.get("original_text", "")
    area  = report.get("area", "")
    city  = report.get("city", "")
    fp    = _fingerprint(text, area, city)

    records = _load_raw()

    # Check for existing fingerprint
    for existing in records:
        if existing.get("_fingerprint") == fp:
            return False, existing["report_id"]

    # Enrich the record
    enriched = {
        **report,
        "source":       "USER SUBMITTED",
        "submitted_at": report.get("submitted_at", datetime.now(timezone.utc).isoformat()),
        "created_at":   report.get("created_at",   datetime.now(timezone.utc).isoformat()),
        "_fingerprint": fp,
    }
    # Ensure required map fields exist with correct Ahmedabad/Surat area coords
    if enriched.get("latitude") is None or enriched.get("longitude") is None:
        coords = _lookup_area_coords(area, city)
        enriched["latitude"]  = coords[0]
        enriched["longitude"] = coords[1]

    records.append(enriched)
    _save_raw(records)
    return True, enriched["report_id"]


def clear_all() -> None:
    """Remove all user-submitted reports (used in tests only)."""
    _save_raw([])


def count_open() -> int:
    """Return count of open (non-resolved) user-submitted reports."""
    return sum(1 for r in _load_raw() if r.get("status", "OPEN") == "OPEN")


# ─────────────────────────────────────────────────────────────────────────────
# Area coordinate lookup
# ─────────────────────────────────────────────────────────────────────────────

# Embedded copy of area coordinates so this module has zero dependencies
# on seed_generator.  Kept in sync with data/areas.json.
_AREA_COORDS: dict[str, tuple[float, float]] = {
    # Ahmedabad
    "Maninagar":   (22.9908, 72.6084),
    "Navrangpura": (23.0395, 72.5616),
    "Naroda":      (23.0892, 72.6571),
    "Vatva":       (22.9518, 72.6401),
    "Gota":        (23.1187, 72.5574),
    "Chandkheda":  (23.1169, 72.5877),
    "Bopal":       (23.0239, 72.4705),
    "Satellite":   (23.0218, 72.5260),
    "Vejalpur":    (22.9995, 72.5191),
    "Isanpur":     (22.9726, 72.6226),
    "Nikol":       (23.0457, 72.6481),
    "Odhav":       (23.0057, 72.6601),
    "Piplaj":      (22.9478, 72.5641),
    "Ranip":       (23.0751, 72.5627),
    "Ambawadi":    (23.0278, 72.5521),
    # Surat
    "Adajan":      (21.2063, 72.8060),
    "Katargam":    (21.2253, 72.8317),
    "Rander":      (21.2371, 72.7734),
    "Udhna":       (21.1680, 72.8501),
    "Limbayat":    (21.1817, 72.8611),
    "Vesu":        (21.1553, 72.7888),
    "Pal":         (21.1820, 72.7791),
    "Varachha":    (21.2100, 72.8606),
    "Bhatar":      (21.2326, 72.8591),
    "Piplod":      (21.1618, 72.8050),
    "Althan":      (21.1446, 72.7952),
    "Sarthana":    (21.2302, 72.8813),
    "Dindoli":     (21.1451, 72.8388),
    "Kamrej":      (21.2638, 72.9278),
    "Sachin":      (21.0916, 72.8773),
}

# Default city centres as fallback
_CITY_CENTRES: dict[str, tuple[float, float]] = {
    "Ahmedabad": (23.0225, 72.5714),
    "Surat":     (21.1702, 72.8311),
}


def _lookup_area_coords(area: str, city: str) -> tuple[float, float]:
    """Return (lat, lon) for a known area, or city centre as fallback."""
    if area in _AREA_COORDS:
        return _AREA_COORDS[area]
    return _CITY_CENTRES.get(city, (23.0225, 72.5714))
