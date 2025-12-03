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
  --set-secrets "SUPABASE_URL=SUPABASE_URL:latest,SUPABASE_SERVICE_KEY=SUPABASE_SERVICE_KEY:latest,MEM0_API_KEY=MEM0_API_KEY:latest,GEMINI_API_KEY=GEMINI_API_KEY:latest"

GATEWAY_URL=$(gcloud run services describe king-gateway --region $REGION --format 'value(status.url)')
echo "✅ Gateway deployed at: $GATEWAY_URL"

# 2. Deploy Services
echo "Deploying Agent Services..."

# Code Writer
gcloud run deploy king-code-writer \
  --source ./services/code-writer \
  --region $REGION \
  --project $PROJECT_ID \
  --allow-unauthenticated \
  --set-secrets "GEMINI_API_KEY=GEMINI_API_KEY:latest"
CODE_WRITER_URL=$(gcloud run services describe king-code-writer --region $REGION --format 'value(status.url)')

# Code Reviewer
gcloud run deploy king-code-reviewer \
  --source ./services/code-reviewer \
  --region $REGION \
  --project $PROJECT_ID \
  --allow-unauthenticated \
  --set-secrets "GEMINI_API_KEY=GEMINI_API_KEY:latest"
CODE_REVIEWER_URL=$(gcloud run services describe king-code-reviewer --region $REGION --format 'value(status.url)')

# Video Planner
gcloud run deploy king-video-planner \
  --source ./services/video-planner \
  --region $REGION \
  --project $PROJECT_ID \
  --allow-unauthenticated \
  --set-secrets "GEMINI_API_KEY=GEMINI_API_KEY:latest"
VIDEO_PLANNER_URL=$(gcloud run services describe king-video-planner --region $REGION --format 'value(status.url)')

# Script Writer
gcloud run deploy king-script-writer \
  --source ./services/script-writer \
  --region $REGION \
  --project $PROJECT_ID \
  --allow-unauthenticated \
  --set-secrets "GEMINI_API_KEY=GEMINI_API_KEY:latest"
SCRIPT_WRITER_URL=$(gcloud run services describe king-script-writer --region $REGION --format 'value(status.url)')

# Memory Selector
gcloud run deploy king-memory-selector \
  --source ./services/memory-selector \
  --region $REGION \
  --project $PROJECT_ID \
  --allow-unauthenticated \
  --set-secrets "GEMINI_API_KEY=GEMINI_API_KEY:latest"
MEMORY_SELECTOR_URL=$(gcloud run services describe king-memory-selector --region $REGION --format 'value(status.url)')

# Ambedkar (Constitutional Architect)
gcloud run deploy king-ambedkar \
  --source ./services/ambedkar \
  --region $REGION \
  --project $PROJECT_ID \
  --allow-unauthenticated \
  --set-secrets "GEMINI_API_KEY=GEMINI_API_KEY:latest"
AMBEDKAR_URL=$(gcloud run services describe king-ambedkar --region $REGION --format 'value(status.url)')

# Telegram Bot
gcloud run deploy king-telegram-bot \
  --source ./telegram-bot \
  --region $REGION \
  --project $PROJECT_ID \
  --allow-unauthenticated \
  --set-secrets "TELEGRAM_BOT_TOKEN=TELEGRAM_BOT_TOKEN:latest" \
  --set-env-vars "KING_GATEWAY_URL=$GATEWAY_URL"
TELEGRAM_BOT_URL=$(gcloud run services describe king-telegram-bot --region $REGION --format 'value(status.url)')

echo "✅ Services deployed."

# 3. Output SQL for Registry Update
echo ""
echo "---------------------------------------------------------"
echo "⚠️  ACTION REQUIRED: Run this SQL in Supabase to update registry:"
echo "---------------------------------------------------------"
echo "INSERT INTO agent_registry (agent_name, service_url, status) VALUES"
echo "  ('code_writer', '$CODE_WRITER_URL', 'active'),"
echo "  ('code_reviewer', '$CODE_REVIEWER_URL', 'active'),"
echo "  ('video_planner', '$VIDEO_PLANNER_URL', 'active'),"
echo "  ('script_writer', '$SCRIPT_WRITER_URL', 'active'),"
echo "  ('memory_selector', '$MEMORY_SELECTOR_URL', 'active'),"
echo "  ('ambedkar', '$AMBEDKAR_URL', 'active')"
echo "ON CONFLICT (agent_name) DO UPDATE SET service_url = EXCLUDED.service_url, status = EXCLUDED.status, updated_at = NOW();"
echo "---------------------------------------------------------"
echo ""
echo "Telegram Bot Webhook (run manually):"
echo "curl -X POST 'https://api.telegram.org/bot\${TELEGRAM_BOT_TOKEN}/setWebhook?url=$TELEGRAM_BOT_URL/webhook'"
echo "---------------------------------------------------------"
echo "👑 KING Stack Deployment Complete!"

