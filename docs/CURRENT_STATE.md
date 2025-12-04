# KINGDOM CURRENT STATE

**Last Updated:** 2025-12-04
**Status:** Phase 1 Complete, Phase 2 Pending

---

## ⚠️ DEPLOYMENT TROUBLESHOOTING

### Container Failed to Start on PORT 8080

**Symptom:**
```
ERROR: The user-provided container failed to start and listen on the port
defined provided by the PORT=8080 environment variable
```

**Root Cause:** Deployed from wrong directory.

| If you ran from... | What happens |
|--------------------|--------------|
| `ai-ecosystem/` (root) | Buildpacks finds `package.json` → assumes Node.js → expects `index.js` → **FAILS** |
| `ai-ecosystem/king/gateway/` | Finds `Dockerfile` → builds Python container → **WORKS** |

**Solution:**
```bash
# CORRECT - specify service directory
gcloud run deploy king-gateway --source ./king/gateway --region us-central1

# OR run deploy.sh from king/
cd king && ./deploy.sh
```

**Diagnostic command:**
```bash
gcloud logging read "resource.type=cloud_run_revision AND resource.labels.service_name=king-gateway" --limit=20
```

---

## DEPLOYED SERVICES

| Service | Revision | Status | Endpoint |
|---------|----------|--------|----------|
| king-orchestrator | 00008+ | ✅ LIVE | `/king/decide`, `/health` |
| king-gateway | 00050+ | ✅ LIVE | `/spawn`, `/chat`, `/health` |

### Service URLs

| Service | URL |
|---------|-----|
| Gateway | https://king-gateway-250524159533.us-central1.run.app |
| Orchestrator | https://king-orchestrator-d3zysgasgq-uc.a.run.app |
| king-telegram | Active | ✅ LIVE | Webhook-based |
| king-code-writer | Active | ✅ LIVE | `/run` |
| king-code-reviewer | Active | ✅ LIVE | `/run` |
| king-memory-selector | Active | ✅ LIVE | `/run` |
| king-script-writer | Active | ✅ LIVE | `/run` |
| king-video-planner | Active | ✅ LIVE | `/run` |

---

## ARCHITECTURE LAYERS

### 1. Gateway Layer (Thin Ingress)
**Location:** `king/gateway/`

| File | Purpose |
|------|---------|
| `main.py` | FastAPI app, `/spawn`, `/chat` endpoints |
| `state_manager.py` | Supabase client for state |
| `agent_factory.py` | Agent creation utilities |
| `memory/` | Memory subsystem (not fully wired) |

**Key Behavior:**
- Receives user requests
- Calls `ORCHESTRATOR_URL/king/decide`
- Returns orchestrator response

### 2. Orchestrator Layer (Strategic Brain)
**Location:** `king/orchestrator/`

| Directory | Contents |
|-----------|----------|
| `api/` | `decide.py`, `meta.py`, `tasks.py` |
| `agents/` | Ministers, spec_designer, video_planner |
| `services/` | Core business logic (16 services) |
| `scripts/` | Utilities like `sync_specs.py` |

**Key Endpoint:** `POST /king/decide`
```json
{
  "task_description": "string",
  "input_data": {},
  "user_id": "optional",
  "trace_id": "optional"
}
```

**Response:**
```json
{
  "decision": "registered|ephemeral|rejected",
  "agent_id": "if registered",
  "reasoning": "why this decision",
  "output": { "result": "...", "confidence": 0.0-1.0 },
  "trace_id": "uuid",
  "duration_ms": 1234
}
```

### 3. Agent Services Layer
**Location:** `king/services/`

Each service follows identical structure:
```
king/services/{agent-name}/
├── main.py          # FastAPI app with /run endpoint
├── requirements.txt # Dependencies
└── Dockerfile       # Cloud Run container
```

### 4. Memory Layer
**Location:** `king/gateway/memory/`

| File | Purpose | Status |
|------|---------|--------|
| `curator.py` | AI-powered memory selection | ✅ Implemented |
| `reflection.py` | Pattern extraction | ⚠️ Not wired |
| `entity_resolver.py` | Canonical entity tracking | ⚠️ Not wired |
| `decay.py` | Time-based relevance | ✅ Implemented |
| `promotion.py` | Working → Long-term transfer | ✅ Implemented |
| `schema.py` | Memory type definitions | ✅ Implemented |
| `seeding.py` | Initial memory population | ✅ Implemented |

---

## DATABASE SCHEMA

### Core Tables

| Table | Purpose | Migration |
|-------|---------|-----------|
| `agent_registry` | Deployed agents + URLs | 20251127055045 |
| `agent_specs` | Agent DNA (prompts, tools) | 20251203120000 |
| `agent_runs` | Execution telemetry | 20251127055045 |
| `tasks` | Work items | 20251127055045 |
| `dna_proposals` | Mutation proposals | 20251127073300 |
| `dna_versions` | Versioned DNA | 20251127073300 |
| `deployed_artifacts` | Deployment records | 20251127120000 |
| `user_preferences` | Personalization | 20251127130000 |
| `entities` | Canonical entity registry | 20251203100000 |

### Total Migrations Applied: 13

---

## ENVIRONMENT VARIABLES

### Google Secret Manager (Canonical Source)

| Secret Name | Used By | Notes |
|-------------|---------|-------|
| `GEMINI_API_KEY` | All services | ⚠️ NOT `GOOGLE_API_KEY` |
| `SUPABASE_URL` | Gateway, Orchestrator | |
| `SUPABASE_SERVICE_KEY` | Gateway, Orchestrator | |
| `MEM0_API_KEY` | Gateway, Orchestrator | |
| `TELEGRAM_BOT_TOKEN` | Telegram Bot | |

> **IMPORTANT:** Code uses `GEMINI_API_KEY`. Do not create `GOOGLE_API_KEY` - it will be ignored.

### Gateway (.env.yaml)
```yaml
SUPABASE_URL: "https://xxx.supabase.co"
SUPABASE_SERVICE_KEY: "eyJ..."
MEM0_API_KEY: "m0-..."
GEMINI_API_KEY: "AIza..."
ORCHESTRATOR_URL: "https://king-orchestrator-xxx.run.app"
```

### Orchestrator (.env.yaml)
```yaml
SUPABASE_URL: "https://xxx.supabase.co"
SUPABASE_SERVICE_KEY: "eyJ..."
GEMINI_API_KEY: "AIza..."
MEM0_API_KEY: "m0-..."
```

---

## VERIFIED FLOWS

### E2E Flow (Tested 2025-12-03)
```
User → Gateway /spawn → Orchestrator /king/decide → Guardian → Agent Match → Execute → Response
```

**Test Result:**
```json
{
  "decision": "ephemeral",
  "reasoning": "No registered agent match",
  "output": { "result": "Hello there!" },
  "trace_id": "49457bed-...",
  "duration_ms": 14605
}
```

---

## KNOWN GAPS

### Critical (Wire Before Phase 2)
1. **sync_specs.py not run** — `agent_specs` table empty
2. **Entity resolution not wired** — Code exists, not called
3. **Reflection not wired** — Code exists, not called

### Phase 2 Blockers
1. **No tool execution** — Agents can only generate text
2. **No file ingestion** — No `/upload` endpoint
3. **No UI** — Telegram only

---

## NEXT ACTIONS

| Priority | Action | Owner |
|----------|--------|-------|
| P0 | Run `sync_specs.py` | Deploy team |
| P0 | Wire entity resolution into `/king/decide` | Dev |
| P1 | Create `tool-executor` service | Dev |
| P2 | Build `/upload` endpoint | Dev |
| P3 | Create web UI | Dev |

---

*Document auto-generated from codebase scan.*

