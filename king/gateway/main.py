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

app = FastAPI(title="KING Gateway", version="1.3.0")
state_manager = StateManager()

# Initialize Mem0 client and Memory Resolver
mem0_api_key = os.getenv("MEM0_API_KEY")
if not mem0_api_key:
    print("Warning: MEM0_API_KEY is not set. Memory functions will be disabled.")
    mem0_client = None
else:
    mem0_client = MemoryClient(api_key=mem0_api_key)

entity_resolver = EntityResolver()
memory_resolver = MemoryResolver(mem0_client=mem0_client, entity_resolver=entity_resolver)

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
    if user_id and agent_name != "memory_selector":
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


@app.post("/spawn")
async def spawn_and_execute(request: SpawnRequest):
    """
    KING's brain: Smart routing for agent tasks.
    - Reuses existing agents when possible
    - Spawns new agents when needed
    - Coordinates teams for complex tasks
    """
    start_time = time.time()
    user_id = request.input_data.get("user_id")

    # 1. SMART SPAWN: AI decides reuse/spawn/team
    result = await smart_spawn(
        task_description=request.task_description,
        input_data=request.input_data,
        user_context=request.user_context
    )

    decision = result.get("decision", "spawned")
    agent_spec = result.get("agent_spec", {})
    output = result.get("output", {})
    reasoning = result.get("reasoning", "")

    # Handle different decision types
    if decision == "team":
        team_results = result.get("team_results", [])
        success = bool(output)
        agent_name = "team_coordinator"
    elif decision in ("system", "memory"):
        # System queries (list agents, memory) - no agent spawned
        team_results = None
        success = True
        agent_name = agent_spec.get("agent_name", decision)
    else:
        success = isinstance(output, dict) and ("error" not in output or output.get("confidence", 0) > 0)
        agent_name = agent_spec.get("agent_name", "unknown") if isinstance(agent_spec, dict) else "unknown"
        team_results = None

    duration_ms = int((time.time() - start_time) * 1000)
    error_msg = output.get("error") if isinstance(output, dict) else None

    # 2. Log execution
    state_manager.log_run(
        agent_name=f"{decision}:{agent_name}",
        input_data=request.input_data,
        output_data=output,
        success=success,
        error=error_msg,
        duration_ms=duration_ms
    )

    # 3. Persist agent if requested and successful (only for spawned)
    persisted = False
    if request.persist and success and decision == "spawned" and isinstance(agent_spec, dict):
        client = state_manager.get_client()
        if client:
            try:
                client.table("agent_specs").upsert({
                    "agent_name": agent_spec.get("agent_name"),
                    "purpose": agent_spec.get("purpose"),
                    "dna_rules": agent_spec.get("dna_rules"),
                    "output_schema": agent_spec.get("output_schema"),
                    "version": "spawned-1.0"
                }).execute()
                persisted = True
            except Exception as e:
                print(f"Failed to persist agent: {e}")

    # 4. Self-reflection
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
        "reasoning": reasoning,
        "agent_spec": agent_spec,
        "team_results": team_results,
        "output": output,
        "success": success,
        "persisted": persisted,
        "duration_ms": duration_ms
    }
