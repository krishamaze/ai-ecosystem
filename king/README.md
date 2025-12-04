# KING — Kingdom Intelligence Nexus Gateway

**Status:** Production (Phase 1 Complete)
**Last Updated:** 2025-12-04

---

## ⚠️ CRITICAL: Cloud Run Deployment Rules

> **DO NOT** run `gcloud run deploy --source .` from repository root (`ai-ecosystem/`).
> This causes Cloud Buildpacks to misdetect the project type and fail.

### Why This Fails

The repository root contains `package.json` (for supabase CLI). When you deploy from root:
1. Cloud Run finds no Dockerfile → uses Buildpacks auto-detection
2. Buildpacks sees `package.json` → assumes Node.js project
3. Expects `index.js` entry point → **container crashes immediately**
4. Error: `Cannot find module '/workspace/index.js'`

### Correct Deployment

**Always specify the service directory containing the Dockerfile:**

```bash
# From repo root - CORRECT
gcloud run deploy king-gateway --source ./king/gateway --region us-central1

# From king/ directory - CORRECT
cd king
gcloud run deploy king-gateway --source ./gateway --region us-central1

# From repo root - WRONG ❌
gcloud run deploy king-gateway --source . --region us-central1
```

---

## Documentation

| Document | Purpose |
|----------|---------|
| [docs/INDEX.md](../docs/INDEX.md) | Master documentation index |
| [docs/CONSTITUTION.md](../docs/CONSTITUTION.md) | Supreme law of the Kingdom |
| [docs/CURRENT_STATE.md](../docs/CURRENT_STATE.md) | Live deployment status |
| [docs/TODO.md](../docs/TODO.md) | Active task list |
| [docs/ARCHITECTURE.md](../docs/ARCHITECTURE.md) | System diagrams |

---

## Quick Reference

### Live Services

| Service | Endpoint |
|---------|----------|
| Gateway | https://king-gateway-250524159533.us-central1.run.app |
| Orchestrator | https://king-orchestrator-d3zysgasgq-uc.a.run.app |

### Deploy a Service

```bash
# MUST run from king/ directory
cd king
gcloud run deploy king-{service} --source ./{service} --region us-central1 --allow-unauthenticated --set-secrets "..."

# OR specify full path from repo root
gcloud run deploy king-gateway --source ./king/gateway --region us-central1 --allow-unauthenticated
```

### Test E2E Flow

```bash
curl -X POST "https://king-gateway-d3zysgasgq-uc.a.run.app/spawn" \
  -H "Content-Type: application/json" \
  -d '{"task_description": "hello", "input_data": {"user_id": "test"}}'
```

---

## Directory Structure

```
king/
├── gateway/           # Thin ingress layer
├── orchestrator/      # Strategic brain
├── services/          # Independent agent services
│   ├── code-writer/
│   ├── code-reviewer/
│   ├── video-planner/
│   ├── script-writer/
│   └── memory-selector/
└── telegram-bot/      # Telegram interface
```

---

## Local Development

```bash
# Start all services locally
docker-compose up --build

# Verify Gateway
curl http://localhost:8000/health
```

---

*See [docs/INDEX.md](../docs/INDEX.md) for complete documentation.*

