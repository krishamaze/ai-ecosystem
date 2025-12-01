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
import json

from .agent_dependencies import validate_agent_can_call, run_dependency_health_check
from .supabase_client import supabase
from ..agents.agent_runner import AgentRunner
from ..agents.base_agent import AgentResponse


class PipelineExecutor:
    """Execute multi-agent pipelines with dependency validation."""
    
    MAX_RETRIES = 3
    
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
    
    def execute_creation_pipeline(self, initial_request: str, task_id: Optional[str] = None) -> Dict[str, Any]:
        """
        Execute the Creation Council pipeline with correction loop.
        
        Flow:
        1. Spec Designer (Design)
        2. Guardian Minister (Safety Check)
        3. Validator Minister (Structure Check)
        
        If ministers block/reject, loop back to Spec Designer with error context.
        Max Retries: 3
        """
        pipeline_id = str(uuid.uuid4())[:8]
        if not task_id:
            task_id = f"creation-{pipeline_id}"
            
        current_request = initial_request
        error_context = ""
        retries = 0
        
        while retries <= self.MAX_RETRIES:
            print(f"DEBUG: Creation Loop Attempt {retries + 1}/{self.MAX_RETRIES + 1}")
            
            # --- Step 1: Spec Designer ---
            designer_input = {
                "request": current_request,
                "context": error_context
            }
            
            designer_resp = self._run_step(
                task_id, pipeline_id, "spec_designer", 
                designer_input, step_num=1 + (retries * 3)
            )
            
            if designer_resp["status"] != "success":
                return self._fail_pipeline(pipeline_id, "Spec Designer failed", designer_resp)
            
            designer_output = designer_resp["output"]
            mode = designer_output.get("mode")
            
            # If INTERVIEW mode, we stop and ask user (in a real system). 
            # For this pipeline, we treat it as a "success" but requiring user input, 
            # so we might return the question. 
            # The prompt says "If approved, return result". 
            # If INTERVIEW, it's not approved yet, but it's a valid stop state.
            if mode == "INTERVIEW":
                return {
                    "pipeline_id": pipeline_id,
                    "status": "clarification_needed",
                    "output": designer_output,
                    "retries": retries
                }
            
            spec = designer_output.get("spec", {})
            
            # --- Step 2: Guardian Minister ---
            # Check the generated spec for dangerous patterns
            guardian_input = {
                "content": json.dumps(spec),
                "context": "output" # Strict checking
            }
            
            guardian_resp = self._run_step(
                task_id, pipeline_id, "guardian_minister", 
                guardian_input, step_num=2 + (retries * 3)
            )
            
            guardian_output = guardian_resp["output"] or {}
            if guardian_output.get("verdict") == "BLOCKED":
                error_context = f"Guardian Blocked: {guardian_output.get('violation_type')} - {guardian_output.get('reason')}"
                retries += 1
                continue # Loop back
            
            # --- Step 3: Validator Minister ---
            validator_input = {
                "spec": spec
            }
            
            validator_resp = self._run_step(
                task_id, pipeline_id, "validator_minister", 
                validator_input, step_num=3 + (retries * 3)
            )
            
            validator_output = validator_resp["output"] or {}
            if validator_output.get("verdict") == "INVALID":
                issues = "; ".join(validator_output.get("issues", []))
                error_context = f"Validator Rejected: {issues}"
                retries += 1
                continue # Loop back

            # --- Success ---
            return {
                "pipeline_id": pipeline_id,
                "status": "success",
                "final_spec": spec,
                "retries": retries
            }
            
        # --- Max Retries Exceeded ---
        return {
            "pipeline_id": pipeline_id,
            "status": "failed",
            "error": "Max retries exceeded",
            "last_error_context": error_context,
            "retries": retries
        }

    def _run_step(self, task_id: str, pipeline_id: str, role: str, input_data: Dict, step_num: int) -> Dict:
        """Helper to run a single step and record telemetry."""
        try:
            response = self.runner.run(role, input_data)
            output = response.output or {}
            
            success = response.status == "success"
            
            self._record_step_telemetry(
                task_id=task_id,
                pipeline_id=pipeline_id,
                agent_role=role,
                step=step_num,
                success=success,
                output=output,
                error=str(response.error) if response.error else None
            )
            
            return {
                "status": response.status,
                "output": output,
                "error": response.error
            }
        except Exception as e:
            self._record_step_telemetry(
                task_id=task_id,
                pipeline_id=pipeline_id,
                agent_role=role,
                step=step_num,
                success=False,
                error=str(e)
            )
            return {"status": "error", "error": str(e), "output": {}}

    def _fail_pipeline(self, pipeline_id: str, reason: str, details: Dict) -> Dict:
        """Helper to construct failure response."""
        return {
            "pipeline_id": pipeline_id,
            "status": "failed",
            "error": reason,
            "details": details
        }

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
                "human_feedback": None,
                # "memory_used": memory_used,
                # "memory_sources": memory_sources,
                # "rag_enabled": rag_enabled,
                # "rag_query": rag_query,
                # "rag_source_count": rag_source_count,
            }
            supabase.table("task_telemetry").insert(record).execute()
        except Exception as e:
            print(f"TELEMETRY ERROR: {e}")
            pass  # Don't fail pipeline on telemetry error
