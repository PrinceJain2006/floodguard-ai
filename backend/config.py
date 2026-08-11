"""
FloodGuard AI — Configuration management.
Loads settings from environment variables / .env file.
"""
import os
from pathlib import Path
from dotenv import load_dotenv

# Load .env from project root
env_path = Path(__file__).parent.parent / ".env"
if env_path.exists():
    load_dotenv(env_path)
else:
    load_dotenv()

# ──────────────────────────────────────────────
# IBM WatsonX / Granite
# ──────────────────────────────────────────────
WATSONX_API_KEY: str = os.getenv("WATSONX_API_KEY", "")
WATSONX_PROJECT_ID: str = os.getenv("WATSONX_PROJECT_ID", "")
WATSONX_URL: str = os.getenv("WATSONX_URL", "https://us-south.ml.cloud.ibm.com")
GRANITE_MODEL_ID: str = "ibm/granite-3-8b-instruct"

# ──────────────────────────────────────────────
# JWT / Auth
# ──────────────────────────────────────────────
JWT_SECRET_KEY: str = os.getenv("JWT_SECRET_KEY", "floodguard-dev-secret-change-in-prod")
JWT_ALGORITHM: str = os.getenv("JWT_ALGORITHM", "HS256")
JWT_ACCESS_TOKEN_EXPIRE_MINUTES: int = int(os.getenv("JWT_ACCESS_TOKEN_EXPIRE_MINUTES", "480"))

# ──────────────────────────────────────────────
# Database
# ──────────────────────────────────────────────
DATABASE_URL: str = os.getenv("DATABASE_URL", "sqlite:///./floodguard.db")

# ──────────────────────────────────────────────
# API / App
# ──────────────────────────────────────────────
BACKEND_URL: str = os.getenv("BACKEND_URL", "http://localhost:8000")
APP_NAME: str = os.getenv("APP_NAME", "FloodGuard AI")
APP_VERSION: str = os.getenv("APP_VERSION", "1.0.0")
DEBUG: bool = os.getenv("DEBUG", "false").lower() == "true"

# ──────────────────────────────────────────────
# Demo / Simulation
# ──────────────────────────────────────────────
DEMO_MODE: bool = os.getenv("DEMO_MODE", "true").lower() == "true"

# ──────────────────────────────────────────────
# External APIs (optional)
# ──────────────────────────────────────────────
OPENWEATHER_API_KEY: str = os.getenv("OPENWEATHER_API_KEY", "")
OPENAI_API_KEY: str = os.getenv("OPENAI_API_KEY", "")

# ──────────────────────────────────────────────
# Paths
# ──────────────────────────────────────────────
BASE_DIR: Path = Path(__file__).parent.parent
DATA_DIR: Path = BASE_DIR / "data"
ML_MODELS_DIR: Path = BASE_DIR / "ml" / "models"
LOGS_DIR: Path = BASE_DIR / "logs"

# Ensure directories exist
for _dir in [DATA_DIR, ML_MODELS_DIR, LOGS_DIR]:
    _dir.mkdir(parents=True, exist_ok=True)
