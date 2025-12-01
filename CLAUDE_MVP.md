# CLAUDE_MVP.md - Minimal Viable Product Guide

**Version:** MVP 1.0 (Deployment Ready)
**Last Updated:** 2025-12-01
**Deployment Target:** Cloud Run + Supabase Cloud

> **Stripped-down production deployment** focusing on core agent orchestration without Phase 1 ministers or advanced features. This is your deployable subset that works NOW.

---

## Quick Deploy Checklist

```bash
# 1. Environment (Cloud)
GEMINI_API_KEY=<required>
SUPABASE_URL=<cloud-instance>
SUPABASE_SERVICE_KEY=<cloud-key>
META_ADMIN_KEY=<generate-secure>

# 2. Deploy to Cloud Run
gcloud run deploy ai-orchestrator \
  --source ./mvp \
  --region us-central1 \
  --allow-unauthenticated \
  --set-env-vars GEMINI_API_KEY=$GEMINI_API_KEY

# 3. Verify
curl https://your-service-url.run.app/health
```

---

## What's INCLUDED in MVP

### ✅ Core Agent System (4 Agents)
| Agent | Purpose | Status |
|-------|---------|--------|
| **code_writer** | Generate production code | ✅ Working |
| **code_reviewer** | Review & gate deployment | ✅ Working |
| **video_planner** | Extract video context | ✅ Working |
| **script_writer** | Create timestamped scripts | ✅ Working |

### ✅ Essential Services
- **Agent Factory**: Hot-reload capability
- **Agent Runner**: LLM execution via Gemini
- **Pipeline Executor**: Basic code_generation pipeline
- **Conversation Service**: Simplified intent detection
- **Supabase Client**: Database connectivity

### ✅ Basic API (8 Endpoints)
```
GET  /health                      # Health check
POST /meta/converse               # Main conversation endpoint
GET  /meta/dependencies/health    # Dependency validation
POST /meta/pipeline/execute       # Run multi-agent pipeline
GET  /meta/pipeline/templates     # List pipelines
POST /tasks/create                # Create task
GET  /tasks/{id}                  # Get task
GET  /tasks/{id}/runs             # Get agent runs
```

### ✅ Database Schema (Minimal)
- `tasks` - Task records
- `agent_runs` - Execution traces
- `task_context` - Versioned context

---

## What's EXCLUDED from MVP

### ❌ Phase 1 Features (Move to `future/`)
- ❌ Guardian Minister (dangerous pattern detection)
- ❌ Validator Minister (spec validation)
- ❌ Audit Minister (telemetry analysis)
- ❌ Spec Designer (agent creation)
- ❌ Creation Pipeline (correction loops)

### ❌ Advanced Features (Move to `future/`)
- ❌ DNA Mutation System (8-step workflow)
- ❌ Memory System (Mem0 integration)
- ❌ RAG System (retrieval)
- ❌ User Preferences (personalization)
- ❌ Evaluation Framework (automated testing)
- ❌ Telegram Bot (multi-channel)
- ❌ Action Executor (deployment automation)

### ❌ Complex Tables (Move to `future/`)
- ❌ `dna_proposals`, `dna_versions`, `audit_reports`
- ❌ `deployed_artifacts`, `action_audit_log`
- ❌ `user_preferences`, `user_context`, `conversation_feedback`
- ❌ `memory_telemetry`, `rag_telemetry`

---

## MVP Architecture

```
mvp/
├── backend/
│   ├── main.py                    # Simplified FastAPI app
│   ├── agents/
│   │   ├── agent_factory.py       # Core factory (no changes)
│   │   ├── agent_runner.py        # LLM-only (remove minister dispatch)
│   │   ├── agent_specs_mvp.json   # 4 agents only
│   │   └── __init__.py
│   ├── api/
│   │   ├── meta.py                # 8 endpoints only
│   │   └── tasks.py               # Basic CRUD
│   ├── services/
│   │   ├── agent_dependencies.py  # 4 agents only
│   │   ├── pipeline_executor.py   # Basic pipelines only
│   │   ├── conversation_service.py # Simplified (no memory/RAG)
│   │   ├── gemini.py              # Core LLM wrapper
│   │   └── supabase_client.py     # DB client
│   ├── requirements_mvp.txt       # Minimal dependencies
│   └── Dockerfile                 # Cloud Run optimized
├── supabase/
│   └── migrations_mvp/
│       └── 001_core_tables.sql    # 3 tables only
├── .env.example
└── README_DEPLOY.md
```

---

## MVP Agent Specs

**File:** `mvp/backend/agents/agent_specs_mvp.json`

```json
{
  "code_writer": {
    "role": "code_writer",
    "purpose": "Generate production-ready code with tests",
    "dna_rules": [
      "output code ONLY in specified language",
      "every function must have docstring",
      "include basic error handling",
      "output must include at least one test case",
      "code must be complete and runnable",
      "output valid JSON only"
    ],
    "output_schema": {
      "language": "string",
      "code": "string",
      "tests": "array",
      "confidence": "float"
    }
  },
  "code_reviewer": {
    "role": "code_reviewer",
    "purpose": "Review code for correctness and security",
    "dna_rules": [
      "check for security vulnerabilities",
      "verify error handling exists",
      "verdict must be APPROVE or REJECT",
      "output valid JSON only"
    ],
    "output_schema": {
      "verdict": "string",
      "issues": "array",
      "security_score": "float",
      "confidence": "float"
    }
  },
  "video_planner": {
    "role": "video_planner",
    "purpose": "Extract structured context via questioning",
    "dna_rules": [
      "ask ONE question at a time",
      "when missing_fields is empty, set needs_clarification to false",
      "output valid JSON only"
    ],
    "output_schema": {
      "confidence": "float",
      "known_context": "object",
      "missing_fields": "array",
      "needs_clarification": "boolean"
    }
  },
  "script_writer": {
    "role": "script_writer",
    "purpose": "Create timestamped reel script",
    "dna_rules": [
      "follow context from planner",
      "no missing timestamps",
      "output valid JSON only"
    ],
    "output_schema": {
      "confidence": "float",
      "script_blocks": "array",
      "duration_seconds": "int"
    }
  }
}
```

---

## MVP Dependencies

**File:** `mvp/backend/services/agent_dependencies.py`

```python
AGENT_DEPENDENCIES: Dict[str, List[str]] = {
    # Content pipeline
    "video_planner": ["script_writer"],
    "script_writer": [],

    # Code pipeline
    "code_writer": ["code_reviewer"],
    "code_reviewer": [],
}
```

---

## MVP Database Migration

**File:** `mvp/supabase/migrations_mvp/001_core_tables.sql`

```sql
-- MVP: Core tables only (3 tables)

-- Tasks
CREATE TABLE tasks (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id TEXT NOT NULL,
    description TEXT NOT NULL,
    status TEXT DEFAULT 'pending',
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX idx_tasks_user_id ON tasks(user_id);
CREATE INDEX idx_tasks_status ON tasks(status);

-- Agent Runs (execution traces)
CREATE TABLE agent_runs (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    task_id UUID REFERENCES tasks(id) ON DELETE CASCADE,
    agent_role TEXT NOT NULL,
    input JSONB NOT NULL,
    output JSONB,
    confidence FLOAT,
    success BOOLEAN DEFAULT false,
    error TEXT,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX idx_agent_runs_task_id ON agent_runs(task_id);
CREATE INDEX idx_agent_runs_agent_role ON agent_runs(agent_role);

-- Task Context (versioned)
CREATE TABLE task_context (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    task_id UUID REFERENCES tasks(id) ON DELETE CASCADE,
    context_data JSONB NOT NULL,
    is_active BOOLEAN DEFAULT true,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX idx_task_context_task_id ON task_context(task_id);
CREATE INDEX idx_task_context_active ON task_context(is_active);
```

---

## MVP Requirements

**File:** `mvp/backend/requirements_mvp.txt`

```txt
# Core dependencies only
fastapi==0.104.1
uvicorn[standard]==0.24.0
pydantic==2.5.0
python-dotenv==1.0.0

# Database
supabase==2.0.3

# AI Services
google-generativeai==0.3.1

# Utilities
httpx==0.25.0
```

---

## MVP API Endpoints

### 1. Health Check
```bash
GET /health
Response: {"status": "ok"}
```

### 2. Main Conversation
```bash
POST /meta/converse
Body: {
  "message": "Create a Python function to validate emails",
  "user_id": "user-123"
}
Response: {
  "reply": "I'll create that function for you.",
  "intent": "generate_code",
  "trace_id": "uuid"
}
```

### 3. Dependency Health
```bash
GET /meta/dependencies/health
Response: {
  "is_healthy": true,
  "errors": [],
  "registered_agents": ["code_writer", "code_reviewer", "video_planner", "script_writer"]
}
```

### 4. Execute Pipeline
```bash
POST /meta/pipeline/execute
Body: {
  "steps": ["code_writer", "code_reviewer"],
  "initial_input": {"task": "Create fibonacci function"}
}
Response: {
  "results": [...],
  "success": true
}
```

### 5. Pipeline Templates
```bash
GET /meta/pipeline/templates
Response: {
  "templates": {
    "code_generation": ["code_writer", "code_reviewer"],
    "video_content": ["video_planner", "script_writer"]
  }
}
```

### 6. Create Task
```bash
POST /tasks/create
Body: {
  "description": "Generate authentication code",
  "user_id": "user-123"
}
Response: {
  "task_id": "uuid",
  "status": "pending"
}
```

### 7. Get Task
```bash
GET /tasks/{task_id}
Response: {
  "id": "uuid",
  "description": "...",
  "status": "completed"
}
```

### 8. Get Agent Runs
```bash
GET /tasks/{task_id}/runs
Response: {
  "runs": [
    {"agent_role": "code_writer", "success": true, ...},
    {"agent_role": "code_reviewer", "success": true, ...}
  ]
}
```

---

## Deployment Steps

### 1. Prepare Environment

```bash
# Clone MVP subset
cd ai-ecosystem
mkdir mvp
cp -r backend/orchestrator/agents/agent_factory.py mvp/backend/agents/
cp -r backend/orchestrator/agents/agent_runner.py mvp/backend/agents/
# ... copy only MVP files
```

### 2. Setup Supabase Cloud

```bash
# Create project at supabase.com
# Get SUPABASE_URL and SUPABASE_SERVICE_KEY
# Run migration
supabase db push --project-ref <project-id>
```

### 3. Deploy to Cloud Run

```bash
# Build and deploy
cd mvp
gcloud run deploy ai-orchestrator \
  --source . \
  --region us-central1 \
  --platform managed \
  --allow-unauthenticated \
  --set-env-vars GEMINI_API_KEY=$GEMINI_API_KEY,SUPABASE_URL=$SUPABASE_URL,SUPABASE_SERVICE_KEY=$SUPABASE_SERVICE_KEY,META_ADMIN_KEY=$META_ADMIN_KEY

# Get service URL
gcloud run services describe ai-orchestrator --region us-central1 --format 'value(status.url)'
```

### 4. Verify Deployment

```bash
export SERVICE_URL=<cloud-run-url>

# Health check
curl $SERVICE_URL/health

# Dependency check
curl $SERVICE_URL/meta/dependencies/health

# Test conversation
curl -X POST $SERVICE_URL/meta/converse \
  -H "Content-Type: application/json" \
  -d '{"message": "Create hello world function", "user_id": "test-user"}'
```

---

## MVP Dockerfile

**File:** `mvp/backend/Dockerfile`

```dockerfile
FROM python:3.11-slim

WORKDIR /app

# Install dependencies
COPY requirements_mvp.txt .
RUN pip install --no-cache-dir -r requirements_mvp.txt

# Copy MVP code only
COPY agents/ ./agents/
COPY api/ ./api/
COPY services/ ./services/
COPY main.py .

# Cloud Run expects PORT env var
ENV PORT=8080
EXPOSE 8080

CMD uvicorn main:app --host 0.0.0.0 --port $PORT
```

---

## Simplified Conversation Service

**Key Changes for MVP:**

```python
# Remove: Memory search, RAG decision, User preferences
# Keep: Basic intent detection, Agent dispatch, Simple response

class ConversationServiceMVP:
    def process(self, request: ConverseRequest) -> ConverseResponse:
        # 1. Detect intent (simplified patterns)
        intent = self._detect_intent(request.message)

        # 2. Route to agent based on intent
        if intent == Intent.GENERATE_CODE:
            result = run_pipeline("code_generation", {"task": request.message})
        elif intent == Intent.GENERATE_VIDEO:
            result = run_pipeline("video_content", {"task": request.message})
        else:
            result = {"reply": "I can help with code or video generation."}

        # 3. Format response
        return ConverseResponse(
            reply=result.get("reply", "Task completed"),
            intent=intent,
            trace_id=str(uuid.uuid4())
        )
```

---

## Simplified Pipeline Executor

**Key Changes for MVP:**

```python
# Remove: Telemetry recording, Handoff transforms, Halting conditions
# Keep: Sequential execution, Dependency validation

PREDEFINED_PIPELINES = {
    "code_generation": ["code_writer", "code_reviewer"],
    "video_content": ["video_planner", "script_writer"]
}

def execute_pipeline(steps: List[str], initial_input: dict) -> dict:
    # 1. Validate dependencies
    validate_pipeline(steps)

    # 2. Execute sequentially
    current_input = initial_input
    results = []

    for agent_role in steps:
        output = run_agent(agent_role, current_input)
        results.append(output)
        current_input = output  # Simple passthrough

    return {"results": results, "success": True}
```

---

## Critical MVP Conventions

### ✅ DO (MVP Safe)
- Use 4 core agents only
- Call `/meta/dependencies/health` before pipelines
- Record basic agent_runs in database
- Use Gemini API for LLM execution
- Deploy to Cloud Run with minimal config

### ❌ DON'T (Not in MVP)
- Don't use guardian/validator/audit ministers
- Don't attempt DNA mutations
- Don't integrate Mem0 or RAG
- Don't enable Telegram bot
- Don't use correction loops
- Don't deploy evaluation framework

---

## MVP Limitations

### Performance
- **No caching**: Every request hits Gemini API
- **No rate limiting**: Implement externally if needed
- **No retries**: Failed agent runs are final

### Features
- **No memory**: Agents don't remember past conversations
- **No personalization**: All users get same experience
- **No safety checks**: Guardian minister not included
- **No validation**: Validator minister not included

### Scalability
- **Single region**: Deploy to one Cloud Run region
- **No load balancing**: Cloud Run handles this automatically
- **No CDN**: Responses not cached globally

---

## Migration Path (MVP → Full)

### Phase 1: Deploy MVP (NOW)
```bash
# Get working deployment in production
mvp/ → Cloud Run + Supabase Cloud
```

### Phase 2: Add Ministers (LATER)
```bash
# Copy from future/ to mvp/
future/agents/guardian_minister.py → mvp/agents/
future/agents/validator_minister.py → mvp/agents/
# Redeploy with ministers enabled
```

### Phase 3: Enable Advanced Features (LATER)
```bash
# Add one feature at a time
future/services/mem0_tool.py → mvp/services/
future/services/retrieval_service.py → mvp/services/
# Test each addition independently
```

### Phase 4: Full Convergence (FUTURE)
```bash
# Eventually mvp/ contains all features from future/
# At that point, rename mvp/ → backend/
```

---

## Monitoring MVP

### Health Checks
```bash
# Cloud Run automatic health checks
GET /health every 30s

# Manual checks
curl $SERVICE_URL/health
curl $SERVICE_URL/meta/dependencies/health
```

### Logs
```bash
# View Cloud Run logs
gcloud run services logs read ai-orchestrator --region us-central1

# Filter by error
gcloud run services logs read ai-orchestrator --region us-central1 --filter "severity>=ERROR"
```

### Metrics
```bash
# Cloud Run console metrics
- Request count
- Request latency
- Error rate
- Container CPU usage
- Container memory usage
```

---

## Cost Estimation (MVP)

### Cloud Run
- **Free tier**: 2M requests/month, 360K GB-seconds
- **After free tier**: $0.00002400/request + $0.00001200/GB-second
- **Estimated**: <$10/month for low traffic

### Supabase
- **Free tier**: 500MB database, 2GB bandwidth
- **Pro tier**: $25/month (2 compute hours, 8GB database)
- **Estimated**: $0-25/month

### Gemini API
- **Free tier**: 60 requests/minute
- **After free tier**: $0.001/1K characters (prompt), $0.002/1K characters (response)
- **Estimated**: $5-20/month depending on usage

**Total MVP Cost: $5-55/month**

---

## Support & Troubleshooting

### Common Issues

**1. Dependency Health Check Fails**
```bash
# Check agent_specs_mvp.json has 4 agents
# Check AGENT_DEPENDENCIES has 4 entries
# Restart service
```

**2. Gemini API Errors**
```bash
# Check GEMINI_API_KEY is set
# Check API quota not exceeded
# Check network connectivity
```

**3. Database Connection Fails**
```bash
# Check SUPABASE_URL and SUPABASE_SERVICE_KEY
# Check Supabase project is active
# Check migrations ran successfully
```

---

## Next Steps After MVP Deployment

1. ✅ **Verify MVP works** - Run all 8 endpoints
2. ✅ **Monitor for 48 hours** - Check logs and metrics
3. ✅ **Add basic auth** - Implement API key if needed
4. ✅ **Setup CI/CD** - Automate deployments
5. ⏸️ **Pause ministers** - Keep in `future/` until MVP stable
6. ⏸️ **Pause DNA mutations** - Not needed for MVP
7. ⏸️ **Pause advanced features** - Add incrementally later

---

## Summary

**MVP = 4 Agents + 8 Endpoints + 3 Tables**

This is your deployable foundation that:
- ✅ Works NOW
- ✅ Costs <$55/month
- ✅ Deploys to Cloud Run in <10 minutes
- ✅ Preserves 100% of your Phase 1 work in `future/`
- ✅ Enables incremental feature additions

**Full platform stays in:** `d:\ai-ecosystem/future/`
**MVP deployment lives in:** `d:\ai-ecosystem/mvp/`

---

**Deploy MVP first. Prove it works. Add features later.**
