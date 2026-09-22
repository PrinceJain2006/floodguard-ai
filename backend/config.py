"""
FloodGuard AI — Configuration management.

Credential resolution order (highest priority first):
  1. Streamlit st.secrets  — used on Streamlit Cloud
  2. Environment variables — used locally with a .env file
  3. Hardcoded defaults    — safe no-op defaults only
"""
import os
from pathlib import Path
from dotenv import load_dotenv

# Load .env from project root when running locally.
# On Streamlit Cloud there is no .env; secrets come from st.secrets instead.
env_path = Path(__file__).parent.parent / ".env"
if env_path.exists():
    load_dotenv(env_path)
else:
    load_dotenv()


def _secret(key: str, default: str = "") -> str:
    """
    Return the value for *key* from the first source that provides a
    non-empty string:
      1. st.secrets[key]       (Streamlit Cloud / local secrets.toml)
      2. os.environ[key]       (set by dotenv or host shell)
      3. *default*

    st.secrets is only consulted when Streamlit is already fully imported
    (present in sys.modules) AND its ScriptRunContext is active for the
    current thread.  We use only sys.modules lookups and getattr — no
    'import' or 'from ... import' statements — to avoid triggering
    Streamlit's heavy protobuf compilation in pytest / CLI contexts.
    """
    try:
        # Only proceed if streamlit was already imported by the caller's process
        _st = sys.modules.get("streamlit")
        if _st is None:
            raise LookupError("streamlit not in sys.modules")

        # Verify a ScriptRunContext exists for this thread (i.e. we are inside
        # a Streamlit worker).  Access via already-imported submodule only.
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
        # Not running inside Streamlit (pytest, CLI, background threads) — fall through
        pass

    # Fall back to environment variable (populated from .env by dotenv above)
    return os.getenv(key, default)


# ──────────────────────────────────────────────
# IBM WatsonX / Granite
# ──────────────────────────────────────────────
WATSONX_API_KEY: str    = _secret("WATSONX_API_KEY")
WATSONX_PROJECT_ID: str = _secret("WATSONX_PROJECT_ID")
WATSONX_URL: str        = _secret("WATSONX_URL", "https://us-south.ml.cloud.ibm.com")
# ibm/granite-4-h-small is the verified available model for this project/region.
# Override via GRANITE_MODEL_ID env var / secret to use a different model.
GRANITE_MODEL_ID: str   = _secret("GRANITE_MODEL_ID", "ibm/granite-4-h-small")

# ──────────────────────────────────────────────
# JWT / Auth
# ──────────────────────────────────────────────
JWT_SECRET_KEY: str = _secret("JWT_SECRET_KEY", "floodguard-dev-secret-change-in-prod")
JWT_ALGORITHM: str  = _secret("JWT_ALGORITHM", "HS256")
JWT_ACCESS_TOKEN_EXPIRE_MINUTES: int = int(_secret("JWT_ACCESS_TOKEN_EXPIRE_MINUTES", "480"))

# ──────────────────────────────────────────────
# Database
# ──────────────────────────────────────────────
DATABASE_URL: str = _secret("DATABASE_URL", "sqlite:///./floodguard.db")

# ──────────────────────────────────────────────
# API / App
# ──────────────────────────────────────────────
BACKEND_URL: str  = _secret("BACKEND_URL", "http://localhost:8000")
APP_NAME: str     = _secret("APP_NAME", "FloodGuard AI")
APP_VERSION: str  = _secret("APP_VERSION", "1.0.0")
DEBUG: bool       = _secret("DEBUG", "false").lower() == "true"

# ──────────────────────────────────────────────
# Demo / Simulation
# ──────────────────────────────────────────────
DEMO_MODE: bool = _secret("DEMO_MODE", "true").lower() == "true"

# ──────────────────────────────────────────────
# External APIs (optional)
# ──────────────────────────────────────────────
OPENWEATHER_API_KEY: str = _secret("OPENWEATHER_API_KEY")
OPENAI_API_KEY: str      = _secret("OPENAI_API_KEY")

# ──────────────────────────────────────────────
# Live Weather / Open-Meteo (no API key required)
# ──────────────────────────────────────────────
# Set to "false" to force DEMO mode even when internet is available.
LIVE_WEATHER_ENABLED: bool    = _secret("LIVE_WEATHER_ENABLED", "true").lower() == "true"
# How many seconds a live weather result is considered fresh before re-fetching.
LIVE_DATA_CACHE_TTL: int      = int(_secret("LIVE_DATA_CACHE_TTL", "600"))   # 10 minutes
# Hard timeout for outbound HTTP requests to weather APIs.
LIVE_DATA_REQUEST_TIMEOUT: int = int(_secret("LIVE_DATA_REQUEST_TIMEOUT", "8"))
# Maximum age (seconds) of a cached result before it is treated as stale.
LIVE_DATA_STALE_THRESHOLD: int = int(_secret("LIVE_DATA_STALE_THRESHOLD", "1800"))  # 30 min

# ──────────────────────────────────────────────
# Flood Alert Engine
# ──────────────────────────────────────────────
ALERT_THRESHOLD_GREEN:  float = float(_secret("ALERT_THRESHOLD_GREEN",  "25"))
ALERT_THRESHOLD_YELLOW: float = float(_secret("ALERT_THRESHOLD_YELLOW", "40"))
ALERT_THRESHOLD_ORANGE: float = float(_secret("ALERT_THRESHOLD_ORANGE", "60"))
ALERT_THRESHOLD_RED:    float = float(_secret("ALERT_THRESHOLD_RED",    "75"))
ALERT_COOLDOWN_SECONDS: int   = int(_secret("ALERT_COOLDOWN_SECONDS", "1800"))

# ──────────────────────────────────────────────
# Email notifications (optional)
# ──────────────────────────────────────────────
EMAIL_ENABLED:    bool = _secret("EMAIL_ENABLED",    "false").lower() == "true"
SMTP_HOST:        str  = _secret("SMTP_HOST")
SMTP_PORT:        int  = int(_secret("SMTP_PORT", "587"))
SMTP_USERNAME:    str  = _secret("SMTP_USERNAME")
# SMTP_PASSWORD: never read here — always fetched at call time via _secret()
# to avoid caching credentials in the module-level namespace.
SMTP_FROM:        str  = _secret("SMTP_FROM")
ALERT_RECIPIENTS: str  = _secret("ALERT_RECIPIENTS")

# ──────────────────────────────────────────────
# SMS notifications (optional — Twilio)
# ──────────────────────────────────────────────
SMS_ENABLED:    bool = _secret("SMS_ENABLED",    "false").lower() == "true"
SMS_PROVIDER:   str  = _secret("SMS_PROVIDER",   "twilio")
# SMS_API_KEY / SMS_API_SECRET: fetched at call time — not cached here.
SMS_SENDER:     str  = _secret("SMS_SENDER")
SMS_RECIPIENTS: str  = _secret("SMS_RECIPIENTS")

# ──────────────────────────────────────────────
# Webhook notifications (optional)
# ──────────────────────────────────────────────
WEBHOOK_ENABLED: bool = _secret("WEBHOOK_ENABLED", "false").lower() == "true"
WEBHOOK_URL:     str  = _secret("WEBHOOK_URL")
# WEBHOOK_SECRET: fetched at call time — not cached here.

# ──────────────────────────────────────────────
# Test mode
# ──────────────────────────────────────────────
TEST_NOTIFICATION_MODE: bool = _secret("TEST_NOTIFICATION_MODE", "false").lower() == "true"

# ──────────────────────────────────────────────
# Paths
# ──────────────────────────────────────────────
BASE_DIR: Path      = Path(__file__).parent.parent
DATA_DIR: Path      = BASE_DIR / "data"
ML_MODELS_DIR: Path = BASE_DIR / "ml" / "models"
LOGS_DIR: Path      = BASE_DIR / "logs"

# Ensure directories exist
for _dir in [DATA_DIR, ML_MODELS_DIR, LOGS_DIR]:
    _dir.mkdir(parents=True, exist_ok=True)
