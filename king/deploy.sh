#!/bin/bash

# Configuration
PROJECT_ID="gen-lang-client-0695295266"
REGION="us-central1"

echo "👑 Deploying KING Stack to Google Cloud Run..."

# 1. Deploy Gateway
echo "Deploying Gateway..."
gcloud run deploy king-gateway \
  --source ./gateway \
  --region $REGION \
  --project $PROJECT_ID \
  --allow-unauthenticated \
  --set-env-vars "SUPABASE_URL=${SUPABASE_URL},SUPABASE_SERVICE_KEY=${SUPABASE_SERVICE_KEY},MEM0_API_KEY=${MEM0_API_KEY}"

GATEWAY_URL=$(gcloud run services describe king-gateway --region $REGION --format 'value(status.url)')
echo "✅ Gateway deployed at: $GATEWAY_URL"

# 2. Deploy Services
echo "Deploying Agent Services..."

# Code Writer
gcloud run deploy code-writer-service \
  --source ./services/code-writer \
  --region $REGION \
  --project $PROJECT_ID \
  --allow-unauthenticated \
  --set-env-vars "GEMINI_API_KEY=${GEMINI_API_KEY}"
CODE_WRITER_URL=$(gcloud run services describe code-writer-service --region $REGION --format 'value(status.url)')

# Code Reviewer
gcloud run deploy code-reviewer-service \
  --source ./services/code-reviewer \
  --region $REGION \
  --project $PROJECT_ID \
  --allow-unauthenticated \
  --set-env-vars "GEMINI_API_KEY=${GEMINI_API_KEY}"
CODE_REVIEWER_URL=$(gcloud run services describe code-reviewer-service --region $REGION --format 'value(status.url)')

# Video Planner
gcloud run deploy video-planner-service \
  --source ./services/video-planner \
  --region $REGION \
  --project $PROJECT_ID \
  --allow-unauthenticated \
  --set-env-vars "GEMINI_API_KEY=${GEMINI_API_KEY}"
VIDEO_PLANNER_URL=$(gcloud run services describe video-planner-service --region $REGION --format 'value(status.url)')

# Script Writer
gcloud run deploy script-writer-service \
  --source ./services/script-writer \
  --region $REGION \
  --project $PROJECT_ID \
  --allow-unauthenticated \
  --set-env-vars "GEMINI_API_KEY=${GEMINI_API_KEY}"
SCRIPT_WRITER_URL=$(gcloud run services describe script-writer-service --region $REGION --format 'value(status.url)')

# Memory Selector
gcloud run deploy memory-selector-service \
    --source ./services/memory-selector \
    --region $REGION \
    --project $PROJECT_ID \
    --allow-unauthenticated \
    --set-env-vars "GEMINI_API_KEY=${GEMINI_API_KEY}"
MEMORY_SELECTOR_URL=$(gcloud run services describe memory-selector-service --region $REGION --format 'value(status.url)')

echo "✅ Services deployed."

# 3. Output SQL for Registry Update
echo ""
echo "---------------------------------------------------------"
echo "⚠️  ACTION REQUIRED: Run this SQL in Supabase to update registry:"
echo "---------------------------------------------------------"
echo "INSERT INTO agent_registry (agent_name, service_url) VALUES"
echo "  ('code_writer', '$CODE_WRITER_URL'),"
echo "  ('code_reviewer', '$CODE_REVIEWER_URL'),"
echo "  ('video_planner', '$VIDEO_PLANNER_URL'),"
echo "  ('script_writer', '$SCRIPT_WRITER_URL'),"
echo "  ('memory_selector', '$MEMORY_SELECTOR_URL')"
echo "ON CONFLICT (agent_name) DO UPDATE SET service_url = EXCLUDED.service_url;"
echo "---------------------------------------------------------"
echo "KING Stack Deployment Complete!"

