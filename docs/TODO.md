# KINGDOM TODO & ROADMAP

**Document Type:** Living Task List  
**Last Updated:** 2025-12-03  
**Status:** Phase 1 Complete → Entering Phase 2

---

## IMMEDIATE ACTIONS (Do Now)

### P0: Critical Wiring

- [ ] **Run sync_specs.py**
  - Location: `king/orchestrator/scripts/sync_specs.py`
  - Purpose: Populate `agent_specs` table so registered agents get matched
  - Without this: All requests fall to ephemeral spawn

- [ ] **Wire entity resolution into /king/decide**
  - Location: `king/gateway/memory/entity_resolver.py`
  - Wire into: `king/orchestrator/api/decide.py`
  - Purpose: Normalize entity references before agent matching

- [ ] **Wire reflection post-execution**
  - Location: `king/gateway/memory/reflection.py`
  - Wire into: After agent execution returns
  - Purpose: Extract patterns and learnings from interactions

---

## PHASE 2: THE BODY (Capabilities)

### 2.1 The Hands (Tools & Actions) — HIGH PRIORITY

**Goal:** Allow agents to execute tools, not just generate text.

| Task | Status | Notes |
|------|--------|-------|
| Evaluate SandboxFusion | 🔍 Researched | ByteDance, Apache 2.0, 20+ languages |
| Decide hosting model | ❓ Pending | Cloud Run vs GCE VM vs Hosted API |
| Create tool-executor service | ❌ Not started | `king/services/tool-executor/` |
| Implement `_execute_code()` | ❌ Not started | Sandboxed Python |
| Implement `_execute_web_search()` | ❌ Not started | SerpAPI or Google |
| Implement `_execute_api_call()` | ❌ Not started | Safe external API calls |
| Wire into orchestrator | ❌ Not started | Tool requests from agents |

**Hosting Options Discussed:**

| Option | Pros | Cons |
|--------|------|------|
| **A) GCE VM + Docker** | Full control, --privileged | Ops overhead |
| **B) Cloud Run + gVisor** | Managed, cheap | Limited isolation |
| **C) Hosted API (E2B/Modal)** | Zero ops, instant | Cost, vendor lock |

**Recommendation:** Option C for speed, migrate to A later.

### 2.2 The Senses (Files & Data) — MEDIUM PRIORITY

**Goal:** Accept file uploads, process documents, ingest data.

| Task | Status | Notes |
|------|--------|-------|
| Create `/upload` endpoint | ❌ Not started | Gateway route |
| Create data-processor service | ❌ Not started | `king/services/data-processor/` |
| Implement PDF parsing | ❌ Not started | PyPDF2 or similar |
| Implement CSV ingestion | ❌ Not started | pandas |
| Implement image analysis | ❌ Not started | Gemini Vision |
| Wire to memory system | ❌ Not started | Store processed data |

### 2.3 The Face (UI) — LOW PRIORITY

**Goal:** WhatsApp-like web interface.

| Task | Status | Notes |
|------|--------|-------|
| Choose framework | ❓ Pending | Streamlit vs React |
| Create chat interface | ❌ Not started | WebSocket or polling |
| Add file upload UI | ❌ Not started | Drag-and-drop |
| Add conversation history | ❌ Not started | From Supabase |
| Deploy to Cloud Run | ❌ Not started | Static or SSR |

---

## PHASE 3: THE SOUL (Self-Improvement)

### 3.1 DNA Mutation System

| Task | Status | Notes |
|------|--------|-------|
| Activate Audit Minister | ⚠️ Code exists | Wire telemetry analysis |
| Implement mutation proposals | ⚠️ Code exists | `dna_mutator.py` |
| Create approval workflow | ❌ Not started | Admin UI or API |
| Auto-rollback on regression | ❌ Not started | Performance gating |

### 3.2 Agent Promotion Pipeline (Council-Governed)

**Goal:** Agents self-promote based on performance, governed by the Council.

| Task | Status | Notes |
|------|--------|-------|
| Create `agent_lifecycle` table | ❌ Not started | States: candidate → probation → active → core |
| Track ephemeral performance | ⚠️ Partial | `agent_runs` table |
| Define promotion criteria | ❌ Not started | 10+ runs, 90%+ success, <5% error |
| Implement Council vote endpoint | ❌ Not started | Guardian + Validator approve promotions |
| Create `/agents/promote` API | ❌ Not started | Orchestrator endpoint |
| Auto-register promoted agents | ❌ Not started | Insert to `agent_registry` + `agent_specs` |
| Demotion on regression | ❌ Not started | Performance gating, auto-demote if <70% |

**Lifecycle States:**

```
candidate → probation (7 days) → active → core (permanent)
     ↓           ↓                  ↓
  rejected    demoted            demoted
```

**Council Approval Flow:**
1. Agent hits promotion threshold (metrics)
2. Guardian Minister reviews for safety violations
3. Validator Minister reviews spec completeness
4. Both approve → promotion executed
5. Either rejects → stays in current tier with feedback

---

## TECHNICAL DEBT

| Item | Location | Priority |
|------|----------|----------|
| Clean up unused imports | Various | Low |
| Add comprehensive logging | All services | Medium |
| Implement rate limiting | Gateway | Medium |
| Add health check endpoints | All services | Low |
| Create integration tests | `tests/` | High |

---

## DISCUSSED BUT NOT CONFIRMED

These items were discussed in planning but not formally approved:

1. **SandboxFusion integration** — Discussed as code execution backend
2. **E2B/Modal for hosted sandboxes** — Mentioned as alternative
3. **Streamlit for UI** — Mentioned but not decided
4. **Agent marketplace** — Long-term vision, no timeline
5. **Federation with other KINGs** — Conceptual only

---

## BLOCKED ITEMS

| Item | Blocker | Resolution |
|------|---------|------------|
| Agent matching | `agent_specs` empty | Run sync_specs.py |
| Entity normalization | Not wired | Wire entity_resolver |
| Learning from interactions | Not wired | Wire reflection |

---

## CHANGELOG

| Date | Change |
|------|--------|
| 2025-12-03 | Initial TODO created from session analysis |
| 2025-12-03 | Phase 1 declared complete |
| 2025-12-03 | Phase 2 planning documented |

---

*This TODO is maintained by the Kingdom and updated after each session.*

