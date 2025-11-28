from abc import ABC, abstractmethod
from pydantic import BaseModel
import json

# DNA rules enforced for all agents
class AgentResponse(BaseModel):
    agent: str
    status: str
    output: dict | None = None
    confidence: float | None = None
    needs_clarification: bool | None = None
    error: dict | None = None

class BaseAgent(ABC):
    role: str

    @abstractmethod
    def run(self, input_data: dict) -> AgentResponse:
        pass

    def validate_response(self, response: dict) -> AgentResponse:
        try:
            validated = AgentResponse(**response)
            return validated
        except Exception as e:
            return AgentResponse(
                agent=self.role,
                status="error",
                error={"type": "INVALID_FORMAT", "details": str(e)},
                confidence=0.0,
                needs_clarification=True,
                output=None
            )

