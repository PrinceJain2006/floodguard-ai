#!/bin/bash
# FloodGuard AI — Container Entrypoint
# IBM Cloud Code Engine reads PORT env variable and injects it.
# Streamlit must listen on 0.0.0.0:$PORT for the ingress to route traffic.

set -e

# Use PORT provided by IBM Cloud Code Engine (default 8080)
PORT="${PORT:-8080}"

echo "======================================"
echo " FloodGuard AI — Starting up"
echo " Port : $PORT"
echo " Mode : ${DEMO_MODE:-true}"
echo " Granite: ${WATSONX_API_KEY:+configured}"
echo "======================================"

# Ensure required directories exist (in case of read-only filesystem)
mkdir -p logs ml/models data

# Run Streamlit bound to 0.0.0.0 on the cloud port
exec streamlit run app.py \
  --server.port "$PORT" \
  --server.address "0.0.0.0" \
  --server.headless true \
  --server.enableCORS false \
  --server.enableXsrfProtection false \
  --browser.gatherUsageStats false
