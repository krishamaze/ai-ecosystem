"""
KING Memory Resolver - Multi-tier memory search with inheritance chain.
Uses AI Context Curator to determine search strategy.
"""
import time
import logging
from typing import Optional, List, Dict, Any
from .types import Memory, MemoryType, MemorySearchResult, MEMORY_RESOLUTION_ORDER
from .seeding import get_collective_memories, get_lineage_memories
from .decay import apply_decay_to_memories, filter_expired_memories
from .curator import create_search_plan
from .entity_resolver import EntityResolver

logger = logging.getLogger(__name__)

class MemoryResolver:
    """
    Resolves memories across all tiers with inheritance.
    """
    
    def __init__(self, mem0_client=None, entity_resolver: Optional[EntityResolver] = None):
        """
        Args:
            mem0_client: Mem0 client for searching episodic/semantic memories
            entity_resolver: Optional resolver for normalizing entity handles
        """
        self.mem0_client = mem0_client
        self.entity_resolver = entity_resolver
        self._collective_cache: Optional[List[Memory]] = None
        self._lineage_cache: Dict[str, List[Memory]] = {}
    
    async def resolve(
        self,
        query: str,
        user_id: Optional[str] = None,
        agent_id: Optional[str] = None,
        session_id: Optional[str] = None,
        working_memories: Optional[List[Memory]] = None,
        resolve_entity: bool = False
    ) -> MemorySearchResult:
        """
        Resolve memories using AI-generated plan.
        """
        start_time = time.time()
        result = MemorySearchResult()
        
        canonical_user_id = user_id
        if resolve_entity and user_id and self.entity_resolver:
            try:
                entity = await self.entity_resolver.resolve(user_id)
                if entity and "id" in entity:
                    canonical_user_id = str(entity["id"])
                    logger.info(f"Resolved user '{user_id}' to entity '{canonical_user_id}'")
            except Exception as e:
                logger.error(f"Entity resolution failed for '{user_id}': {e}")

        # AI decides search strategy
        plan = await create_search_plan(
            query=query, 
            user_id=canonical_user_id, 
            agent_name=agent_id or "unknown",
            session_context={"session_id": session_id}
        )
        
        logger.info(f"Memory Search Plan: {plan.get('reasoning')}")
        
        limit_per_tier = plan.get("limit_per_tier", 5)
        filters = plan.get("filters", {})
        
        # Override user_id/agent_id from filters if AI suggests (e.g. for cross-user search if allowed)
        # But for security, we usually respect the passed user_id or ensure the AI doesn't hallucinate access.
        # We will use the passed identifiers as primary, but allow keywords from AI.
        
        # SECURITY FIX: Always enforce the authenticated user_id. 
        # Ignore any user_id suggested by the AI curator to prevent data leakage.
        filters["user_id"] = canonical_user_id 
        
        search_keywords = filters.get("keywords", [])
        search_query = f"{query} {' '.join(search_keywords)}" if search_keywords else query

        for tier_name in plan.get("tiers", []):
            try:
                # Normalize tier name to match enum values (lowercase)
                mem_type = MemoryType(tier_name.lower())
            except ValueError:
                logger.warning(f"Invalid memory tier suggested by curator: {tier_name}")
                continue

            tier_memories = self._search_tier(
                mem_type, 
                search_query, 
                canonical_user_id, 
                agent_id, 
                session_id,
                working_memories, 
                limit_per_tier
            )
            
            if tier_memories:
                # Apply decay and filter
                tier_memories = apply_decay_to_memories(tier_memories)
                tier_memories = filter_expired_memories(tier_memories)[:limit_per_tier]
                
                result.memories[mem_type] = tier_memories
                result.total_count += len(tier_memories)
            
            # Early stop if enough context found
            if plan.get("early_stop") and result.total_count >= limit_per_tier * 2:
                break
        
        result.search_time_ms = (time.time() - start_time) * 1000
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
                # Basic filter to ensure we respect the requested memory type if stored in metadata
                # Note: Mem0 results usually don't strictly separate unless we use graph/custom filters.
                # For MVP, we accept what Mem0 gives but label it requested type.
                
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
