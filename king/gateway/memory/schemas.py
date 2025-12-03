from pydantic import BaseModel, Field, validator
from typing import Optional, Dict, Any, List
from datetime import datetime
from .types import MemoryType, EntityType

class MemoryCreate(BaseModel):
    """Schema for creating a new memory."""
    content: str = Field(..., min_length=1)
    memory_type: MemoryType
    importance: float = Field(0.5, ge=0.0, le=1.0)
    user_id: str
    agent_id: Optional[str] = None
    metadata: Dict[str, Any] = Field(default_factory=dict)
    
    @validator('content')
    def content_must_be_meaningful(cls, v):
        if len(v.strip()) < 3:
            raise ValueError('Memory content too short')
        return v

class MemoryResponse(MemoryCreate):
    """Schema for returning a memory."""
    id: Optional[str] = None
    created_at: datetime = Field(default_factory=datetime.utcnow)

class EntityCreate(BaseModel):
    """Schema for creating a new entity."""
    canonical_name: str = Field(..., min_length=1)
    type: EntityType = EntityType.SYSTEM
    aliases: List[str] = Field(default_factory=list)

class EntityResponse(EntityCreate):
    """Schema for returning an entity."""
    id: str
    created_at: datetime
    updated_at: datetime

