from datetime import datetime
from typing import List, Optional, Any, Dict, Tuple
import asyncio

from .eval_contracts import EvalCase, EvalResult, EvalExpectation
from .contracts import InteractionRecord, DetectedIntent, ExecutionOutcome, IntentType
from .conversation_service import ConversationService, ConverseRequest, ConverseResponse

class EvaluationRunner:
    def __init__(self, conversation_service: Optional[ConversationService] = None):
        self.conversation_service = conversation_service or ConversationService()

    async def run_case(self, case: EvalCase) -> EvalResult:
        """
        Executes a single evaluation case.
        """
        # 1. Prepare request
        request = ConverseRequest(
            message=case.input_message,
            medium="api", # Simulate API call
            user_id=case.user_id,
            context=case.context
        )

        # 2. Execute through the service
        # Explicitly unpack the response and interaction record
        try:
            response, interaction = await self.conversation_service.process(request)
        except Exception as e:
            # Handle unexpected crashes in the service
            return EvalResult(
                case_id=case.id,
                eval_type=case.eval_type,
                passed=False,
                score=0.0,
                details={"error": f"Service crash: {str(e)}"},
                created_at=datetime.utcnow()
            )
        
        if not interaction:
            return EvalResult(
                case_id=case.id,
                eval_type=case.eval_type,
                passed=False,
                score=0.0,
                details={"error": "No interaction record returned"},
                created_at=datetime.utcnow()
            )

        # 3. Compute score
        passed, score, details = self._score(case, interaction)

        return EvalResult(
            case_id=case.id,
            eval_type=case.eval_type,
            passed=passed,
            score=score,
            details=details,
            interaction_record=interaction,
            created_at=datetime.utcnow(),
        )

    def _score(
        self,
        case: EvalCase,
        record: InteractionRecord,
    ) -> Tuple[bool, float, Dict[str, Any]]:
        t = case.eval_type
        if t == "intent":
            return self._score_intent(case, record)
        elif t == "plan":
            return self._score_plan(case, record)
        elif t == "execution":
            return self._score_execution(case, record)
        elif t == "end_to_end":
            return self._score_end_to_end(case, record)
        else:
            return False, 0.0, {"error": f"unknown eval_type: {t}"}

    def _score_intent(
        self,
        case: EvalCase,
        record: InteractionRecord,
    ) -> Tuple[bool, float, Dict[str, Any]]:
        exp: EvalExpectation = case.expectation
        actual = record.detected_intent.intent_type
        expected = exp.expected_intent_type

        if expected is None:
            return False, 0.0, {"error": "expected_intent_type not set in expectation"}

        passed = (actual == expected)
        score = 1.0 if passed else 0.0

        details = {
            "expected_intent": expected,
            "actual_intent": actual,
            "raw_intent": record.detected_intent.raw_intent,
            "confidence": record.detected_intent.confidence
        }
        return passed, score, details

    def _score_plan(
        self,
        case: EvalCase,
        record: InteractionRecord,
    ) -> Tuple[bool, float, Dict[str, Any]]:
        exp: EvalExpectation = case.expectation
        plan = record.plan
        
        # If no plan generated but one was expected (implicit in plan eval)
        if not plan:
            # If intent was to plan, this is a failure. 
            # If intent was something else that doesn't produce a 'Plan' object but executes directly,
            # we need to check if that's valid. 
            # For now, 'plan' eval implies a Plan object check.
            return False, 0.0, {"error": "No plan object found in record"}

        issues: List[Dict[str, Any]] = []
        steps = plan.steps or []
        step_count = len(steps)

        # Expected agents check
        if exp.expected_agents:
            actual_agents = [s.agent_role for s in steps]
            missing = [a for a in exp.expected_agents if a not in actual_agents]
            if missing:
                issues.append({"type": "missing_agents", "missing": missing})

        # Forbidden agents check
        if exp.forbidden_agents:
            actual_agents = [s.agent_role for s in steps]
            forbidden = [a for a in exp.forbidden_agents if a in actual_agents]
            if forbidden:
                issues.append({"type": "forbidden_agents_found", "found": forbidden})

        # Min/Max steps check
        if exp.min_steps is not None and step_count < exp.min_steps:
            issues.append({
                "type": "too_few_steps",
                "expected_min": exp.min_steps,
                "actual": step_count,
            })
        if exp.max_steps is not None and step_count > exp.max_steps:
            issues.append({
                "type": "too_many_steps",
                "expected_max": exp.max_steps,
                "actual": step_count,
            })

        passed = len(issues) == 0
        # simple scoring: each issue penalizes
        penalty = 0.25 * len(issues)
        score = max(0.0, 1.0 - penalty)

        return passed, score, {"issues": issues, "step_count": step_count, "steps": [s.dict() for s in steps]}

    def _score_execution(
        self,
        case: EvalCase,
        record: InteractionRecord,
    ) -> Tuple[bool, float, Dict[str, Any]]:
        exp: EvalExpectation = case.expectation
        outcome = record.execution_outcome
        
        if not outcome:
             return False, 0.0, {"error": "No execution outcome recorded"}

        success = outcome.success
        must = exp.must_succeed

        if must and not success:
            passed = False
            score = 0.0
        elif must and success:
            passed = True
            score = 1.0
        else:
            # if not required to succeed, treat partial as neutral/pass
            passed = True
            score = 1.0

        details = {
            "must_succeed": must,
            "actual_success": success,
            "status": outcome.status,
            "error": outcome.error,
        }
        return passed, score, details

    def _score_end_to_end(
        self,
        case: EvalCase,
        record: InteractionRecord,
    ) -> Tuple[bool, float, Dict[str, Any]]:
        # reuse logic, no duplication
        
        # 1. Check Intent (if expectation provided)
        intent_pass, intent_score, intent_details = True, 1.0, {}
        if case.expectation.expected_intent_type:
            intent_pass, intent_score, intent_details = self._score_intent(case, record)

        # 2. Check Plan (if expectation provided OR if intent implies planning)
        # Note: Not all successful interactions have a Plan object (e.g. direct code gen doesn't use PlannerAgent currently)
        # We only score plan if specific plan expectations are set.
        plan_pass, plan_score, plan_details = True, 1.0, {}
        if case.expectation.expected_agents or case.expectation.min_steps or case.expectation.max_steps:
             plan_pass, plan_score, plan_details = self._score_plan(case, record)

        # 3. Check Execution
        exec_pass, exec_score, exec_details = self._score_execution(case, record)

        passed = intent_pass and plan_pass and exec_pass
        
        # Average score of active components
        components = [intent_score, plan_score, exec_score]
        score = sum(components) / len(components)

        return passed, score, {
            "intent": intent_details,
            "plan": plan_details,
            "execution": exec_details,
        }
