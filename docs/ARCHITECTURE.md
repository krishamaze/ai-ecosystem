# KINGDOM ARCHITECTURE

**Document Type:** Technical Reference  
**Last Updated:** 2025-12-03  
**Diagram Version:** 3.0 (Post-Orchestrator)

---

## SYSTEM OVERVIEW

```
┌─────────────────────────────────────────────────────────────────────┐
│                         EXTERNAL LAYER                               │
├─────────────────────────────────────────────────────────────────────┤
│  [Telegram Bot]    [Web UI (Future)]    [API Clients]               │
│        │                  │                   │                      │
│        └──────────────────┼───────────────────┘                      │
│                           ▼                                          │
│                    ┌──────────────┐                                  │
│                    │   GATEWAY    │  ← Thin ingress, no logic       │
│                    │  /spawn      │                                  │
│                    │  /chat       │                                  │
│                    └──────┬───────┘                                  │
│                           │                                          │
├───────────────────────────┼─────────────────────────────────────────┤
│                    BRAIN LAYER                                       │
├───────────────────────────┼─────────────────────────────────────────┤
│                           ▼                                          │
│                    ┌──────────────┐                                  │
│                    │ ORCHESTRATOR │  ← Strategic decision engine    │
│                    │ /king/decide │                                  │
│                    └──────┬───────┘                                  │
│                           │                                          │
│            ┌──────────────┼──────────────┐                          │
│            ▼              ▼              ▼                          │
│     ┌──────────┐   ┌──────────┐   ┌──────────┐                     │
│     │ Guardian │   │ Validator│   │  Audit   │  ← Ministry Council │
│     │ Minister │   │ Minister │   │ Minister │                     │
│     └──────────┘   └──────────┘   └──────────┘                     │
│                                                                      │
├─────────────────────────────────────────────────────────────────────┤
│                    EXECUTION LAYER                                   │
├─────────────────────────────────────────────────────────────────────┤
│                                                                      │
│  ┌─────────────┐ ┌─────────────┐ ┌─────────────┐ ┌─────────────┐   │
│  │ code-writer │ │code-reviewer│ │video-planner│ │script-writer│   │
│  │   /run      │ │    /run     │ │    /run     │ │    /run     │   │
│  └─────────────┘ └─────────────┘ └─────────────┘ └─────────────┘   │
│                                                                      │
│  ┌─────────────┐ ┌─────────────┐                                    │
│  │mem-selector │ │  EPHEMERAL  │  ← Spawned on-demand              │
│  │   /run      │ │   Agents    │                                    │
│  └─────────────┘ └─────────────┘                                    │
│                                                                      │
├─────────────────────────────────────────────────────────────────────┤
│                    DATA LAYER                                        │
├─────────────────────────────────────────────────────────────────────┤
│                                                                      │
│  ┌──────────────────┐    ┌──────────────────┐                       │
│  │     SUPABASE     │    │      MEM0        │                       │
│  │   PostgreSQL     │    │  Memory Store    │                       │
│  │                  │    │                  │                       │
│  │ • agent_registry │    │ • collective     │                       │
│  │ • agent_specs    │    │ • lineage        │                       │
│  │ • agent_runs     │    │ • episodic       │                       │
│  │ • tasks          │    │ • semantic       │                       │
│  │ • entities       │    │                  │                       │
│  └──────────────────┘    └──────────────────┘                       │
│                                                                      │
└─────────────────────────────────────────────────────────────────────┘
```

---

## DECISION FLOW

```
Request → Gateway → Orchestrator → Guardian Check → Agent Match → Execute → Response
                                        │
                                        ▼
                              [BLOCKED if dangerous]
```

### Decision Types

| Decision | Condition | Action |
|----------|-----------|--------|
| `registered` | Match in `agent_specs` | Route to agent URL |
| `ephemeral` | No match | Spawn temporary agent |
| `rejected` | Guardian blocks | Return error |

---

## SERVICE REGISTRY

| Service | Port | Cloud Run URL |
|---------|------|---------------|
| king-gateway | 8080 | king-gateway-d3zysgasgq-uc.a.run.app |
| king-orchestrator | 8080 | king-orchestrator-d3zysgasgq-uc.a.run.app |
| king-code-writer | 8080 | king-code-writer-d3zysgasgq-uc.a.run.app |
| king-code-reviewer | 8080 | king-code-reviewer-d3zysgasgq-uc.a.run.app |
| king-video-planner | 8080 | king-video-planner-d3zysgasgq-uc.a.run.app |
| king-script-writer | 8080 | king-script-writer-d3zysgasgq-uc.a.run.app |
| king-memory-selector | 8080 | king-memory-selector-d3zysgasgq-uc.a.run.app |

---

## DIRECTORY STRUCTURE

```
king/
├── gateway/                    # Thin ingress layer
│   ├── main.py                # FastAPI routes
│   ├── state_manager.py       # Supabase client
│   ├── agent_factory.py       # Agent creation
│   └── memory/                # Memory subsystem
│       ├── curator.py         # AI-powered selection
│       ├── reflection.py      # Pattern extraction
│       ├── entity_resolver.py # Canonical entities
│       └── decay.py           # Time-based relevance
│
├── orchestrator/              # Strategic brain
│   ├── api/                   # HTTP endpoints
│   │   ├── decide.py          # /king/decide
│   │   ├── meta.py            # /health, /agents
│   │   └── tasks.py           # /tasks
│   ├── agents/                # Agent implementations
│   │   ├── guardian_minister.py
│   │   ├── validator_minister.py
│   │   ├── audit_minister.py
│   │   └── base_agent.py
│   ├── services/              # Business logic
│   │   ├── gemini.py          # LLM calls
│   │   ├── mem0_tool.py       # Memory access
│   │   └── guardrails.py      # Safety checks
│   └── scripts/               # Utilities
│       └── sync_specs.py      # DB population
│
├── services/                  # Independent agents
│   ├── code-writer/
│   ├── code-reviewer/
│   ├── video-planner/
│   ├── script-writer/
│   └── memory-selector/
│
└── telegram-bot/              # Telegram interface
```

---

## MEMORY ARCHITECTURE

### Tier Hierarchy

```
┌─────────────────────────────────────┐
│         WORKING MEMORY              │  ← Current session context
├─────────────────────────────────────┤
│         EPISODIC MEMORY             │  ← Recent events
├─────────────────────────────────────┤
│         SEMANTIC MEMORY             │  ← Conceptual knowledge
├─────────────────────────────────────┤
│         LINEAGE MEMORY              │  ← Agent-specific patterns
├─────────────────────────────────────┤
│         COLLECTIVE MEMORY           │  ← Kingdom-wide truths
└─────────────────────────────────────┘
```

### Mem0 Configuration

| Tier | user_id | enable_graph |
|------|---------|--------------|
| Collective | `__kingdom__` | True |
| Lineage | `{agent_id}` | False |
| Episodic | `{user_id}` | False |
| Semantic | `{user_id}` | True |

---

*This architecture evolves with the Kingdom.*

