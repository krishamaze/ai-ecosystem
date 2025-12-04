"""
KING Orchestrator - Strategic Decision Endpoint

The brain of the Kingdom. Gateway delegates ALL strategic decisions here.
Flow: Guardian check → Memory lookup → Route decision → Agent selection → Verdict
"""
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Optional, Dict, Any, List
import logging

from agents.agent_runner import AgentRunner
from agents.guardian_minister import GuardianMinister
from services.supabase_client import supabase
from services.mem0_tool import search_memory, select_memories

logger = logging.getLogger(__name__)
router = APIRouter()
runner = AgentRunner()


class DecideRequest(BaseModel):
    """Request from gateway for strategic decision."""
    user_id: str
    message: str
    session_id: Optional[str] = None
    context: Optional[Dict[str, Any]] = None


class AgentVerdict(BaseModel):
    """Verdict on which agent to use."""
    agent_type: str  # "registered" | "ephemeral" | "pipeline"
    agent_name: str
    service_url: Optional[str] = None  # For registered agents
    spec: Optional[Dict[str, Any]] = None  # For ephemeral agents
    pipeline_steps: Optional[List[str]] = None  # For pipelines


class DecideResponse(BaseModel):
    """Strategic decision response."""
    action: str  # "execute" | "blocked" | "clarify" | "memory_only"
    verdict: Optional[AgentVerdict] = None
    enriched_input: Dict[str, Any]
    memory_context: Optional[List[str]] = None
    reasoning: str
    trace_id: str
    guardian_decision: Dict[str, Any]


def _get_registered_agents() -> Dict[str, str]:
    """Fetch registered agents and their URLs from DB."""
    try:
        result = supabase.table("agent_registry") \
            .select("agent_name, service_url") \
            .eq("status", "active") \
            .execute()
        return {r["agent_name"]: r["service_url"] for r in (result.data or [])}
    except Exception as e:
        logger.error(f"Failed to fetch agent registry: {e}")
        return {}


def _get_agent_spec(agent_name: str) -> Optional[Dict[str, Any]]:
    """Fetch agent spec from DB (runtime authority)."""
    try:
        result = supabase.table("agent_specs") \
            .select("*") \
            .eq("agent_name", agent_name) \
            .eq("is_active", True) \
            .single() \
            .execute()
        return result.data
    except Exception:
        return None


def _route_task(message: str, registered_agents: List[str]) -> Dict[str, Any]:
    """
    Determine best agent for task.
    Priority: registered > cached ephemeral > spawn new
    """
    msg_lower = message.lower()
    
    # Direct matches for registered agents
    agent_keywords = {
        "code_writer": ["write code", "generate code", "create function", "implement"],
        "code_reviewer": ["review code", "check code", "audit code"],
        "video_planner": ["video", "youtube", "content plan"],
        "script_writer": ["script", "screenplay", "dialogue"],
        "memory_selector": ["remember", "recall", "what did", "history"],
    }
    
    for agent, keywords in agent_keywords.items():
        if agent in registered_agents:
            if any(kw in msg_lower for kw in keywords):
                return {
                    "decision": "registered",
                    "agent_name": agent,
                    "reasoning": f"Keyword match for registered agent: {agent}"
                }
    
    # Check for pipeline patterns
    if "generate" in msg_lower and "review" in msg_lower:
        return {
            "decision": "pipeline",
            "pipeline_steps": ["code_writer", "code_reviewer"],
            "reasoning": "Multi-step task requiring code generation and review"
        }
    
    # Default: spawn ephemeral
    return {
        "decision": "ephemeral",
        "reasoning": "No registered agent match, will spawn ephemeral"
    }


@router.post("/decide", response_model=DecideResponse)
async def decide(request: DecideRequest) -> DecideResponse:
    """
    Strategic decision endpoint. Gateway calls this for EVERY user request.
    
    Flow:
    1. Guardian Minister checks safety
    2. Memory lookup for context
    3. Route to appropriate agent
    4. Return verdict for gateway to execute
    """
    from services.guardrails import generate_trace_id
    trace_id = generate_trace_id()
    
    # === Step 1: Guardian Minister (Safety Gate) ===
    guardian = GuardianMinister(request.message, user_id=request.user_id, context="input")
    guardian_decision = guardian.get_decision()
    
    if guardian_decision["verdict"] == "BLOCKED":
        logger.warning(f"[{trace_id}] Guardian BLOCKED: {guardian_decision['reason']}")
        return DecideResponse(
            action="blocked",
            verdict=None,
            enriched_input={"original": request.message},
            memory_context=None,
            reasoning=guardian_decision["reason"],
            trace_id=trace_id,
            guardian_decision=guardian_decision
        )
    
    # === Step 2: Memory Lookup ===
    memory_context = []
    try:
        raw_result = search_memory(request.message, request.user_id, limit=5)
        raw_memories = raw_result.get("memories", [])
        
        if raw_memories:
            selection = select_memories(request.message, raw_memories, request.user_id)
            memory_context = selection.get("approved", [])
    except Exception as e:
        logger.error(f"[{trace_id}] Memory lookup failed: {e}")
    
    # === Step 3: Build Enriched Input ===
    enriched_input = {
        "original_message": request.message,
        "user_id": request.user_id,
        "session_id": request.session_id,
    }
    
    if memory_context:
        enriched_input["memory_context"] = memory_context
    
    if request.context:
        enriched_input["user_context"] = request.context
    
    # === Step 4: Route Decision ===
    registered_agents = _get_registered_agents()
    route = _route_task(request.message, list(registered_agents.keys()))
    
    verdict = None
    
    if route["decision"] == "registered":
        agent_name = route["agent_name"]
        verdict = AgentVerdict(
            agent_type="registered",
            agent_name=agent_name,
            service_url=registered_agents.get(agent_name)
        )
    
    elif route["decision"] == "pipeline":
        verdict = AgentVerdict(
            agent_type="pipeline",
            agent_name="pipeline_executor",
            pipeline_steps=route["pipeline_steps"]
        )
    
    elif route["decision"] == "ephemeral":
        # Return minimal spec for gateway to spawn
        verdict = AgentVerdict(
            agent_type="ephemeral",
            agent_name="spawn_required",
            spec={
                "task": request.message,
                "user_id": request.user_id,
                "memory_context": memory_context
            }
        )
    
    return DecideResponse(
        action="execute",
        verdict=verdict,
        enriched_input=enriched_input,
        memory_context=memory_context if memory_context else None,
        reasoning=route["reasoning"],
        trace_id=trace_id,
        guardian_decision=guardian_decision
    )


@router.post("/execute-agent")
async def execute_agent(
    agent_name: str,
    input_data: Dict[str, Any],
    user_id: str
) -> Dict[str, Any]:
    """
    Execute a registered/known agent. Called by gateway after /decide.
    Handles telemetry logging.
    """
    import time
    start = time.time()
    
    try:
        response = runner.run(agent_name, input_data)
        duration_ms = int((time.time() - start) * 1000)
        
        # Log to agent_runs
        supabase.table("agent_runs").insert({
            "agent_name": agent_name,
            "input": input_data,
            "output": response.output,
            "success": response.status == "success",
            "error": str(response.error) if response.error else None,
            "duration_ms": duration_ms,
            "user_id": user_id
        }).execute()
        
        return {
            "status": response.status,
            "output": response.output,
            "confidence": response.confidence,
            "duration_ms": duration_ms
        }
    
    except Exception as e:
        logger.error(f"Agent execution failed: {e}")
        return {
            "status": "error",
            "error": str(e),
            "output": None
        }

