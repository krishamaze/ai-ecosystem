from fastapi import APIRouter, HTTPException, Header, Depends
from fastapi.responses import PlainTextResponse
from pydantic import BaseModel
from typing import Optional, List, Dict, Any
from datetime import datetime, timedelta
from ..agents.agent_runner import AgentRunner
from ..services.supabase_client import supabase
from ..services.dna_mutator import apply_proposal_mutation, _validate_specs, _write_specs_safely
from ..services.agent_dependencies import (
    run_dependency_health_check,
    get_dependency_graph_mermaid,
    validate_agent_can_call,
    AGENT_DEPENDENCIES,
)
from ..services.pipeline_executor import PipelineExecutor
from ..services.action_executor import ActionExecutor, ActionRequest, ActionType
from ..services.conversation_service import (
    ConversationService, ConverseRequest, ConverseResponse, Medium
)
from ..services.user_preferences import (
    get_user_preferences, update_user_preferences, UserPreferences
)
import json
import os
from pathlib import Path

router = APIRouter()
runner = AgentRunner()
pipeline_executor = PipelineExecutor()
action_executor = ActionExecutor()
conversation_service = ConversationService()

META_ADMIN_KEY = os.getenv("META_ADMIN_KEY", "")


def require_admin_key(x_admin_key: str = Header(..., alias="X-Admin-Key")):
    """Dependency to enforce admin key on mutation endpoints."""
    if not META_ADMIN_KEY:
        raise HTTPException(status_code=500, detail="META_ADMIN_KEY not configured")
    if x_admin_key != META_ADMIN_KEY:
        raise HTTPException(status_code=403, detail="Invalid admin key")
    return x_admin_key


class TelemetryInput(BaseModel):
    task_id: str
    agent_role: str
    success: bool
    time_taken_seconds: Optional[int] = None
    confidence_final: Optional[float] = None
    human_feedback: Optional[str] = None
    failure_reason: Optional[str] = None
    # New structured metrics
    human_override: Optional[bool] = False
    failure_category: Optional[str] = None  # formatting, factual, logic, performance, timeout, unknown
    dna_version: Optional[str] = None
    # Memory metrics
    memory_used: Optional[bool] = False
    memory_sources: Optional[List[str]] = None
    # RAG metrics
    rag_enabled: Optional[bool] = False
    rag_query: Optional[str] = None
    rag_source_count: Optional[int] = None


class ProposalAction(BaseModel):
    action: str  # 'approve' or 'reject'
    reviewed_by: str


@router.post("/telemetry")
def record_telemetry(data: TelemetryInput):
    """Record task outcome telemetry for learning."""
    result = supabase.table("task_telemetry").insert({
        "task_id": data.task_id,
        "agent_role": data.agent_role,
        "success": data.success,
        "time_taken_seconds": data.time_taken_seconds,
        "confidence_final": data.confidence_final,
        "human_feedback": data.human_feedback,
        "failure_reason": data.failure_reason,
        "human_override": data.human_override,
        "failure_category": data.failure_category,
        "dna_version": data.dna_version,
        "memory_used": data.memory_used,
        "memory_sources": data.memory_sources,
        "rag_enabled": data.rag_enabled,
        "rag_query": data.rag_query,
        "rag_source_count": data.rag_source_count
    }).execute()
    return {"telemetry_id": result.data[0]["id"]}


@router.post("/audit")
def run_audit(days: int = 7):
    """Run agent_auditor on recent telemetry."""
    end_time = datetime.utcnow()
    start_time = end_time - timedelta(days=days)
    
    # Fetch telemetry
    telemetry = supabase.table("task_telemetry") \
        .select("*") \
        .gte("created_at", start_time.isoformat()) \
        .execute()
    
    # Fetch agent runs for context
    runs = supabase.table("agent_runs") \
        .select("*") \
        .gte("created_at", start_time.isoformat()) \
        .execute()
    
    if not telemetry.data and not runs.data:
        return {"status": "no_data", "message": "No telemetry or runs in time range"}
    
    # Run auditor agent
    audit_input = {
        "time_range": {"start": start_time.isoformat(), "end": end_time.isoformat()},
        "telemetry": telemetry.data or [],
        "agent_runs": runs.data or []
    }
    
    response = runner.run("agent_auditor", audit_input)
    
    if response.status != "success":
        return {"status": "error", "error": response.error}
    
    # Store audit report
    output = response.output
    report = supabase.table("audit_reports").insert({
        "time_range_start": start_time.isoformat(),
        "time_range_end": end_time.isoformat(),
        "agents_analyzed": output.get("agents_analyzed", []),
        "total_runs": output.get("risk_summary", {}).get("total_runs", 0),
        "failure_count": output.get("risk_summary", {}).get("failures", 0),
        "low_confidence_count": output.get("risk_summary", {}).get("low_confidence_count", 0),
        "findings": output.get("findings", []),
        "recommendations": output.get("recommendations", [])
    }).execute()
    
    return {"audit_id": report.data[0]["id"], "output": output}


@router.post("/propose/{audit_id}")
def generate_proposals(audit_id: str):
    """Run meta_reasoner to propose DNA changes based on audit."""
    # Fetch audit report
    audit = supabase.table("audit_reports") \
        .select("*") \
        .eq("id", audit_id) \
        .single() \
        .execute()
    
    if not audit.data:
        raise HTTPException(status_code=404, detail="Audit not found")
    
    # Run meta_reasoner
    response = runner.run("meta_reasoner", {
        "audit_id": audit_id,
        "findings": audit.data["findings"],
        "recommendations": audit.data["recommendations"]
    })
    
    if response.status != "success":
        return {"status": "error", "error": response.error}
    
    output = response.output
    proposals = []
    
    # Store each proposal
    for change in output.get("suggested_changes", []):
        result = supabase.table("dna_proposals").insert({
            "audit_report_id": audit_id,
            "target_role": change.get("target_role"),
            "change_type": change.get("change_type"),
            "change_content": change.get("content"),
            "risk_level": output.get("risk_level", "medium"),
            "confidence": output.get("confidence", 0.5),
            "rollback_strategy": output.get("rollback_strategy", "Revert to previous DNA version")
        }).execute()
        proposals.append(result.data[0])
    
    return {"proposals": proposals, "meta_output": output}


@router.get("/proposals")
def list_proposals(status: str = "pending"):
    """List DNA change proposals."""
    result = supabase.table("dna_proposals") \
        .select("*") \
        .eq("status", status) \
        .order("created_at", desc=True) \
        .execute()
    return {"proposals": result.data}


@router.post("/proposals/{proposal_id}/review")
def review_proposal(proposal_id: str, action: ProposalAction, _: str = Depends(require_admin_key)):
    """Approve or reject a DNA proposal. Requires X-Admin-Key header."""
    if action.action not in ["approve", "reject"]:
        raise HTTPException(status_code=400, detail="Action must be 'approve' or 'reject'")
    
    new_status = "approved" if action.action == "approve" else "rejected"
    
    supabase.table("dna_proposals") \
        .update({
            "status": new_status,
            "reviewed_by": action.reviewed_by,
            "reviewed_at": datetime.utcnow().isoformat()
        }) \
        .eq("id", proposal_id) \
        .execute()
    
    return {"status": new_status, "proposal_id": proposal_id}


class ApplyRequest(BaseModel):
    approved_by: str


class RollbackRequest(BaseModel):
    requested_by: str


@router.post("/proposals/{proposal_id}/apply")
def apply_proposal(proposal_id: str, request: ApplyRequest, _: str = Depends(require_admin_key)):
    """Apply an approved DNA proposal - mutates agent_specs.json. Requires X-Admin-Key header."""
    try:
        result = apply_proposal_mutation(proposal_id, request.approved_by)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

    return {
        "status": "dna_updated",
        "version": result["version"],
        "target_role": result["target_role"],
        "change_type": result["change_type"]
    }


@router.post("/rollback/{version}")
def rollback_dna(version: str, request: RollbackRequest, _: str = Depends(require_admin_key)):
    """Rollback DNA to a previous version snapshot. Requires X-Admin-Key header."""
    record = supabase.table("dna_versions").select("*").eq("version", version).single().execute()

    if not record.data:
        raise HTTPException(status_code=404, detail="Version not found")

    snapshot = record.data["snapshot_json"]

    # Validate before overwrite
    try:
        _validate_specs(snapshot)
        _write_specs_safely(snapshot)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=f"Invalid snapshot: {str(e)}")

    # Mark the proposal as rolled back if exists
    if record.data.get("proposal_id"):
        supabase.table("dna_proposals").update({
            "status": "rolled_back"
        }).eq("id", record.data["proposal_id"]).execute()

    # Hot reload agents
    from ..agents.agent_factory import AgentFactory
    reload_result = AgentFactory.reload()

    return {
        "status": "rolled_back",
        "version": version,
        "rolled_back_by": request.requested_by,
        "agents_reloaded": reload_result
    }


@router.post("/reload")
def reload_agents(_: str = Depends(require_admin_key)):
    """Force reload agent specs from disk. Requires X-Admin-Key header."""
    from ..agents.agent_factory import AgentFactory
    result = AgentFactory.reload()
    return {"status": "reloaded", **result}


@router.get("/analytics/agents")
def get_agent_performance():
    """Get agent performance metrics from view."""
    result = supabase.table("agent_performance").select("*").execute()
    return {"agents": result.data}


@router.get("/analytics/dna")
def get_dna_performance():
    """Get DNA version performance comparison."""
    result = supabase.table("dna_version_performance").select("*").execute()
    return {"versions": result.data}


@router.get("/analytics/failures")
def get_failure_analysis():
    """Get failure category breakdown."""
    result = supabase.table("failure_analysis").select("*").execute()
    return {"failures": result.data}


# ============================================================
# DEPENDENCY MAP ENDPOINTS
# ============================================================

@router.get("/dependencies/health")
def check_dependency_health():
    """
    Run dependency health check. Must pass before pipelines or proposals.
    Returns is_healthy flag and any errors.
    """
    return run_dependency_health_check()


@router.get("/dependencies/map")
def get_dependency_map():
    """Return the canonical agent dependency map."""
    return {
        "dependencies": AGENT_DEPENDENCIES,
        "description": "agent -> [agents it can call]"
    }


@router.get("/dependencies/mermaid", response_class=PlainTextResponse)
def get_dependency_mermaid():
    """Return Mermaid diagram syntax for dependency visualization."""
    return get_dependency_graph_mermaid()


@router.get("/dependencies/can-call")
def check_agent_can_call(caller: str, callee: str):
    """Check if caller agent is allowed to invoke callee agent."""
    allowed = validate_agent_can_call(caller, callee)
    return {
        "caller": caller,
        "callee": callee,
        "allowed": allowed,
        "reason": "In dependency map" if allowed else f"{caller} cannot call {callee}"
    }


# ============================================================
# PIPELINE ENDPOINTS
# ============================================================

class PipelineRequest(BaseModel):
    pipeline_name: str
    steps: List[str]
    input: Dict[str, Any]
    task_id: Optional[str] = None


@router.post("/pipeline/validate")
def validate_pipeline(request: PipelineRequest):
    """Validate a pipeline before execution."""
    result = pipeline_executor.validate_pipeline(request.steps)
    return result


@router.post("/pipeline/execute")
def execute_pipeline(request: PipelineRequest):
    """Execute a multi-agent pipeline."""
    result = pipeline_executor.execute(
        pipeline_name=request.pipeline_name,
        steps=request.steps,
        initial_input=request.input,
        task_id=request.task_id
    )
    return result


# Predefined pipelines for common workflows
PREDEFINED_PIPELINES = {
    "code_generation": {
        "steps": ["code_writer", "code_reviewer"],
        "description": "Generate code and review for quality/security"
    },
    "video_content": {
        "steps": ["video_planner", "script_writer"],
        "description": "Plan video structure and generate script"
    }
}


@router.get("/pipeline/templates")
def list_pipeline_templates():
    """List available predefined pipeline templates."""
    return {"templates": PREDEFINED_PIPELINES}


@router.post("/pipeline/run/{template_name}")
def run_predefined_pipeline(template_name: str, input: Dict[str, Any]):
    """Run a predefined pipeline template."""
    if template_name not in PREDEFINED_PIPELINES:
        raise HTTPException(status_code=404, detail=f"Template '{template_name}' not found")

    template = PREDEFINED_PIPELINES[template_name]
    result = pipeline_executor.execute(
        pipeline_name=template_name,
        steps=template["steps"],
        initial_input=input
    )
    return result


# ============================================================
# ACTION EXECUTION ENDPOINTS
# ============================================================

class ExecuteActionRequest(BaseModel):
    pipeline_id: str
    action_type: str  # deploy_code, store_draft, store_script, mark_production, reject
    executed_by: str
    artifact_data: Dict[str, Any]
    force: bool = False


@router.post("/actions/execute")
def execute_action(request: ExecuteActionRequest, admin_key: str = Depends(require_admin_key)):
    """Execute a deployment action. Requires admin authentication."""
    try:
        action_type = ActionType(request.action_type)
    except ValueError:
        raise HTTPException(status_code=400, detail=f"Invalid action_type: {request.action_type}")

    action_request = ActionRequest(
        pipeline_id=request.pipeline_id,
        action_type=action_type,
        executed_by=request.executed_by,
        artifact_data=request.artifact_data,
        force=request.force
    )

    result = action_executor.execute(action_request)

    if not result.get("success"):
        raise HTTPException(status_code=400, detail=result.get("error"))

    return result


@router.get("/actions/pending")
def list_pending_actions():
    """List artifacts pending action (drafts, pending review)."""
    drafts = supabase.table("deployed_artifacts").select("*").eq("status", "draft").execute()
    pending = supabase.table("deployed_artifacts").select("*").eq("status", "pending").execute()

    return {
        "drafts": drafts.data,
        "pending": pending.data,
        "total": len(drafts.data) + len(pending.data)
    }


@router.get("/actions/deployed")
def list_deployed_artifacts():
    """List successfully deployed artifacts."""
    result = supabase.table("deployed_artifacts").select("*").eq("status", "deployed").order("deployed_at", desc=True).limit(50).execute()
    return {"deployed": result.data, "count": len(result.data)}


@router.get("/actions/audit")
def get_action_audit_log(limit: int = 50):
    """Get audit log of all actions."""
    result = supabase.table("action_audit_log").select("*").order("created_at", desc=True).limit(limit).execute()
    return {"audit_log": result.data}


@router.post("/pipeline/execute-and-deploy")
def execute_pipeline_and_deploy(request: PipelineRequest, executed_by: str, admin_key: str = Depends(require_admin_key)):
    """Execute pipeline and auto-deploy if reviewer approves with high confidence."""
    # Execute the pipeline
    pipeline_result = pipeline_executor.execute(
        pipeline_name=request.pipeline_name,
        steps=request.steps,
        initial_input=request.input,
        task_id=request.task_id
    )

    if pipeline_result.get("status") != "completed":
        return pipeline_result

    # Check if we should auto-deploy
    results = pipeline_result.get("results", [])
    code_output = None
    review_output = None

    for r in results:
        if r.get("agent") == "code_writer":
            code_output = r.get("output", {})
        elif r.get("agent") == "code_reviewer":
            review_output = r.get("output", {})

    if not code_output or not review_output:
        pipeline_result["action"] = "no_action"
        pipeline_result["reason"] = "Missing code or review output"
        return pipeline_result

    suggested_action = review_output.get("suggested_action", "MANUAL_REVIEW")
    verdict = review_output.get("verdict", "")
    security_score = review_output.get("security_score", 0)

    # Determine action based on review
    if suggested_action == "DEPLOY" and verdict == "APPROVE" and security_score >= 0.8:
        # Auto-deploy
        action_result = action_executor.execute(ActionRequest(
            pipeline_id=pipeline_result["pipeline_id"],
            action_type=ActionType.DEPLOY_CODE,
            executed_by=executed_by,
            artifact_data={
                **code_output,
                **review_output
            }
        ))
        pipeline_result["action"] = "deployed"
        pipeline_result["deployment"] = action_result
    elif suggested_action == "STORE_DRAFT" or review_output.get("confidence", 1) < 0.6:
        # Store as draft
        action_result = action_executor.execute(ActionRequest(
            pipeline_id=pipeline_result["pipeline_id"],
            action_type=ActionType.STORE_DRAFT,
            executed_by=executed_by,
            artifact_data={
                **code_output,
                **review_output,
                "type": "code"
            }
        ))
        pipeline_result["action"] = "stored_draft"
        pipeline_result["draft"] = action_result
    else:
        pipeline_result["action"] = "manual_review_required"
        pipeline_result["suggested_action"] = suggested_action
        pipeline_result["reason"] = f"Verdict: {verdict}, Security: {security_score}"

    return pipeline_result


# ============================================================
# UNIFIED CONVERSATION ENDPOINT
# ============================================================

class ConverseRequestAPI(BaseModel):
    """API model for /converse endpoint."""
    message: str
    medium: str = "api"  # telegram, dashboard, api
    context: Optional[Dict[str, Any]] = None
    user_id: Optional[str] = None


@router.post("/converse")
def converse(request: ConverseRequestAPI):
    """
    Unified conversation endpoint for all interaction mediums.

    - Telegram bot: medium="telegram"
    - React dashboard: medium="dashboard"
    - API clients: medium="api"

    Returns structured response with UI elements that each frontend renders appropriately.
    """
    try:
        medium = Medium(request.medium)
    except ValueError:
        medium = Medium.API

    converse_request = ConverseRequest(
        message=request.message,
        medium=medium,
        context=request.context,
        user_id=request.user_id
    )

    response = conversation_service.process(converse_request)

    return {
        "reply": response.reply,
        "action": response.action,
        "intent": response.intent.value,
        "trace_id": response.trace_id,
        "ui_elements": [el.model_dump() for el in response.ui_elements],
        "data": response.data,
        "next_context": response.next_context
    }


@router.post("/converse/action")
def converse_action(
    action: str,
    payload: Dict[str, Any],
    user_id: str,
    admin_key: Optional[str] = Header(None, alias="X-Admin-Key")
):
    """
    Execute an action from a UI element payload.
    Used when user clicks a button from /converse response.
    """
    # Actions that require admin auth
    protected_actions = ["deploy_code", "deploy", "mark_production"]

    if action in protected_actions:
        if not admin_key or admin_key != META_ADMIN_KEY:
            raise HTTPException(status_code=401, detail="Admin key required for this action")

    # Route action
    if action == "deploy_code" or action == "deploy":
        pipeline_id = payload.get("pipeline_id")
        if not pipeline_id:
            raise HTTPException(status_code=400, detail="pipeline_id required")

        # Fetch pipeline data (would come from stored result in production)
        return {
            "reply": f"Deployment initiated for pipeline {pipeline_id}",
            "action": "complete",
            "data": {"pipeline_id": pipeline_id, "status": "deploying"}
        }

    elif action in ["generate_code", "generate_video", "check_status"]:
        # Re-route to converse with appropriate intent trigger
        return converse(ConverseRequestAPI(
            message=f"I want to {action.replace('_', ' ')}",
            medium="api",
            context=payload,
            user_id=user_id
        ))

    elif action == "cancel":
        return {"reply": "Action cancelled.", "action": "complete"}

    else:
        return {"reply": f"Unknown action: {action}", "action": "error"}


# ============================================================
# USER PREFERENCES ENDPOINTS
# ============================================================

class UserPreferencesUpdate(BaseModel):
    """Allowed fields for user preference updates."""
    display_name: Optional[str] = None
    preferred_language: Optional[str] = None
    code_style: Optional[str] = None
    include_tests: Optional[bool] = None
    include_docstrings: Optional[bool] = None
    content_tone: Optional[str] = None
    target_audience: Optional[str] = None
    auto_deploy_threshold: Optional[float] = None
    require_confirmation: Optional[bool] = None
    verbose_responses: Optional[bool] = None


@router.get("/user/{user_id}/preferences")
def get_preferences(user_id: str):
    """Get user preferences."""
    prefs = get_user_preferences(user_id)
    return prefs.model_dump()


@router.put("/user/{user_id}/preferences")
def update_preferences(user_id: str, updates: UserPreferencesUpdate):
    """Update user preferences."""
    # Filter out None values
    update_dict = {k: v for k, v in updates.model_dump().items() if v is not None}

    if not update_dict:
        raise HTTPException(status_code=400, detail="No valid fields to update")

    prefs = update_user_preferences(user_id, update_dict)
    return prefs.model_dump()


@router.get("/user/{user_id}/context")
def get_user_context_endpoint(user_id: str, session_id: Optional[str] = None):
    """Get user's current conversation context."""
    from ..services.user_preferences import get_user_context

    context = get_user_context(user_id, session_id)
    return {"user_id": user_id, "context": context}


@router.delete("/user/{user_id}/context")
def clear_user_context(user_id: str):
    """Clear user's conversation context."""
    supabase.table("user_context").delete().eq("user_id", user_id).execute()
    return {"status": "cleared", "user_id": user_id}


# ============================================================
# TELEGRAM WEBHOOK ENDPOINT
# ============================================================

@router.post("/telegram/webhook")
async def telegram_webhook(request: Dict[str, Any]):
    """
    Webhook endpoint for Telegram Bot API.

    Set webhook via:
    https://api.telegram.org/bot<TOKEN>/setWebhook?url=https://your-domain/meta/telegram/webhook
    """
    from ..services.telegram_bot import process_webhook_update

    try:
        await process_webhook_update(request)
        return {"ok": True}
    except Exception as e:
        return {"ok": False, "error": str(e)}


@router.get("/telegram/status")
def telegram_status():
    """Check Telegram bot configuration status."""
    token = os.getenv("TELEGRAM_BOT_TOKEN", "")
    return {
        "configured": bool(token),
        "token_prefix": token[:10] + "..." if token else None,
        "webhook_endpoint": "/meta/telegram/webhook"
    }


# ============================================================
# FEEDBACK ENDPOINTS
# ============================================================

class FeedbackRequest(BaseModel):
    trace_id: str
    feedback_type: str  # 'positive', 'negative', 'report'
    feedback_text: Optional[str] = None


@router.post("/feedback")
def submit_feedback(request: FeedbackRequest, user_id: str = None):
    """Submit feedback for a conversation turn."""
    supabase.table("conversation_feedback").update({
        "feedback_type": request.feedback_type,
        "feedback_text": request.feedback_text
    }).eq("trace_id", request.trace_id).execute()

    return {"status": "recorded", "trace_id": request.trace_id}


@router.get("/analytics/success-rates")
def get_success_rates():
    """Get intent success rates for the last 7 days."""
    result = supabase.rpc("exec_sql", {
        "query": """
            SELECT intent, COUNT(*) as total,
                   SUM(CASE WHEN success THEN 1 ELSE 0 END) as successful,
                   ROUND(100.0 * SUM(CASE WHEN success THEN 1 ELSE 0 END) / COUNT(*), 2) as rate
            FROM conversation_feedback
            WHERE created_at > now() - interval '7 days'
            GROUP BY intent ORDER BY total DESC
        """
    }).execute()
    return result.data if result.data else []


@router.get("/analytics/daily-usage")
def get_daily_usage():
    """Get daily request counts."""
    result = supabase.table("conversation_feedback").select(
        "created_at", count="exact"
    ).gte("created_at", "now() - interval '7 days'").execute()
    return {"total_requests_7d": result.count}