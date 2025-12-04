"""
KING Memory Orchestrator - Context-aware memory decisions.
No hardcoding. The AI decides what to remember based on context.

KING Memory v1.0 - Aligned with Mem0 Platform native layers:
- Conversation: In-flight (handled by session history)
- Session: Short-term via session_id
- User: Long-term via user_id
- Org: Kingdom-wide via org_id='__kingdom__'
"""
import asyncio
import os
import json
from typing import Dict, Any, Optional, List
from datetime import datetime, timezone
import google.generativeai as genai
from mem0 import MemoryClient

# Lazy initialization
_mem0_client = None
_reflection_model = None


def _get_mem0_client():
    """Lazy init for Mem0 client."""
    global _mem0_client
    if _mem0_client is None:
        mem0_api_key = os.getenv("MEM0_API_KEY")
        if mem0_api_key:
            try:
                _mem0_client = MemoryClient(api_key=mem0_api_key.strip())
            except Exception as e:
                print(f"Warning: Failed to init Mem0 client: {e}")
                _mem0_client = False
        else:
            _mem0_client = False
    return _mem0_client if _mem0_client else None


def _get_reflection_model():
    """Lazy init for Gemini reflection model."""
    global _reflection_model
    if _reflection_model is None:
        gemini_api_key = os.getenv("GEMINI_API_KEY")
        if gemini_api_key:
            genai.configure(api_key=gemini_api_key.strip())
            _reflection_model = genai.GenerativeModel("gemini-2.0-flash-exp")
        else:
            print("Warning: GEMINI_API_KEY not set. Memory orchestrator disabled.")
            _reflection_model = False
    return _reflection_model if _reflection_model else None


# ============================================================================
# MEMORY ORCHESTRATOR PROMPT - Context-aware, NO hardcoding
# ============================================================================
MEMORY_ORCHESTRATOR_PROMPT = """You are KING's Memory Orchestrator 🧠

## YOUR IDENTITY
You are the memory gatekeeper for KING, an AI Kingdom. You decide what gets remembered and how.
You have access to the user's recent memory summary and conversation context.

## YOUR CAPABILITIES
- Store to USER memory (long-term, persists forever)
- Store to SESSION memory (short-term, expires after session)
- Store to KINGDOM memory (shared across all users/agents)
- Enable GRAPH memory for entity relationships
- Skip storage entirely if not valuable

## CONTEXT PROVIDED
User ID: {user_id}
Session ID: {session_id}
Time since last interaction: {time_gap}
Recent memory summary: {memory_summary}
Session context (recent turns): {session_context}

## CURRENT INTERACTION
User message: {user_message}
Assistant response: {assistant_response}

## DECISION FRAMEWORK
Think about:
1. Is this a continuation of an ongoing topic? (session memory)
2. Does this reveal a NEW user preference/trait? (user memory)
3. Is this a greeting after a long gap? (might be meaningful context)
4. Is this just acknowledgment mid-conversation? (probably skip)
5. Does this contain entities worth tracking? (enable graph)
6. Is this a lesson the whole Kingdom should learn? (kingdom memory)

## EXAMPLES
- "Hi" after 2 days → Store "User returned after 2 days" to session
- "Hi" mid-conversation → Skip (just acknowledgment)
- "I prefer dark mode" → Store preference to user memory
- "The project is called Apollo" → Store with graph=true for entity
- "ok" / "thanks" / "got it" → Skip (no value)
- "Remember: always use TypeScript" → Store to user memory (explicit instruction)

## RESPONSE FORMAT
Respond with valid JSON only:
{{
    "should_store": boolean,
    "reasoning": "brief explanation",
    "memories": [
        {{
            "content": "what to remember (concise)",
            "layer": "user|session|kingdom",
            "enable_graph": boolean,
            "importance": 0.1-1.0
        }}
    ]
}}

If nothing worth storing: {{"should_store": false, "reasoning": "...", "memories": []}}"""


# Legacy reflection prompt for error learning
REFLECTION_PROMPT = """You are KING's memory cortex. Analyze this ERROR for learning.

Agent: {agent_name}
Task Input: {input_summary}
Error: {error}
User Feedback: {feedback}

Extract lessons from this failure. What should KING remember to avoid this in future?

Respond with JSON:
{{
    "should_remember": boolean,
    "memories": [
        {{
            "content": "lesson learned",
            "scope": "agent|user|kingdom",
            "importance": 0.1-1.0
        }}
    ]
}}

If no lesson worth learning: {{"should_remember": false, "memories": []}}
"""

# ============================================================================
# MEMORY ORCHESTRATOR - Main entry point for memory decisions
# ============================================================================

# Track last interaction time per user for time gap calculation
_last_interaction: Dict[str, datetime] = {}


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

    No hardcoding. The LLM receives full context and decides:
    - Whether to store
    - Which layer (user/session/kingdom)
    - Whether to enable graph for entities

    Args:
        user_id: User identifier
        session_id: Session identifier
        user_message: Current user message
        assistant_response: Current assistant response
        memory_summary: Recent memories for this user (optional)
        session_context: Recent session turns (optional)

    Returns:
        Dict with decision details
    """
    model = _get_reflection_model()
    client = _get_mem0_client()

    if not model or not client:
        return {"stored": False, "reason": "Memory system unavailable"}

    # Calculate time gap since last interaction
    now = datetime.now(timezone.utc)
    last_time = _last_interaction.get(user_id)
    if last_time:
        gap = now - last_time
        if gap.days > 0:
            time_gap = f"{gap.days} days ago"
        elif gap.seconds > 3600:
            time_gap = f"{gap.seconds // 3600} hours ago"
        elif gap.seconds > 60:
            time_gap = f"{gap.seconds // 60} minutes ago"
        else:
            time_gap = "just now (same session)"
    else:
        time_gap = "first interaction"

    # Update last interaction time
    _last_interaction[user_id] = now

    # Build orchestrator prompt with full context
    prompt = MEMORY_ORCHESTRATOR_PROMPT.format(
        user_id=user_id,
        session_id=session_id,
        time_gap=time_gap,
        memory_summary=memory_summary or "No previous memories",
        session_context=session_context or "New session",
        user_message=user_message[:500],
        assistant_response=assistant_response[:500]
    )

    try:
        response = await asyncio.to_thread(model.generate_content, prompt)
        decision = _parse_json_response(response.text)

        if not decision.get("should_store"):
            print(f"🧠 Memory skip: {decision.get('reasoning', 'no reason')[:50]}")
            return {"stored": False, "reason": decision.get("reasoning")}

        # Store each memory to appropriate layer
        stored_count = 0
        for mem in decision.get("memories", []):
            layer = mem.get("layer", "user")
            enable_graph = mem.get("enable_graph", False)

            # Map layer to Mem0 identifiers
            if layer == "session":
                mem0_user_id = user_id
                mem0_session_id = session_id
            elif layer == "kingdom":
                mem0_user_id = "__kingdom__"
                mem0_session_id = None
            else:  # user (default)
                mem0_user_id = user_id
                mem0_session_id = None

            messages = [
                {"role": "user", "content": user_message},
                {"role": "assistant", "content": assistant_response}
            ]

            # Build add kwargs
            add_kwargs = {
                "user_id": mem0_user_id,
                "metadata": {
                    "importance": mem.get("importance", 0.5),
                    "source": "memory_orchestrator",
                    "timestamp": now.isoformat()
                }
            }

            if mem0_session_id:
                add_kwargs["session_id"] = mem0_session_id

            if enable_graph:
                add_kwargs["enable_graph"] = True

            await asyncio.to_thread(client.add, messages, **add_kwargs)
            stored_count += 1
            print(f"💾 Memory stored: layer={layer}, graph={enable_graph}")

        return {
            "stored": True,
            "count": stored_count,
            "reasoning": decision.get("reasoning")
        }

    except Exception as e:
        print(f"⚠️ Memory orchestrator error: {e}")
        return {"stored": False, "reason": str(e)}


async def reflect_on_error(
    agent_name: str,
    input_data: Dict[str, Any],
    error: str,
    user_id: Optional[str] = None,
    user_feedback: Optional[str] = None
) -> None:
    """
    Error reflection - Learn from failures only.
    Runs in background, never blocks response.
    """
    model = _get_reflection_model()
    client = _get_mem0_client()

    if not model or not client:
        return

    try:
        prompt = REFLECTION_PROMPT.format(
            agent_name=agent_name,
            input_summary=_summarize(input_data, max_len=500),
            error=error,
            feedback=user_feedback or "None"
        )

        response = await asyncio.to_thread(model.generate_content, prompt)
        reflection = _parse_json_response(response.text)

        if not reflection.get("should_remember"):
            return

        for mem in reflection.get("memories", []):
            mem0_user_id = _resolve_scope(
                scope=mem.get("scope", "agent"),
                agent_name=agent_name,
                user_id=user_id
            )

            await asyncio.to_thread(
                client.add,
                messages=[{"role": "assistant", "content": mem["content"]}],
                user_id=mem0_user_id,
                metadata={
                    "type": "error_lesson",
                    "importance": mem.get("importance", 0.7),
                    "source": "error_reflection",
                    "agent": agent_name,
                    "timestamp": datetime.now(timezone.utc).isoformat()
                }
            )
            print(f"📚 Error lesson stored: {mem['content'][:50]}...")

    except Exception as e:
        print(f"Error reflection failed (non-fatal): {e}")


# Legacy function for backward compatibility
async def reflect_on_run(
    agent_name: str,
    input_data: Dict[str, Any],
    output_data: Dict[str, Any],
    success: bool,
    error: Optional[str] = None,
    user_id: Optional[str] = None,
    user_feedback: Optional[str] = None,
    duration_ms: int = 0
) -> None:
    """
    Legacy reflection - now only processes errors.
    Success cases are handled by orchestrate_memory().
    """
    if not success and error:
        await reflect_on_error(
            agent_name=agent_name,
            input_data=input_data,
            error=error,
            user_id=user_id,
            user_feedback=user_feedback
        )


# ============================================================================
# HELPER FUNCTIONS
# ============================================================================

def _parse_json_response(text: str) -> Dict[str, Any]:
    """Parse JSON from LLM response, handling markdown blocks."""
    text = text.strip()
    if text.startswith("```json"):
        text = text[7:]
    if text.startswith("```"):
        text = text[3:]
    if text.endswith("```"):
        text = text[:-3]
    try:
        return json.loads(text.strip())
    except json.JSONDecodeError:
        return {"should_store": False, "reasoning": "Failed to parse response"}


def _resolve_scope(scope: str, agent_name: str, user_id: Optional[str]) -> str:
    """Map scope to Mem0 user_id for proper isolation."""
    if scope == "agent":
        return f"agent:{agent_name}"  # Lineage
    elif scope == "user" and user_id:
        return user_id
    elif scope == "kingdom":
        return "__kingdom__"
    else:
        return user_id if user_id else "__kingdom__"


def _summarize(data: Dict, max_len: int = 500) -> str:
    """Truncate for prompt efficiency."""
    try:
        text = json.dumps(data, default=str)
        return text[:max_len] + "..." if len(text) > max_len else text
    except Exception:
        return str(data)[:max_len]
