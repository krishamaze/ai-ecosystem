from pydantic import BaseModel, Field
from typing import Literal, Optional, Dict, Any, List
from datetime import datetime
from .contracts import (
    DetectedIntent,
    Plan,
    ExecutionOutcome,
    InteractionRecord,
    IntentType
)

EvalType = Literal["intent", "plan", "execution", "end_to_end"]

class EvalExpectation(BaseModel):
    """
    Defines what a successful outcome looks like for a given test case.
    """
    # Intent expectations
    expected_intent_type: Optional[IntentType] = None
    
    # Plan expectations
    expected_agents: Optional[List[str]] = Field(None, description="List of agent roles that must appear in the plan")
    forbidden_agents: Optional[List[str]] = Field(None, description="List of agent roles that must NOT appear")
    min_steps: Optional[int] = None
    max_steps: Optional[int] = None
    
    # Execution expectations
    must_succeed: bool = True
    
    # Custom validation logic (placeholder for future use)
    custom_validator: Optional[str] = None

class EvalCase(BaseModel):
    """
    A single test case definition.
    """
    id: str
    eval_type: EvalType
    user_id: Optional[str] = "eval_user"
    input_message: str
    expectation: EvalExpectation
    context: Optional[Dict[str, Any]] = None

class EvalResult(BaseModel):
    """
    The result of running a single evaluation case.
    """
    case_id: str
    eval_type: EvalType
    passed: bool
    score: float = Field(..., ge=0.0, le=1.0)
    details: Dict[str, Any] = Field(default_factory=dict, description="Diagnostic info on why it passed/failed")
    interaction_record: Optional[InteractionRecord] = None
    created_at: datetime = Field(default_factory=datetime.utcnow)






