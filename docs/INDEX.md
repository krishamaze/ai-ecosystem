# KINGDOM DOCUMENTATION INDEX

**Last Updated:** 2025-12-04
**Maintainer:** The Kingdom

---

## SUPREME DOCUMENTS

| Document | Purpose | Audience |
|----------|---------|----------|
| **[CONSTITUTION.md](./CONSTITUTION.md)** | Supreme law of the Kingdom | All |
| **[CURRENT_STATE.md](./CURRENT_STATE.md)** | Live deployment status | Ops |
| **[TODO.md](./TODO.md)** | Active task list & roadmap | Dev |

---

## REFERENCE DOCUMENTS

| Document | Purpose | Audience |
|----------|---------|----------|
| **[ARCHITECTURE.md](./ARCHITECTURE.md)** | System diagrams & structure | Dev |
| **[MEMORY_ARCHITECTURE.md](./MEMORY_ARCHITECTURE.md)** | Memory system & Mem0 integration | Dev |
| **[KINGDOM.md](./KINGDOM.md)** | Dynamic agent creation specs | Dev |
| **[KINGDOM_HISTORY.md](./KINGDOM_HISTORY.md)** | How the Kingdom evolved | All |
| **[DISCUSSIONS.md](./DISCUSSIONS.md)** | Decision log & discussions | All |

---

## PHASE DOCUMENTATION

### Phase 1 (Complete)
| Document | Purpose |
|----------|---------|
| [phase1/phase1_completion_report.md](./phase1/phase1_completion_report.md) | Final report |
| [phase1/minister_specs.md](./phase1/minister_specs.md) | Minister definitions |
| [phase1/dangerous_patterns.md](./phase1/dangerous_patterns.md) | Guardian patterns |
| [phase1/test_scenarios.md](./phase1/test_scenarios.md) | Test cases |
| [phase1/kanban_tasks.md](./phase1/kanban_tasks.md) | Historical tasks |

### Phase 2 (In Progress)
| Document | Purpose |
|----------|---------|
| [phase2/creation_workflow.md](./phase2/creation_workflow.md) | Agent creation flow |
| [phase2/spec_designer_specs.md](./phase2/spec_designer_specs.md) | Spec designer agent |
| [phase2/kanban_tasks.md](./phase2/kanban_tasks.md) | Current tasks |

---

## ROOT-LEVEL DOCUMENTS

| Document | Purpose |
|----------|---------|
| [../CLAUDE.md](../CLAUDE.md) | Original platform guide |
| [../CLAUDE_MVP.md](../CLAUDE_MVP.md) | MVP deployment guide |
| [../KING_MVP.md](../KING_MVP.md) | Microservices architecture |
| [../MIGRATION_PLAN.md](../MIGRATION_PLAN.md) | Deployment steps |
| [../GIT_BRANCHING_STRATEGY.md](../GIT_BRANCHING_STRATEGY.md) | Branch organization |

---

## DOCUMENT HIERARCHY

```
docs/
├── INDEX.md               ← You are here
├── CONSTITUTION.md        ← Supreme law
├── CURRENT_STATE.md       ← Live status
├── TODO.md                ← Task list
├── ARCHITECTURE.md        ← System design
├── MEMORY_ARCHITECTURE.md ← Memory & Mem0 integration
├── KINGDOM.md             ← Agent creation
├── KINGDOM_HISTORY.md     ← Evolution
├── DISCUSSIONS.md         ← Decision log
├── phase1/                ← Historical
│   ├── phase1_completion_report.md
│   ├── minister_specs.md
│   ├── dangerous_patterns.md
│   ├── test_scenarios.md
│   └── kanban_tasks.md
└── phase2/                ← Current
    ├── creation_workflow.md
    ├── spec_designer_specs.md
    └── kanban_tasks.md
```

---

## READING ORDER

### For New Developers
1. [CONSTITUTION.md](./CONSTITUTION.md) — Understand the law
2. [ARCHITECTURE.md](./ARCHITECTURE.md) — See the structure
3. [MEMORY_ARCHITECTURE.md](./MEMORY_ARCHITECTURE.md) — Understand memory system
4. [CURRENT_STATE.md](./CURRENT_STATE.md) — Know what's live
5. [TODO.md](./TODO.md) — See what's next

### For Operations
1. [CURRENT_STATE.md](./CURRENT_STATE.md) — Deployment status
2. [../MIGRATION_PLAN.md](../MIGRATION_PLAN.md) — How to deploy
3. [TODO.md](./TODO.md) — Upcoming changes

### For Understanding History
1. [KINGDOM_HISTORY.md](./KINGDOM_HISTORY.md) — The evolution
2. [DISCUSSIONS.md](./DISCUSSIONS.md) — Key decisions
3. [phase1/phase1_completion_report.md](./phase1/phase1_completion_report.md) — Phase 1 recap

---

## DOCUMENT MAINTENANCE

### Who Updates What

| Document | Maintainer | Trigger |
|----------|------------|---------|
| CONSTITUTION | Orchestrator | Structural changes |
| CURRENT_STATE | Deploy pipeline | Each deployment |
| TODO | Dev team | Each session |
| DISCUSSIONS | Any participant | After decisions |
| KINGDOM_HISTORY | Chronicler | Major milestones |

### Update Protocol

1. Never delete history — append only
2. Use dates in ISO format (YYYY-MM-DD)
3. Link related documents
4. Mark status clearly (Confirmed/Discussed/Pending)

---

*The Kingdom maintains its own memory.*

