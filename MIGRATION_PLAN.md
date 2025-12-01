# Migration Plan: Full Platform → Deployable MVP

**Date:** 2025-12-01
**Goal:** Deploy working MVP to Cloud Run while preserving 100% of Phase 1 work
**Time:** ~2 hours total

---

## Quick Summary

```
Current: backend/orchestrator/ (13 agents, 16 services, 34 endpoints)

Target:
├── future/  ← ALL Phase 1 work (100% preserved)
├── mvp/     ← Deployable subset (4 agents, 5 services, 8 endpoints)
└── king/    ← Optional microservices experiment
```

---

## Step 1: Preserve Everything (5 min)

```bash
cd d:/ai-ecosystem

# Create future/ and move everything
mkdir future
mv backend future/
mv supabase future/
mv tests future/
mv scripts future/
mv docs future/

# Commit preservation
git add future/
git commit -m "Phase 1 complete: Preserve all work in future/"
```

**Result:** 100% of Phase 1 work safely stored.

---

## Step 2: Create MVP Structure (10 min)

```bash
# Create directories
mkdir -p mvp/backend/{agents,api,services}
mkdir -p mvp/supabase/migrations

# MVP will contain:
# - 4 agents (code_writer, code_reviewer, video_planner, script_writer)
# - 5 services (agent_factory, agent_runner, pipeline_executor, gemini, supabase)
# - 8 endpoints (health, converse, dependencies, pipeline, tasks)
# - 3 database tables (tasks, agent_runs, task_context)
```

---

## Step 3: Copy Core Files (15 min)

```bash
# Copy unchanged files
cp future/backend/orchestrator/agents/agent_factory.py mvp/backend/agents/
cp future/backend/orchestrator/services/gemini.py mvp/backend/services/
cp future/backend/orchestrator/services/supabase_client.py mvp/backend/services/

# Create __init__.py files
touch mvp/backend/__init__.py
touch mvp/backend/agents/__init__.py
touch mvp/backend/api/__init__.py
touch mvp/backend/services/__init__.py
```

---

## Step 4: Create MVP-Specific Files (60 min)

### Create agent_specs_mvp.json (4 agents only)
### Create simplified agent_runner.py (LLM-only, no ministers)
### Create simplified api/meta.py (8 endpoints)
### Create simplified api/tasks.py (3 endpoints)
### Create simplified services/agent_dependencies.py (4 agents)
### Create simplified services/pipeline_executor.py (basic)
### Create simplified services/conversation_service.py (no memory/RAG)
### Create main.py (simplified FastAPI app)

**(See CLAUDE_MVP.md for full code examples)**

---

## Step 5: Create Deployment Files (7 min)

### requirements_mvp.txt
```
fastapi==0.104.1
uvicorn[standard]==0.24.0
pydantic==2.5.0
python-dotenv==1.0.0
supabase==2.0.3
google-generativeai==0.3.1
httpx==0.25.0
```

### Dockerfile
```dockerfile
FROM python:3.11-slim
WORKDIR /app
COPY requirements_mvp.txt .
RUN pip install --no-cache-dir -r requirements_mvp.txt
COPY . .
ENV PORT=8080
EXPOSE 8080
CMD uvicorn main:app --host 0.0.0.0 --port $PORT
```

### .env.example
```bash
GEMINI_API_KEY=your-key-here
SUPABASE_URL=https://your-project.supabase.co
SUPABASE_SERVICE_KEY=your-service-key-here
META_ADMIN_KEY=generate-secure
```

---

## Step 6: Setup Supabase Cloud (10 min)

```bash
# 1. Go to supabase.com
# 2. Create new project
# 3. Copy URL and service key
# 4. Create migration file

cat > mvp/supabase/migrations/001_mvp_tables.sql << 'SQL'
CREATE TABLE tasks (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id TEXT NOT NULL,
    description TEXT NOT NULL,
    status TEXT DEFAULT 'pending',
    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE TABLE agent_runs (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    task_id UUID REFERENCES tasks(id) ON DELETE CASCADE,
    agent_role TEXT NOT NULL,
    input JSONB NOT NULL,
    output JSONB,
    success BOOLEAN DEFAULT false,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE TABLE task_context (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    task_id UUID REFERENCES tasks(id) ON DELETE CASCADE,
    context_data JSONB NOT NULL,
    is_active BOOLEAN DEFAULT true,
    created_at TIMESTAMPTZ DEFAULT NOW()
);
SQL

# 5. Run migration
supabase db push --project-ref <your-project-id>
```

---

## Step 7: Deploy to Cloud Run (15 min)

```bash
cd mvp

# Create .env
cat > .env << ENV
GEMINI_API_KEY=<your-gemini-key>
SUPABASE_URL=<your-supabase-url>
SUPABASE_SERVICE_KEY=<your-service-key>
META_ADMIN_KEY=<generate-secure-key>
ENV

# Deploy
gcloud run deploy ai-ecosystem-mvp \
  --source ./backend \
  --region us-central1 \
  --platform managed \
  --allow-unauthenticated \
  --set-env-vars GEMINI_API_KEY=$GEMINI_API_KEY,SUPABASE_URL=$SUPABASE_URL,SUPABASE_SERVICE_KEY=$SUPABASE_SERVICE_KEY

# Get URL
gcloud run services describe ai-ecosystem-mvp --region us-central1 --format 'value(status.url)'
```

---

## Step 8: Verify Deployment (10 min)

```bash
export SERVICE_URL=<your-cloud-run-url>

# Test 1: Health
curl $SERVICE_URL/health

# Test 2: Dependencies
curl $SERVICE_URL/meta/dependencies/health

# Test 3: Create task
curl -X POST $SERVICE_URL/tasks/create \
  -H "Content-Type: application/json" \
  -d '{"description": "Test", "user_id": "test-user"}'

# Test 4: Conversation
curl -X POST $SERVICE_URL/meta/converse \
  -H "Content-Type: application/json" \
  -d '{"message": "Create hello world", "user_id": "test-user"}'

# Test 5: Templates
curl $SERVICE_URL/meta/pipeline/templates
```

---

## Final Structure

```
d:\ai-ecosystem/
├── CLAUDE.md           # Full platform docs
├── CLAUDE_MVP.md       # MVP docs
├── KING_MVP.md         # Microservices docs
├── MIGRATION_PLAN.md   # This file
│
├── future/             # Phase 1 complete (PRESERVED)
│   ├── backend/
│   │   └── orchestrator/
│   ├── supabase/
│   ├── tests/
│   └── docs/
│
├── mvp/                # Deployable MVP (CLOUD RUN READY)
│   ├── backend/
│   │   ├── agents/     # 4 agents
│   │   ├── api/        # 8 endpoints
│   │   ├── services/   # 5 services
│   │   ├── main.py
│   │   ├── requirements_mvp.txt
│   │   └── Dockerfile
│   ├── supabase/
│   │   └── migrations/ # 1 migration
│   └── .env.example
│
└── king/               # Optional microservices
    ├── gateway/
    └── services/
```

---

## Checklist

### Pre-Migration
- [ ] Backup: `git commit -m "Pre-migration backup"`
- [ ] Review CLAUDE.md
- [ ] Verify Phase 1 work committed

### Migration Steps
- [ ] Step 1: Preserve (5 min) - Move to future/
- [ ] Step 2: Structure (10 min) - Create mvp/
- [ ] Step 3: Copy files (15 min)
- [ ] Step 4: Create MVP files (60 min)
- [ ] Step 5: Deployment files (7 min)
- [ ] Step 6: Supabase setup (10 min)
- [ ] Step 7: Deploy Cloud Run (15 min)
- [ ] Step 8: Verify (10 min)

### Post-Migration
- [ ] Monitor MVP for 48 hours
- [ ] Update README.md
- [ ] Document costs
- [ ] Plan feature additions

---

## Rollback Plan

If deployment fails:

```bash
# Nothing is lost - deploy from future/
cd future/backend
uvicorn orchestrator.main:app --reload
```

---

## Success Criteria

MVP deployed successfully when:
1. ✅ All 8 endpoints respond
2. ✅ Database connected
3. ✅ Agents execute correctly
4. ✅ Costs <$10/month
5. ✅ Deploys in <2 minutes

---

## Timeline

| Task | Time | Total |
|------|------|-------|
| Preserve Phase 1 | 5 min | 5 min |
| Create structure | 10 min | 15 min |
| Copy files | 15 min | 30 min |
| Create MVP files | 60 min | 90 min |
| Deployment files | 7 min | 97 min |
| Supabase setup | 10 min | 107 min |
| Cloud Run deploy | 15 min | 122 min |
| Verify | 10 min | 132 min |

**Total: ~2 hours**

---

## Next Steps

1. **Monitor** (48 hrs) - Watch logs, costs
2. **Decide on KING** (optional) - Build in parallel
3. **Add features** - Copy from future/ incrementally
4. **Update docs** - Keep separate docs per version

---

**Everything is preserved in future/. MVP is deployable. KING is optional.**
