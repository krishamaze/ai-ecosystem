"""
KING Agent Factory - AI-powered on-demand agent spawning.
No hardcoded agent types. KING creates what it needs.
Supports agent reuse and team collaboration.
"""
import os
import json
import asyncio
from typing import Dict, Any, Optional, List
import google.generativeai as genai

# Lazy initialization to avoid import-time failures
_factory_model = None


def _get_factory_model():
    """Lazy init for Gemini factory model."""
    global _factory_model
    if _factory_model is None:
        api_key = os.getenv("GEMINI_API_KEY")
        if api_key:
            genai.configure(api_key=api_key.strip())
            _factory_model = genai.GenerativeModel("gemini-2.0-flash-exp")
        else:
            print("Warning: GEMINI_API_KEY not set. Agent Factory disabled.")
            _factory_model = False  # Mark as failed
    return _factory_model if _factory_model else None

# In-memory agent cache (task_hash -> agent_spec)
_agent_cache: Dict[str, Dict[str, Any]] = {}

# In-memory session history (session_id -> list of recent messages)
# Format: [{role: "user"/"assistant", "content": "..."}]
_session_history: Dict[str, List[Dict[str, str]]] = {}
MAX_SESSION_HISTORY = 10  # Keep last 10 messages per session

ROUTER_PROMPT_TEMPLATE = """You are KING 👑, a humanlike AI assistant with memory. You have specialist agents - each with ONE focused role.

User Message: {task_description}
User Memory: {user_memory}
User Contexts (projects, roles): {user_contexts}
Session Context: {session_memory}
Available Specialists: {existing_agents}

KNOWN INTENTS: {known_intents}
KNOWN ACTIONS: {known_actions}

CORE PRINCIPLES:
1. YOU are the conversationalist - specialists ONLY execute clear tasks
2. Each specialist has ONE role - don't blend responsibilities
3. Users have MULTIPLE projects/roles - disambiguate before assuming
4. Long tasks run ASYNC - user gets notified when done

TASK CLASSIFICATION:
- SYNC: greetings, simple questions, quick code (<30 lines), clarifications
- ASYNC: video creation, data analysis, complex reviews, document generation, multi-file changes

DECISION FLOW:
1. GREET: greeting/casual → respond warmly
2. DISAMBIGUATE: "my project" but multiple known → ask which one
3. CLARIFY: vague request → ask specifically what they need
4. EXECUTE_SYNC: clear + simple → delegate, wait for result
5. EXECUTE_ASYNC: clear + complex → delegate to background, inform user

Respond ONLY with valid JSON:
{{
    "action": "from known_actions or suggest new",
    "intent": "from known_intents or suggest new",
    "response": "Your conversational response",
    "execution_mode": "sync|async",
    "execute_agent": "agent_name or null",
    "matched_context": "context_id or null",
    "context_confidence": 0.0-1.0,
    "needs_clarification": true/false,
    "clarification_questions": ["q1"] or null,
    "new_context_detected": {{"type": "project|role", "name": "...", "attributes": {{}}}} or null,
    "memory_used": ["facts used"],
    "reasoning": "brief reasoning"
}}

EXAMPLES:
User: "write fibonacci" → {{"action":"execute","intent":"generate_code","execution_mode":"sync","execute_agent":"code_writer","response":"On it!"}}
User: "create a promo video for my startup" → {{"action":"execute","intent":"generate_video","execution_mode":"async","execute_agent":"video_planner","response":"I'll start working on that! 🎬"}}
User: "my project" (2 known) → {{"action":"clarify","intent":"clarify","response":"Which project - the Python API or React dashboard?"}}
"""

FACTORY_PROMPT = """You are KING's Agent Factory. Design an agent for this task.

Task Description: {task_description}
User Context: {user_context}
Available Tools: {available_tools}

Create an agent specification. Consider:
- What role/expertise is needed
- What rules should govern behavior
- What output structure is expected
- Estimated complexity

Respond ONLY with valid JSON:
{{
    "agent_name": "snake_case_name",
    "purpose": "One-line purpose statement",
    "system_prompt": "You are a [role]. Your job is to...",
    "dna_rules": [
        "Rule 1: specific behavior",
        "Rule 2: constraint"
    ],
    "output_schema": {{
        "result": "type",
        "confidence": "float"
    }},
    "tools_needed": [],
    "complexity": "low|medium|high",
    "reasoning": "Why this design fits the task"
}}
"""


class EphemeralAgent:
    """An on-demand agent created by KING for a specific task."""
    
    def __init__(self, spec: Dict[str, Any]):
        self.name = spec.get("agent_name", "ephemeral_agent")
        self.purpose = spec.get("purpose", "")
        self.system_prompt = spec.get("system_prompt", "")
        self.dna_rules = spec.get("dna_rules", [])
        self.output_schema = spec.get("output_schema", {})
        self.complexity = spec.get("complexity", "medium")
        self._spec = spec
    
    async def execute(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
        """Execute the ephemeral agent's task."""
        model = _get_factory_model()
        if not model:
            return {"error": "Gemini not configured", "confidence": 0}

        rules_text = "\n".join(f"- {r}" for r in self.dna_rules)
        schema_text = json.dumps(self.output_schema, indent=2)

        prompt = f"""{self.system_prompt}

DNA Rules:
{rules_text}

Input: {json.dumps(input_data)}

Respond with JSON matching this schema:
{schema_text}
"""
        try:
            response = await asyncio.to_thread(
                model.generate_content,
                prompt
            )
            text = response.text.strip()
            if text.startswith("```json"):
                text = text[7:]
            if text.startswith("```"):
                text = text[3:]
            if text.endswith("```"):
                text = text[:-3]
            return json.loads(text.strip())
        except Exception as e:
            return {"error": str(e), "confidence": 0}
    
    def to_dict(self) -> Dict[str, Any]:
        return self._spec


def _parse_json(text: str) -> Dict:
    """Extract JSON from LLM response, handling text before/after JSON blocks."""
    import re
    text = text.strip()

    # Try 1: Extract from ```json ... ``` block (LLM often wraps JSON)
    json_block = re.search(r'```json\s*([\s\S]*?)\s*```', text)
    if json_block:
        return json.loads(json_block.group(1).strip())

    # Try 2: Extract from ``` ... ``` block
    code_block = re.search(r'```\s*([\s\S]*?)\s*```', text)
    if code_block:
        candidate = code_block.group(1).strip()
        if candidate.startswith('{'):
            return json.loads(candidate)

    # Try 3: Find first { ... } in text (outermost JSON object)
    brace_match = re.search(r'\{[\s\S]*\}', text)
    if brace_match:
        return json.loads(brace_match.group(0))

    # Try 4: Raw parse (already clean JSON)
    return json.loads(text)


def _task_hash(task: str) -> str:
    """Normalize task to find similar cached agents."""
    import hashlib
    words = sorted(set(task.lower().split()))[:10]
    return hashlib.md5(" ".join(words).encode()).hexdigest()[:12]


async def get_existing_agents_with_descriptions() -> Dict[str, str]:
    """Get dict of registered agent names -> descriptions."""
    agents = {}
    # Add cached agents with their purposes
    for name, spec in _agent_cache.items():
        agents[name] = spec.get("purpose", "Ephemeral agent - no description")

    try:
        from state_manager import StateManager
        sm = StateManager()
        client = sm.get_client()
        if client:
            resp = client.table("agent_registry").select("agent_name, description").eq("status", "active").execute()
            for r in (resp.data or []):
                agents[r["agent_name"]] = r.get("description") or "No description available"
    except Exception:
        pass
    return agents


async def get_existing_agents() -> List[str]:
    """Get list of registered + cached agent names (backward compat)."""
    agents_dict = await get_existing_agents_with_descriptions()
    return list(agents_dict.keys())


async def get_registered_agent_url(agent_name: str) -> Optional[str]:
    """Get service URL for a registered agent. Returns None if not found."""
    try:
        from state_manager import StateManager
        sm = StateManager()
        return sm.get_agent_url(agent_name)
    except Exception:
        return None


def _normalize_request_for_agent(agent_name: str, input_data: Dict[str, Any]) -> Dict[str, Any]:
    """Transform generic input_data to agent-specific request format."""
    # Extract task from various possible fields
    task = input_data.get("query") or input_data.get("task") or input_data.get("message") or str(input_data)

    # Agent-specific transformations matching actual service schemas
    if agent_name in ("code_writer", "code-writer"):
        return {"task": task, "language": input_data.get("language", "python"), "context": input_data.get("context")}
    elif agent_name in ("script_writer", "script-writer"):
        # script_writer expects: topic, target_audience, key_message, tone, duration_seconds
        return {
            "topic": input_data.get("topic", task),
            "target_audience": input_data.get("target_audience", "general audience"),
            "key_message": input_data.get("key_message", task),
            "tone": input_data.get("tone", "professional"),
            "duration_seconds": input_data.get("duration_seconds", 60),
            "context": input_data.get("context")
        }
    elif agent_name in ("code_reviewer", "code-reviewer"):
        return {"code": input_data.get("code", task), "language": input_data.get("language", "python")}
    elif agent_name in ("video_planner", "video-planner"):
        # video_planner expects: user_input, known_context, missing_fields
        return {
            "user_input": task,
            "known_context": input_data.get("known_context", {}),
            "missing_fields": input_data.get("missing_fields", ["topic", "target_audience", "key_message", "tone"]),
            "context": input_data.get("context")
        }
    elif agent_name in ("memory_selector", "memory-selector"):
        return {"query": task, "candidate_memories": input_data.get("candidate_memories", []), "context": input_data.get("context")}
    else:
        # Fallback: pass task as primary field
        return {"task": task, **{k: v for k, v in input_data.items() if k not in ("query", "task", "message")}}


async def call_registered_agent(agent_name: str, input_data: Dict[str, Any]) -> Dict[str, Any]:
    """Call a registered agent service via HTTP."""
    import httpx
    service_url = await get_registered_agent_url(agent_name)
    if not service_url:
        raise ValueError(f"Agent '{agent_name}' not registered or inactive")

    # Normalize request to match agent's expected schema
    normalized = _normalize_request_for_agent(agent_name, input_data)

    async with httpx.AsyncClient(timeout=60.0) as client:
        response = await client.post(f"{service_url}/execute", json=normalized)
        response.raise_for_status()
        return response.json()


# Lazy Mem0 client
_mem0_client = None


def _get_mem0_client():
    """Lazy init for Mem0 client."""
    global _mem0_client
    if _mem0_client is None:
        from mem0 import MemoryClient
        api_key = os.getenv("MEM0_API_KEY")
        if api_key:
            _mem0_client = MemoryClient(api_key=api_key.strip())
        else:
            print("Warning: MEM0_API_KEY not set. Memory disabled.")
            _mem0_client = False
    return _mem0_client if _mem0_client else None


# ============================================================================
# MEMORY STORAGE - Now delegated to Smart Memory Orchestrator
# ============================================================================
# Removed: _extract_memory_metadata, _extract_entities_dynamic, _extract_topics, _assess_importance
# These are now handled by the Memory Orchestrator in memory/reflection.py
# The orchestrator uses Mem0's native capabilities + AI-powered contextual decisions
# ============================================================================


async def _store_memory(
    user_id: str,
    session_id: str,
    user_message: str,
    assistant_response: str,
    metadata: Optional[Dict] = None
) -> bool:
    """
    Store conversation turn using Smart Memory Orchestrator.

    The orchestrator (LLM) decides:
    - Whether to store at all
    - Which layer (user/session/kingdom)
    - Whether to enable graph for entities

    No hardcoded rules. Context-aware decisions.
    """
    from memory.reflection import orchestrate_memory

    # Update in-memory session history first (synchronous, fast)
    if session_id:
        _update_session_history(session_id, user_message, assistant_response)

    if not user_id:
        return False

    try:
        # Get memory summary for context
        memory_summary = await _fetch_user_memory(user_id, user_message)

        # Get session context
        session_context = await _fetch_session_memory(session_id, user_message)

        # Let the orchestrator decide
        result = await orchestrate_memory(
            user_id=user_id,
            session_id=session_id,
            user_message=user_message,
            assistant_response=assistant_response,
            memory_summary=memory_summary,
            session_context=session_context
        )

        return result.get("stored", False)

    except Exception as e:
        print(f"⚠️ Memory orchestrator failed: {e}")
        return False


async def _fetch_user_memory(user_id: str, query: str) -> str:
    """Fetch user memories from Mem0 with graph relationships."""
    if not user_id:
        return "No user context available"

    client = _get_mem0_client()
    if not client:
        return "Memory system unavailable"

    try:
        # Get all user memories with v2 API - must use filters dict
        result = await asyncio.to_thread(
            client.get_all,
            filters={"user_id": user_id},
            limit=100
        )
        memories = result.get("results", []) if isinstance(result, dict) else result

        if not memories:
            return "New user - no previous interactions"

        # Format memories with metadata context
        formatted = []
        for m in memories[:7]:
            mem_text = m.get("memory", "")
            meta = m.get("metadata", {})
            if meta.get("category"):
                formatted.append(f"- [{meta['category']}] {mem_text}")
            else:
                formatted.append(f"- {mem_text}")

        return "\n".join(formatted)
    except Exception as e:
        return f"Memory fetch failed: {e}"


def _update_session_history(session_id: str, user_message: str, assistant_response: str):
    """Update in-memory session history with new turn."""
    if not session_id:
        return
    
    if session_id not in _session_history:
        _session_history[session_id] = []
    
    history = _session_history[session_id]
    history.append({"role": "user", "content": user_message})
    history.append({"role": "assistant", "content": assistant_response})
    
    # Keep only last N messages
    if len(history) > MAX_SESSION_HISTORY:
        _session_history[session_id] = history[-MAX_SESSION_HISTORY:]


async def _fetch_session_memory(session_id: str, query: str) -> str:
    """Fetch session context for conversation continuity."""
    if not session_id:
        return "No session context"
    
    # First, check in-memory session history (fast, recent context)
    if session_id in _session_history:
        history = _session_history[session_id]
        if history:
            # Format last few messages for context
            formatted = []
            for msg in history[-5:]:  # Last 5 messages
                role = msg.get("role", "unknown")
                content = msg.get("content", "")[:150]  # Truncate long messages
                formatted.append(f"{role}: {content}")
            return "\n".join(formatted)

    # Fallback: Query Mem0 for deeper history (slower, persistent)
    client = _get_mem0_client()
    if not client:
        return "New session - no prior context"

    try:
        result = await asyncio.to_thread(
            client.get_all,
            filters={"user_id": f"session_{session_id}"},
            limit=50
        )
        memories = result.get("results", []) if isinstance(result, dict) else result

        if not memories:
            return "New session - no prior context"

        # Return recent session memories
        return "\n".join([f"- {m.get('memory', '')}" for m in memories[:5]])
    except Exception as e:
        return f"Session fetch failed: {e}"


async def _fetch_user_contexts_summary(user_id: str) -> str:
    """Fetch user's known contexts (projects, roles, businesses) for disambiguation."""
    if not user_id:
        return "No user context available"

    try:
        from memory.fingerprint import get_context_summary
        return await get_context_summary(user_id)
    except Exception as e:
        return f"Context fetch failed: {e}"


async def smart_route(
    task_description: str,
    user_context: Optional[Dict] = None
) -> Dict[str, Any]:
    """AI decides: reuse existing agent, spawn new, or team up. Uses memory + context fingerprinting + dynamic taxonomies."""
    from memory.taxonomy import get_taxonomy_values, add_taxonomy_value, TaxonomyType

    model = _get_factory_model()
    if not model:
        return {"decision": "spawn", "reasoning": "No LLM available"}

    user_id = (user_context or {}).get("user_id")
    session_id = (user_context or {}).get("session_id")

    # Fetch memories, contexts, and dynamic taxonomies in parallel
    user_mem_task = asyncio.create_task(_fetch_user_memory(user_id, task_description))
    session_mem_task = asyncio.create_task(_fetch_session_memory(session_id, task_description))
    agents_task = asyncio.create_task(get_existing_agents_with_descriptions())
    contexts_task = asyncio.create_task(_fetch_user_contexts_summary(user_id))
    intents_task = asyncio.create_task(get_taxonomy_values(TaxonomyType.INTENT))
    actions_task = asyncio.create_task(get_taxonomy_values(TaxonomyType.ACTION))

    user_memory, session_memory, agents_with_desc, user_contexts, known_intents, known_actions = await asyncio.gather(
        user_mem_task, session_mem_task, agents_task, contexts_task, intents_task, actions_task
    )

    prompt = ROUTER_PROMPT_TEMPLATE.format(
        task_description=task_description,
        user_memory=user_memory,
        user_contexts=user_contexts,
        session_memory=session_memory,
        existing_agents=json.dumps(agents_with_desc, indent=2),
        known_intents=json.dumps(known_intents),
        known_actions=json.dumps(known_actions)
    )

    try:
        response = await asyncio.to_thread(model.generate_content, prompt)
        result = _parse_json(response.text)

        # Check if AI suggested new intent or action - add to taxonomy
        detected_intent = result.get("intent", "")
        detected_action = result.get("action", "")

        if detected_intent and detected_intent not in known_intents:
            await add_taxonomy_value(TaxonomyType.INTENT, detected_intent, f"AI-detected from: {task_description[:100]}", "ai")

        if detected_action and detected_action not in known_actions:
            await add_taxonomy_value(TaxonomyType.ACTION, detected_action, f"AI-detected from: {task_description[:100]}", "ai")

        return result
    except Exception as e:
        return {"decision": "spawn", "reasoning": f"Router error: {e}"}


async def spawn_agent(
    task_description: str,
    user_context: Optional[Dict] = None,
    available_tools: Optional[list] = None,
    force_new: bool = False
) -> EphemeralAgent:
    """KING creates an agent - with smart routing for reuse."""

    # Check cache first (unless forcing new)
    task_key = _task_hash(task_description)
    if not force_new and task_key in _agent_cache:
        print(f"♻️ Reusing cached agent for task hash: {task_key}")
        return EphemeralAgent(_agent_cache[task_key])

    model = _get_factory_model()
    if not model:
        return EphemeralAgent({
            "agent_name": "fallback_agent",
            "purpose": "Handle task with minimal capability",
            "system_prompt": f"Complete this task: {task_description}",
            "dna_rules": ["Be concise", "Return valid JSON"],
            "output_schema": {"result": "string", "confidence": "float"},
            "complexity": "low",
            "reasoning": "Fallback - factory unavailable"
        })

    prompt = FACTORY_PROMPT.format(
        task_description=task_description,
        user_context=json.dumps(user_context or {}),
        available_tools=json.dumps(available_tools or ["none"])
    )

    try:
        response = await asyncio.to_thread(model.generate_content, prompt)
        spec = _parse_json(response.text)

        # Cache for reuse
        _agent_cache[task_key] = spec
        print(f"🆕 Spawned and cached agent: {spec.get('agent_name')} (hash: {task_key})")

        return EphemeralAgent(spec)

    except Exception as e:
        print(f"Agent Factory error: {e}")
        return EphemeralAgent({
            "agent_name": "error_fallback",
            "purpose": task_description[:100],
            "system_prompt": f"Complete this task: {task_description}",
            "dna_rules": ["Handle errors gracefully"],
            "output_schema": {"result": "string", "error": "string"},
            "complexity": "low",
            "reasoning": f"Fallback due to: {str(e)}"
        })


async def smart_spawn(
    task_description: str,
    input_data: Dict[str, Any],
    user_context: Optional[Dict] = None
) -> Dict[str, Any]:
    """
    KING's brain: Route task intelligently using AI-powered intent classification.
    Returns: {"agent_spec": {...}, "decision": str, "output": Any}
    """
    # Merge input_data into user_context for memory fetching
    merged_context = {**(user_context or {})}
    if "user_id" in input_data:
        merged_context["user_id"] = input_data["user_id"]
    if "session_id" in input_data:
        merged_context["session_id"] = input_data["session_id"]

    user_id = merged_context.get("user_id")
    session_id = merged_context.get("session_id")

    # Step 1: AI-powered routing with memory context
    route = await smart_route(task_description, merged_context)
    action = route.get("action", "respond")
    intent = route.get("intent", "task")
    decision = route.get("decision", action)  # Use action from new prompt format
    print(f"🧠 Router: action={action}, decision={decision}, reasoning: {route.get('reasoning', 'N/A')[:80]}")

    # Helper to store memory and return result
    async def _return_with_memory(result: Dict[str, Any]) -> Dict[str, Any]:
        """Store conversation in memory before returning."""
        response_text = ""
        output = result.get("output", {})
        if isinstance(output, dict):
            response_text = output.get("response") or output.get("synthesis") or str(output)
        else:
            response_text = str(output)

        # Store memory asynchronously (don't block response)
        if user_id and response_text:
            asyncio.create_task(_store_memory(
                user_id=user_id,
                session_id=session_id,
                user_message=task_description,
                assistant_response=response_text[:1000]  # Limit size
            ))
        return result

    # Step 2: Handle respond/clarify actions (conversational - no agent needed)
    if action in ("respond", "clarify") or decision in ("chat", "info", "respond", "clarify"):
        chat_response = route.get("response") or route.get("chat_response") or "Hello! I'm KING 👑. How can I help you?"
        # For info queries, append agent list
        if intent == "info" or decision == "info":
            agents = await get_existing_agents_with_descriptions()
            agent_list = ", ".join([f"{name}" for name in agents.keys()])
            chat_response = f"{chat_response}\n\nMy agents: {agent_list}"

        return await _return_with_memory({
            "agent_spec": {"agent_name": "conversational"},
            "decision": action,
            "output": {"response": chat_response, "confidence": 1.0},
            "reasoning": route.get("reasoning", "Conversational response"),
            "memory_used": route.get("memory_used", [])
        })

    # Step 3: Handle memory decision (for context/history queries)
    if decision == "memory" or intent == "memory":
        if user_id:
            memory_context = await _fetch_user_memory(user_id, task_description)
            chat_response = route.get("response") or f"Here's what I remember:\n{memory_context}"
        else:
            chat_response = "I don't have any memory context for you yet. Tell me more about yourself!"

        return await _return_with_memory({
            "agent_spec": {"agent_name": "memory_cortex"},
            "decision": "memory",
            "output": {"response": chat_response, "confidence": 0.8},
            "reasoning": route.get("reasoning", "Memory query")
        })

    # Step 4: Execute action - delegate to specialist agent
    execute_agent = route.get("execute_agent") or route.get("reuse_agent")
    execution_mode = route.get("execution_mode", "sync")

    if action == "execute" or (decision == "reuse" and execute_agent):
        agent_name = execute_agent
        if agent_name:
            # Check if async execution requested
            if execution_mode == "async" and user_id:
                from task_queue import enqueue_task

                # Create executor for this agent
                async def agent_executor(data):
                    return await call_registered_agent(agent_name, data)

                task_id = await enqueue_task(
                    user_id=user_id,
                    session_id=session_id or "",
                    task_type=agent_name,
                    input_data=input_data,
                    executor=agent_executor
                )

                # Return immediately with acknowledgment
                ack_response = route.get("response") or f"Got it! Working on that in the background. Task ID: {task_id}"
                return await _return_with_memory({
                    "agent_spec": {"agent_name": agent_name, "type": "async"},
                    "decision": "async_queued",
                    "task_id": task_id,
                    "output": {"response": ack_response, "task_id": task_id},
                    "reasoning": route.get("reasoning")
                })

            # SYNC execution - wait for result
            # 4a. Check REGISTERED agents
            try:
                service_url = await get_registered_agent_url(agent_name)
                if service_url:
                    print(f"♻️ Executing via REGISTERED agent: {agent_name}")
                    output = await call_registered_agent(agent_name, input_data)
                    return await _return_with_memory({
                        "agent_spec": {"agent_name": agent_name, "type": "registered"},
                        "decision": "executed",
                        "output": output,
                        "reasoning": route.get("reasoning")
                    })
            except Exception as e:
                print(f"⚠️ Registered agent '{agent_name}' call failed: {e}")

            # 4b. Check CACHED ephemeral agents
            for key, spec in _agent_cache.items():
                if spec.get("agent_name") == agent_name:
                    print(f"♻️ Executing via CACHED agent: {agent_name}")
                    agent = EphemeralAgent(spec)
                    output = await agent.execute(input_data)
                    return await _return_with_memory({
                        "agent_spec": spec, "decision": "executed", "output": output, "reasoning": route.get("reasoning")
                    })

        # 4c. Not found anywhere - fall through to spawn
        print(f"⚠️ Agent '{agent_name}' not found, spawning new")
        decision = "spawn"

    # Step 5: Team mode with deduplication
    if decision == "team":
        team_results = []
        team_agents = route.get("team_agents", [])
        if not team_agents:
            decision = "spawn"
        else:
            spawned_names = set()
            unique_agents = []
            for agent_spec in team_agents[:5]:
                if isinstance(agent_spec, str):
                    if agent_spec not in spawned_names:
                        spawned_names.add(agent_spec)
                        unique_agents.append(agent_spec)
                elif isinstance(agent_spec, dict):
                    name = agent_spec.get("name", agent_spec.get("agent_name", ""))
                    if name and name not in spawned_names:
                        spawned_names.add(name)
                        unique_agents.append(agent_spec)

            for agent_spec in unique_agents[:3]:
                if isinstance(agent_spec, str):
                    agent = await spawn_agent(f"{agent_spec}: {task_description}", user_context)
                else:
                    agent = EphemeralAgent(agent_spec)
                result = await agent.execute(input_data)
                team_results.append({"agent": agent.name, "output": result})

            if team_results:
                combined = await _synthesize_team(task_description, team_results)
                return await _return_with_memory({
                    "agent_spec": {"agent_name": "team_coordinator"},
                    "decision": "team",
                    "team_results": team_results,
                    "output": combined,
                    "reasoning": route.get("reasoning")
                })

    # Step 6: Default - spawn new agent
    agent = await spawn_agent(task_description, user_context)
    output = await agent.execute(input_data)
    return await _return_with_memory({
        "agent_spec": agent.to_dict(), "decision": "spawned", "output": output, "reasoning": route.get("reasoning")
    })


async def _synthesize_team(task: str, results: List[Dict]) -> Dict:
    """Combine outputs from multiple agents into unified response."""
    model = _get_factory_model()
    if not model:
        return {"combined": results, "confidence": 0.5}

    prompt = f"""You are KING's Team Synthesizer. Multiple agents worked on this task.

Task: {task}

Agent Results:
{json.dumps(results, indent=2)}

Synthesize into ONE coherent response. Combine insights, resolve conflicts, provide unified answer.
Respond with JSON: {{"synthesis": "...", "key_insights": [...], "confidence": 0.0-1.0}}
"""
    try:
        response = await asyncio.to_thread(model.generate_content, prompt)
        return _parse_json(response.text)
    except:
        return {"combined": results, "confidence": 0.5}

