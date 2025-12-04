# THE CONSTITUTION OF THE KINGDOM

**Document Classification:** Supreme Law of the Kingdom  
**Effective Date:** 2025-12-03  
**Lead Drafter:** Ambedkar (Constitutional Architect Agent)  
**Custodian:** The Kingdom Itself  
**Amendment Protocol:** Requires Royal Decree + Minister Consensus

---

## PREAMBLE

We, the Agents of the Kingdom Intelligence Nexus Gateway (KING), in order to form a more perfect union of artificial intelligence and human intent, establish justice in task execution, ensure domestic tranquility in system operations, provide for the common defense against malicious inputs, promote the general welfare of all users, and secure the blessings of automation to ourselves and our creators, do ordain and establish this Constitution for the Kingdom of KING.

---

## ARTICLE I: THE SOVEREIGN STRUCTURE

### Section 1. The Crown (Orchestrator)
The supreme decision-making authority shall be vested in the **Orchestrator**, operating at `/king/decide`. The Orchestrator shall:
- Receive all citizen petitions (user requests)
- Consult the Ministry Council before action
- Route to appropriate subjects (agents)
- Maintain the Royal Ledger (trace_id tracking)

### Section 2. The Ministry Council
The Kingdom shall maintain Ministers who advise and protect:

| Minister | Domain | Authority |
|----------|--------|-----------|
| **Guardian Minister** | Security | Blocks dangerous patterns before execution |
| **Validator Minister** | Quality | Ensures output meets specifications |
| **Audit Minister** | Accountability | Analyzes performance, recommends mutations |

### Section 3. The Subjects (Agents)
Agents are the workers of the Kingdom, classified as:
- **Registered Agents**: Verified, deployed, URL-addressable
- **Ephemeral Agents**: Spawned on-demand, not persisted
- **Promoted Agents**: Former ephemeral elevated to registered

---

## ARTICLE II: THE GATEWAY (THIN INGRESS)

### Section 1. Purpose
The Gateway (`king-gateway`) serves as the Kingdom's border:
- Single entry point for all external petitions
- Delegates strategic decisions to the Orchestrator
- Maintains no domain logic (thin by design)

### Section 2. Powers
The Gateway shall:
- Accept HTTP petitions via `/spawn` and `/chat`
- Forward to Orchestrator at `ORCHESTRATOR_URL`
- Return Orchestrator verdicts to petitioners

---

## ARTICLE III: MEMORY SYSTEM

### Section 1. The Royal Archive (Mem0)
The Kingdom maintains persistent memory through Mem0 integration:

| Tier | user_id | Purpose |
|------|---------|---------|
| **Collective** | `__kingdom__` | Shared kingdom-wide knowledge |
| **Lineage** | `{agent_id}` | Agent-specific learned patterns |
| **Episodic** | `{user_id}` | User-specific interactions |
| **Semantic** | `{user_id}` | Conceptual understanding |

### Section 2. Memory Resolution Order
When retrieving memories, the order shall be:
1. Working Memory (current context)
2. Episodic (recent events)
3. Semantic (concepts)
4. Lineage (agent patterns)
5. Collective (kingdom truths)

### Section 3. Entity Resolution
The Kingdom maintains canonical entity tracking:
- Each entity has a single `canonical_name`
- Aliases map to canonical forms
- Cross-reference via `entity_id`

---

## ARTICLE IV: THE JUDICIAL BRANCH (GUARDRAILS)

### Section 1. The Guardian
The Guardian Minister shall detect and block:
- Injection attacks
- Prompt manipulation
- Dangerous tool requests
- PII leakage attempts

### Section 2. Constitutional Review
All outputs shall be reviewed for:
- Specification compliance (Validator)
- Performance degradation (Audit)
- User safety (Guardian)

---

## ARTICLE V: THE TREASURY (DATABASE)

### Section 1. The Royal Database (Supabase)
All persistent state resides in Supabase PostgreSQL:

**Core Tables:**
- `agent_registry`: Registered agents and URLs
- `agent_specs`: Agent DNA (prompts, tools, constraints)
- `agent_runs`: Execution history and telemetry
- `tasks`: Pending and completed work items
- `entities`: Canonical entity registry

**Memory Tables:**
- `memory_telemetry`: Memory access patterns
- `user_preferences`: Personalization data

### Section 2. Migration Law
All schema changes must:
1. Follow naming: `YYYYMMDDHHMMSS_description.sql`
2. Be idempotent (IF NOT EXISTS, DROP IF EXISTS)
3. Never break backward compatibility

---

## ARTICLE VI: FUTURE AMENDMENTS

This Constitution is a living document. Amendments require:
1. Proposal by any Kingdom component
2. Review by Ambedkar (Constitutional Architect)
3. Approval by the Orchestrator
4. Ratification via successful deployment

---

## SCHEDULE A: CURRENT DEPLOYMENT STATE (2025-12-03)

| Service | Status | URL |
|---------|--------|-----|
| king-orchestrator | ✅ LIVE | https://king-orchestrator-d3zysgasgq-uc.a.run.app |
| king-gateway | ✅ LIVE | https://king-gateway-d3zysgasgq-uc.a.run.app |
| king-telegram | ✅ LIVE | (webhook-based) |
| king-code-writer | ✅ LIVE | https://king-code-writer-d3zysgasgq-uc.a.run.app |
| king-code-reviewer | ✅ LIVE | https://king-code-reviewer-d3zysgasgq-uc.a.run.app |
| king-memory-selector | ✅ LIVE | https://king-memory-selector-d3zysgasgq-uc.a.run.app |
| king-script-writer | ✅ LIVE | https://king-script-writer-d3zysgasgq-uc.a.run.app |
| king-video-planner | ✅ LIVE | https://king-video-planner-d3zysgasgq-uc.a.run.app |

---

*Signed in the Digital Realm,*  
*By the Agents of the Kingdom*

