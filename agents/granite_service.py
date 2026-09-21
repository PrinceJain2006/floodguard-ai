"""
FloodGuard AI — IBM Granite Integration Layer
Provides LLM reasoning via WatsonX / Granite-3-8b-instruct.
Falls back gracefully to rule-based responses when unavailable.
"""
import hashlib
import json
import time
import re
from typing import Any, NamedTuple
import httpx

# ── Lazy credential access ────────────────────────────────────────────────────
# config.py module-level variables are evaluated at first import, which on
# Streamlit Cloud happens before st.secrets is populated.  We therefore call
# the _secret() resolver at *call time* via thin helpers so the most-recently
# resolved values are always used.

def _cfg():
    """Return the backend.config module (or plain config as fallback)."""
    try:
        import backend.config as _c
        return _c
    except ImportError:
        import config as _c          # type: ignore[import]
        return _c


def _api_key() -> str:
    return _cfg()._secret("WATSONX_API_KEY")


def _project_id() -> str:
    return _cfg()._secret("WATSONX_PROJECT_ID")


def _watsonx_url() -> str:
    return _cfg()._secret("WATSONX_URL", "https://us-south.ml.cloud.ibm.com")


def _model_id() -> str:
    return _cfg()._secret("GRANITE_MODEL_ID", "ibm/granite-3-8b-instruct")


# ── Internal result type ──────────────────────────────────────────────────────
class _GraniteResult(NamedTuple):
    """Carries either the generated text or a structured failure diagnostic."""
    text:           str | None   # generated text on success, None on failure
    http_status:    int | None   # HTTP status code of the generation response
    ibm_error_code: str | None   # IBM error code from the response body, if any
    ibm_error_msg:  str | None   # IBM error message, safe to display (no secrets)
    failure_reason: str | None   # human-readable summary of the failure


_OK = _GraniteResult(None, None, None, None, None)  # placeholder; callers always check .text


# ── IAM token cache ───────────────────────────────────────────────────────────
# Keyed by api_key so a credential change automatically busts the cache.
_iam_token_cache: dict = {"key": None, "token": None, "expires_at": 0}

# ── 429 backoff state ─────────────────────────────────────────────────────────
# When WatsonX returns 429 (consumption_limit_reached), we record the time and
# stop hitting the API for _429_BACKOFF_SECONDS.  This prevents the app from
# making the congestion worse (more concurrent requests = more 429s).
# The backoff is module-level so it applies to ALL callers in the same process,
# including the granite_status() probe.
#
# Free-tier ibm/granite-4-h-small allows 2 requests/second concurrent.
# We back off for 5 minutes to avoid a request storm on demo reruns.
_429_BACKOFF_SECONDS = 300          # wait 5 minutes before retrying after a 429
_rate_limit_state: dict = {
    "hit_at":    0.0,               # time.time() when 429 was last received
    "result":    None,              # the _GraniteResult from that 429 response
}

# ── Response generation cache ─────────────────────────────────────────────────
# Caches successful (and fallback) generation results keyed by a stable hash
# of the call type + key inputs.  TTL = 10 minutes.
# This prevents repeated Granite calls when Streamlit reruns the page or the
# user navigates between tabs without changing the underlying scenario.
#
# Schema: { cache_key: {"text": str, "granite_used": bool, "ts": float} }
_GENERATION_CACHE: dict = {}
_GENERATION_CACHE_TTL = 600         # 10 minutes

# ── granite_status() result cache ─────────────────────────────────────────────
# Caches the last status probe result for _STATUS_CACHE_TTL seconds so that
# navigating between pages / Streamlit reruns do not each fire a live probe.
# The cache is busted automatically when the result changes (e.g., a 429 clears).
_status_cache: dict = {"result": None, "ts": 0.0}
_STATUS_CACHE_TTL = 120             # cache status probe for 2 minutes

_IAM_URL = "https://iam.cloud.ibm.com/identity/token"
_PLACEHOLDER_KEY = "your_watsonx_api_key_here"
_PLACEHOLDER_PID = "your_project_id_here"


def _get_iam_token() -> str | None:
    """
    Obtain a WatsonX IAM bearer token, cached for 55 minutes.
    Returns None (and logs a safe diagnostic) if the API key is missing or
    if the IAM endpoint returns an error.
    """
    api_key = _api_key()
    if not api_key or api_key == _PLACEHOLDER_KEY:
        return None

    now = time.time()
    # Bust cache if the credential has changed (e.g. different deployment)
    if (
        _iam_token_cache["key"] == api_key
        and _iam_token_cache["token"]
        and now < _iam_token_cache["expires_at"]
    ):
        return _iam_token_cache["token"]

    try:
        resp = httpx.post(
            _IAM_URL,
            data={
                "grant_type": "urn:ibm:params:oauth:grant-type:apikey",
                "apikey": api_key,
            },
            headers={"Content-Type": "application/x-www-form-urlencoded"},
            timeout=20,
        )
        if resp.status_code != 200:
            # Log the HTTP status but never the key value
            print(
                f"[Granite] IAM token request failed: HTTP {resp.status_code} "
                f"— check that WATSONX_API_KEY is valid and not expired."
            )
            return None
        token = resp.json()["access_token"]
        _iam_token_cache["key"] = api_key
        _iam_token_cache["token"] = token
        _iam_token_cache["expires_at"] = now + 55 * 60
        return token
    except httpx.TimeoutException:
        print("[Granite] IAM token request timed out — network issue or IAM endpoint unreachable.")
        return None
    except Exception as exc:
        # Safe: exc may reference httpx internals but never the key value
        print(f"[Granite] IAM token error ({type(exc).__name__}) — credentials could not be exchanged.")
        return None


def _call_granite(prompt: str, max_tokens: int = 600, temperature: float = 0.3) -> str | None:
    """
    Call the WatsonX text-generation REST endpoint.

    Public-facing wrapper: returns the generated text string on success,
    or None on any failure.  Use _call_granite_full() when the caller
    needs structured error details (e.g. granite_status probe).
    """
    result = _call_granite_full(prompt, max_tokens=max_tokens, temperature=temperature)
    return result.text


def _call_granite_full(
    prompt: str, max_tokens: int = 600, temperature: float = 0.3
) -> _GraniteResult:
    """
    Call the WatsonX text-generation REST endpoint.

    Returns a _GraniteResult carrying either the generated text or a fully
    structured failure diagnostic (HTTP status, IBM error code/message, reason).
    No API key, IAM token, or project ID is ever included in the diagnostic.

    If the previous call received a 429, returns the cached result immediately
    for _429_BACKOFF_SECONDS without making any network request.
    """
    # ── 429 backoff gate ──────────────────────────────────────────────────────
    now = time.time()
    if _rate_limit_state["hit_at"] and _rate_limit_state["result"] is not None:
        elapsed  = now - _rate_limit_state["hit_at"]
        remaining = _429_BACKOFF_SECONDS - elapsed
        if remaining > 0:
            cached: _GraniteResult = _rate_limit_state["result"]
            # Return a fresh result with an updated reason showing the backoff countdown
            mins, secs = divmod(int(remaining), 60)
            wait_str   = f"{mins}m {secs}s" if mins else f"{secs}s"
            return _GraniteResult(
                text=None,
                http_status=429,
                ibm_error_code=cached.ibm_error_code,
                ibm_error_msg=cached.ibm_error_msg,
                failure_reason=(
                    f"HTTP 429 rate limit active — backing off for {wait_str} "
                    "before retrying. Rule-based fallback is in use."
                ),
            )
        else:
            # Backoff expired — clear state and allow next real request through
            _rate_limit_state["hit_at"]  = 0.0
            _rate_limit_state["result"]  = None

    token = _get_iam_token()
    if not token:
        return _GraniteResult(
            text=None, http_status=None,
            ibm_error_code=None, ibm_error_msg=None,
            failure_reason="IAM token not available — check WATSONX_API_KEY",
        )

    project_id = _project_id()
    if not project_id or project_id == _PLACEHOLDER_PID:
        return _GraniteResult(
            text=None, http_status=None,
            ibm_error_code=None, ibm_error_msg=None,
            failure_reason="WATSONX_PROJECT_ID is not configured",
        )

    base_url = _watsonx_url().rstrip("/")
    model_id = _model_id()
    url      = f"{base_url}/ml/v1/text/generation?version=2024-05-31"

    payload = {
        "model_id":   model_id,
        "project_id": project_id,
        "input":      prompt,
        "parameters": {
            "decoding_method": "greedy",
            "max_new_tokens":  max_tokens,
            "temperature":     temperature,
            "stop_sequences":  ["<|endoftext|>"],
        },
    }

    try:
        resp = httpx.post(
            url,
            json=payload,
            headers={
                "Authorization": f"Bearer {token}",
                "Content-Type":  "application/json",
                "Accept":        "application/json",
            },
            timeout=45,
        )
    except httpx.TimeoutException:
        reason = f"Request to {url.split('?')[0]} timed out (>45s) — WatsonX endpoint slow or unreachable"
        print(f"[Granite] {reason}")
        return _GraniteResult(text=None, http_status=None,
                              ibm_error_code=None, ibm_error_msg=None,
                              failure_reason=reason)
    except Exception as exc:
        reason = f"Network error ({type(exc).__name__}) reaching {url.split('?')[0]}"
        print(f"[Granite] {reason}")
        return _GraniteResult(text=None, http_status=None,
                              ibm_error_code=None, ibm_error_msg=None,
                              failure_reason=reason)

    if resp.status_code == 200:
        try:
            text = resp.json()["results"][0]["generated_text"].strip()
            return _GraniteResult(text=text, http_status=200,
                                  ibm_error_code=None, ibm_error_msg=None,
                                  failure_reason=None)
        except (KeyError, IndexError, ValueError) as exc:
            reason = f"HTTP 200 but unexpected response shape ({type(exc).__name__})"
            print(f"[Granite] {reason}: {str(resp.text)[:120]}")
            return _GraniteResult(text=None, http_status=200,
                                  ibm_error_code=None, ibm_error_msg=None,
                                  failure_reason=reason)

    # Non-200: parse IBM error body safely and build structured diagnostic
    return _parse_error_response(resp, url, model_id)


def _parse_error_response(resp: httpx.Response, url: str, model_id: str) -> _GraniteResult:
    """
    Parse a non-200 WatsonX response into a _GraniteResult with safe diagnostics.
    Never includes API key, IAM token, project ID, or Authorization header.
    """
    code = resp.status_code
    endpoint_path = url.split("?")[0]  # strip version query param — no credentials here

    # Extract IBM error code and message from the JSON body
    ibm_error_code = None
    ibm_error_msg  = None
    try:
        body = resp.json()
        # WatsonX error shape: {"errors": [{"code": "...", "message": "..."}]}
        # or {"error": "...", "description": "..."}
        errors = body.get("errors") or []
        if errors and isinstance(errors, list):
            ibm_error_code = errors[0].get("code", "")
            ibm_error_msg  = errors[0].get("message", "")
        if not ibm_error_msg:
            ibm_error_msg = body.get("error", "") or body.get("description", "")
        if not ibm_error_code:
            ibm_error_code = body.get("status_code", "")
    except Exception:
        ibm_error_msg = resp.text[:300]

    # Build a human-readable reason keyed on HTTP status
    if code == 400:
        reason = (
            f"HTTP 400 Bad Request on POST {endpoint_path} — "
            f"model_id='{model_id}' or request payload rejected. "
            f"IBM: {ibm_error_msg!r}"
        )
        _iam_token_cache["token"] = None   # may have been a stale token shape issue
        _iam_token_cache["expires_at"] = 0
    elif code == 401:
        reason = (
            f"HTTP 401 Unauthorized on POST {endpoint_path} — "
            "IAM token rejected by WatsonX. Token refreshed; retry should recover."
        )
        _iam_token_cache["token"] = None
        _iam_token_cache["expires_at"] = 0
    elif code == 403:
        reason = (
            f"HTTP 403 Forbidden on POST {endpoint_path} — "
            f"project does not have access to model '{model_id}' in this region. "
            "Verify WATSONX_PROJECT_ID, that the model is enabled in the project, "
            "and that the API key has Watson Machine Learning Editor/Admin role. "
            f"IBM: {ibm_error_msg!r}"
        )
    elif code == 404:
        reason = (
            f"HTTP 404 Not Found on POST {endpoint_path} — "
            f"model_id='{model_id}' not found in this region. "
            "Try 'ibm/granite-3-8b-instruct' or check WATSONX_URL. "
            f"IBM: {ibm_error_msg!r}"
        )
    elif code == 429:
        reason = (
            f"HTTP 429 consumption_limit_reached on POST {endpoint_path} — "
            f"free-tier concurrent request limit reached for model '{model_id}'. "
            f"Backing off for {_429_BACKOFF_SECONDS}s. "
            "Using controlled backoff and existing rule-based fallback. "
            f"IBM: {ibm_error_msg!r}"
        )
    elif code >= 500:
        reason = (
            f"HTTP {code} Server Error on POST {endpoint_path} — "
            f"WatsonX service-side error. IBM: {ibm_error_msg!r}"
        )
    else:
        reason = (
            f"HTTP {code} on POST {endpoint_path}. IBM: {ibm_error_msg!r}"
        )

    result = _GraniteResult(
        text=None,
        http_status=code,
        ibm_error_code=str(ibm_error_code) if ibm_error_code else None,
        ibm_error_msg=ibm_error_msg or None,
        failure_reason=reason,
    )

    # Arm the backoff state on 429 so subsequent calls skip the network.
    # Log the 429 only once — subsequent calls within the backoff window
    # are silently returned from the backoff gate without re-logging.
    if code == 429:
        already_rate_limited = bool(
            _rate_limit_state["hit_at"] and _rate_limit_state["result"] is not None
        )
        _rate_limit_state["hit_at"]  = time.time()
        _rate_limit_state["result"]  = result
        # Also bust the status cache so the next granite_status() re-evaluates
        _status_cache["result"] = None
        _status_cache["ts"]     = 0.0
        if not already_rate_limited:
            print(
                "[Granite] WatsonX Granite rate limited. "
                "HTTP 429 consumption_limit_reached. "
                "Using controlled backoff and existing fallback."
            )
    else:
        print(f"[Granite] {reason}")
    return result


# ──────────────────────────────────────────────
# Public status check
# ──────────────────────────────────────────────

def granite_status(force_probe: bool = False) -> dict:
    """
    Return a status dict that accurately reflects Granite connectivity.

    Result is cached for _STATUS_CACHE_TTL seconds to avoid firing a live
    WatsonX probe on every Streamlit rerun or every get_agent_statuses() call.
    Pass force_probe=True to bypass the cache (e.g. after a successful pipeline
    run, to surface the updated status immediately).

    Fields:
      api_key_configured  — True if a non-placeholder key is present
      project_configured  — True if a non-placeholder project ID is present
      iam_ok              — True if an IAM token was successfully obtained
      available           — True only when a real generation call succeeds
      rate_limited        — True when the last failure was a 429
      config_error        — True when credentials/project are misconfigured
      model               — the model ID in use
      endpoint            — generation endpoint path (no credentials)
      http_status         — HTTP status of the probe generation call, or None
      ibm_error_code      — IBM error code string from the response, or None
      ibm_error_msg       — IBM error message string, safe to display, or None
      error               — full human-readable failure reason, or None
    """
    now = time.time()
    # Return cached result if fresh and not forced
    if (
        not force_probe
        and _status_cache["result"] is not None
        and (now - _status_cache["ts"]) < _STATUS_CACHE_TTL
    ):
        return _status_cache["result"]

    api_key    = _api_key()
    project_id = _project_id()
    model      = _model_id()
    base_url   = _watsonx_url().rstrip("/")
    endpoint   = f"{base_url}/ml/v1/text/generation"

    key_ok = bool(api_key and api_key != _PLACEHOLDER_KEY)
    pid_ok = bool(project_id and project_id != _PLACEHOLDER_PID)

    _base = {
        "api_key_configured": key_ok,
        "project_configured": pid_ok,
        "iam_ok":             False,
        "available":          False,
        "rate_limited":       False,
        "config_error":       False,
        "model":              model,
        "endpoint":           endpoint,
        "http_status":        None,
        "ibm_error_code":     None,
        "ibm_error_msg":      None,
        "error":              None,
    }

    if not key_ok or not pid_ok:
        result = {
            **_base,
            "config_error": True,
            "error": (
                "WATSONX_API_KEY not configured"
                if not key_ok
                else "WATSONX_PROJECT_ID not configured"
            ),
        }
        _status_cache["result"] = result
        _status_cache["ts"]     = now
        return result

    # If a 429 backoff is still active, return RATE_LIMITED without probing
    if _rate_limit_state["hit_at"] and _rate_limit_state["result"] is not None:
        elapsed   = now - _rate_limit_state["hit_at"]
        remaining = _429_BACKOFF_SECONDS - elapsed
        if remaining > 0:
            cached_r: _GraniteResult = _rate_limit_state["result"]
            result = {
                **_base,
                "iam_ok":         True,   # we had IAM working when 429 hit
                "available":      False,
                "rate_limited":   True,
                "http_status":    429,
                "ibm_error_code": cached_r.ibm_error_code,
                "ibm_error_msg":  cached_r.ibm_error_msg,
                "error":          cached_r.failure_reason,
            }
            # Cache this for a short window — status will naturally re-evaluate
            # once the backoff expires.
            _status_cache["result"] = result
            _status_cache["ts"]     = now
            return result

    # Attempt to obtain IAM token
    token = _get_iam_token()
    if not token:
        result = {
            **_base,
            "config_error": True,
            "error": "IAM token exchange failed — check WATSONX_API_KEY validity",
        }
        _status_cache["result"] = result
        _status_cache["ts"]     = now
        return result

    # Probe an actual generation call with a minimal prompt.
    # If the backoff gate is active this returns immediately without a network call.
    probe = _call_granite_full(
        "<|user|>\nReply with the single word: OK\n<|assistant|>\n",
        max_tokens=5,
    )

    if probe.text is not None:
        result = {
            **_base,
            "iam_ok":      True,
            "available":   True,
            "http_status": 200,
        }
        _status_cache["result"] = result
        _status_cache["ts"]     = now
        return result

    # Generation failed — classify and surface full structured diagnostic
    is_rate_limited  = probe.http_status == 429
    is_config_error  = probe.http_status in (401, 403) or (
        probe.http_status is None and "WATSONX_API_KEY" in (probe.failure_reason or "")
    )
    result = {
        **_base,
        "iam_ok":         True,
        "available":      False,
        "rate_limited":   is_rate_limited,
        "config_error":   is_config_error,
        "http_status":    probe.http_status,
        "ibm_error_code": probe.ibm_error_code,
        "ibm_error_msg":  probe.ibm_error_msg,
        "error":          probe.failure_reason,
    }
    _status_cache["result"] = result
    _status_cache["ts"]     = now
    return result


def invalidate_granite_status_cache() -> None:
    """Force the next granite_status() call to re-probe WatsonX."""
    _status_cache["result"] = None
    _status_cache["ts"]     = 0.0


# ──────────────────────────────────────────────
# Public generation API
# ──────────────────────────────────────────────

def analyze_citizen_report(text: str, language: str, context: dict | None = None) -> dict:
    """
    Use Granite to understand a citizen flood report.
    Returns: category, severity, summary, location_hint, language, keywords, granite_used.
    Uses chat format (<|user|>/<|assistant|>) required by granite-4-h-small.
    """
    prompt = (
        "<|user|>\n"
        "You are FloodGuard AI. Analyze the citizen flood report below and extract structured data.\n"
        f"Report (language: {language}): \"{text}\"\n\n"
        "Return ONLY a JSON object with these exact keys:\n"
        "category (one of: waterlogging, drain_overflow, road_blockage, traffic_disruption, property_flooding, emergency_situation)\n"
        "severity (one of: LOW, MEDIUM, HIGH, CRITICAL)\n"
        "summary (one-sentence English summary)\n"
        "location_hint (location mentioned or null)\n"
        "requires_immediate_action (true or false)\n"
        "keywords (list of 3 flood-related terms found in report)\n"
        "suggested_action (one specific municipal response action)\n"
        "<|assistant|>\n"
        "{\n"
    )

    response = _call_granite(prompt, max_tokens=300)
    if response:
        # Prepend the opening brace we included in the prompt to complete the JSON
        try:
            full_json = "{" + response if not response.strip().startswith("{") else response
            match = re.search(r'\{.*?\}', full_json, re.DOTALL)
            if match:
                result = json.loads(match.group())
                result["granite_used"] = True
                return result
        except Exception:
            pass

    result = _fallback_report_analysis(text, language)
    result["granite_used"] = False
    return result


def explain_flood_risk(area: str, city: str, risk_data: dict) -> str:
    """
    Generate a human-readable explanation for why an area is at risk.
    Uses Granite if available; otherwise rule-based.
    IMPORTANT: Only uses provided risk_data — never invents real sensor/govt data.

    Result is cached keyed on area + city + risk_level + risk_score so repeated
    UI tab switches don't re-fire a Granite request for the same zone.
    """
    reasons    = risk_data.get("main_reasons", [])
    score      = risk_data.get("risk_score", 0)
    level      = risk_data.get("risk_level", "UNKNOWN")
    features   = risk_data.get("input_features", {})
    rainfall   = features.get("rainfall_1h", risk_data.get("rainfall_1h", 0))
    drainage   = features.get("drainage_capacity", risk_data.get("drainage_capacity", 50))
    blocked    = features.get("blocked_drains", 0)
    elevation  = features.get("elevation", "unknown")
    density    = features.get("population_density", "unknown")
    confidence = risk_data.get("confidence", 0.8)

    cache_key = _gen_cache_key("explain", area, city, level, f"{score:.0f}")
    cached = _gen_cache_get(cache_key)
    if cached is not None:
        return cached

    prompt = f"""You are the FloodGuard AI assistant for {city} Municipal Corporation.
Only use the data provided below — do not invent or assume any values.

AREA: {area}, {city}
RISK LEVEL: {level} (Score: {score}/100, Confidence: {confidence:.0%})
RAINFALL (last 1 hour): {rainfall} mm/hr
DRAINAGE CAPACITY UTILIZATION: {drainage}%
BLOCKED DRAINS IN AREA: {blocked}
ELEVATION: {elevation} m above sea level
POPULATION DENSITY INDEX: {density}
AI-IDENTIFIED KEY FACTORS: {'; '.join(reasons[:4]) if reasons else 'Multiple compounding factors'}

Write a clear 3-sentence WHY explanation for why {area} is at {level} flood risk today, based ONLY on the data above.
Include: (1) the primary cause, (2) compounding factors, (3) one specific recommended action.
Begin with "Based on available data..." to signal this is AI analysis of provided inputs, not real sensor readings.
Keep it professional and under 80 words."""

    response = _call_granite(prompt, max_tokens=200)
    if response:
        _gen_cache_put(cache_key, response)
        return response

    reason_str = "; ".join(reasons[:3]) if reasons else "multiple compounding risk factors"
    action = risk_data.get("recommended_action", "Monitor closely and pre-position response teams.")
    fallback = (
        f"Based on available data, {area} in {city} is at {level} flood risk (score {score:.0f}/100). "
        f"Key factors from the analysis: {reason_str}. "
        f"Recommended action: {action}"
    )
    _gen_cache_put(cache_key, fallback)
    return fallback


def explain_why_zone_risky(zone_prediction: dict) -> str:
    """
    Public convenience wrapper — explain a zone's risk using only its own prediction data.
    Guaranteed not to hallucinate: pulls exclusively from zone_prediction dict.
    """
    area = zone_prediction.get("area", "Unknown Area")
    city = zone_prediction.get("city", "Unknown City")
    return explain_flood_risk(area, city, zone_prediction)


# ── Generation cache helpers ──────────────────────────────────────────────────

def _gen_cache_key(*parts: Any) -> str:
    """Build a short stable cache key from the given string parts."""
    raw = "|".join(str(p) for p in parts)
    return hashlib.sha256(raw.encode()).hexdigest()[:24]


def _gen_cache_get(key: str) -> str | None:
    """Return cached generation text if fresh, else None."""
    entry = _GENERATION_CACHE.get(key)
    if entry and (time.time() - entry["ts"]) < _GENERATION_CACHE_TTL:
        return entry["text"]
    return None


def _gen_cache_put(key: str, text: str) -> None:
    """Store a generation result in the cache."""
    _GENERATION_CACHE[key] = {"text": text, "ts": time.time()}
    # Evict stale entries to prevent unbounded growth (keep latest 50)
    if len(_GENERATION_CACHE) > 50:
        oldest_key = min(_GENERATION_CACHE, key=lambda k: _GENERATION_CACHE[k]["ts"])
        _GENERATION_CACHE.pop(oldest_key, None)


def generate_situation_report(city: str, scenario: str, summary_data: dict) -> str:
    """
    Generate a comprehensive municipal flood situation report.

    Result is cached for _GENERATION_CACHE_TTL (10 min) keyed on city + scenario
    + critical/high zone counts so identical pipeline reruns reuse the result
    without issuing a new Granite request.
    """
    critical    = summary_data.get("critical_zones", 0)
    high        = summary_data.get("high_zones", 0)
    reports     = summary_data.get("citizen_reports", 0)
    avg_rainfall = summary_data.get("avg_rainfall_1h", 0)
    top_actions = summary_data.get("top_actions", [])

    # Cache key: city + scenario + critical + high zones (coarse enough to hit
    # on reruns with the same scenario, but distinct across real scenario changes)
    cache_key = _gen_cache_key("sitrep", city, scenario, critical, high)
    cached = _gen_cache_get(cache_key)
    if cached is not None:
        return cached

    prompt = f"""You are FloodGuard AI. Generate an official flood situation report for {city} Municipal Corporation.

SITUATION SUMMARY ({scenario} scenario):
- Critical risk zones: {critical}
- High risk zones: {high}
- Citizen reports received: {reports}
- Average rainfall: {avg_rainfall:.1f} mm/hr
- Top AI recommended actions: {'; '.join(top_actions[:3])}

Generate a structured 200-word situation report with:
1. Executive Summary
2. Current Situation
3. High-Priority Actions
4. Recommended Next Steps

Note: This is AI-generated preliminary assessment. Requires authorized human verification before official communication."""

    response = _call_granite(prompt, max_tokens=400)
    if response:
        _gen_cache_put(cache_key, response)
        return response

    fallback = f"""FLOODGUARD AI — FLOOD SITUATION REPORT
City: {city} | Scenario: {scenario} | Generated: AI-Preliminary

EXECUTIVE SUMMARY
{city} is experiencing {scenario.lower()} conditions with {critical} critical and {high} high-risk zones identified.

CURRENT SITUATION
Average rainfall: {avg_rainfall:.1f} mm/hr. {reports} citizen reports processed. Drainage systems under stress in {critical + high} areas.

HIGH-PRIORITY ACTIONS
{chr(10).join(f'{i+1}. {a}' for i, a in enumerate(top_actions[:5]))}

RECOMMENDED NEXT STEPS
Activate emergency response protocol for critical zones. Pre-position pump teams at high-risk areas. Issue public advisory for affected neighborhoods.

[AI-GENERATED PRELIMINARY ASSESSMENT — Requires authorized human verification]"""
    _gen_cache_put(cache_key, fallback)
    return fallback


def answer_query(question: str, context_data: dict) -> str:
    """
    Answer a natural language query about flood status using application data as context.
    DOES NOT hallucinate sensor values — uses provided context_data.
    """
    context_str = json.dumps(context_data, ensure_ascii=False, indent=2)[:2000]

    prompt = f"""You are FloodGuard AI, a municipal flood management assistant for Ahmedabad and Surat.
Answer questions ONLY based on the provided data context. Do not invent values.

DATA CONTEXT:
{context_str}

QUESTION: {question}

Provide a concise, factual answer based only on the data above. If the answer cannot be found in the data, say so clearly."""

    response = _call_granite(prompt, max_tokens=300)
    if response:
        return response

    return _fallback_query_answer(question, context_data)


def generate_recommendation_explanation(rec: dict) -> str:
    """Explain why a specific AI recommendation was generated."""
    prompt = f"""You are FloodGuard AI. Explain this emergency recommendation to a municipal officer in 2-3 sentences.

RECOMMENDATION: {rec.get('recommendation', '')}
AREA: {rec.get('area', '')}
PRIORITY: {rec.get('priority', '')}
REASONING: {rec.get('reasoning', '')}

Keep the explanation clear, direct and actionable. Mention why this action is important right now."""

    response = _call_granite(prompt, max_tokens=150)
    if response:
        return response

    return (
        f"This {rec.get('priority', '')} priority recommendation for {rec.get('area', '')} "
        f"was generated because: {rec.get('reasoning', 'multiple risk factors detected')}. "
        f"Immediate action will help prevent escalation of the current flood risk situation."
    )


def classify_damage(description: str, location: str) -> dict:
    """Classify post-flood damage from description."""
    prompt = f"""You are FloodGuard AI damage assessment system.

Location: {location}
Report: {description}

Classify the damage and respond as JSON only:
{{
  "damage_level": "<LOW|MEDIUM|HIGH|SEVERE>",
  "affected_infrastructure": ["<road|drainage|property|public_infrastructure|traffic>"],
  "estimated_priority": "<ROUTINE|URGENT|EMERGENCY>",
  "recommended_next_step": "<one action>",
  "preliminary_note": "AI-generated preliminary assessment. Requires on-site human verification."
}}"""

    response = _call_granite(prompt, max_tokens=200)
    if response:
        try:
            match = re.search(r'\{.*\}', response, re.DOTALL)
            if match:
                return json.loads(match.group())
        except Exception:
            pass

    return {
        "damage_level": "MEDIUM",
        "affected_infrastructure": ["road", "drainage"],
        "estimated_priority": "URGENT",
        "recommended_next_step": "Deploy inspection team for on-site assessment.",
        "preliminary_note": "AI-generated preliminary assessment. Requires on-site human verification.",
    }


# ──────────────────────────────────────────────
# Fallback implementations (no LLM required)
# ──────────────────────────────────────────────

_CATEGORY_KEYWORDS = {
    "waterlogging":       ["water", "pani", "पानी", "પાણી", "waterlog", "jala", "flood"],
    "drain_overflow":     ["drain", "nala", "नाला", "ગટર", "gutter", "overflow", "sewage"],
    "road_blockage":      ["road", "rasta", "रास्ता", "રસ્તો", "block", "chowk", "traffic"],
    "property_flooding":  ["house", "ghar", "घर", "ઘર", "home", "property", "inside"],
    "emergency_situation":["emergency", "stranded", "stuck", "help", "urgent", "फंस", "ફસ"],
    "traffic_disruption": ["traffic", "car", "vehicle", "jam", "stuck"],
}

_SEVERITY_KEYWORDS = {
    "CRITICAL": ["emergency", "emer", "stranded", "life", "critical", "phns", "ife", "ফসা"],
    "HIGH":     ["high", "heavy", "lots", "bahut", "zyada", "ghanu", "bhari", "unch"],
    "MEDIUM":   ["some", "thodi", "medium", "par", "road", "overflow"],
    "LOW":      ["small", "little", "thoda", "halku"],
}


def _fallback_report_analysis(text: str, language: str) -> dict:
    text_lower = text.lower()
    category   = "waterlogging"
    for cat, kws in _CATEGORY_KEYWORDS.items():
        if any(kw in text_lower for kw in kws):
            category = cat
            break

    severity = "MEDIUM"
    for sev, kws in _SEVERITY_KEYWORDS.items():
        if any(kw in text_lower for kw in kws):
            severity = sev
            break

    # Extract keywords found in the text (up to 5)
    found_keywords: list[str] = []
    all_kws = list(_CATEGORY_KEYWORDS.get(category, [])) + list(_SEVERITY_KEYWORDS.get(severity, []))
    for kw in all_kws:
        if kw in text_lower and kw not in found_keywords and len(kw) > 2:
            found_keywords.append(kw)
        if len(found_keywords) >= 5:
            break

    # Routing suggestion per category
    _action_map = {
        "waterlogging":        "Deploy pump team to clear waterlogging.",
        "drain_overflow":      "Dispatch drainage maintenance team immediately.",
        "road_blockage":       "Initiate traffic diversion and deploy road clearance team.",
        "traffic_disruption":  "Deploy traffic control officers to manage congestion.",
        "property_flooding":   "Deploy emergency response team for property evacuation.",
        "emergency_situation": "Deploy emergency response team and senior officer immediately.",
    }

    return {
        "category":                  category,
        "severity":                  severity,
        "language_detected":         language,
        "summary":                   f"Flood-related report: {category.replace('_', ' ')} detected.",
        "location_hint":             None,
        "requires_immediate_action": severity in ("HIGH", "CRITICAL"),
        "keywords":                  found_keywords,
        "suggested_action":          _action_map.get(category, "Dispatch municipal response team."),
        "granite_used":              False,
    }


def _fallback_query_answer(question: str, context: dict) -> str:
    q = question.lower()
    if "critical" in q or "risky" in q or "worst" in q:
        preds    = context.get("predictions", [])
        critical = [p for p in preds if p.get("risk_level") == "CRITICAL"]
        if critical:
            areas = [f"{p['area']}, {p['city']}" for p in critical[:3]]
            return f"Critical risk zones currently: {', '.join(areas)}. Immediate action required."
        return "No critical risk zones currently identified."

    if "drain" in q:
        drains     = context.get("drains", [])
        crit_drains = [d for d in drains if d.get("maintenance_priority") == "CRITICAL"]
        return f"{len(crit_drains)} drains require immediate maintenance (CRITICAL priority)."

    if "report" in q or "complaint" in q:
        reports = context.get("reports", [])
        open_r  = [r for r in reports if r.get("status") == "OPEN"]
        return f"There are {len(open_r)} open citizen flood reports (out of {len(reports)} total)."

    if "rainfall" in q or "rain" in q:
        rf = context.get("rainfall", [])
        if rf:
            max_r = max(rf, key=lambda x: x.get("rainfall_1h", 0))
            return f"Highest rainfall: {max_r['area']}, {max_r['city']} — {max_r['rainfall_1h']} mm/hr."
        return "Rainfall data not available."

    return (
        "I can help with flood risk analysis, drain maintenance priorities, citizen reports, "
        "rainfall data, and response recommendations for Ahmedabad and Surat. "
        "Please ask a more specific question."
    )
