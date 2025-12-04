"""
KING Memory Types - KING Memory v1.0

Aligned with Mem0 Platform native layers (Dec 2024):
- Conversation: In-flight messages (handled by session history in-memory)
- Session: Short-term via session_id (expires after session)
- User: Long-term via user_id (persists forever)
- Org: Kingdom-wide via org_id='__kingdom__' (shared across all)

KING Conceptual Layers (mapped to Mem0 Platform):
- WORKING → Conversation (in-memory session history)
- EPISODIC → Session memory (session_id)
- SEMANTIC → User memory (user_id, long-term facts)
- LINEAGE → Agent memory (user_id=agent:{name})
- COLLECTIVE → Org memory (user_id='__kingdom__', enable_graph=True)

Note: Version numbers (e.g., "KING Memory v1.0") are KING internal versions,
not Mem0 official versions. Mem0 has its own versioning (v2 filters, etc.).
"""
from enum import Enum
from dataclasses import dataclass, field
from typing import Optional, List, Dict, Any
from datetime import datetime


class MemoryLayer(str, Enum):
    """Mem0-aligned memory layers."""
    CONVERSATION = "conversation"  # In-flight, in-memory only
    SESSION = "session"            # Short-term, session_id scoped
    USER = "user"                  # Long-term, user_id scoped
    AGENT = "agent"                # Agent-specific learning
    KINGDOM = "kingdom"            # Shared across all, graph-enabled


# Legacy enum for backward compatibility
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


# Resolution order: most specific → most general
MEMORY_RESOLUTION_ORDER = [
    MemoryType.WORKING,
    MemoryType.EPISODIC,
    MemoryType.SEMANTIC,
    MemoryType.LINEAGE,
    MemoryType.COLLECTIVE,
]


@dataclass
class MemoryConfig:
    """Configuration for each memory layer."""
    scope: str
    decays: bool
    default_importance: float
    enable_graph: bool = False
    mem0_layer: MemoryLayer = MemoryLayer.USER


# Map KING types to Mem0 layers
MEMORY_CONFIGS: Dict[MemoryType, MemoryConfig] = {
    MemoryType.COLLECTIVE: MemoryConfig(
        scope="kingdom", decays=False, default_importance=1.0,
        enable_graph=True, mem0_layer=MemoryLayer.KINGDOM
    ),
    MemoryType.LINEAGE: MemoryConfig(
        scope="agent_type", decays=False, default_importance=0.9,
        enable_graph=False, mem0_layer=MemoryLayer.AGENT
    ),
    MemoryType.EPISODIC: MemoryConfig(
        scope="user+session", decays=True, default_importance=0.7,
        enable_graph=False, mem0_layer=MemoryLayer.SESSION
    ),
    MemoryType.SEMANTIC: MemoryConfig(
        scope="user", decays=False, default_importance=0.8,
        enable_graph=False, mem0_layer=MemoryLayer.USER
    ),
    MemoryType.WORKING: MemoryConfig(
        scope="session", decays=True, default_importance=1.0,
        enable_graph=False, mem0_layer=MemoryLayer.CONVERSATION
    ),
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

