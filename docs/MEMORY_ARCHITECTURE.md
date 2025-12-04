# KING Memory Architecture

> Session Date: 2024-12-04
> Status: Implemented ✅
> KING Internal Version: 1.0

## Executive Summary

This document captures the complete memory architecture redesign session where we:
1. Analyzed Mem0 Platform native capabilities (as of Dec 2024)
2. Identified and removed redundant custom extraction code
3. Implemented a Smart Memory Orchestrator with zero hardcoding
4. Aligned KING's 5-tier memory system with Mem0 Platform's native layers

> **Note:** Version numbers in this doc (e.g., "KING Memory v1.0") are KING internal versions, not Mem0 official versions. Mem0 Platform has its own versioning (v2 filters, etc.).

---

## Problem Statement

### Before: Redundant Extraction Pipeline

The gateway was making **3-4 LLM calls per message** for memory operations:
1. `_extract_memory_metadata()` - Category extraction
2. `_extract_entities_dynamic()` - Entity extraction
3. `_extract_topics()` - Topic tagging
4. `_assess_importance()` - Importance heuristics (hardcoded!)

**Issues:**
- ~1.5s latency overhead per message
- Mem0 Platform already handles categorization, entity extraction, and graph relationships natively
- Hardcoded skip rules like `if msg in ['hi', 'hello', 'ok']` - not context-aware

### User's Core Requirement

> "No hardcoding. The message receiver itself is an agent. Let it decide. 'Hi' after 2 days vs 'Hi' mid-conversation should be handled differently. That's what smart means."

---

## Solution: Smart Memory Orchestrator

### Architecture

```
User Message
     ↓
┌─────────────────────────────────────────────────────────────┐
│ MEMORY ORCHESTRATOR (LLM-powered, NO hardcoding)           │
│                                                             │
│ Context Provided:                                           │
│ - Time gap: "2 days ago" / "just now" / "first interaction"│
│ - Memory summary: Recent memories for context               │
│ - Session context: Last few conversation turns              │
│                                                             │
│ AI Decision Output:                                         │
│ {                                                           │
│   "should_store": true/false,                               │
│   "reasoning": "why",                                       │
│   "memories": [{                                            │
│     "content": "what to remember",                          │
│     "layer": "user|session|kingdom",                        │
│     "enable_graph": true/false,                             │
│     "importance": 0.1-1.0                                   │
│   }]                                                        │
│ }                                                           │
└─────────────────────────────────────────────────────────────┘
     ↓
MEM0 PLATFORM
(auto: entity extraction, categorization, deduplication, graph relationships)
```

### Decision Examples

| Message | Context | Decision |
|---------|---------|----------|
| "Hi" | After 2 days gap | Store "User returned after 2 days" to session |
| "Hi" | Mid-conversation | Skip (just acknowledgment) |
| "I prefer dark mode" | Any | Store preference to user memory |
| "The project is called Apollo" | Any | Store with `enable_graph=true` |
| "ok" / "thanks" | Mid-conversation | Skip (no value) |
| "Remember: always use TypeScript" | Any | Store to user memory (explicit instruction) |

---

## Mem0 Platform Memory Layers

> Reference: [docs.mem0.ai/core-concepts/memory-types](https://docs.mem0.ai/core-concepts/memory-types) (Dec 2024)

### Mem0 Native Layers

| Layer | Scope | Persistence | Use Case |
|-------|-------|-------------|----------|
| **Conversation** | In-flight | Turn only | Current message context |
| **Session** | `session_id` | Session duration | Short-term task context |
| **User** | `user_id` | Forever | Long-term preferences, facts |
| **Organization** | `org_id` | Forever | Shared knowledge across users |

### KING Layers → Mem0 Mapping

| KING Layer | Mem0 Layer | Mem0 Identifier | Graph |
|------------|------------|-----------------|-------|
| WORKING | Conversation | In-memory only | No |
| EPISODIC | Session | `session_id={sid}` | No |
| SEMANTIC | User | `user_id={uid}` | No |
| LINEAGE | Agent | `user_id=agent:{name}` | No |
| COLLECTIVE | Organization | `user_id='__kingdom__'` | **Yes** |

---

## Files Modified

### 1. `king/gateway/memory/reflection.py`

**Added:** `orchestrate_memory()` - The smart memory orchestrator

```python
async def orchestrate_memory(
    user_id: str,
    session_id: str,
    user_message: str,
    assistant_response: str,
    memory_summary: Optional[str] = None,
    session_context: Optional[str] = None
) -> Dict[str, Any]:
    """
    Smart Memory Orchestrator - AI decides what to remember.
    No hardcoding. The LLM receives full context and decides.
    """
```

**Added:** `MEMORY_ORCHESTRATOR_PROMPT` - Context-aware prompt with:
- Identity: "You are KING's Memory Orchestrator 🧠"
- Capabilities: Store to user/session/kingdom, enable graph
- Context: Time gap, memory summary, session turns
- Decision framework: Questions to consider
- Examples: Concrete decision patterns

**Changed:** `reflect_on_run()` - Now only processes errors (success cases handled by orchestrator)

**Added:** `reflect_on_error()` - Dedicated error learning function

### 2. `king/gateway/memory/types.py`

**Added:** `MemoryLayer` enum aligned with Mem0:
```python
class MemoryLayer(str, Enum):
    CONVERSATION = "conversation"  # In-flight, in-memory only
    SESSION = "session"            # Short-term, session_id scoped
    USER = "user"                  # Long-term, user_id scoped
    AGENT = "agent"                # Agent-specific learning
    KINGDOM = "kingdom"            # Shared across all, graph-enabled
```

**Updated:** `MEMORY_CONFIGS` to include `mem0_layer` mapping


## Performance Impact

| Metric | Before | After |
|--------|--------|-------|
| LLM calls per message | 3-4 | 0-1 |
| Latency overhead | ~1.5s | ~200ms (only when storing) |
| Code complexity | High (~130 lines extraction) | Low (delegated to Mem0) |
| Memory quality | Manual extraction | Mem0 native + AI decision |
| Context awareness | None (hardcoded rules) | Full (time gap, history, session) |

---

## Key Design Principles

### 1. No Hardcoding
Every decision is AI-powered with full context. No `if msg == 'hi': skip`.

### 2. Delegate to Mem0
Let the platform handle what it's good at:
- Entity extraction (via `enable_graph=True`)
- Auto-categorization
- Deduplication
- Relationship graphs

### 3. Store Broadly, Filter at Retrieval
2025 best practice: Don't over-filter at storage time. Let retrieval do the work with:
- Semantic search
- Keyword matching
- Reranking
- Metadata filters

### 4. Context is King
The orchestrator receives:
- **Time gap**: First interaction? Just now? 2 days ago?
- **Memory summary**: What does the user already have stored?
- **Session context**: What's the current conversation about?

---

## Usage

### Storing Memory (Automatic)
Memory storage happens automatically after each conversation turn via `_store_memory()` in `agent_factory.py`.

### Error Learning (Automatic)
When an agent fails, `reflect_on_error()` is called to extract lessons.

### Manual Memory Add
```python
from memory.reflection import orchestrate_memory

result = await orchestrate_memory(
    user_id="tg_123456",
    session_id="session_abc",
    user_message="Remember: I prefer Python over JavaScript",
    assistant_response="Got it! I'll remember your preference for Python.",
    memory_summary="User works on KING project...",
    session_context="Discussing language preferences..."
)
# result: {"stored": True, "count": 1, "reasoning": "Explicit preference stated"}
```

---

## Memory Resolution Order

When retrieving memories, KING resolves in this order (most specific first):

```
WORKING (in-memory session)
    ↓
EPISODIC (session_id scoped)
    ↓
SEMANTIC (user_id scoped, long-term)
    ↓
LINEAGE (agent-specific learning)
    ↓
COLLECTIVE (kingdom-wide, graph-enabled)
```

---

## Related Files

| File | Purpose |
|------|---------|
| `memory/reflection.py` | Memory Orchestrator + Error Reflection |
| `memory/types.py` | Memory type definitions, Mem0 layer mapping |
| `memory/taxonomy.py` | Dynamic taxonomies (categories, intents, entities) |
| `memory/fingerprint.py` | Context fingerprinting for user profiles |
| `agent_factory.py` | Main gateway with `_store_memory()` integration |

---

## Future Enhancements

1. **Memory Index for Orchestrator**: Instead of full memory summary, provide a lightweight index that the orchestrator can "dive deep" into if needed.

2. **Orchestrator → Driver Pattern**: The orchestrator knows WHO to call (which memory layer), the driver (Mem0) knows HOW to store.

3. **Tool Integration**: As we add web scraping, sandbox, etc., the orchestrator decides which tools to invoke and delegates to specialist drivers.

---

## References

- [Mem0 Documentation](https://docs.mem0.ai)
- [Mem0 Memory Types](https://docs.mem0.ai/core-concepts/memory-types)
- [Mem0 v2 Filters](https://docs.mem0.ai/platform/features/v2-memory-filters)
- [Anthropic Memory Patterns](https://www.anthropic.com/research) - Store broadly, filter at retrieval
