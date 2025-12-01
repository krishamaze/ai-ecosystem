# KING_MVP.md - Thin Orchestrator Architecture

**Version:** KING (Kingdom Intelligence Nexus Gateway) MVP 1.0
**Last Updated:** 2025-12-01
**Philosophy:** Ultra-thin orchestrator, agents as microservices

> **Radical simplification:** Orchestrator is ONLY routing + state. Agents are independent deployments. Phase 1 ministers become optional sidecar services.

---

## KING vs CLAUDE Architecture

### CLAUDE (Current - Monolithic)
```
┌─────────────────────────────────────┐
│   Backend Orchestrator (Monolith)  │
│  ┌──────────────────────────────┐  │
│  │ Agent Factory                │  │
│  │ Agent Runner                 │  │
│  │ 13 Agent Specs (in memory)   │  │
│  │ Pipeline Executor            │  │
│  │ Conversation Service         │  │
│  │ Memory, RAG, Telemetry       │  │
│  └──────────────────────────────┘  │
│          ↓ Gemini API               │
└─────────────────────────────────────┘
```

### KING (Proposed - Microservices)
```
┌───────────────┐
│  KING Gateway │  ← Thin orchestrator (FastAPI)
│  (Routing)    │
└───┬───────┬───┘
    │       │
    ↓       ↓
┌────────┐ ┌────────┐ ┌────────┐ ┌────────┐
│ Agent  │ │ Agent  │ │ Agent  │ │ Agent  │
│ Writer │ │ Review │ │ Planner│ │ Script │
│ Service│ │ Service│ │ Service│ │ Service│
└────────┘ └────────┘ └────────┘ └────────┘
    ↓          ↓          ↓          ↓
   Gemini    Gemini    Gemini    Gemini
```

---

## KING Core Principles

### 1. Routing Only
**Orchestrator does NOT:**
- ❌ Execute agents directly
- ❌ Call Gemini API
- ❌ Cache agent specs
- ❌ Transform handoffs

**Orchestrator ONLY:**
- ✅ Route requests to agent URLs
- ✅ Track execution state
- ✅ Validate dependencies
- ✅ Return responses

### 2. Agents as Services
Each agent is a standalone FastAPI service:
```
code-writer-service:8001
code-reviewer-service:8002
video-planner-service:8003
script-writer-service:8004
```

### 3. State in Database
- Agent specs → Supabase table `agent_specs`
- Agent URLs → Supabase table `agent_registry`
- Execution state → Supabase table `agent_runs`

### 4. No Business Logic
Orchestrator is pure infrastructure:
- HTTP routing
- Request validation
- Response aggregation
- State persistence

---

## KING MVP Architecture

```
┌─────────────────────────────────────────────────────┐
│                  KING Gateway                       │
│  ┌────────────────────────────────────────────┐    │
│  │ Router (FastAPI)                           │    │
│  │  - POST /execute/{agent_name}              │    │
│  │  - POST /pipeline/run                      │    │
│  │  - GET  /agents/list                       │    │
│  │  - GET  /health                            │    │
│  └────────────────────────────────────────────┘    │
│  ┌────────────────────────────────────────────┐    │
│  │ State Manager (Supabase Client)            │    │
│  │  - Query agent_registry for URLs           │    │
│  │  - Record agent_runs                       │    │
│  │  - Validate dependencies                   │    │
│  └────────────────────────────────────────────┘    │
└─────────────────────────────────────────────────────┘
                     ↓ HTTP requests
┌──────────────┐ ┌──────────────┐ ┌──────────────┐
│ code-writer  │ │code-reviewer │ │ video-planner│
│   Service    │ │   Service    │ │   Service    │
│  (Port 8001) │ │  (Port 8002) │ │  (Port 8003) │
└──────────────┘ └──────────────┘ └──────────────┘
       ↓                ↓                ↓
    Gemini API      Gemini API      Gemini API
```

---

## KING Database Schema

### Table: agent_registry
```sql
CREATE TABLE agent_registry (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    agent_name TEXT UNIQUE NOT NULL,
    service_url TEXT NOT NULL,
    status TEXT DEFAULT 'active',  -- active | disabled | maintenance
    version TEXT DEFAULT '1.0.0',
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- Seed data
INSERT INTO agent_registry (agent_name, service_url) VALUES
    ('code_writer', 'http://code-writer-service:8001'),
    ('code_reviewer', 'http://code-reviewer-service:8002'),
    ('video_planner', 'http://video-planner-service:8003'),
    ('script_writer', 'http://script-writer-service:8004');
```

### Table: agent_specs (DNA moved to DB)
```sql
CREATE TABLE agent_specs (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    agent_name TEXT UNIQUE NOT NULL,
    purpose TEXT NOT NULL,
    dna_rules JSONB NOT NULL,  -- Array of rules
    output_schema JSONB NOT NULL,  -- Expected output structure
    dependencies JSONB NOT NULL,  -- Array of agent names
    version TEXT DEFAULT '1.0.0',
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- Example
INSERT INTO agent_specs (agent_name, purpose, dna_rules, output_schema, dependencies) VALUES
    ('code_writer', 'Generate production code',
     '["output code ONLY in specified language", "include basic error handling"]'::jsonb,
     '{"language": "string", "code": "string", "confidence": "float"}'::jsonb,
     '["code_reviewer"]'::jsonb);
```

### Table: agent_runs (unchanged)
```sql
CREATE TABLE agent_runs (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    agent_name TEXT NOT NULL,
    input JSONB NOT NULL,
    output JSONB,
    success BOOLEAN DEFAULT false,
    error TEXT,
    duration_ms INT,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX idx_agent_runs_agent_name ON agent_runs(agent_name);
```

---

## KING Gateway Implementation

**File:** `king/gateway/main.py`

```python
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
import httpx
from supabase import create_client
import os

app = FastAPI(title="KING Gateway")

# Supabase client
supabase = create_client(
    os.getenv("SUPABASE_URL"),
    os.getenv("SUPABASE_SERVICE_KEY")
)

class ExecuteRequest(BaseModel):
    agent_name: str
    input_data: dict

class PipelineRequest(BaseModel):
    steps: list[str]
    initial_input: dict

@app.get("/health")
def health_check():
    return {"status": "ok", "service": "KING Gateway"}

@app.get("/agents/list")
def list_agents():
    """List all registered agents."""
    result = supabase.table("agent_registry") \
        .select("agent_name, service_url, status") \
        .eq("status", "active") \
        .execute()
    return {"agents": result.data}

@app.post("/execute/{agent_name}")
async def execute_agent(agent_name: str, request: ExecuteRequest):
    """Route execution to agent service."""
    # 1. Get agent URL from registry
    result = supabase.table("agent_registry") \
        .select("service_url") \
        .eq("agent_name", agent_name) \
        .eq("status", "active") \
        .single() \
        .execute()

    if not result.data:
        raise HTTPException(status_code=404, detail=f"Agent {agent_name} not found")

    service_url = result.data["service_url"]

    # 2. Forward request to agent service
    async with httpx.AsyncClient() as client:
        try:
            response = await client.post(
                f"{service_url}/execute",
                json=request.input_data,
                timeout=30.0
            )
            response.raise_for_status()
            output = response.json()
        except Exception as e:
            # Record failure
            supabase.table("agent_runs").insert({
                "agent_name": agent_name,
                "input": request.input_data,
                "success": False,
                "error": str(e)
            }).execute()
            raise HTTPException(status_code=500, detail=str(e))

    # 3. Record execution
    supabase.table("agent_runs").insert({
        "agent_name": agent_name,
        "input": request.input_data,
        "output": output,
        "success": True,
        "duration_ms": int(response.elapsed.total_seconds() * 1000)
    }).execute()

    return output

@app.post("/pipeline/run")
async def run_pipeline(request: PipelineRequest):
    """Execute multi-agent pipeline."""
    results = []
    current_input = request.initial_input

    for agent_name in request.steps:
        # Execute agent
        response = await execute_agent(agent_name, ExecuteRequest(
            agent_name=agent_name,
            input_data=current_input
        ))
        results.append(response)

        # Pass output to next agent
        current_input = response

    return {"results": results, "success": True}

@app.get("/dependencies/validate")
def validate_dependencies():
    """Validate agent dependency graph."""
    # Query all specs
    result = supabase.table("agent_specs") \
        .select("agent_name, dependencies") \
        .execute()

    agents = {spec["agent_name"]: spec["dependencies"] for spec in result.data}

    # Check for circular dependencies (simple check)
    errors = []
    for agent, deps in agents.items():
        for dep in deps:
            if dep not in agents:
                errors.append(f"{agent} depends on non-existent {dep}")

    return {
        "is_healthy": len(errors) == 0,
        "errors": errors,
        "registered_agents": list(agents.keys())
    }
```

---

## Agent Service Template

**File:** `king/services/code-writer/main.py`

```python
from fastapi import FastAPI
from pydantic import BaseModel
import google.generativeai as genai
import os

app = FastAPI(title="Code Writer Service")

# Configure Gemini
genai.configure(api_key=os.getenv("GEMINI_API_KEY"))
model = genai.GenerativeModel("gemini-2.0-flash-exp")

# Load DNA rules from environment or config
DNA_RULES = [
    "output code ONLY in specified language",
    "every function must have docstring",
    "include basic error handling",
    "output valid JSON only"
]

class ExecuteRequest(BaseModel):
    task: str
    language: str = "python"

@app.get("/health")
def health_check():
    return {"status": "ok", "service": "code-writer"}

@app.post("/execute")
def execute(request: ExecuteRequest):
    """Execute code writer agent."""
    # Build prompt
    prompt = f"""You are a code writer agent.

DNA Rules:
{chr(10).join(f'- {rule}' for rule in DNA_RULES)}

Task: {request.task}
Language: {request.language}

Output JSON with:
- language: string
- code: string
- confidence: float (0.0-1.0)
"""

    # Call Gemini
    response = model.generate_content(prompt)

    # Parse JSON response
    import json
    try:
        output = json.loads(response.text.strip('```json\n').strip('```'))
    except:
        output = {
            "language": request.language,
            "code": response.text,
            "confidence": 0.5
        }

    return output
```

---

## KING Deployment (Docker Compose)

**File:** `king/docker-compose.yml`

```yaml
version: '3.8'

services:
  # Gateway (thin orchestrator)
  gateway:
    build: ./gateway
    ports:
      - "8000:8000"
    environment:
      - SUPABASE_URL=${SUPABASE_URL}
      - SUPABASE_SERVICE_KEY=${SUPABASE_SERVICE_KEY}
    depends_on:
      - code-writer
      - code-reviewer
      - video-planner
      - script-writer

  # Agent services
  code-writer:
    build: ./services/code-writer
    ports:
      - "8001:8001"
    environment:
      - GEMINI_API_KEY=${GEMINI_API_KEY}

  code-reviewer:
    build: ./services/code-reviewer
    ports:
      - "8002:8002"
    environment:
      - GEMINI_API_KEY=${GEMINI_API_KEY}

  video-planner:
    build: ./services/video-planner
    ports:
      - "8003:8003"
    environment:
      - GEMINI_API_KEY=${GEMINI_API_KEY}

  script-writer:
    build: ./services/video-planner
    ports:
      - "8004:8004"
    environment:
      - GEMINI_API_KEY=${GEMINI_API_KEY}
```

**Usage:**
```bash
cd king
docker-compose up -d

# Test gateway
curl http://localhost:8000/health
curl http://localhost:8000/agents/list

# Test agent directly
curl http://localhost:8001/health

# Execute through gateway
curl -X POST http://localhost:8000/execute/code_writer \
  -H "Content-Type: application/json" \
  -d '{"agent_name": "code_writer", "input_data": {"task": "hello world", "language": "python"}}'
```

---

## KING Advantages

### ✅ Independent Scaling
```bash
# Scale code_writer independently
docker-compose up -d --scale code-writer=3

# Scale gateway separately
docker-compose up -d --scale gateway=2
```

### ✅ Independent Deployment
```bash
# Update code_writer without touching gateway
docker-compose build code-writer
docker-compose up -d code-writer
```

### ✅ Language Agnostic
```python
# code-writer in Python
# code-reviewer in Go
# video-planner in Node.js
# All communicate via HTTP + JSON
```

### ✅ Easy Testing
```bash
# Test agent in isolation
cd services/code-writer
uvicorn main:app --reload
# No need to run entire orchestrator
```

### ✅ Clear Boundaries
```
Gateway: Routing + State
Agents: Business Logic + LLM Calls
Database: Persistent State
```

---

## KING Disadvantages

### ❌ Network Overhead
- HTTP calls between services (latency)
- More failure points (network issues)

### ❌ Deployment Complexity
- 5 services instead of 1
- Container orchestration required
- Service discovery needed

### ❌ Debugging Harder
- Distributed traces needed
- Logs scattered across services

### ❌ Cost Increase
- More containers = more resources
- Cloud Run: 5 services = 5x cost

---

## Migration: CLAUDE → KING

### Step 1: Extract Agent Logic
```bash
# Create agent service skeleton
king/services/code-writer/
├── main.py              # FastAPI app
├── agent_logic.py       # Extracted from agent_runner.py
├── requirements.txt
└── Dockerfile

# Copy DNA rules
backend/orchestrator/agents/agent_specs.json → code-writer/dna_rules.json
```

### Step 2: Create Gateway
```bash
king/gateway/
├── main.py              # Routing only
├── state_manager.py     # Supabase client
├── requirements.txt
└── Dockerfile
```

### Step 3: Migrate Database
```bash
# Add new tables
king/supabase/migrations/001_king_tables.sql
# INSERT agent_registry entries
# INSERT agent_specs from JSON
```

### Step 4: Parallel Deployment
```bash
# Keep CLAUDE running (port 8000)
# Deploy KING alongside (port 9000)
# Test KING thoroughly
# Switch traffic: 8000 → 9000
# Retire CLAUDE
```

---

## KING + Phase 1 Ministers

### Ministers as Sidecar Services

```yaml
# Optional: Add minister services
services:
  guardian-minister:
    build: ./services/guardian-minister
    ports:
      - "8101:8101"
    # Called by gateway BEFORE agent execution

  validator-minister:
    build: ./services/validator-minister
    ports:
      - "8102:8102"
    # Called by gateway for spec validation

  audit-minister:
    build: ./services/audit-minister
    ports:
      - "8103:8103"
    # Runs async, analyzes agent_runs table
```

### Gateway with Ministers

```python
@app.post("/execute/{agent_name}")
async def execute_agent(agent_name: str, request: ExecuteRequest):
    # 1. Optional: Check guardian
    if os.getenv("ENABLE_GUARDIAN") == "true":
        guardian_check = await check_guardian(request.input_data)
        if guardian_check["verdict"] == "BLOCKED":
            raise HTTPException(status_code=403, detail="Blocked by guardian")

    # 2. Execute agent (as before)
    output = await _call_agent_service(agent_name, request.input_data)

    # 3. Optional: Record for audit
    if os.getenv("ENABLE_AUDIT") == "true":
        await notify_audit_minister(agent_name, request.input_data, output)

    return output
```

---

## Folder Structure: Future vs MVP vs KING

```
d:\ai-ecosystem/
├── CLAUDE.md                 # Full documentation
├── CLAUDE_MVP.md             # MVP subset documentation
├── KING_MVP.md               # This file (microservices architecture)
│
├── future/                   # Full platform (Phase 1 complete)
│   ├── backend/
│   │   ├── agents/           # 13 agents + ministers
│   │   ├── services/         # 16 services
│   │   ├── api/              # 34 endpoints
│   │   └── main.py
│   ├── supabase/
│   │   └── migrations/       # 9 migrations
│   └── tests/                # Full test suite
│
├── mvp/                      # Deployable MVP (monolithic)
│   ├── backend/
│   │   ├── agents/           # 4 agents only
│   │   ├── services/         # 5 services only
│   │   ├── api/              # 8 endpoints only
│   │   └── main.py
│   ├── supabase/
│   │   └── migrations_mvp/   # 1 migration (3 tables)
│   └── Dockerfile            # Cloud Run ready
│
├── king/                     # Microservices architecture (experimental)
│   ├── gateway/              # Thin orchestrator
│   │   ├── main.py
│   │   ├── state_manager.py
│   │   └── Dockerfile
│   ├── services/
│   │   ├── code-writer/      # Independent service
│   │   │   ├── main.py
│   │   │   └── Dockerfile
│   │   ├── code-reviewer/
│   │   ├── video-planner/
│   │   └── script-writer/
│   ├── supabase/
│   │   └── migrations_king/  # agent_registry + agent_specs
│   └── docker-compose.yml
│
└── backend/                  # Original (keep as reference)
    └── orchestrator/
```

---

## Decision Matrix: Which Architecture?

| Factor | CLAUDE (Monolith) | MVP (Slim Monolith) | KING (Microservices) |
|--------|-------------------|---------------------|----------------------|
| **Deployment Speed** | ⚠️ Slow (many features) | ✅ Fast (minimal) | ⚠️ Medium (5 services) |
| **Operational Cost** | ⚠️ High (all features) | ✅ Low (<$55/mo) | ⚠️ Medium (5x resources) |
| **Scalability** | ⚠️ Limited (monolith) | ⚠️ Limited (monolith) | ✅ Excellent (per-agent) |
| **Development Speed** | ✅ Fast (all in one) | ✅ Fast (simple) | ⚠️ Slow (coordination) |
| **Debugging** | ✅ Easy (one process) | ✅ Easy (one process) | ⚠️ Hard (distributed) |
| **Feature Richness** | ✅ Full (13 agents) | ⚠️ Basic (4 agents) | ⚠️ Basic (4 agents) |
| **Production Ready** | ⚠️ Not yet tested | ✅ Yes (MVP proven) | ❌ No (experimental) |

---

## Recommendations

### For Immediate Deployment: Choose MVP
```bash
# Reason: Works NOW, costs least, simplest to operate
cd mvp
gcloud run deploy
```

### For Future Growth: Plan for KING
```bash
# Reason: Scales better, clearer boundaries, easier to maintain
# But: Deploy MVP first, migrate to KING later when proven
```

### Keep CLAUDE/future/ as Reference
```bash
# Reason: Phase 1 work is valuable
# Keep in future/ for incremental migration to MVP or KING
```

---

## KING Roadmap

### Phase 1: Prove MVP (NOW)
- Deploy mvp/ to Cloud Run
- Validate 4 agents work
- Monitor for 1-2 weeks

### Phase 2: Experiment with KING (LATER)
- Build king/ in parallel
- Deploy to staging environment
- Compare performance vs MVP

### Phase 3: Migrate to KING (FUTURE)
- If KING proves better, migrate MVP → KING
- If not, enhance MVP incrementally
- Keep future/ features for either path

---

## Summary

**KING = Radical Simplification**

- Gateway: 200 lines (routing only)
- Agent Service: 50 lines each (logic + LLM)
- Database: 3 tables (registry, specs, runs)
- Deployment: 5 containers (1 gateway + 4 agents)

**Trade-offs:**
- ✅ Clearer boundaries
- ✅ Independent scaling
- ✅ Language agnostic
- ❌ More operational complexity
- ❌ Network latency
- ❌ Higher cloud costs

**Recommendation:**
Deploy MVP first (monolithic). Experiment with KING in parallel. Migrate only if proven better.

---

**Future is flexible. MVP is deployable. KING is experimental.**
Choose based on your priority: speed (MVP) or scale (KING).
