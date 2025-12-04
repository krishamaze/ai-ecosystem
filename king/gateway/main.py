from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
import httpx
import os
import time
from typing import Dict, Any, List, Optional
from state_manager import StateManager
from mem0 import MemoryClient
import json
from dataclasses import asdict
from memory import MemoryResolver, EntityResolver
from memory.reflection import reflect_on_run
from agent_factory import spawn_agent, smart_spawn, EphemeralAgent
import asyncio
import logging

logger = logging.getLogger(__name__)

app = FastAPI(title="KING Gateway", version="2.0.0")
state_manager = StateManager()

# Orchestrator URL (king-orchestrator service)
ORCHESTRATOR_URL = os.getenv("ORCHESTRATOR_URL", "")
ORCHESTRATOR_TIMEOUT = 30.0

# Lazy initialization to avoid import-time failures
_mem0_client = None
_entity_resolver = None
_memory_resolver = None


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
            print("Warning: MEM0_API_KEY is not set. Memory functions will be disabled.")
            _mem0_client = False
    return _mem0_client if _mem0_client else None


def _get_entity_resolver():
    """Lazy init for EntityResolver."""
    global _entity_resolver
    if _entity_resolver is None:
        try:
            _entity_resolver = EntityResolver()
        except Exception as e:
            print(f"Warning: Failed to init EntityResolver: {e}")
            _entity_resolver = False
    return _entity_resolver if _entity_resolver else None


def _get_memory_resolver():
    """Lazy init for MemoryResolver."""
    global _memory_resolver
    if _memory_resolver is None:
        mem0 = _get_mem0_client()
        entity = _get_entity_resolver()
        if mem0 and entity:
            _memory_resolver = MemoryResolver(mem0_client=mem0, entity_resolver=entity)
        else:
            _memory_resolver = False
    return _memory_resolver if _memory_resolver else None

class ExecuteRequest(BaseModel):
    agent_name: str
    input_data: Dict[str, Any]

class PipelineRequest(BaseModel):
    steps: List[str]
    initial_input: Dict[str, Any]

class SpawnRequest(BaseModel):
    task_description: str
    input_data: Dict[str, Any]
    user_context: Optional[Dict[str, Any]] = None
    persist: bool = False  # If True, register agent for future use

async def _call_agent_service(agent_name: str, input_data: Dict) -> Dict:
    """Internal helper to call an agent service."""
    service_url = state_manager.get_agent_url(agent_name)
    if not service_url:
        raise HTTPException(status_code=404, detail=f"Agent '{agent_name}' not found or inactive")

    async with httpx.AsyncClient() as client:
        try:
            response = await client.post(
                f"{service_url}/execute",
                json=input_data,
                timeout=60.0
            )
            response.raise_for_status()
            return response.json()
        except httpx.HTTPStatusError as e:
            raise HTTPException(status_code=e.response.status_code, detail=f"Agent Service Error: {e.response.text}")
        except Exception as e:
            raise HTTPException(status_code=502, detail=f"Gateway Error calling '{agent_name}': {str(e)}")

@app.get("/health")
def health_check():
    """Basic health check."""
    return {"status": "ok", "service": "KING Gateway"}

@app.get("/agents/list")
def list_agents():
    """List all registered active agents."""
    client = state_manager.get_client()
    if not client:
        return {"error": "Database connection unavailable", "agents": []}
    
    try:
        # Use direct query here as this is an admin/debug endpoint, freshness matters more than cache
        result = client.table("agent_registry") \
            .select("agent_name, service_url, status, version") \
            .eq("status", "active") \
            .execute()
        return {"agents": result.data}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/execute/{agent_name}")
async def execute_agent(agent_name: str, request: ExecuteRequest):
    """Route execution, with memory middleware."""
    start_time = time.time()
    
    user_id = request.input_data.get("user_id")
    session_id = request.input_data.get("session_id")
    enriched_input = request.input_data.copy()

    # 1. Hierarchical Memory Search
    memory_resolver = _get_memory_resolver()
    if user_id and agent_name != "memory_selector" and memory_resolver:
        query = enriched_input.get("query") or str(enriched_input)

        # Use the resolver for multi-tier search (async call)
        memory_results = await memory_resolver.resolve(
            query=query,
            user_id=user_id,
            agent_id=agent_name,
            session_id=session_id,
            resolve_entity=True # Enable entity resolution
        )
        
        candidate_memories = memory_results.get_all_flat()
        
        if candidate_memories:
            try:
                # Run memory_selector service to filter
                selector_input = {
                    "query": query, 
                    "candidate_memories": [{"content": m.content, "importance": m.importance, "memory_type": m.memory_type.value} for m in candidate_memories] # Convert to dict compatible format
                }
                selection_result = await _call_agent_service("memory_selector", selector_input)
                
                # Inject approved memories into the context for the target agent
                if selection_result.get("approved_memories"):
                    if "context" not in enriched_input:
                        enriched_input["context"] = {}
                    enriched_input["context"]["memory"] = selection_result["approved_memories"]

            except Exception as e:
                print(f"Memory selection failed for user {user_id}: {e}")
                # Continue without memory enrichment on failure

    # 2. Call Target Agent Service
    output = None
    success = False
    error_msg = None
    
    try:
        output = await _call_agent_service(agent_name, enriched_input)
        success = True
    except HTTPException as e:
        error_msg = e.detail
        raise e  # Re-raise to return the specific error to the client
    except Exception as e:
        error_msg = str(e)
        raise HTTPException(status_code=500, detail=error_msg)
    finally:
        # 3. Log Execution to Supabase
        duration_ms = int((time.time() - start_time) * 1000)
        state_manager.log_run(
            agent_name=agent_name,
            input_data=request.input_data, # Log original request
            output_data=output,
            success=success,
            error=error_msg,
            duration_ms=duration_ms
        )
        
        # 4. Add result to Mem0 (Episodic Memory)
        mem0_client = _get_mem0_client()
        if user_id and success and mem0_client:
            try:
                # Store structured episodic memory
                mem0_client.add(
                    f"Interaction with '{agent_name}'. Output: {json.dumps(output)}",
                    user_id=user_id,
                    metadata={"agent_id": agent_name, "category": "episodic"}
                )
            except Exception as e:
                print(f"Mem0 add failed for user {user_id}: {e}")

        # 5. Self-Reflection (async, non-blocking)
        asyncio.create_task(
            reflect_on_run(
                agent_name=agent_name,
                input_data=request.input_data,
                output_data=output or {},
                success=success,
                error=error_msg,
                user_id=user_id,
                user_feedback=request.input_data.get("feedback"),
                duration_ms=duration_ms
            )
        )

    return output

@app.post("/pipeline/run")
async def run_pipeline(request: PipelineRequest):
    """Execute a simple sequential pipeline."""
    results = []
    current_input = request.initial_input
    
    for step_agent in request.steps:
        try:
            # Construct internal request object
            step_req = ExecuteRequest(agent_name=step_agent, input_data=current_input)
            
            # Await the handler directly. This re-uses the whole middleware flow for each step.
            step_output = await execute_agent(step_agent, step_req)
            
            results.append({
                "agent": step_agent,
                "output": step_output,
                "status": "success"
            })
            
            # Chain output to next input (naive chaining)
            current_input = step_output
            # Pass user_id through pipeline steps
            if "user_id" in request.initial_input:
                if isinstance(current_input, dict):
                    current_input["user_id"] = request.initial_input["user_id"]

        except Exception as e:
            # Extract detail if it's an HTTPException
            error_detail = e.detail if isinstance(e, HTTPException) else str(e)
            results.append({
                "agent": step_agent,
                "error": error_detail,
                "status": "failed"
            })
            # Stop pipeline on failure
            return {
                "success": False, 
                "results": results, 
                "error": f"Pipeline failed at step {step_agent}: {error_detail}"
            }

    return {"success": True, "results": results}


async def _call_orchestrator_decide(user_id: str, message: str, session_id: str = None, context: dict = None) -> dict:
    """Call orchestrator /king/decide endpoint for strategic decision."""
    if not ORCHESTRATOR_URL:
        return None  # Fallback to local smart_spawn

    async with httpx.AsyncClient() as client:
        try:
            response = await client.post(
                f"{ORCHESTRATOR_URL}/king/decide",
                json={
                    "user_id": user_id or "anonymous",
                    "message": message,
                    "session_id": session_id,
                    "context": context
                },
                timeout=ORCHESTRATOR_TIMEOUT
            )
            response.raise_for_status()
            return response.json()
        except Exception as e:
            logger.error(f"Orchestrator call failed: {e}")
            return None  # Fallback to local


async def _execute_verdict(verdict: dict, enriched_input: dict) -> dict:
    """Execute the orchestrator's verdict."""
    agent_type = verdict.get("agent_type")
    agent_name = verdict.get("agent_name")

    if agent_type == "registered":
        service_url = verdict.get("service_url")
        if service_url:
            async with httpx.AsyncClient() as client:
                resp = await client.post(f"{service_url}/execute", json=enriched_input, timeout=60)
                return resp.json()
        # Fallback: try via state_manager
        return await _call_agent_service(agent_name, enriched_input)

    elif agent_type == "pipeline":
        pipeline_steps = verdict.get("pipeline_steps", [])
        return await run_pipeline(PipelineRequest(steps=pipeline_steps, initial_input=enriched_input))

    elif agent_type == "ephemeral":
        # Spawn ephemeral agent locally (fallback path)
        spec = verdict.get("spec", {})
        result = await smart_spawn(
            task_description=spec.get("task", ""),
            input_data=enriched_input,
            user_context=spec.get("memory_context")
        )
        return result.get("output", {})

    return {"error": f"Unknown agent_type: {agent_type}"}


@app.post("/spawn")
async def spawn_and_execute(request: SpawnRequest):
    """
    KING Gateway: Delegates strategic decisions to orchestrator.

    Flow:
    1. Call orchestrator /king/decide for strategic decision
    2. If blocked → return immediately
    3. Execute verdict (registered/pipeline/ephemeral)
    4. Log + reflect

    Fallback: If orchestrator unreachable, use local smart_spawn
    """
    start_time = time.time()
    user_id = request.input_data.get("user_id")
    session_id = request.input_data.get("session_id")

    # === Step 1: Call Orchestrator for Decision ===
    orchestrator_response = await _call_orchestrator_decide(
        user_id=user_id,
        message=request.task_description,
        session_id=session_id,
        context=request.user_context
    )

    # === Step 2: Handle Orchestrator Response or Fallback ===
    if orchestrator_response:
        action = orchestrator_response.get("action")
        trace_id = orchestrator_response.get("trace_id", "unknown")
        reasoning = orchestrator_response.get("reasoning", "")

        # BLOCKED by Guardian
        if action == "blocked":
            return {
                "decision": "blocked",
                "reasoning": reasoning,
                "agent_spec": None,
                "output": {"error": reasoning},
                "success": False,
                "trace_id": trace_id,
                "duration_ms": int((time.time() - start_time) * 1000)
            }

        verdict = orchestrator_response.get("verdict")
        enriched_input = orchestrator_response.get("enriched_input", request.input_data)

        # Execute verdict
        output = await _execute_verdict(verdict, enriched_input)
        decision = verdict.get("agent_type", "unknown")
        agent_name = verdict.get("agent_name", "unknown")
        agent_spec = verdict

    else:
        # Fallback: local smart_spawn (orchestrator unreachable)
        logger.warning("Orchestrator unreachable, using local smart_spawn")
        result = await smart_spawn(
            task_description=request.task_description,
            input_data=request.input_data,
            user_context=request.user_context
        )
        decision = result.get("decision", "spawned")
        agent_spec = result.get("agent_spec", {})
        output = result.get("output", {})
        reasoning = result.get("reasoning", "")
        agent_name = agent_spec.get("agent_name", "unknown") if isinstance(agent_spec, dict) else "unknown"
        trace_id = "local"

    # === Step 3: Determine Success ===
    success = isinstance(output, dict) and "error" not in output
    error_msg = output.get("error") if isinstance(output, dict) else None
    duration_ms = int((time.time() - start_time) * 1000)

    # === Step 4: Log Execution ===
    state_manager.log_run(
        agent_name=f"{decision}:{agent_name}",
        input_data=request.input_data,
        output_data=output,
        success=success,
        error=error_msg,
        duration_ms=duration_ms
    )

    # === Step 5: Persist if Requested ===
    persisted = False
    if request.persist and success and decision == "ephemeral" and isinstance(agent_spec, dict):
        client = state_manager.get_client()
        if client:
            try:
                client.table("agent_specs").upsert({
                    "agent_name": agent_spec.get("agent_name"),
                    "purpose": agent_spec.get("purpose", ""),
                    "dna_rules": agent_spec.get("dna_rules", []),
                    "output_schema": agent_spec.get("output_schema", {}),
                    "version": "spawned-1.0"
                }).execute()
                persisted = True
            except Exception as e:
                logger.error(f"Failed to persist agent: {e}")

    # === Step 6: Self-reflection (non-blocking) ===
    asyncio.create_task(
        reflect_on_run(
            agent_name=f"{decision}:{agent_name}",
            input_data={"task": request.task_description, **request.input_data},
            output_data=output or {},
            success=success,
            error=error_msg,
            user_id=user_id,
            duration_ms=duration_ms
        )
    )

    return {
        "decision": decision,
        "reasoning": reasoning if 'reasoning' in dir() else "",
        "agent_spec": agent_spec,
        "output": output,
        "success": success,
        "persisted": persisted,
        "trace_id": trace_id if 'trace_id' in dir() else "local",
        "duration_ms": duration_ms
    }
