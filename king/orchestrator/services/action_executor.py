"""
Action Executor - Executes deployment decisions from pipeline outputs.
Turns AI suggestions into real system changes with human gate.
"""
from typing import Dict, Any, Optional, Literal
from datetime import datetime
from pathlib import Path
from pydantic import BaseModel, field_validator
from enum import Enum
import json
import os

from .supabase_client import supabase


class ActionType(str, Enum):
    DEPLOY_CODE = "deploy_code"
    STORE_DRAFT = "store_draft"
    STORE_SCRIPT = "store_script"
    MARK_PRODUCTION = "mark_production"
    REJECT = "reject"


class ActionRequest(BaseModel):
    pipeline_id: str
    action_type: ActionType
    executed_by: str
    artifact_data: Dict[str, Any]
    force: bool = False  # Override automated checks
    
    @field_validator('executed_by')
    @classmethod
    def validate_executor(cls, v):
        if not v or len(v) < 2:
            raise ValueError("executed_by must identify the approver")
        return v


# Deployment paths (relative to workspace)
DEPLOY_PATHS = {
    "code": "deployed/code",
    "script": "deployed/scripts",
    "config": "deployed/config"
}


class ActionExecutor:
    """Executes approved actions from pipeline outputs."""
    
    def __init__(self):
        self.workspace_root = Path(os.getenv("WORKSPACE_ROOT", "/app/workspace"))
    
    def execute(self, request: ActionRequest) -> Dict[str, Any]:
        """Execute an action with full audit trail."""
        started_at = datetime.utcnow()
        
        # Route to appropriate handler
        handlers = {
            ActionType.DEPLOY_CODE: self._deploy_code,
            ActionType.STORE_DRAFT: self._store_draft,
            ActionType.STORE_SCRIPT: self._store_script,
            ActionType.MARK_PRODUCTION: self._mark_production,
            ActionType.REJECT: self._reject_artifact,
        }
        
        handler = handlers.get(request.action_type)
        if not handler:
            return {"success": False, "error": f"Unknown action: {request.action_type}"}
        
        try:
            result = handler(request)
            self._log_action(request, result)
            result["duration_ms"] = int((datetime.utcnow() - started_at).total_seconds() * 1000)
            return result
        except Exception as e:
            error_result = {"success": False, "error": str(e)}
            self._log_action(request, error_result)
            return error_result
    
    def _deploy_code(self, request: ActionRequest) -> Dict[str, Any]:
        """Deploy code artifact to filesystem."""
        data = request.artifact_data
        
        # Validate review scores
        security_score = data.get("security_score", 0)
        verdict = data.get("verdict", "")
        
        if not request.force:
            if verdict != "APPROVE":
                return {"success": False, "error": f"Cannot deploy: verdict is {verdict}, not APPROVE"}
            if security_score < 0.7:
                return {"success": False, "error": f"Cannot deploy: security_score {security_score} < 0.7"}
        
        # Prepare file
        code = data.get("code", "")
        language = data.get("language", "python")
        filename = data.get("filename") or f"generated_{request.pipeline_id}.{self._get_extension(language)}"
        
        # Write to deployed directory
        deploy_dir = self.workspace_root / DEPLOY_PATHS["code"] / language
        deploy_dir.mkdir(parents=True, exist_ok=True)
        file_path = deploy_dir / filename
        
        file_path.write_text(code)
        
        # Record in database
        artifact_id = self._record_artifact(
            pipeline_id=request.pipeline_id,
            artifact_type="code",
            file_path=str(file_path),
            content=code,
            language=language,
            verdict=verdict,
            security_score=security_score,
            quality_score=data.get("quality_score", 0),
            status="deployed",
            deployed_by=request.executed_by
        )
        
        return {
            "success": True,
            "action": "deploy_code",
            "artifact_id": artifact_id,
            "file_path": str(file_path),
            "language": language,
            "deployed_by": request.executed_by
        }
    
    def _store_draft(self, request: ActionRequest) -> Dict[str, Any]:
        """Store as draft for later review."""
        data = request.artifact_data
        
        artifact_id = self._record_artifact(
            pipeline_id=request.pipeline_id,
            artifact_type=data.get("type", "code"),
            file_path="",
            content=data.get("code") or json.dumps(data.get("content", {})),
            language=data.get("language"),
            verdict=data.get("verdict"),
            security_score=data.get("security_score"),
            quality_score=data.get("quality_score"),
            status="draft",
            deployed_by=None
        )
        
        return {
            "success": True,
            "action": "store_draft",
            "artifact_id": artifact_id,
            "status": "draft",
            "message": "Stored as draft - requires manual review"
        }
    
    def _store_script(self, request: ActionRequest) -> Dict[str, Any]:
        """Store approved script content."""
        data = request.artifact_data
        content = data.get("script_blocks") or data.get("content", {})

        result = supabase.table("draft_scripts").insert({
            "pipeline_id": request.pipeline_id,
            "script_type": data.get("script_type", "video"),
            "content": content,
            "confidence": data.get("confidence", 0),
            "status": "approved",
            "approved_by": request.executed_by,
            "approved_at": datetime.utcnow().isoformat()
        }).execute()

        script_id = result.data[0]["id"] if result.data else None

        return {
            "success": True,
            "action": "store_script",
            "script_id": script_id,
            "status": "approved"
        }

    def _mark_production(self, request: ActionRequest) -> Dict[str, Any]:
        """Mark existing artifact as production-ready."""
        artifact_id = request.artifact_data.get("artifact_id")
        if not artifact_id:
            return {"success": False, "error": "artifact_id required"}

        supabase.table("deployed_artifacts").update({
            "status": "deployed",
            "deployed_at": datetime.utcnow().isoformat(),
            "deployed_by": request.executed_by
        }).eq("id", artifact_id).execute()

        return {
            "success": True,
            "action": "mark_production",
            "artifact_id": artifact_id,
            "status": "deployed"
        }

    def _reject_artifact(self, request: ActionRequest) -> Dict[str, Any]:
        """Reject and archive artifact."""
        artifact_id = request.artifact_data.get("artifact_id")
        reason = request.artifact_data.get("reason", "Rejected by reviewer")

        if artifact_id:
            supabase.table("deployed_artifacts").update({
                "status": "rejected"
            }).eq("id", artifact_id).execute()

        return {
            "success": True,
            "action": "reject",
            "artifact_id": artifact_id,
            "reason": reason
        }

    def _record_artifact(self, pipeline_id: str, artifact_type: str, file_path: str,
                         content: str, language: Optional[str], verdict: Optional[str],
                         security_score: Optional[float], quality_score: Optional[float],
                         status: str, deployed_by: Optional[str]) -> str:
        """Record artifact in database."""
        data = {
            "pipeline_id": pipeline_id,
            "artifact_type": artifact_type,
            "file_path": file_path,
            "content": content,
            "language": language,
            "reviewer_verdict": verdict,
            "security_score": security_score,
            "quality_score": quality_score,
            "status": status
        }

        if status == "deployed" and deployed_by:
            data["deployed_at"] = datetime.utcnow().isoformat()
            data["deployed_by"] = deployed_by

        result = supabase.table("deployed_artifacts").insert(data).execute()
        return result.data[0]["id"] if result.data else None

    def _log_action(self, request: ActionRequest, result: Dict[str, Any]):
        """Audit log for all actions."""
        try:
            supabase.table("action_audit_log").insert({
                "action_type": request.action_type.value,
                "pipeline_id": request.pipeline_id,
                "artifact_id": result.get("artifact_id"),
                "executed_by": request.executed_by,
                "previous_state": None,
                "new_state": result
            }).execute()
        except Exception:
            pass  # Don't fail action on audit log error

    def _get_extension(self, language: str) -> str:
        """Get file extension for language."""
        extensions = {
            "python": "py",
            "javascript": "js",
            "typescript": "ts",
            "go": "go",
            "rust": "rs",
            "java": "java",
            "sql": "sql"
        }
        return extensions.get(language.lower(), "txt")

