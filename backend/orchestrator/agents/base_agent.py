from pydantic import BaseModel, Field
from typing import Optional, Dict, Any, List

class AgentResponse(BaseModel):
    agent: str
    status: str
    output: Optional[Dict[str, Any]] = None
    error: Optional[Dict[str, Any]] = None
    confidence: float = 0.0
    needs_clarification: bool = False

class BaseAgent(BaseModel):
    
    def run(self, input_data: Dict[str, Any]) -> AgentResponse:
        raise NotImplementedError("Each agent must implement the 'run' method.")

