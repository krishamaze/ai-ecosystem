"""
KING Memory Resolver - Multi-tier memory search with inheritance chain.

Resolution Order (like Python's MRO):
1. working    - Current session
2. episodic   - User+agent experiences  
3. semantic   - Learned facts
4. lineage    - Agent expertise
5. collective - Kingdom DNA
"""
import time
import logging
from typing import Optional, List, Dict, Any
from datetime import datetime, timezone

from .types import Memory, MemoryType, MemorySearchResult, MEMORY_RESOLUTION_ORDER
from .seeding import get_collective_memories, get_lineage_memories
from .decay import apply_decay_to_memories, filter_expired_memories

logger = logging.getLogger(__name__)


class MemoryResolver:
    """
    Resolves memories across all tiers with inheritance.
    """
    
    def __init__(self, mem0_client=None):
        """
        Args:
            mem0_client: Mem0 client for searching episodic/semantic memories
        """
        self.mem0_client = mem0_client
        self._collective_cache: Optional[List[Memory]] = None
        self._lineage_cache: Dict[str, List[Memory]] = {}
    
    def resolve(
        self,
        query: str,
        user_id: Optional[str] = None,
        agent_id: Optional[str] = None,
        session_id: Optional[str] = None,
        working_memories: Optional[List[Memory]] = None,
        limit_per_tier: int = 5,
        early_stop: bool = False
    ) -> MemorySearchResult:
        """
        Resolve memories across all tiers.
        
        Args:
            query: Search query for semantic search
            user_id: User ID for episodic/semantic search
            agent_id: Agent ID for lineage memories
            session_id: Session ID for working memories
            working_memories: Pre-loaded working memories from session
            limit_per_tier: Max memories per tier
            early_stop: Stop if sufficient context found
            
        Returns:
            MemorySearchResult with memories grouped by tier
        """
        start_time = time.time()
        result = MemorySearchResult()
        
        for mem_type in MEMORY_RESOLUTION_ORDER:
            tier_memories = self._search_tier(
                mem_type, query, user_id, agent_id, session_id,
                working_memories, limit_per_tier
            )
            
            if tier_memories:
                # Apply decay and filter
                tier_memories = apply_decay_to_memories(tier_memories)
                tier_memories = filter_expired_memories(tier_memories)[:limit_per_tier]
                
                result.memories[mem_type] = tier_memories
                result.total_count += len(tier_memories)
            
            # Early stop if we have enough context
            if early_stop and result.total_count >= 10:
                logger.debug(f"Early stop at tier {mem_type.value} with {result.total_count} memories")
                break
        
        result.search_time_ms = (time.time() - start_time) * 1000
        logger.info(f"Memory resolution: {result.total_count} memories in {result.search_time_ms:.1f}ms")
        
        return result
    
    def _search_tier(
        self,
        mem_type: MemoryType,
        query: str,
        user_id: Optional[str],
        agent_id: Optional[str],
        session_id: Optional[str],
        working_memories: Optional[List[Memory]],
        limit: int
    ) -> List[Memory]:
        """Search a specific memory tier."""
        
        if mem_type == MemoryType.WORKING:
            return (working_memories or [])[:limit]
        
        elif mem_type == MemoryType.COLLECTIVE:
            return self._get_collective()[:limit]
        
        elif mem_type == MemoryType.LINEAGE:
            if agent_id:
                return self._get_lineage(agent_id)[:limit]
            return []
        
        elif mem_type in (MemoryType.EPISODIC, MemoryType.SEMANTIC):
            return self._search_mem0(query, user_id, agent_id, mem_type, limit)
        
        return []
    
    def _get_collective(self) -> List[Memory]:
        """Get cached collective memories."""
        if self._collective_cache is None:
            self._collective_cache = get_collective_memories()
        return self._collective_cache
    
    def _get_lineage(self, agent_id: str) -> List[Memory]:
        """Get cached lineage memories for agent."""
        if agent_id not in self._lineage_cache:
            self._lineage_cache[agent_id] = get_lineage_memories(agent_id)
        return self._lineage_cache[agent_id]
    
    def _search_mem0(
        self,
        query: str,
        user_id: Optional[str],
        agent_id: Optional[str],
        mem_type: MemoryType,
        limit: int
    ) -> List[Memory]:
        """Search Mem0 for episodic/semantic memories."""
        if not self.mem0_client or not user_id:
            return []
        
        try:
            results = self.mem0_client.search(
                query=query,
                user_id=user_id,
                limit=limit * 2  # Get extra for filtering
            )
            
            memories = []
            for r in results.get("results", []):
                mem = Memory(
                    content=r.get("memory", ""),
                    memory_type=mem_type,
                    importance=r.get("score", 0.5),
                    mem0_id=r.get("id"),
                    user_id=user_id,
                    agent_id=agent_id,
                    metadata=r.get("metadata", {})
                )
                memories.append(mem)
            
            return memories[:limit]
            
        except Exception as e:
            logger.error(f"Mem0 search failed: {e}")
            return []

