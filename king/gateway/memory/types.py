"""
KING Memory Types - Human-inspired hierarchical memory system.
"""
from enum import Enum
from dataclasses import dataclass, field
from typing import Optional, List, Dict, Any
from datetime import datetime


class MemoryType(str, Enum):
    COLLECTIVE = "collective"
    LINEAGE = "lineage"
    EPISODIC = "episodic"
    SEMANTIC = "semantic"
    WORKING = "working"


class EntityType(str, Enum):
    HUMAN = "Human"
    AI = "AI"
    ORGANIZATION = "Organization"
    SYSTEM = "System"


MEMORY_RESOLUTION_ORDER = [
    MemoryType.WORKING,
    MemoryType.EPISODIC,
    MemoryType.SEMANTIC,
    MemoryType.LINEAGE,
    MemoryType.COLLECTIVE,
]


@dataclass
class MemoryConfig:
    scope: str
    decays: bool
    default_importance: float
    enable_graph: bool = False


MEMORY_CONFIGS: Dict[MemoryType, MemoryConfig] = {
    MemoryType.COLLECTIVE: MemoryConfig("kingdom", False, 1.0, True),
    MemoryType.LINEAGE: MemoryConfig("agent_type", False, 0.9, False),
    MemoryType.EPISODIC: MemoryConfig("user+agent", True, 0.7, False),
    MemoryType.SEMANTIC: MemoryConfig("user|global", False, 0.8, False),
    MemoryType.WORKING: MemoryConfig("session", True, 1.0, False),
}


@dataclass
class Memory:
    content: str
    memory_type: MemoryType
    importance: float = 0.5
    created_at: datetime = field(default_factory=datetime.utcnow)
    metadata: Dict[str, Any] = field(default_factory=dict)
    user_id: Optional[str] = None
    agent_id: Optional[str] = None
    session_id: Optional[str] = None
    mem0_id: Optional[str] = None


@dataclass
class MemorySearchResult:
    memories: Dict[MemoryType, List[Memory]] = field(default_factory=dict)
    total_count: int = 0
    search_time_ms: float = 0.0

    def get_all_flat(self) -> List[Memory]:
        result = []
        for mem_type in MEMORY_RESOLUTION_ORDER:
            result.extend(self.memories.get(mem_type, []))
        return result

    def get_top_k(self, k: int = 5) -> List[Memory]:
        all_mems = self.get_all_flat()
        return sorted(all_mems, key=lambda m: m.importance, reverse=True)[:k]

