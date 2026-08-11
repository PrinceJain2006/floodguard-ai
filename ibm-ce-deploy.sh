#!/bin/bash
# ============================================================
# FloodGuard AI — IBM Cloud Code Engine Deployment Script
# Run this script once from your terminal after IBM CLI login.
# GitHub Repo: https://github.com/PrinceJain2006/floodguard-ai
# ============================================================
# 
# PRE-REQUISITES (one-time setup):
#   1. Install IBM Cloud CLI: https://cloud.ibm.com/docs/cli
#   2. Install Code Engine plugin: ibmcloud plugin install code-engine
#   3. Login: ibmcloud login --sso
#   4. Set your WATSONX_API_KEY and WATSONX_PROJECT_ID below
#
# USAGE:
#   bash ibm-ce-deploy.sh
# ============================================================

set -e

# ── EDIT THESE VALUES ────────────────────────────────────────
IBM_REGION="us-south"
RESOURCE_GROUP="Default"
CE_PROJECT_NAME="floodguard-ai"
APP_NAME="floodguard-ai"
GITHUB_REPO="https://github.com/PrinceJain2006/floodguard-ai"
GITHUB_BRANCH="main"
WATSONX_API_KEY="YOUR_WATSONX_API_KEY_HERE"
WATSONX_PROJECT_ID="YOUR_WATSONX_PROJECT_ID_HERE"
WATSONX_URL="https://us-south.ml.cloud.ibm.com"
# ─────────────────────────────────────────────────────────────

echo "======================================"
echo " FloodGuard AI — IBM Code Engine Deploy"
echo "======================================"

# Step 1 — Login & target region
echo "[1/8] Targeting IBM Cloud region: $IBM_REGION"
ibmcloud target -r "$IBM_REGION" -g "$RESOURCE_GROUP"

# Step 2 — Select / create Code Engine project
echo "[2/8] Selecting Code Engine project: $CE_PROJECT_NAME"
if ibmcloud ce project get --name "$CE_PROJECT_NAME" > /dev/null 2>&1; then
  ibmcloud ce project select --name "$CE_PROJECT_NAME"
else
  echo "  Project not found — creating..."
  ibmcloud ce project create --name "$CE_PROJECT_NAME"
  ibmcloud ce project select --name "$CE_PROJECT_NAME"
fi

# Step 3 — Create secrets for IBM Granite credentials
echo "[3/8] Creating secrets..."
ibmcloud ce secret create \
  --name floodguard-secrets \
  --from-literal WATSONX_API_KEY="$WATSONX_API_KEY" \
  --from-literal WATSONX_PROJECT_ID="$WATSONX_PROJECT_ID" \
  --from-literal WATSONX_URL="$WATSONX_URL" \
  --from-literal DEMO_MODE="true" \
  --from-literal APP_NAME="FloodGuard AI" \
  --from-literal APP_VERSION="2.0.0" \
  --from-literal JWT_SECRET_KEY="$(openssl rand -hex 32 2>/dev/null || echo 'floodguard-cloud-secret-change-me')" \
  2>/dev/null || \
ibmcloud ce secret update \
  --name floodguard-secrets \
  --from-literal WATSONX_API_KEY="$WATSONX_API_KEY" \
  --from-literal WATSONX_PROJECT_ID="$WATSONX_PROJECT_ID" \
  --from-literal WATSONX_URL="$WATSONX_URL"
echo "  Secrets created/updated."

# Step 4 — Deploy application from GitHub source
echo "[4/8] Deploying from GitHub source..."
if ibmcloud ce app get --name "$APP_NAME" > /dev/null 2>&1; then
  echo "  App exists — updating..."
  ibmcloud ce app update \
    --name "$APP_NAME" \
    --build-source "$GITHUB_REPO" \
    --build-git-branch "$GITHUB_BRANCH" \
    --env-from-secret floodguard-secrets \
    --port 8080 \
    --min-scale 0 \
    --max-scale 3 \
    --cpu 1 \
    --memory 4G \
    --wait
else
  echo "  Creating new app..."
  ibmcloud ce app create \
    --name "$APP_NAME" \
    --build-source "$GITHUB_REPO" \
    --build-git-branch "$GITHUB_BRANCH" \
    --dockerfile Dockerfile \
    --env-from-secret floodguard-secrets \
    --port 8080 \
    --min-scale 0 \
    --max-scale 3 \
    --cpu 1 \
    --memory 4G \
    --wait
fi

# Step 5 — Get public URL
echo ""
echo "[5/8] Getting public URL..."
APP_URL=$(ibmcloud ce app get --name "$APP_NAME" --output json | python3 -c "import sys,json; d=json.load(sys.stdin); print(d.get('status',{}).get('url','Not available yet'))" 2>/dev/null || echo "Run: ibmcloud ce app get --name $APP_NAME")

echo ""
echo "============================================"
echo " DEPLOYMENT COMPLETE!"
echo "============================================"
echo " App Name   : $APP_NAME"
echo " Public URL : $APP_URL"
echo " Region     : $IBM_REGION"
echo " Project    : $CE_PROJECT_NAME"
echo "============================================"
echo ""
echo " To check logs:"
echo "   ibmcloud ce app logs --name $APP_NAME --follow"
echo ""
echo " To check status:"
echo "   ibmcloud ce app get --name $APP_NAME"
echo "============================================"
