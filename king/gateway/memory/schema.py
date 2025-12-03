from pydantic import BaseModel, Field, validator
from typing import Optional, Dict, Any
from datetime import datetime
from .types import MemoryType

class MemoryRecord(BaseModel):
    """Validated memory record."""
    content: str = Field(..., min_length=1)
    memory_type: MemoryType
    importance: float = Field(0.5, ge=0.0, le=1.0)
    user_id: Optional[str] = None
    agent_id: Optional[str] = None
    session_id: Optional[str] = None
    metadata: Dict[str, Any] = Field(default_factory=dict)
    
    @validator('content')
    def content_must_be_meaningful(cls, v):
        if len(v.strip()) < 3:
            raise ValueError('Memory content too short')
        return v

def validate_memory(data: dict) -> MemoryRecord:
    """Helper to validate raw dict against schema."""
    return MemoryRecord(**data)
