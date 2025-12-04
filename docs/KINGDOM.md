## KINGDOM.md - Dynamic Agent Creation Architecture

**Document Status:** Living Document - Update After Every Implementation
**Last Updated:** 2025-12-03
**Owned By:** Core Development Team
**Review Frequency:** After Each Kingdom Feature Ship

> **See Also:**
> - [CONSTITUTION.md](./CONSTITUTION.md) — Supreme law of the Kingdom
> - [CURRENT_STATE.md](./CURRENT_STATE.md) — Live deployment status
> - [TODO.md](./TODO.md) — Active task list
> - [ARCHITECTURE.md](./ARCHITECTURE.md) — System diagrams
> - [KINGDOM_HISTORY.md](./KINGDOM_HISTORY.md) — Historical evolution
> - [DISCUSSIONS.md](./DISCUSSIONS.md) — Decision log

***

### Purpose

This document defines the **Kingdom Architecture** - a hierarchical multi-agent system enabling on-demand specialist creation. Users request capabilities, the system creates specialists, tracks performance as "unverified," and promotes to "verified" after admin approval.

**Core Principle:** The King (Orchestrator) delegates tasks to Ministers (safeguards) and Specialists (workers). When no specialist exists, the Creation Council assembles to build one.

***

### 1. Kingdom Hierarchy

```
┌────────────────────────────────────────────────────┐
│              KING (Orchestrator Service)            │
│  Analyzes tasks, routes to specialists, triggers   │
│  creation when no match found                      │
└───────────┬────────────────────────────────────────┘
            │
    ┌───────┴────────┐
    │                │
┌───▼────────────┐   │   ┌──────────────────────────┐
│   MINISTERS    │   │   │   CREATION COUNCIL       │
│   (Council)    │   │   │   (Collaborative Team)   │
│                │   │   │                          │
│ Guardian ◄─────┼───┴───┤ spec_designer            │
│ Auditor        │       │ safety_reviewer          │
│ Validator      │       │ test_generator           │
│                │       │ trainer_agent            │
└────────────────┘       └──────────────────────────┘
        │
        │ approves
        ▼
┌────────────────────────────────────────────────────┐
│              SPECIALISTS (Workers)                  │
│                                                    │
│ Verified: code_writer, video_planner, [8 total]   │
│ Unverified: [user-created, pending promotion]     │
└────────────────────────────────────────────────────┘
```

***

### 2. Agent Role Definitions

#### King Layer

**orchestrator_service** (New microservice, wraps `conversation_service`)

- **Purpose:** Main routing intelligence - decides specialist assignment or creation
- **Capabilities:**
  - Analyzes task complexity and frequency using LLM[7]
  - Semantic search across verified + unverified specialists
  - Triggers Creation Council when justified
  - Routes to fallback for trivial tasks
- **Dependencies:** All ministers, all specialists (read access)
- **Location:** `backend/orchestrator/services/orchestrator_service.py` (new file)

#### Minister Council

**guardian_minister** (New role)
- **Purpose:** Content safety and dangerous pattern detection
- **Extends:** Your existing `RequestGuard` in `guardrails.py`[1]
- **Blocks:** Code execution, file system access, privilege escalation in specs
- **Output:** `{"verdict": "APPROVED|BLOCKED", "risk_level": "low|medium|high", "reason": "..."}`

**audit_minister** (Rename from `agent_auditor`)
- **Purpose:** Analyzes telemetry for specialist performance patterns
- **New Capability:** Audits proposed specialist specs for quality issues
- **Existing Capability:** Feeds `meta_reasoner` for DNA evolution[1]
- **Migration:** Rename role in `agent_specs.json`, update `AGENT_DEPENDENCIES`

**validator_minister** (New role)
- **Purpose:** Technical validation of specialist specs
- **Checks:** Output schema structure, DNA rule clarity, dependency cycles
- **Output:** `{"verdict": "VALID|INVALID", "issues": [...], "suggestions": [...]}`

#### Creation Council (Collaborative Team)

Executes as a **pipeline** using your existing `pipeline_executor.py`:[1]

```python
PREDEFINED_PIPELINES = {
    # ... existing pipelines
    "specialist_creation": [
        "spec_designer",       # Designs agent spec from user requirements
        "safety_reviewer",     # Calls guardian_minister for approval
        "validator_minister",  # Technical validation
        "test_generator",      # Creates test cases
        # trainer_agent runs separately after user provides resources
    ]
}
```

**spec_designer**
- **Input:** Task analysis from orchestrator
- **Output:** Complete `AgentSpec` structure (role, purpose, dna_rules, output_schema)
- **Uses:** LLM to generate spec, `memory_selector` to check duplicates[1]

**safety_reviewer**
- **Input:** Spec proposal from `spec_designer`
- **Output:** Safety verdict from `guardian_minister`
- **Blocks:** Dangerous capabilities, injection patterns

**test_generator**
- **Input:** Validated spec
- **Output:** Test suite `[{"input": "...", "expected_output": "..."}]`
- **Uses:** LLM to generate realistic test cases based on purpose

**trainer_agent** (Runs separately, not in pipeline)
- **Input:** Spec + test suite + user-provided resources (API keys)
- **Execution:** Sandboxed Docker container[5][2]
- **Output:** Training results with avg confidence score
- **Approval Gate:** If `avg_confidence < 0.75`, reject creation

***

### 3. Specialist Lifecycle

```
┌──────────────┐
│ User Request │
└──────┬───────┘
       │
       ▼
┌─────────────────────────┐
│ Orchestrator Analyzes   │
│ - Complexity?           │
│ - Frequency?            │
│ - Existing match?       │
└──────┬──────────────────┘
       │
       ├─ Match found → Execute existing specialist
       │
       ├─ Trivial → Fallback to general agent
       │
       └─ No match + justified → Trigger Creation Council
                                  │
                                  ▼
                        ┌──────────────────────┐
                        │ Creation Pipeline    │
                        │ 1. Design spec       │
                        │ 2. Safety review     │
                        │ 3. Validate          │
                        │ 4. Generate tests    │
                        └──────┬───────────────┘
                               │
                               ▼
                        ┌──────────────────────┐
                        │ User Approval Dialog │
                        │ - Show spec summary  │
                        │ - Request resources  │
                        │ - Confirm creation   │
                        └──────┬───────────────┘
                               │
                               ▼
                        ┌──────────────────────┐
                        │ Sandboxed Training   │
                        │ - Run tests          │
                        │ - Record metrics     │
                        │ - Confidence check   │
                        └──────┬───────────────┘
                               │
                               ├─ Success → Register as UNVERIFIED
                               └─ Failure → Reject with explanation
                                            │
                                            ▼
                        ┌─────────────────────────────┐
                        │ Unverified Specialist Active │
                        │ - User-scoped execution      │
                        │ - Telemetry recorded         │
                        │ - Admin dashboard shows      │
                        └──────┬──────────────────────┘
                               │
                               │ (After N successful executions)
                               ▼
                        ┌──────────────────────┐
                        │ Admin Reviews        │
                        │ - Telemetry analysis │
                        │ - Quality assessment │
                        │ - Promote to VERIFIED│
                        └──────┬───────────────┘
                               │
                               ▼
                        ┌──────────────────────┐
                        │ Verified Specialist  │
                        │ - Global scope       │
                        │ - Reusable by all    │
                        └──────────────────────┘
```

***

### 4. Database Schema Extensions

**New Tables:**

```sql
-- Stores all dynamic specialists (user-created)
CREATE TABLE dynamic_agents (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    role VARCHAR(100) UNIQUE NOT NULL,
    created_by VARCHAR(255) NOT NULL,  -- user_id
    spec_snapshot JSONB NOT NULL,      -- Full agent_spec
    status VARCHAR(50) DEFAULT 'unverified',  -- unverified | verified | deprecated
    scope VARCHAR(50) DEFAULT 'user',  -- user | global
    execution_count INT DEFAULT 0,
    success_count INT DEFAULT 0,
    avg_confidence FLOAT,
    admin_approved_by VARCHAR(255),
    admin_approved_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    last_used_at TIMESTAMPTZ
);

-- User approval state machine
CREATE TABLE specialist_approvals (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id VARCHAR(255) NOT NULL,
    spec_proposal JSONB NOT NULL,
    test_suite JSONB NOT NULL,
    state VARCHAR(50) DEFAULT 'awaiting_confirmation',  
    -- awaiting_confirmation | awaiting_resources | training | completed | rejected
    provided_resources JSONB,  -- API keys, encrypted
    training_results JSONB,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    expires_at TIMESTAMPTZ DEFAULT NOW() + INTERVAL '10 minutes'
);

-- Per-user encrypted secrets
CREATE TABLE user_credentials (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id VARCHAR(255) NOT NULL,
    specialist_role VARCHAR(100) NOT NULL,
    credential_key VARCHAR(100) NOT NULL,  -- e.g., "twilio_api_key"
    encrypted_value TEXT NOT NULL,
    encryption_key_id VARCHAR(100),  -- KMS key reference
    created_at TIMESTAMPTZ DEFAULT NOW(),
    expires_at TIMESTAMPTZ,
    UNIQUE(user_id, specialist_role, credential_key)
);

CREATE INDEX idx_dynamic_agents_status ON dynamic_agents(status, scope);
CREATE INDEX idx_dynamic_agents_user ON dynamic_agents(created_by);
CREATE INDEX idx_specialist_approvals_user_state ON specialist_approvals(user_id, state);
```

***

### 5. Intent Detection: AI-Powered Routing

**Current Problem:** Fixed regex patterns in `conversation_service.py`[1]

```python
# OLD APPROACH (Remove this)
INTENT_PATTERNS = {
    Intent.GENERATE_CODE: [r"(create|generate|write).*code"],
    Intent.GENERATE_VIDEO: [r"(create|make|generate).*video"],
    # ... hardcoded patterns
}
```

**New Approach:** Semantic similarity using LLM embeddings[6][7]

```python
# NEW APPROACH (AI-powered)
async def detect_intent_ai(self, message: str, user_id: str) -> dict:
    """
    Use LLM + embeddings for intent classification
    """
    # Step 1: Check verified specialists first (fast semantic search)
    verified_match = await self._search_verified_specialists(message)
    if verified_match and verified_match["similarity"] > 0.85:
        return {
            "intent": f"specialist:{verified_match['role']}",
            "agent": verified_match["role"],
            "confidence": verified_match["similarity"]
        }
    
    # Step 2: Check user's unverified specialists
    unverified_match = await self._search_user_specialists(message, user_id)
    if unverified_match and unverified_match["similarity"] > 0.80:
        return {
            "intent": f"specialist:{unverified_match['role']}",
            "agent": unverified_match["role"],
            "confidence": unverified_match["similarity"],
            "scope": "user"
        }
    
    # Step 3: LLM analyzes if creation is justified
    analysis = await self._analyze_task_with_llm(message)
    # Returns: {
    #   "complexity": "low|medium|high",
    #   "frequency": "one_time|occasional|frequent",
    #   "required_capabilities": [...],
    #   "should_create_specialist": true/false
    # }
    
    if analysis["should_create_specialist"]:
        return {"intent": "create_specialist", "analysis": analysis}
    
    # Step 4: Fallback to general-purpose agent
    return {"intent": "general", "analysis": analysis}
```

**Implementation:**
- Use Gemini's embedding API for semantic search
- Store agent purposes as embeddings in `agent_embeddings` table
- Recompute embeddings when new specialists verified

***

### 6. Sandboxed Execution (Security Critical)

**Requirement:** Safely test unverified specialists without risking system[3][2][5]

**Implementation Pattern:**

```python
# backend/orchestrator/services/sandbox_executor.py

import docker
from typing import Optional

class SandboxExecutor:
    """
    Docker-based sandbox for testing unverified agents
    """
    
    RESOURCE_LIMITS = {
        "mem_limit": "256m",
        "cpu_quota": 50000,  # 50% of one core
        "pids_limit": 50,
        "execution_timeout": 30  # seconds
    }
    
    def create_sandbox(self, sandbox_id: str) -> str:
        """Create isolated Python environment"""
        client = docker.from_env()
        container = client.containers.run(
            image="python:3.11-slim",
            name=f"specialist-sandbox-{sandbox_id}",
            command="tail -f /dev/null",
            detach=True,
            mem_limit=self.RESOURCE_LIMITS["mem_limit"],
            cpu_quota=self.RESOURCE_LIMITS["cpu_quota"],
            pids_limit=self.RESOURCE_LIMITS["pids_limit"],
            security_opt=["no-new-privileges"],
            cap_drop=["ALL"],  # Drop all Linux capabilities
            network_mode="none",  # No network access
            read_only=True,  # Read-only filesystem
            user="nobody"  # Non-root user
        )
        return container.id
    
    def execute_test(
        self,
        sandbox_id: str,
        test_case: dict,
        agent_spec: dict
    ) -> dict:
        """
        Execute single test case in sandbox
        Returns: {"success": bool, "output": str, "confidence": float}
        """
        client = docker.from_env()
        container = client.containers.get(f"specialist-sandbox-{sandbox_id}")
        
        # Generate test execution code
        test_code = self._generate_test_code(test_case, agent_spec)
        
        try:
            # Execute with timeout
            exec_result = container.exec_run(
                cmd=["python", "-c", test_code],
                user="nobody",
                demux=True,
                timeout=self.RESOURCE_LIMITS["execution_timeout"]
            )
            
            # Parse output
            output = exec_result.output.decode() if exec_result.output else ""
            return self._parse_test_result(output, test_case["expected_output"])
            
        except docker.errors.ContainerError as e:
            return {"success": False, "error": "Container error", "output": str(e)}
        except TimeoutError:
            return {"success": False, "error": "Execution timeout"}
    
    def cleanup_sandbox(self, sandbox_id: str):
        """Destroy sandbox after testing"""
        client = docker.from_env()
        try:
            container = client.containers.get(f"specialist-sandbox-{sandbox_id}")
            container.stop()
            container.remove()
        except docker.errors.NotFound:
            pass
```

**Security Guarantees:**
- No network access (network_mode="none")
- Read-only filesystem (read_only=True)
- Capability dropping (cap_drop=["ALL"])
- Resource limits (CPU, memory, processes)
- Non-root execution (user="nobody")
- Timeout enforcement (30 seconds max)

***

### 7. User Secret Management

**Problem:** Users provide API keys for specialists (e.g., Twilio for SMS agent)[9][8]

**Solution:** Encrypted storage with field-level encryption

```python
# backend/orchestrator/services/credential_manager.py

from cryptography.fernet import Fernet
import os

class CredentialManager:
    """
    Manage per-user encrypted credentials
    """
    
    def __init__(self):
        # In production: Use AWS KMS, Google Secret Manager, or HashiCorp Vault
        self.encryption_key = os.getenv("CREDENTIAL_ENCRYPTION_KEY")
        self.cipher = Fernet(self.encryption_key.encode())
    
    def store_credential(
        self,
        user_id: str,
        specialist_role: str,
        credential_key: str,
        credential_value: str
    ) -> str:
        """
        Encrypt and store user credential
        """
        encrypted = self.cipher.encrypt(credential_value.encode())
        
        supabase.table("user_credentials").upsert({
            "user_id": user_id,
            "specialist_role": specialist_role,
            "credential_key": credential_key,
            "encrypted_value": encrypted.decode(),
            "encryption_key_id": "primary"  # KMS key ID in production
        }).execute()
        
        return "stored"
    
    def retrieve_credential(
        self,
        user_id: str,
        specialist_role: str,
        credential_key: str
    ) -> Optional[str]:
        """
        Decrypt and retrieve credential
        """
        result = supabase.table("user_credentials")\
            .select("encrypted_value")\
            .eq("user_id", user_id)\
            .eq("specialist_role", specialist_role)\
            .eq("credential_key", credential_key)\
            .execute()
        
        if not result.data:
            return None
        
        encrypted = result.data[0]["encrypted_value"].encode()
        decrypted = self.cipher.decrypt(encrypted)
        return decrypted.decode()
```

**Production Hardening:**
- Use managed secret services (AWS Secrets Manager, Google Secret Manager)
- Rotate encryption keys periodically
- Audit credential access
- Enforce expiration policies

***

### 8. Migration Path from Current System

**Phase 1: Rename & Extend Ministers** (Week 1)

Tasks:
1. Rename `agent_auditor` → `audit_minister` in `agent_specs.json`
2. Update all references in `AGENT_DEPENDENCIES`
3. Add guardian_minister and validator_minister specs
4. Test existing workflows still function

**Phase 2: Build Orchestrator Wrapper** (Week 2)

Tasks:
1. Create `orchestrator_service.py` (wraps `conversation_service`)
2. Implement `detect_intent_ai()` - LLM-based intent detection
3. Add specialist matcher with semantic search
4. Route to existing agents (no creation yet)

**Phase 3: Creation Council Pipeline** (Week 3)

Tasks:
1. Define 4 Creation Council agents in `agent_specs.json`
2. Add `specialist_creation` pipeline to `PREDEFINED_PIPELINES`
3. Implement approval state machine in `specialist_approvals` table
4. Build user dialog flow for approvals

**Phase 4: Sandbox & Training** (Week 4)

Tasks:
1. Implement `SandboxExecutor` with Docker
2. Add `trainer_agent` that uses sandbox
3. Test with one simple specialist (email validator)
4. Validate telemetry capture for unverified agents

**Phase 5: Secret Management** (Week 5)

Tasks:
1. Implement `CredentialManager` with encryption
2. Add `user_credentials` table migration
3. Integrate credential injection during training
4. Test with specialist requiring API key

**Phase 6: Admin Promotion Workflow** (Week 6)

Tasks:
1. Build admin dashboard UI for unverified agents
2. Show telemetry: execution_count, success_rate, avg_confidence
3. Implement promotion endpoint (unverified → verified)
4. Update orchestrator to prioritize verified agents

***

### 9. Critical Implementation Rules

**DO:**
- ✅ Reuse existing `pipeline_executor.py` for Creation Council[1]
- ✅ Reuse existing `dna_mutator.py` patterns for validation[1]
- ✅ Leverage `memory_selector` to detect duplicate specialists[1]
- ✅ Use `retriever_agent` for pulling API docs during spec design[1]
- ✅ Record telemetry for every unverified agent execution[1]
- ✅ Run `run_dependency_health_check()` before registering specialists[1]
- ✅ Call `AgentFactory.reload()` after registration[1]

**DON'T:**
- ❌ Bypass sandbox execution for unverified agents
- ❌ Store plaintext credentials in database
- ❌ Auto-verify specialists without admin approval
- ❌ Allow unverified agents global scope (user-only)
- ❌ Skip Creation Council safety reviews
- ❌ Create specialists for one-time tasks
- ❌ Ignore resource limits in sandbox

***

### 10. Open Questions for Team Discussion

**Q1: Embedding Storage Strategy**
- Store agent purpose embeddings in PostgreSQL with pgvector extension?
- Or use external vector DB (Pinecone, Weaviate)?

**Q2: Specialist Deprecation Policy**
- Auto-deprecate unverified agents after N days of inactivity?
- Or require explicit user deletion?

**Q3: Verification Threshold**
- How many successful executions before eligible for admin review?
- Should confidence score factor into eligibility?

**Q4: Resource Request UX**
- Ask for API keys upfront (before training)?
- Or allow "test without credentials" mode with mock responses?

**Q5: Multi-Tenancy for Verified Agents**
- Can users customize verified agents (fork + modify)?
- Or are verified agents immutable for all users?

***

### 11. Developer Workflow

**Adding New Ministry Features:**
1. Search this document for relevant section
2. Update architecture diagrams if structure changes
3. Implement following existing patterns (pipeline, factory, telemetry)
4. Add telemetry tracking for new components
5. Update this document with implementation details
6. Submit PR with "Kingdom:" prefix in title

**Testing New Specialists:**
1. Use sandbox_executor for all unverified agent tests
2. Verify telemetry recording in `task_telemetry` table
3. Check admin dashboard shows new agent correctly
4. Confirm dependency health check passes

**Promoting to Verified:**
1. Review telemetry: `execution_count >= 50`, `success_rate >= 90%`, `avg_confidence >= 0.80`
2. Manual review of spec for quality
3. Run full test suite in sandbox
4. Update `status = 'verified'`, `scope = 'global'`
5. Notify all users of new verified specialist

***

### 12. Document Maintenance Protocol

**This is a LIVING DOCUMENT - update after every Kingdom feature ship**

**When to Update:**
- New agent roles added to hierarchy
- Database schema changes
- Security patterns changed
- Pipeline definitions modified
- API endpoints added/changed
- Questions answered → move to decisions

**Update Process:**
1. Developer makes implementation changes
2. Update relevant KINGDOM.md sections
3. Add "Updated KINGDOM.md" line in PR description
4. Reviewer validates doc matches code
5. Merge only if both code AND docs updated

**Review Schedule:**
- Weekly: Team reviews "Open Questions" section
- Monthly: Architecture diagram accuracy check
- Quarterly: Full document audit for stale content

***

### 13. References

**Internal Documents:**
- `CLAUDE.md` - Main platform reference[1]
- `backend/orchestrator/agents/agent_specs.json` - Agent definitions[1]
- `backend/orchestrator/services/agent_dependencies.py` - Dependency map[1]

**External Research:**
- Hierarchical Multi-Agent Systems: AgentOrchestra[10][11]
- Sandboxed Execution: Python Sandbox for LLMs[4][2][5]
- AI-Powered Routing: Semantic Router patterns[7][6]
- Secret Management: FastAPI Authentication[8][9]

**Implementation Examples:**
- Docker Sandbox:  (Hugging Face secure execution)[5]
- Multi-Agent Orchestration:  (Research paper implementation)[10]

***