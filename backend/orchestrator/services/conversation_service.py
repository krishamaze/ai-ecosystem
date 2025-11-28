"""
Conversation Service - Unified entry point for all interaction mediums.
Detects intent, dispatches agents, returns UI-agnostic structured responses.
"""
from typing import Dict, Any, Optional, List, Literal
from pydantic import BaseModel
from enum import Enum
from datetime import datetime
import re
import hashlib
import logging

from ..agents.agent_runner import AgentRunner
from .pipeline_executor import PipelineExecutor
from .action_executor import ActionExecutor, ActionRequest, ActionType
from .user_preferences import (
    get_user_preferences, increment_request_count,
    get_user_context, save_user_context, UserPreferences
)
from .guardrails import RequestGuard, safe_llm_response
from .retrieval_service import RetrievalService

logger = logging.getLogger(__name__)


class Medium(str, Enum):
    TELEGRAM = "telegram"
    DASHBOARD = "dashboard"
    API = "api"


class Intent(str, Enum):
    GENERATE_CODE = "generate_code"
    GENERATE_VIDEO = "generate_video"
    REVIEW_CODE = "review_code"
    DEPLOY = "deploy"
    CHECK_STATUS = "check_status"
    LIST_TASKS = "list_tasks"
    CLARIFY = "clarify"
    UNKNOWN = "unknown"


class UIElement(BaseModel):
    type: Literal["button", "code_block", "table", "progress", "text"]
    label: Optional[str] = None
    payload: Optional[Dict[str, Any]] = None
    content: Optional[Any] = None


class ConverseRequest(BaseModel):
    message: str
    medium: Medium = Medium.API
    context: Optional[Dict[str, Any]] = None
    user_id: Optional[str] = None


class ConverseResponse(BaseModel):
    reply: str
    action: str
    intent: Intent
    trace_id: Optional[str] = None
    ui_elements: List[UIElement] = []
    data: Optional[Dict[str, Any]] = None
    next_context: Optional[Dict[str, Any]] = None


# Intent patterns
INTENT_PATTERNS = {
    Intent.GENERATE_CODE: [
        r"(create|generate|write|build|make).*(code|function|endpoint|api|class|script)",
        r"(python|javascript|typescript|go|rust).*(function|code|script)",
        r"fastapi|flask|express|django",
    ],
    Intent.GENERATE_VIDEO: [
        r"(create|generate|write|plan).*(video|content|script|tutorial)",
        r"(youtube|tiktok|short|reel)",
    ],
    Intent.REVIEW_CODE: [
        r"(review|check|analyze|audit).*(code|security|quality)",
    ],
    Intent.DEPLOY: [
        r"(deploy|ship|release|push)",
        r"approve.*(deploy|release)",
        r"^deploy\s*(it|this|that|now)?$",
    ],
    Intent.CHECK_STATUS: [
        r"(status|progress|state|health)",
        r"(what|how).*(running|pending|deployed)",
    ],
    Intent.LIST_TASKS: [
        r"(list|show|get).*(task|job|pipeline|artifact)",
    ],
}


class ConversationService:
    """Unified conversation handler for all mediums."""
    
    def __init__(self):
        self.runner = AgentRunner()
        self.pipeline = PipelineExecutor()
        self.actions = ActionExecutor()
        self.retrieval = RetrievalService()
    
    def process(self, request: ConverseRequest) -> ConverseResponse:
        """Process incoming message and return structured response."""
        started_at = datetime.utcnow()
        user_id = request.user_id or "anonymous"

        # Initialize guard with safety check
        guard = RequestGuard(request.message, user_id)

        # Block unsafe content
        if not guard.is_safe:
            self._record_feedback(guard.trace_id, user_id, request.message, "blocked", False)
            blocked = guard.get_blocked_response()
            return ConverseResponse(
                reply=blocked["reply"],
                action="blocked",
                intent=Intent.UNKNOWN,
                trace_id=guard.trace_id,
                ui_elements=[]
            )

        # Load user preferences
        prefs = get_user_preferences(user_id) if user_id != "anonymous" else None

        # Check rate limit
        if prefs and not increment_request_count(user_id):
            self._record_feedback(guard.trace_id, user_id, request.message, "rate_limited", False)
            return ConverseResponse(
                reply="Daily request limit reached. Try again tomorrow.",
                action="rate_limited",
                intent=Intent.UNKNOWN,
                trace_id=guard.trace_id,
                ui_elements=[]
            )

        # Merge saved context with request context
        if user_id != "anonymous" and not request.context:
            saved_ctx = get_user_context(user_id)
            if saved_ctx:
                request.context = saved_ctx

        # Run retrieval pipeline first
        retrieval_result = self.retrieval.run_retrieval(user_id, request.message)
        
        # This will be passed to the handler
        request.context = {
            **(request.context or {}),
            "retrieval": retrieval_result
        }

        intent = self._detect_intent(request.message)

        handlers = {
            Intent.GENERATE_CODE: self._handle_code_generation,
            Intent.GENERATE_VIDEO: self._handle_video_generation,
            Intent.REVIEW_CODE: self._handle_review,
            Intent.DEPLOY: self._handle_deploy,
            Intent.CHECK_STATUS: self._handle_status,
            Intent.LIST_TASKS: self._handle_list,
            Intent.UNKNOWN: self._handle_unknown,
            Intent.CLARIFY: self._handle_clarify,
        }

        handler = handlers.get(intent, self._handle_unknown)

        try:
            response = handler(request, intent, prefs)
            response.trace_id = guard.trace_id
            success = True
        except Exception as e:
            logger.error(f"[{guard.trace_id}] Handler error: {e}")
            response = ConverseResponse(
                reply="Something went wrong. Please try again.",
                action="error",
                intent=intent,
                trace_id=guard.trace_id,
                ui_elements=[]
            )
            success = False

        # Save context for next turn
        if user_id != "anonymous" and response.next_context:
            save_user_context(user_id, response.next_context)

        # Record feedback
        latency_ms = int((datetime.utcnow() - started_at).total_seconds() * 1000)
        pipeline_id = response.data.get("pipeline_id") if response.data else None
        
        # Get memory usage from instance variables set in handler
        memory_used = getattr(self, 'memory_used_for_telemetry', False)
        memory_sources = getattr(self, 'memory_sources_for_telemetry', None)

        self._record_feedback(
            guard.trace_id, user_id, request.message,
            intent.value, success, latency_ms, pipeline_id,
            memory_used, memory_sources,
            retrieval_result.get("enabled"),
            retrieval_result.get("query"),
            retrieval_result.get("source_count")
        )

        # Clean up instance variables
        if hasattr(self, 'memory_used_for_telemetry'):
            del self.memory_used_for_telemetry
        if hasattr(self, 'memory_sources_for_telemetry'):
            del self.memory_sources_for_telemetry

        guard.log_request(intent.value, success)
        return response

    def _record_feedback(
        self, trace_id: str, user_id: str, message: str,
        intent: str, success: bool, latency_ms: int = 0, pipeline_id: str = None,
        memory_used: bool = False, memory_sources: List[str] = None,
        rag_enabled: bool = False, rag_query: str = None, rag_source_count: int = None,
        confidence_delta: float = None
    ):
        """Record request telemetry for learning."""
        try:
            from .supabase_client import supabase
            msg_hash = hashlib.sha256(message.encode()).hexdigest()[:16]
            
            record = {
                "trace_id": trace_id,
                "user_id": user_id,
                "message_hash": msg_hash,
                "intent": intent,
                "success": success,
                "latency_ms": latency_ms,
                "pipeline_id": pipeline_id,
                "memory_used": memory_used,
                "memory_sources": memory_sources,
                "rag_enabled": rag_enabled,
                "rag_query": rag_query,
                "rag_source_count": rag_source_count,
                "confidence_delta": confidence_delta
            }

            supabase.table("conversation_feedback").insert(record).execute()
        except Exception:
            pass  # Don't fail on telemetry
    
    def _detect_intent(self, message: str) -> Intent:
        """Pattern-match to detect user intent."""
        msg_lower = message.lower()
        
        for intent, patterns in INTENT_PATTERNS.items():
            for pattern in patterns:
                if re.search(pattern, msg_lower):
                    return intent
        
        return Intent.UNKNOWN
    
    def _format_retrieved_docs(self, docs: List[Dict]) -> str:
        """Formats a list of documents for injection into a prompt."""
        if not docs:
            return ""
        
        formatted = "\n\n## Retrieved Evidence (do NOT modify facts)\n"
        for i, doc in enumerate(docs):
            formatted += f"{i+1}) <doc source='{doc['source']}'>{doc['text']}</doc>\n"
        formatted += "\nOnly use as reference. If uncertain, request more documents.\n"
        return formatted
    
    def _handle_code_generation(self, req: ConverseRequest, intent: Intent, prefs: Optional[UserPreferences] = None) -> ConverseResponse:
        """Generate code via pipeline with user preferences."""
        
        # 1. Retrieve relevant memories
        memory_response = self.runner.run("memory_selector", {"query": req.message, "top_k": 3})
        memories = memory_response.output.get("memories", [])
        self.memory_used_for_telemetry = len(memories) > 0
        self.memory_sources_for_telemetry = [m.get("source") for m in memories]

        # 2. Check for retrieved documents
        retrieval_result = req.context.get("retrieval", {})
        retrieved_docs_str = ""
        if retrieval_result.get("enabled"):
            retrieved_docs_str = self._format_retrieved_docs(retrieval_result.get("docs", []))

        # Use user's preferred language or extract from message
        language = prefs.preferred_language if prefs else "python"
        for lang in ["javascript", "typescript", "go", "rust", "python"]:
            if lang in req.message.lower():
                language = lang
                break

        # Build input with preferences and memories
        pipeline_input = {
            "requirement": req.message + retrieved_docs_str,
            "language": language,
            "include_tests": prefs.include_tests if prefs else True,
            "include_docstrings": prefs.include_docstrings if prefs else True,
            "code_style": prefs.code_style if prefs else "clean",
            "contextual_memories": memories
        }

        # Add user preference lines to requirement for prompt injection
        if prefs:
            pref_lines = prefs.as_prompt_lines()
            pipeline_input["user_preferences"] = pref_lines

        result = self.pipeline.execute(
            pipeline_name="code_generation",
            steps=["code_writer", "code_reviewer"],
            initial_input=pipeline_input
        )
        
        code_output = None
        review_output = None
        for r in result.get("results", []):
            if r.get("agent") == "code_writer":
                code_output = r.get("output", {})
            elif r.get("agent") == "code_reviewer":
                review_output = r.get("output", {})

        verdict = review_output.get("verdict", "UNKNOWN") if review_output else "ERROR"
        suggested = review_output.get("suggested_action", "MANUAL_REVIEW") if review_output else "ERROR"

        ui_elements = [
            UIElement(type="code_block", content=code_output.get("code", "") if code_output else ""),
        ]

        if verdict == "APPROVE" and suggested == "DEPLOY":
            ui_elements.extend([
                UIElement(type="button", label="Deploy", payload={"next": "deploy", "pipeline_id": result["pipeline_id"]}),
                UIElement(type="button", label="Regenerate", payload={"next": "generate_code"}),
            ])
            reply = f"Code generated and approved (Security: {review_output.get('security_score', 0):.1f}). Ready to deploy?"
        elif verdict == "REQUEST_CHANGES":
            ui_elements.append(
                UIElement(type="button", label="Regenerate", payload={"next": "generate_code"})
            )
            issues = review_output.get("issues", []) if review_output else []
            # Handle issues as list of strings or list of dicts
            issue_strs = [str(i) if isinstance(i, str) else i.get("description", str(i)) for i in issues[:3]]
            reply = f"Code needs changes: {', '.join(issue_strs)}"
        else:
            ui_elements.append(
                UIElement(type="button", label="Manual Review", payload={"next": "review_code", "pipeline_id": result["pipeline_id"]})
            )
            reply = "Code generated. Requires manual review."

        return ConverseResponse(
            reply=reply,
            action="await_confirmation" if verdict == "APPROVE" else "await_revision",
            intent=intent,
            ui_elements=ui_elements,
            data={"pipeline_id": result["pipeline_id"], "verdict": verdict, "code": code_output},
            next_context={"pipeline_id": result["pipeline_id"], "last_intent": intent.value}
        )

    def _handle_video_generation(self, req: ConverseRequest, intent: Intent, prefs: Optional[UserPreferences] = None) -> ConverseResponse:
        """Generate video content via pipeline with user preferences."""
        
        # 1. Retrieve relevant memories first
        memory_response = self.runner.run(
            "memory_selector",
            {"query": req.message, "top_k": 3}
        )
        memories = memory_response.output.get("memories", [])
        memory_used = len(memories) > 0
        memory_sources = [m.get("source") for m in memories]

        # 2. Check for retrieved documents
        retrieval_result = req.context.get("retrieval", {})
        retrieved_docs_str = ""
        if retrieval_result.get("enabled"):
            retrieved_docs_str = self._format_retrieved_docs(retrieval_result.get("docs", []))

        # 3. Inject memories and docs into pipeline input
        pipeline_input = {
            "topic": req.message + retrieved_docs_str,
            "duration_seconds": 60,
            "tone": prefs.content_tone if prefs else "professional",
            "target_audience": prefs.target_audience if prefs else None,
            "contextual_memories": memories # Pass memories to planner
        }

        result = self.pipeline.execute(
            pipeline_name="video_content",
            steps=["video_planner", "script_writer"],
            initial_input=pipeline_input
        )

        script_output = None
        for r in result.get("results", []):
            if r.get("agent") == "script_writer":
                script_output = r.get("output", {})

        blocks = script_output.get("script_blocks", []) if script_output else []

        # Pass memory usage to telemetry
        response = ConverseResponse(
            reply=f"Video script generated with {len(blocks)} segments.",
            action="await_approval",
            intent=intent,
            ui_elements=[
                UIElement(type="table", content=blocks),
                UIElement(type="button", label="Approve Script", payload={"next": "store_script", "pipeline_id": result["pipeline_id"]}),
                UIElement(type="button", label="Regenerate", payload={"next": "generate_video"}),
            ],
            data={"pipeline_id": result["pipeline_id"], "script": script_output, "memory_used": memory_used},
            next_context={"pipeline_id": result["pipeline_id"], "last_intent": intent.value}
        )
        
        # Manually set telemetry data before returning
        self.memory_used_for_telemetry = memory_used
        self.memory_sources_for_telemetry = memory_sources
        
        return response

    def _handle_review(self, req: ConverseRequest, intent: Intent, prefs: Optional[UserPreferences] = None) -> ConverseResponse:
        """Review existing code."""
        context = req.context or {}
        code = context.get("code") or req.message

        response = self.runner.run("code_reviewer", {"code": code, "language": "python"})
        output = response.output or {}

        return ConverseResponse(
            reply=f"Review complete: {output.get('verdict', 'UNKNOWN')}",
            action="complete",
            intent=intent,
            ui_elements=[
                UIElement(type="text", content=output.get("summary", "")),
            ],
            data=output
        )

    def _handle_deploy(self, req: ConverseRequest, intent: Intent, prefs: Optional[UserPreferences] = None) -> ConverseResponse:
        """Handle deploy confirmation."""
        context = req.context or {}
        pipeline_id = context.get("pipeline_id")

        if not pipeline_id:
            return ConverseResponse(
                reply="No pipeline context. What would you like to deploy?",
                action="clarify",
                intent=Intent.CLARIFY,
                ui_elements=[]
            )

        # Check if user requires confirmation
        if prefs and not prefs.require_confirmation:
            return ConverseResponse(
                reply=f"Auto-deploying pipeline {pipeline_id} (confirmation disabled).",
                action="auto_deploy",
                intent=intent,
                ui_elements=[],
                data={"pipeline_id": pipeline_id, "auto": True}
            )

        return ConverseResponse(
            reply=f"Ready to deploy pipeline {pipeline_id}. Confirm with admin key.",
            action="await_auth",
            intent=intent,
            ui_elements=[
                UIElement(type="button", label="Confirm Deploy", payload={"action": "deploy_code", "pipeline_id": pipeline_id}),
                UIElement(type="button", label="Cancel", payload={"next": "cancel"}),
            ],
            data={"pipeline_id": pipeline_id}
        )

    def _handle_status(self, req: ConverseRequest, intent: Intent, prefs: Optional[UserPreferences] = None) -> ConverseResponse:
        """Return system status."""
        from .supabase_client import supabase

        deployed = supabase.table("deployed_artifacts").select("id", count="exact").eq("status", "deployed").execute()
        drafts = supabase.table("deployed_artifacts").select("id", count="exact").eq("status", "draft").execute()

        return ConverseResponse(
            reply=f"System healthy. Deployed: {deployed.count}, Drafts: {drafts.count}",
            action="complete",
            intent=intent,
            ui_elements=[
                UIElement(type="button", label="View Deployed", payload={"next": "list_deployed"}),
                UIElement(type="button", label="View Drafts", payload={"next": "list_drafts"}),
            ],
            data={"deployed": deployed.count, "drafts": drafts.count}
        )

    def _handle_list(self, req: ConverseRequest, intent: Intent, prefs: Optional[UserPreferences] = None) -> ConverseResponse:
        """List artifacts/tasks."""
        from .supabase_client import supabase

        artifacts = supabase.table("deployed_artifacts").select("*").order("created_at", desc=True).limit(10).execute()

        return ConverseResponse(
            reply=f"Found {len(artifacts.data)} artifacts.",
            action="complete",
            intent=intent,
            ui_elements=[
                UIElement(type="table", content=artifacts.data)
            ],
            data={"artifacts": artifacts.data}
        )

    def _handle_unknown(self, req: ConverseRequest, intent: Intent, prefs: Optional[UserPreferences] = None) -> ConverseResponse:
        """Handle unrecognized intent."""
        return ConverseResponse(
            reply="I can help you generate code, create video scripts, review code, or deploy artifacts. What would you like to do?",
            action="clarify",
            intent=intent,
            ui_elements=[
                UIElement(type="button", label="Generate Code", payload={"next": "generate_code"}),
                UIElement(type="button", label="Create Video Script", payload={"next": "generate_video"}),
                UIElement(type="button", label="Check Status", payload={"next": "check_status"}),
            ]
        )

    def _handle_clarify(self, req: ConverseRequest, intent: Intent, prefs: Optional[UserPreferences] = None) -> ConverseResponse:
        """Request clarification."""
        return ConverseResponse(
            reply="Could you provide more details about what you need?",
            action="clarify",
            intent=intent,
            ui_elements=[]
        )

