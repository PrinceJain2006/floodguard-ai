# FloodGuard AI — Dockerfile
# IBM Cloud Code Engine compatible container build
# Python 3.11 slim base — optimised for fast startup

FROM python:3.11-slim

# ── Metadata ────────────────────────────────
LABEL maintainer="FloodGuard AI"
LABEL description="AI-Powered Urban Flood Emergency Command Center"
LABEL version="2.0.0"

# ── System deps ─────────────────────────────
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    g++ \
    && rm -rf /var/lib/apt/lists/*

# ── Working directory ───────────────────────
WORKDIR /app

# ── Install Python dependencies first (layer cache) ──
COPY requirements.txt .
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt

# ── Copy project files ───────────────────────
COPY . .

# ── Ensure required directories exist ────────
RUN mkdir -p logs ml/models data

# ── Ensure start script is executable ────────
RUN chmod +x start.sh

# ── IBM Code Engine: PORT is injected at runtime ──
# Default 8080; overridden by Code Engine automatically
EXPOSE 8080

# ── Health — Streamlit has no native /health; use / ──
HEALTHCHECK --interval=30s --timeout=10s --start-period=60s --retries=3 \
  CMD python -c "import httpx; httpx.get('http://localhost:${PORT:-8080}/', timeout=8)" || exit 1

# ── Entrypoint ───────────────────────────────
CMD ["./start.sh"]
