"""
Memory tier promotion based on pattern detection.
Episodic (1x) → Semantic (3x repeated)
"""
from mem0 import MemoryClient
from typing import Optional
import os

mem0_api_key = os.getenv("MEM0_API_KEY")
mem0_client = MemoryClient(api_key=mem0_api_key) if mem0_api_key else None

SIMILARITY_THRESHOLD = 0.85
PROMOTION_COUNT = 3

def check_and_promote(
    content: str,
    user_id: str,
    agent_name: Optional[str] = None
) -> bool:
    """
    Before storing new memory:
    1. Search for similar existing memories
    2. If found 3+, promote to semantic tier
    3. Return True if promoted (skip storing duplicate)
    """
    if not mem0_client:
        return False

    try:
        # Search for similar
        similar = mem0_client.search(
            query=content,
            user_id=user_id,
            limit=5
        )
        
        # Count high-similarity matches
        matches = [m for m in similar if m.get("score", 0) > SIMILARITY_THRESHOLD]
        
        if len(matches) >= PROMOTION_COUNT:
            # Promote: store as semantic, delete episodic duplicates
            _promote_to_semantic(content, matches, user_id)
            return True
            
    except Exception as e:
        print(f"Promotion check failed: {e}")
    
    return False

def _promote_to_semantic(content: str, duplicates: list, user_id: str):
    """Merge duplicates into single semantic memory."""
    if not mem0_client:
        return

    # Delete old episodic versions
    for mem in duplicates:
        try:
            mem0_client.delete(mem["id"])
        except Exception as e:
            print(f"Failed to delete duplicate memory {mem.get('id')}: {e}")
    
    # Store as semantic with high importance
    try:
        mem0_client.add(
            messages=[{"role": "assistant", "content": content}],
            user_id=user_id,
            metadata={
                "type": "semantic",
                "importance": 0.8,
                "source": "promotion",
                "promoted_from_count": len(duplicates)
            }
        )
    except Exception as e:
        print(f"Failed to add semantic memory: {e}")

