"""
Mem0 Integration Tool
Long-term memory layer for persistent agent intelligence.

Mem0 provides:
- Hybrid graph + vector memory
- User/session/agent scoping
- Semantic search across memories
- Automatic memory extraction from conversations
"""

import os
import logging
from typing import Optional, List, Dict, Any

logger = logging.getLogger(__name__)

# Lazy initialization to avoid import errors if mem0ai not installed
_client = None


def _get_client():
    """Get or create Mem0 client (lazy initialization)."""
    global _client
    if _client is None:
        api_key = os.getenv("MEM0_API_KEY")
        if not api_key:
            raise ValueError("MEM0_API_KEY environment variable not set")
        
        from mem0 import MemoryClient
        _client = MemoryClient(api_key=api_key)
        logger.info("Mem0 client initialized")
    return _client


def add_memory(
    messages: List[Dict[str, str]],
    user_id: str,
    agent_id: Optional[str] = None,
    session_id: Optional[str] = None,
    metadata: Optional[Dict[str, Any]] = None,
    enable_graph: bool = True
) -> Dict[str, Any]:
    """
    Add memory from conversation messages.

    Args:
        messages: List of {"role": "user"|"assistant", "content": "..."}
        user_id: User identifier for scoping
        agent_id: Optional agent identifier
        session_id: Optional session identifier
        metadata: Optional metadata to attach
        enable_graph: Build entity relationship graph (default True)

    Returns:
        Mem0 response with memory IDs
    """
    try:
        client = _get_client()

        kwargs = {"user_id": user_id, "enable_graph": enable_graph}
        if agent_id:
            kwargs["agent_id"] = agent_id
        if session_id:
            kwargs["run_id"] = session_id
        if metadata:
            kwargs["metadata"] = metadata

        result = client.add(messages, **kwargs)
        logger.info(f"Memory added for user={user_id}: {len(messages)} messages (graph={enable_graph})")
        return {"success": True, "result": result}

    except Exception as e:
        logger.error(f"Failed to add memory: {e}")
        return {"success": False, "error": str(e)}


def search_memory(
    query: str,
    user_id: str,
    agent_id: Optional[str] = None,
    limit: int = 5,
    enable_graph: bool = True
) -> Dict[str, Any]:
    """
    Search memories by semantic similarity + graph relationships.

    Args:
        query: Natural language query
        user_id: User identifier for scoping
        agent_id: Optional agent filter
        limit: Max results to return
        enable_graph: Include graph relations in response

    Returns:
        Dict with 'memories' list and optional 'relations' list
    """
    try:
        client = _get_client()

        filters = {"user_id": user_id}
        if agent_id:
            filters["agent_id"] = agent_id

        result = client.search(query, filters=filters, limit=limit, enable_graph=enable_graph)

        # Extract memories and relations
        memories = result.get("results", []) if isinstance(result, dict) else result
        relations = result.get("relations", []) if isinstance(result, dict) else []

        logger.info(f"Memory search for user={user_id}: {len(memories)} memories, {len(relations)} relations")
        return {"memories": memories, "relations": relations}

    except Exception as e:
        logger.error(f"Failed to search memory: {e}")
        return {"memories": [], "relations": []}


def get_all_memories(user_id: str, limit: int = 100) -> List[Dict[str, Any]]:
    """Get all memories for a user."""
    try:
        client = _get_client()
        # v2 API requires filters parameter
        result = client.get_all(filters={"user_id": user_id}, limit=limit)
        memories = result.get("results", []) if isinstance(result, dict) else result
        return memories
    except Exception as e:
        logger.error(f"Failed to get memories: {e}")
        return []


def delete_memory(memory_id: str) -> bool:
    """Delete a specific memory by ID."""
    try:
        client = _get_client()
        client.delete(memory_id)
        logger.info(f"Memory deleted: {memory_id}")
        return True
    except Exception as e:
        logger.error(f"Failed to delete memory: {e}")
        return False


def select_memories(
    query: str,
    raw_memories: List[Dict[str, Any]],
    user_id: str
) -> Dict[str, Any]:
    """
    Filter memories through memory_selector agent to avoid noise/distraction.

    Args:
        query: Current user request/task
        raw_memories: Raw memory list from search_memory()
        user_id: User identifier for context

    Returns:
        Dict with 'approved' list, 'rejected' list, 'confidence', and counts
    """
    if not raw_memories:
        return {"approved": [], "rejected": [], "confidence": 1.0, "memory_used": 0, "memory_rejected": 0}

    # Import here to avoid circular dependency
    from agents.agent_runner import AgentRunner

    # Extract memory text for selector input
    candidate_texts = [
        m.get("memory", m.get("content", str(m)))
        for m in raw_memories
    ]

    runner = AgentRunner()
    response = runner.run(
        role="memory_selector",
        input_data={
            "query": query,
            "candidate_memories": candidate_texts
        }
    )

    if response.status != "success" or not response.output:
        logger.warning(f"Memory selector failed for user={user_id}, passing all memories")
        return {
            "approved": candidate_texts,
            "rejected": [],
            "confidence": 0.0,
            "memory_used": len(candidate_texts),
            "memory_rejected": 0
        }

    approved = response.output.get("approved_memories", [])
    rejected = response.output.get("rejected_memories", [])
    confidence = response.output.get("confidence", 0.5)

    logger.info(f"Memory selection for user={user_id}: {len(approved)} approved, {len(rejected)} rejected")

    return {
        "approved": approved,
        "rejected": rejected,
        "confidence": confidence,
        "memory_used": len(approved),
        "memory_rejected": len(rejected)
    }


def enrich_prompt_with_memory(
    prompt: str,
    user_id: str,
    agent_id: Optional[str] = None,
    max_memories: int = 3
) -> str:
    """
    Enrich a prompt with relevant memories + graph relationships.

    Args:
        prompt: Original prompt
        user_id: User identifier
        agent_id: Optional agent filter
        max_memories: Max memories to include

    Returns:
        Enriched prompt with memory context and entity relationships
    """
    result = search_memory(prompt, user_id, agent_id, limit=max_memories)
    memories = result.get("memories", [])
    relations = result.get("relations", [])

    if not memories and not relations:
        return prompt

    sections = []

    # Add memories
    if memories:
        memory_lines = [f"- {m.get('memory', m.get('content', ''))}" for m in memories]
        sections.append("## Relevant Context from Memory\n" + "\n".join(memory_lines))

    # Add graph relationships
    if relations:
        rel_lines = [
            f"- {r.get('source')} --[{r.get('relationship')}]--> {r.get('target')}"
            for r in relations
        ]
        sections.append("## Entity Relationships\n" + "\n".join(rel_lines))

    enriched = "\n\n".join(sections) + f"\n\n## Current Request\n{prompt}"
    return enriched

