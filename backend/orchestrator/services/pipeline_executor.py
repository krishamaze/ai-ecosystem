"""
Pipeline Executor - Chains agents in dependency-validated sequences.

Features:
- Pre-validates pipeline against dependency map
- Executes agents in sequence, passing output as next input
- Records telemetry for each step
- Halts on failure or rejection verdict
"""

from typing import Dict, Any, List, Optional
from datetime import datetime
import uuid

from .agent_dependencies import validate_agent_can_call, run_dependency_health_check
from .supabase_client import supabase
from ..agents.agent_runner import AgentRunner
from ..agents.base_agent import AgentResponse


class PipelineExecutor:
    """Execute multi-agent pipelines with dependency validation."""
    
    def __init__(self):
        self.runner = AgentRunner()
    
    def validate_pipeline(self, steps: List[str]) -> Dict[str, Any]:
        """
        Validate that a pipeline sequence is legal per dependency map.
        Returns validation result with any errors.
        """
        # System health check first
        health = run_dependency_health_check()
        if not health["is_healthy"]:
            return {
                "valid": False,
                "error": f"System unhealthy: {health['errors']}"
            }
        
        # Check each handoff
        errors = []
        for i in range(len(steps) - 1):
            caller = steps[i]
            callee = steps[i + 1]
            if not validate_agent_can_call(caller, callee):
                errors.append(f"Invalid handoff: {caller} cannot call {callee}")
        
        if errors:
            return {"valid": False, "errors": errors}
        
        return {"valid": True, "steps": steps}
    
    def execute(
        self,
        pipeline_name: str,
        steps: List[str],
        initial_input: Dict[str, Any],
        task_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Execute a pipeline end-to-end.
        
        Args:
            pipeline_name: Human-readable pipeline identifier
            steps: Ordered list of agent roles to execute
            initial_input: Input for first agent
            task_id: Optional task ID for telemetry linkage
        
        Returns:
            Pipeline result with all step outputs and final verdict
        """
        pipeline_id = str(uuid.uuid4())[:8]
        started_at = datetime.utcnow()
        
        # Validate first
        validation = self.validate_pipeline(steps)
        if not validation.get("valid"):
            return {
                "pipeline_id": pipeline_id,
                "status": "validation_failed",
                "error": validation.get("error") or validation.get("errors"),
                "steps_completed": 0
            }
        
        results = []
        current_input = initial_input
        
        for i, agent_role in enumerate(steps):
            step_start = datetime.utcnow()

            try:
                # Execute agent - returns AgentResponse
                response: AgentResponse = self.runner.run(agent_role, current_input)

                # Extract output dict from AgentResponse
                output_dict = response.output or {}

                step_result = {
                    "step": i + 1,
                    "agent": agent_role,
                    "status": response.status,
                    "output": output_dict,
                    "confidence": response.confidence,
                    "duration_ms": int((datetime.utcnow() - step_start).total_seconds() * 1000)
                }
                results.append(step_result)

                # Check for agent error
                if response.status == "error":
                    raise Exception(response.error.get("details", "Agent returned error") if response.error else "Unknown error")

                # Record telemetry
                self._record_step_telemetry(
                    task_id=task_id,
                    pipeline_id=pipeline_id,
                    agent_role=agent_role,
                    step=i + 1,
                    success=True,
                    output=output_dict
                )

                # Check for rejection verdict (code_reviewer)
                if agent_role == "code_reviewer" and output_dict.get("verdict") == "REJECT":
                    return {
                        "pipeline_id": pipeline_id,
                        "status": "rejected",
                        "rejection_reason": output_dict.get("summary", "Code rejected by reviewer"),
                        "steps_completed": i + 1,
                        "results": results,
                        "duration_ms": int((datetime.utcnow() - started_at).total_seconds() * 1000)
                    }

                # Prepare input for next agent
                current_input = self._prepare_handoff(agent_role, steps[i + 1] if i + 1 < len(steps) else None, output_dict)
                
            except Exception as e:
                step_result = {
                    "step": i + 1,
                    "agent": agent_role,
                    "status": "error",
                    "error": str(e),
                    "duration_ms": int((datetime.utcnow() - step_start).total_seconds() * 1000)
                }
                results.append(step_result)
                
                self._record_step_telemetry(
                    task_id=task_id,
                    pipeline_id=pipeline_id,
                    agent_role=agent_role,
                    step=i + 1,
                    success=False,
                    error=str(e)
                )
                
                return {
                    "pipeline_id": pipeline_id,
                    "status": "error",
                    "error": str(e),
                    "steps_completed": i,
                    "results": results,
                    "duration_ms": int((datetime.utcnow() - started_at).total_seconds() * 1000)
                }
        
        return {
            "pipeline_id": pipeline_id,
            "status": "completed",
            "steps_completed": len(steps),
            "results": results,
            "final_output": results[-1]["output"] if results else None,
            "duration_ms": int((datetime.utcnow() - started_at).total_seconds() * 1000)
        }
    
    def _prepare_handoff(self, from_agent: str, to_agent: Optional[str], output: Dict) -> Dict:
        """Transform output for next agent's expected input format."""
        if to_agent is None:
            return output

        # code_writer -> code_reviewer: wrap code for review
        if from_agent == "code_writer" and to_agent == "code_reviewer":
            return {
                "code_to_review": output.get("code", ""),
                "language": output.get("language", "unknown"),
                "tests": output.get("tests", []),
                "context": "Generated by code_writer agent"
            }

        # Default: pass output as-is
        return {"previous_output": output}

    def _record_step_telemetry(
        self,
        task_id: Optional[str],
        pipeline_id: str,
        agent_role: str,
        step: int,
        success: bool,
        output: Optional[Dict] = None,
        error: Optional[str] = None,
        memory_used: Optional[bool] = None,
        memory_sources: Optional[List[str]] = None,
        rag_enabled: Optional[bool] = None,
        rag_query: Optional[str] = None,
        rag_source_count: Optional[int] = None
    ):
        """Record telemetry for a pipeline step."""
        try:
            record = {
                "task_id": task_id or f"pipeline-{pipeline_id}",
                "agent_role": agent_role,
                "success": success,
                "confidence_final": output.get("confidence") if output else None,
                "failure_reason": error,
                "human_feedback": f"pipeline:{pipeline_id}:step:{step}",
                "memory_used": memory_used,
                "memory_sources": memory_sources,
                "rag_enabled": rag_enabled,
                "rag_query": rag_query,
                "rag_source_count": rag_source_count,
            }
            supabase.table("task_telemetry").insert(record).execute()
        except Exception:
            pass  # Don't fail pipeline on telemetry error

