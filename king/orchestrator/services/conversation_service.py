"""
Conversation Service - Unified entry point for all interaction mediums.
Detects intent, dispatches agents, returns UI-agnostic structured responses.
"""
from enum import Enum
from typing import Dict, Any, Optional, List, Literal, Tuple
from pydantic import BaseModel
from datetime import datetime
import re
import hashlib
import logging
import uuid

from agents.agent_runner import AgentRunner
from services.pipeline_executor import PipelineExecutor
from services.action_executor import ActionExecutor
from services.user_preferences import (
    get_user_preferences, increment_request_count,
    get_user_context, save_user_context, UserPreferences
)
from services.guardrails import RequestGuard
from agents.guardian_minister import GuardianMinister
from services.retrieval_service import RetrievalService
from .contracts import (
    DetectedIntent, IntentType, Plan, PlanStep, ExecutionOutcome, InteractionRecord
)

logger = logging.getLogger(__name__)


class Medium(str, Enum):
    TELEGRAM = "telegram"
    DASHBOARD = "dashboard"
    API = "api"


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
    intent: IntentType
    trace_id: Optional[str] = None
    ui_elements: List[UIElement] = []
    data: Optional[Dict[str, Any]] = None
    next_context: Optional[Dict[str, Any]] = None


class ConversationService:
    """Unified conversation handler for all mediums."""
    
    def __init__(self):
        self.runner = AgentRunner()
        self.pipeline = PipelineExecutor()
        self.actions = ActionExecutor()
        self.retrieval = RetrievalService()
    
    async def process(self, request: ConverseRequest) -> Tuple[ConverseResponse, InteractionRecord]:
        """Process incoming message and return structured response with interaction record."""
        started_at = datetime.utcnow()
        user_id = request.user_id or "anonymous"
        trace_id = str(uuid.uuid4())

        # Initialize guard with safety check
        guard = RequestGuard(request.message, user_id)
        guard.trace_id = trace_id # Force trace_id sync

        # Block unsafe content
        if not guard.is_safe:
            interaction_record = self._record_interaction(
                trace_id=trace_id,
                user_id=user_id,
                request_message=request.message,
                detected_intent=DetectedIntent(
                    intent_type=IntentType.UNKNOWN,
                    raw_intent="blocked",
                    confidence=1.0,
                    reasoning="Blocked by RequestGuard"
                ),
                execution_outcome=ExecutionOutcome(
                    success=False,
                    status="rejected",
                    output={"reply": guard.get_blocked_response()["reply"]},
                    duration_ms=int((datetime.utcnow() - started_at).total_seconds() * 1000)
                ),
                guardrail_decisions=[{"verdict": "BLOCKED", "reason": guard.violation_type}]
            )
            blocked = guard.get_blocked_response()
            return ConverseResponse(
                reply=blocked["reply"],
                action="blocked",
                intent=IntentType.UNKNOWN,
                trace_id=trace_id,
                ui_elements=[]
            ), interaction_record

        # Load user preferences
        prefs = get_user_preferences(user_id) if user_id != "anonymous" else None

        # Check rate limit
        if prefs and not increment_request_count(user_id):
            # Record failed interaction due to rate limit
            interaction_record = self._record_interaction(
                trace_id=trace_id,
                user_id=user_id,
                request_message=request.message,
                 detected_intent=DetectedIntent(
                    intent_type=IntentType.UNKNOWN,
                    raw_intent="rate_limited",
                    confidence=1.0,
                    reasoning="Rate limit exceeded"
                ),
                execution_outcome=ExecutionOutcome(
                    success=False,
                    status="rejected",
                    output={"reply": "Daily request limit reached."},
                    duration_ms=int((datetime.utcnow() - started_at).total_seconds() * 1000)
                )
            )
            return ConverseResponse(
                reply="Daily request limit reached. Try again tomorrow.",
                action="rate_limited",
                intent=IntentType.UNKNOWN,
                trace_id=trace_id,
                ui_elements=[]
            ), interaction_record

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

        # Detect Intent using AI
        detected_intent = await self._detect_intent_ai(request.message, user_id)
        
        handlers = {
            IntentType.GENERATE_CODE: self._handle_code_generation,
            IntentType.GENERATE_VIDEO: self._handle_video_generation,
            IntentType.REVIEW_CODE: self._handle_review,
            IntentType.DEPLOY: self._handle_deploy,
            IntentType.CHECK_STATUS: self._handle_status,
            IntentType.LIST_TASKS: self._handle_list,
            IntentType.UNKNOWN: self._handle_unknown,
            IntentType.CLARIFY: self._handle_clarify,
            IntentType.PLAN: self._handle_dynamic_plan,
        }

        handler = handlers.get(detected_intent.intent_type, self._handle_unknown)

        plan_object = None
        execution_outcome = None
        
        try:
            response = handler(request, detected_intent.intent_type, prefs)
            response.trace_id = trace_id
            
            # Extract plan object if it exists (from dynamic planner)
            if response.data and "plan" in response.data:
                 # It might be in the data dict if we passed it through
                 pass 

            execution_outcome = ExecutionOutcome(
                success=True,
                status="completed",
                output={"reply": response.reply, "data": response.data},
                duration_ms=int((datetime.utcnow() - started_at).total_seconds() * 1000),
                pipeline_id=response.data.get("pipeline_id") if response.data else None
            )

        except Exception as e:
            logger.error(f"[{trace_id}] Handler error: {e}")
            response = ConverseResponse(
                reply="Something went wrong. Please try again.",
                action="error",
                intent=detected_intent.intent_type,
                trace_id=trace_id,
                ui_elements=[]
            )
            execution_outcome = ExecutionOutcome(
                success=False,
                status="error",
                output={},
                error=str(e),
                duration_ms=int((datetime.utcnow() - started_at).total_seconds() * 1000)
            )

        # Save context for next turn
        if user_id != "anonymous" and response.next_context:
            save_user_context(user_id, response.next_context)

        # Record Interaction
        interaction_record = self._record_interaction(
            trace_id=trace_id,
            user_id=user_id,
            request_message=request.message,
            detected_intent=detected_intent,
            plan=plan_object,
            execution_outcome=execution_outcome,
            guardrail_decisions=[] # Populate if we had explicit guardrail steps
        )

        return response, interaction_record

    async def _detect_intent_ai(self, message: str, user_id: str) -> DetectedIntent:
        """
        Use LLM + embeddings for intent classification.
        Returns a strongly typed DetectedIntent object.
        """
        from agents.agent_factory import AgentFactory
        
        # Placeholder for semantic search
        agents = AgentFactory.list_agents()
        best_match = None
        highest_score = 0.0

        for agent_name in agents:
            agent_spec = AgentFactory.get_agent(agent_name)
            purpose = agent_spec.get("purpose", "").lower()
            
            # Simple keyword matching
            score = 0
            for word in message.lower().split():
                if word in purpose:
                    score += 1
            
            if score > highest_score:
                highest_score = score
                best_match = agent_name

        if best_match and highest_score > 0:
            confidence = min(highest_score / len(message.lower().split()), 1.0) if message else 0.0
            
            # Map agent to intent type
            intent_type = IntentType.UNKNOWN
            if "code" in best_match:
                intent_type = IntentType.GENERATE_CODE
            elif "video" in best_match:
                intent_type = IntentType.GENERATE_VIDEO
            
            return DetectedIntent(
                intent_type=intent_type,
                raw_intent=f"agent:{best_match}",
                confidence=confidence,
                agent_name=best_match,
                reasoning=f"Matched keywords in {best_match} purpose."
            )

        # Fallback to planner
        return DetectedIntent(
            intent_type=IntentType.PLAN,
            raw_intent="plan",
            confidence=0.5,
            agent_name="planner_agent",
            reasoning="No direct agent match found; defaulting to planner."
        )

    def _record_interaction(
        self,
        trace_id: str,
        user_id: str,
        request_message: str,
        detected_intent: DetectedIntent,
        execution_outcome: ExecutionOutcome,
        plan: Optional[Plan] = None,
        guardrail_decisions: List[Dict[str, Any]] = []
    ) -> InteractionRecord:
        """
        Record the full interaction to Supabase using the InteractionRecord contract.
        Returns the created InteractionRecord.
        """
        record = InteractionRecord(
            trace_id=trace_id,
            user_id=user_id,
            request_message=request_message,
            detected_intent=detected_intent,
            plan=plan,
            execution_outcome=execution_outcome,
            guardrail_decisions=guardrail_decisions
        )
        
        try:
            from .supabase_client import supabase
            
            # MAPPING TO EXISTING TABLE FOR BACKWARD COMPATIBILITY
            legacy_record = {
                "trace_id": trace_id,
                "user_id": user_id,
                "message_hash": hashlib.sha256(request_message.encode()).hexdigest()[:16],
                "intent": detected_intent.intent_type.value,
                "success": execution_outcome.success,
                "latency_ms": execution_outcome.duration_ms,
                "pipeline_id": execution_outcome.pipeline_id,
                # New fields would ideally go into a structured_log column
                # "structured_log": data_dict 
            }
            supabase.table("conversation_feedback").insert(legacy_record).execute()
            
        except Exception as e:
            logger.error(f"Telemetry error: {e}")
        
        return record

    def _format_retrieved_docs(self, docs: List[Dict]) -> str:
        """Formats a list of documents for injection into a prompt."""
        if not docs:
            return ""
        
        formatted = "\n\n## Retrieved Evidence (do NOT modify facts)\n"
        for i, doc in enumerate(docs):
            formatted += f"{i+1}) <doc source='{doc['source']}'>{doc['text']}</doc>\n"
        formatted += "\nOnly use as reference. If uncertain, request more documents.\n"
        return formatted
    
    # --- HANDLERS ---

    def _handle_code_generation(self, req: ConverseRequest, intent: IntentType, prefs: Optional[UserPreferences] = None) -> ConverseResponse:
        """Generate code via pipeline with user preferences."""
        
        # 1. Retrieve relevant memories
        memory_response = self.runner.run("memory_selector", {"query": req.message, "top_k": 3})
        memories = memory_response.output.get("memories", [])

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

    def _handle_video_generation(self, req: ConverseRequest, intent: IntentType, prefs: Optional[UserPreferences] = None) -> ConverseResponse:
        """Generate video content via pipeline with user preferences."""
        
        # 1. Retrieve relevant memories first
        memory_response = self.runner.run(
            "memory_selector",
            {"query": req.message, "top_k": 3}
        )
        memories = memory_response.output.get("memories", [])
        
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

        response = ConverseResponse(
            reply=f"Video script generated with {len(blocks)} segments.",
            action="await_approval",
            intent=intent,
            ui_elements=[
                UIElement(type="table", content=blocks),
                UIElement(type="button", label="Approve Script", payload={"next": "store_script", "pipeline_id": result["pipeline_id"]}),
                UIElement(type="button", label="Regenerate", payload={"next": "generate_video"}),
            ],
            data={"pipeline_id": result["pipeline_id"], "script": script_output},
            next_context={"pipeline_id": result["pipeline_id"], "last_intent": intent.value}
        )
        
        return response

    def _handle_review(self, req: ConverseRequest, intent: IntentType, prefs: Optional[UserPreferences] = None) -> ConverseResponse:
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

    def _handle_deploy(self, req: ConverseRequest, intent: IntentType, prefs: Optional[UserPreferences] = None) -> ConverseResponse:
        """Handle deploy confirmation."""
        context = req.context or {}
        pipeline_id = context.get("pipeline_id")

        if not pipeline_id:
            return ConverseResponse(
                reply="No pipeline context. What would you like to deploy?",
                action="clarify",
                intent=IntentType.CLARIFY,
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

    def _handle_status(self, req: ConverseRequest, intent: IntentType, prefs: Optional[UserPreferences] = None) -> ConverseResponse:
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

    def _handle_list(self, req: ConverseRequest, intent: IntentType, prefs: Optional[UserPreferences] = None) -> ConverseResponse:
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

    def _handle_unknown(self, req: ConverseRequest, intent: IntentType, prefs: Optional[UserPreferences] = None) -> ConverseResponse:
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

    def _handle_clarify(self, req: ConverseRequest, intent: IntentType, prefs: Optional[UserPreferences] = None) -> ConverseResponse:
        """Request clarification."""
        return ConverseResponse(
            reply="Could you provide more details about what you need?",
            action="clarify",
            intent=intent,
            ui_elements=[]
        )

    def _handle_dynamic_plan(self, req: ConverseRequest, intent: IntentType, prefs: Optional[UserPreferences] = None) -> ConverseResponse:
        """
        Generates and executes a dynamic plan.
        """
        # 1. Call the PlannerAgent to generate the plan
        planner_response = self.runner.run("planner_agent", {"request": req.message})
        
        if planner_response.status != "success" or not planner_response.output:
            return ConverseResponse(
                reply="I could not devise a plan for your request.",
                action="error",
                intent=intent,
            )

        # Parse the output into a Plan object if possible, or use the dict
        plan_data = planner_response.output
        
        # Extract steps for the pipeline
        steps_dicts = plan_data.get("steps", [])
        
        # If steps are objects, extract agent_role
        if steps_dicts and isinstance(steps_dicts[0], dict):
             plan_steps = [s.get("agent_role") for s in steps_dicts]
        else:
             plan_steps = steps_dicts # Fallback if it's already a list of strings (though contracts say otherwise)

        if not plan_steps:
            return ConverseResponse(
                reply="The generated plan was empty. I'm not sure how to proceed.",
                action="clarify",
                intent=intent
            )

        # 2. VALIDATION: Audit Plan with GuardianMinister
        guardian = GuardianMinister()
        audit_result = guardian.validate_plan(plan_steps)
        
        if audit_result["verdict"] == "BLOCKED":
            return ConverseResponse(
                reply=f"Plan rejected by policy: {audit_result['reason']}",
                action="blocked",
                intent=intent,
                data=audit_result
            )

        # 3. Execute the plan using the PipelineExecutor
        pipeline_result = self.pipeline.execute(
            pipeline_name="dynamic_plan",
            steps=plan_steps,
            initial_input={"requirement": req.message}
        )

        final_output = pipeline_result.get("final_output", {})
        
        return ConverseResponse(
            reply=f"I have executed the plan. Here is the result: {final_output}",
            action="complete",
            intent=intent,
            data=pipeline_result
        )
