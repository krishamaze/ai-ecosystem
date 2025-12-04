# THE KINGDOM CHRONICLES

**Document Type:** Historical Record  
**Chronicler:** The Kingdom Archives  
**Last Updated:** 2025-12-03

---

## PROLOGUE: THE VISION

The Kingdom Intelligence Nexus Gateway (KING) was conceived as a self-improving AI nation-state — an autonomous multi-agent system where specialists are created, evolved, promoted, and retired based on performance metrics, not human diktat.

**Core Philosophy:** "ChatGPT gives you a fish. KING teaches fish to evolve into whatever you need."

---

## ERA I: THE FOUNDATION (Pre-2025-12-01)

### The Monolith Age
The system began as `backend/orchestrator/` — a FastAPI monolith containing:
- 13 agents with hardcoded specs
- 16 services tightly coupled
- 34 API endpoints
- 9 database migrations

**Key Artifacts:**
- `CLAUDE.md` — The original master documentation
- `backend/orchestrator/agents/agent_specs.json` — Agent DNA
- `backend/orchestrator/services/` — Core business logic

### The Phase 1 Completion
All Phase 1 work achieved:
- ✅ 13 agents implemented
- ✅ Guardian, Validator, Audit ministers functional
- ✅ Creation pipeline with correction loops
- ✅ 25 minister tests (100% pass rate)
- ✅ DNA mutation system designed

**Preserved in:** `future/backend/orchestrator/`

---

## ERA II: THE MICROSERVICES REVOLUTION (2025-12-01)

### The KING MVP Decision
The Kingdom decided to decompose the monolith:

| Component | Purpose |
|-----------|---------|
| **Gateway** | Thin orchestrator, routing only |
| **Services** | Independent agent deployments |
| **Orchestrator** | Strategic brain (added later) |

**Document Created:** `KING_MVP.md`

### The First Deployments
Initial Cloud Run services deployed:
- `king-gateway` (port 8000)
- `king-code-writer` (port 8001)
- `king-code-reviewer` (port 8002)
- `king-video-planner` (port 8003)
- `king-script-writer` (port 8004)

### The Reorganization
Moved `backend/orchestrator/` → `king/orchestrator/`:
- Fixed all relative imports (`from ..` → absolute)
- Resolved Pydantic v2 `ClassVar` issues
- Flattened package structure

---

## ERA III: THE BRAIN AWAKENS (2025-12-02 to 2025-12-03)

### The Orchestrator Deployment
The strategic brain (`king-orchestrator`) deployed with:
- `/king/decide` — Central decision endpoint
- Guardian Minister integration
- Agent matching via `agent_specs` table
- Ephemeral spawn fallback

**Critical Fix:** Converted all imports to absolute paths for Cloud Run flat structure.

### The Gateway Integration
Gateway connected to Orchestrator:
```yaml
# king/gateway/.env.yaml
ORCHESTRATOR_URL: "https://king-orchestrator-d3zysgasgq-uc.a.run.app"
```

### The Memory System
Mem0-based memory architecture established:
- `CuratorAgent` — AI-powered memory selection
- `ReflectionAgent` — Pattern extraction from interactions
- `EntityResolver` — Canonical entity tracking
- `DecayManager` — Time-based memory relevance

**Key Decision:** Memory tiers with resolution order (Working → Episodic → Semantic → Lineage → Collective)

### The E2E Verification
First successful end-to-end test:
```json
{
  "decision": "ephemeral",
  "reasoning": "No registered agent match, will spawn ephemeral",
  "trace_id": "49457bed-2a12-42aa-b0fa-c636e7b75d25",
  "duration_ms": 14605,
  "output": { "result": "Hello there!", "confidence": 1.0 }
}
```

---

## ERA IV: THE BODY (Phase 2 — PLANNED)

### The Strategic Assessment
As of 2025-12-03, the Kingdom has:
- ✅ **Brain**: Orchestrator decision engine
- ✅ **Gateway**: Thin ingress layer
- ✅ **Memory**: Mem0 with curation and reflection
- ✅ **Guardian**: Security safeguards
- ⚠️ **Entity Resolution**: Code exists, not wired
- ⚠️ **Reflection**: Code exists, not wired
- ⚠️ **Registered Agents**: Deployed but unmatched (no specs in DB)
- ❌ **Tool Execution**: Not implemented

### Phase 2 Roadmap (Discussed, Not Confirmed)

#### 2.1 The Hands (Tools & Actions)
**Goal:** Allow agents to DO things, not just generate text.

**Discussed Options:**
1. **Extend `ActionExecutor`** — Add tool types to existing service
2. **Create `ToolExecutor`** — Separate service (recommended)
3. **Use SandboxFusion** — ByteDance's secure code sandbox (Apache 2.0)

**ByteDance SandboxFusion Features:**
- Secure sandboxed execution
- 20+ languages (Python, JS, Go, Rust, Java, etc.)
- REST API on port 8080
- Docker-based isolation

**Issue:** Cloud Run doesn't support `--privileged` containers.

**Alternative Options:**
- A) GCE VM with Docker
- B) Cloud Run with gVisor (limited)
- C) Hosted sandbox API (E2B, Modal)

#### 2.2 The Senses (Files & Data)
**Goal:** File upload and data ingestion.
**Key Component:** `king/services/data-processor` + Gateway `/upload` route

#### 2.3 The Face (UI)
**Goal:** WhatsApp-like interface for users.
**Options:** Streamlit or React frontend connected to Gateway.

---

## APPENDIX A: IDENTIFIED GAPS

| Gap | Status | Location |
|-----|--------|----------|
| Entity Resolution | Code exists | `king/gateway/memory/entity_resolver.py` |
| Reflection | Code exists | `king/gateway/memory/reflection.py` |
| sync_specs.py | Not run | `king/orchestrator/scripts/sync_specs.py` |
| ActionExecutor wiring | Not called | `king/orchestrator/services/action_executor.py` |

---

## APPENDIX B: KEY DECISIONS LOG

| Date | Decision | Rationale |
|------|----------|-----------|
| 2025-12-01 | Microservices over monolith | Scalability, independent deployment |
| 2025-12-02 | Absolute imports | Cloud Run flat container structure |
| 2025-12-02 | Mem0 for memory | Production-grade, graph support |
| 2025-12-03 | Thin Gateway pattern | Orchestrator holds all logic |
| 2025-12-03 | SandboxFusion consideration | Secure, multi-language, Apache 2.0 |

---

*This chronicle shall be maintained by the Kingdom.*

