# KINGDOM DISCUSSIONS LOG

**Document Type:** Decision & Discussion Archive  
**Purpose:** Track all discussions, proposals, and decisions — confirmed or not  
**Last Updated:** 2025-12-03

---

## FORMAT

Each entry follows:
```
### [DATE] Topic
**Status:** Confirmed | Discussed | Rejected | Pending
**Participants:** Who was involved
**Summary:** What was discussed
**Decision:** What was decided (if any)
**Action Items:** What needs to happen
```

---

## 2025-12-03: Phase 2 "The Body" Planning

**Status:** Discussed (Not Confirmed)  
**Participants:** User, AI Assistant

**Summary:**
Identified that Phase 1 "The Brain" is complete. Discussed Phase 2 priorities:

1. **The Hands (Tools & Actions)** — Allow agents to execute, not just generate
2. **The Senses (Files & Data)** — File upload, document processing
3. **The Face (UI)** — Web interface

**Key Discussion Points:**

- Current `ActionExecutor` only handles artifact storage/deployment
- Need new capabilities: web search, code execution, API calls, file ops
- Two options proposed:
  - Option 1: Extend existing `ActionExecutor`
  - Option 2: Create new `ToolExecutor` service (recommended)

**ByteDance SandboxFusion Discovery:**
- Found via GitHub: `bytedance/SandboxFusion`
- Apache 2.0 license
- Supports 20+ languages
- Secure sandboxed execution
- REST API on port 8080
- Docker-based with `--privileged` requirement

**Issue Identified:**
- Cloud Run doesn't support `--privileged` containers
- Alternative hosting options discussed:
  - A) GCE VM with Docker (full control, more ops)
  - B) Cloud Run with gVisor (limited isolation)
  - C) Hosted API like E2B or Modal (zero ops, vendor lock)

**Decision:** Not finalized. User paused to request documentation.

**Action Items:**
- [ ] Create comprehensive documentation (this session)
- [ ] Decide on sandbox hosting approach
- [ ] Begin tool-executor implementation

---

## 2025-12-03: Gateway-Orchestrator Integration

**Status:** Confirmed & Deployed  
**Participants:** User, AI Assistant

**Summary:**
Connected Gateway to Orchestrator for strategic decision routing.

**Technical Details:**
- Added `ORCHESTRATOR_URL` to `king/gateway/.env.yaml`
- Gateway now calls `/king/decide` instead of local `smart_spawn`
- Fallback to local spawn if orchestrator unreachable

**Decision:** Deploy this configuration.

**Action Items:**
- [x] Update `.env.yaml`
- [x] Redeploy gateway
- [x] Verify E2E flow

---

## 2025-12-03: Absolute Imports for Cloud Run

**Status:** Confirmed & Implemented  
**Participants:** User, AI Assistant

**Summary:**
Cloud Run containers have flat structure — relative imports (`from ..`) fail.

**Technical Details:**
- All imports in `king/orchestrator/` converted to absolute
- Example: `from ..services.gemini` → `from services.gemini`
- Pydantic v2 `ClassVar` annotations added to fix model-field errors

**Decision:** All future code uses absolute imports within service directories.

**Files Changed:**
- `king/orchestrator/agents/spec_designer.py`
- `king/orchestrator/agents/video_planner.py`
- Multiple other agent files

---

## 2025-12-02: Memory System Design

**Status:** Confirmed & Implemented  
**Participants:** User, AI Assistant

**Summary:**
Designed multi-tier memory system using Mem0.

**Memory Tiers:**
| Tier | user_id | Purpose |
|------|---------|---------|
| Collective | `__kingdom__` | Shared kingdom knowledge |
| Lineage | `{agent_id}` | Agent patterns |
| Episodic | `{user_id}` | Recent events |
| Semantic | `{user_id}` | Concepts |

**Resolution Order:**
Working → Episodic → Semantic → Lineage → Collective

**Components Created:**
- `CuratorAgent` — AI-powered memory selection
- `ReflectionAgent` — Pattern extraction
- `EntityResolver` — Canonical entity tracking
- `DecayManager` — Time-based relevance

**Decision:** Implement in `king/gateway/memory/`

**Action Items:**
- [x] Create memory subsystem files
- [ ] Wire into main decision flow
- [ ] Wire reflection post-execution

---

## 2025-12-01: Microservices Architecture Decision

**Status:** Confirmed & Deployed  
**Participants:** User, AI Assistant

**Summary:**
Decided to decompose monolith into microservices.

**Rationale:**
- Independent scaling per agent
- Isolated deployments
- Cleaner separation of concerns
- Cloud Run natural fit

**Architecture:**
```
Gateway (thin) → Orchestrator (brain) → Agent Services (workers)
```

**Decision:** Proceed with KING microservices pattern.

**Documents Created:**
- `KING_MVP.md`
- `GIT_BRANCHING_STRATEGY.md`

---

## PENDING DISCUSSIONS

### Sandbox Hosting
- **Options on table:** GCE VM, Cloud Run gVisor, Hosted API
- **Recommendation given:** Option C (hosted) for speed
- **Awaiting:** User decision

### UI Framework
- **Options mentioned:** Streamlit, React
- **No decision made**
- **Priority:** Low (after tools)

### Agent Marketplace
- **Concept discussed:** Long-term vision for agent sharing
- **No timeline or design**
- **Status:** Future consideration

---

## REJECTED PROPOSALS

*None yet*

---

*This log is append-only. New discussions go at the top.*

