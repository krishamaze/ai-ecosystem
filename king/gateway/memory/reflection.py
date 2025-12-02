"""
KING Self-Reflection System.
Autonomous learning from every interaction.
"""
import asyncio
import os
import json
from typing import Dict, Any, Optional
from datetime import datetime
import google.generativeai as genai
from mem0 import MemoryClient

# Initialize clients
mem0_api_key = os.getenv("MEM0_API_KEY")
mem0_client = MemoryClient(api_key=mem0_api_key) if mem0_api_key else None

gemini_api_key = os.getenv("GEMINI_API_KEY")
if gemini_api_key:
    genai.configure(api_key=gemini_api_key)
    # Use a fast, cost-effective model for reflection
    reflection_model = genai.GenerativeModel("gemini-2.0-flash-exp")
else:
    print("Warning: GEMINI_API_KEY not set. Reflection will be disabled.")
    reflection_model = None

REFLECTION_PROMPT = """You are KING's memory cortex. Analyze this interaction.

Agent: {agent_name}
Task Input: {input_summary}
Output Success: {success}
Error (if any): {error}
User Feedback: {feedback}

RULES:
1. Only remember if genuinely NEW and USEFUL for future
2. Never store what LLMs already know (general coding, syntax, etc.)
3. Store user-specific preferences, project-specific patterns, error lessons
4. Be extremely selective — memory is precious

Respond ONLY with valid JSON:
{{
    "should_remember": boolean,
    "memories": [
        {{
            "content": "concise lesson/fact",
            "type": "lineage|semantic|episodic",
            "scope": "agent|user|kingdom",
            "importance": 0.1-1.0
        }}
    ]
}}

If nothing worth remembering, return {{"should_remember": false, "memories": []}}
"""

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
    Async reflection — runs in background, never blocks response.
    """
    if not reflection_model or not mem0_client:
        return

    try:
        # Build reflection prompt
        prompt = REFLECTION_PROMPT.format(
            agent_name=agent_name,
            input_summary=_summarize(input_data, max_len=500),
            success=success,
            error=error or "None",
            feedback=user_feedback or "None"
        )
        
        # Call reflection LLM
        # Run synchronous Gemini call in thread pool to avoid blocking async loop
        response = await asyncio.to_thread(reflection_model.generate_content, prompt)
        
        try:
            # Clean and parse JSON
            text = response.text.strip()
            if text.startswith("```json"):
                text = text[7:]
            if text.endswith("```"):
                text = text[:-3]
            reflection = json.loads(text.strip())
        except json.JSONDecodeError:
            print(f"Reflection failed to parse JSON: {response.text[:100]}...")
            return
        
        if not reflection.get("should_remember"):
            return
        
        # Store each memory with proper scoping
        for mem in reflection.get("memories", []):
            mem0_user_id = _resolve_scope(
                scope=mem.get("scope", "user"),
                agent_name=agent_name,
                user_id=user_id
            )
            
            # Use run_in_executor for blocking mem0 calls if needed, 
            # though mem0 client might be async-compatible or fast enough.
            # Ideally mem0 calls should be async, but standard client is sync.
            # We'll run in thread pool.
            await asyncio.to_thread(
                mem0_client.add,
                messages=[{"role": "assistant", "content": mem["content"]}],
                user_id=mem0_user_id,
                metadata={
                    "type": mem.get("type", "episodic"),
                    "importance": mem.get("importance", 0.5),
                    "source": "self_reflection",
                    "agent": agent_name,
                    "timestamp": datetime.utcnow().isoformat()
                }
            )
            
    except Exception as e:
        # Never fail the main request — log and continue
        print(f"Reflection error (non-fatal): {e}")

def _resolve_scope(scope: str, agent_name: str, user_id: Optional[str]) -> str:
    """Map scope to Mem0 user_id for proper isolation."""
    if scope == "agent":
        return f"agent:{agent_name}"  # Lineage
    elif scope == "user" and user_id:
        return user_id  # User-specific
    elif scope == "kingdom":
        return "__kingdom__"  # Global
    else:
        # Fallback to user if available, else kingdom
        return user_id if user_id else "__kingdom__"

def _summarize(data: Dict, max_len: int = 500) -> str:
    """Truncate for prompt efficiency."""
    try:
        text = json.dumps(data, default=str)
        return text[:max_len] + "..." if len(text) > max_len else text
    except Exception:
        return str(data)[:max_len]

