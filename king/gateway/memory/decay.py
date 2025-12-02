"""
KING Memory Decay - Importance scoring with time-based decay.

Episodic memories fade over time (Ebbinghaus forgetting curve).
Collective and Lineage memories never decay.
"""
import math
from datetime import datetime, timezone
from typing import List
from .types import Memory, MemoryType, MEMORY_CONFIGS


# Decay half-life in days for episodic memories
EPISODIC_HALF_LIFE_DAYS = 30

# Working memory expires after session (hours)
WORKING_MEMORY_TTL_HOURS = 24


def calculate_decay_factor(age_days: float, half_life_days: float = EPISODIC_HALF_LIFE_DAYS) -> float:
    """
    Calculate decay factor using Ebbinghaus forgetting curve.
    
    Formula: retention = e^(-t/S) where t=time, S=stability
    
    Args:
        age_days: Age of memory in days
        half_life_days: Days until memory reaches 50% importance
        
    Returns:
        Decay factor between 0.0 and 1.0
    """
    if age_days <= 0:
        return 1.0
    
    # Ebbinghaus curve: e^(-t/S)
    decay = math.exp(-age_days / half_life_days)
    return max(0.01, decay)  # Never fully forget, minimum 1%


def calculate_importance(memory: Memory, current_time: datetime = None) -> float:
    """
    Calculate effective importance of a memory considering decay.
    
    Args:
        memory: The memory to score
        current_time: Current timestamp (defaults to now)
        
    Returns:
        Effective importance score (0.0 to 1.0)
    """
    if current_time is None:
        current_time = datetime.now(timezone.utc)
    
    # Get config for this memory type
    config = MEMORY_CONFIGS.get(memory.memory_type)
    if not config:
        return memory.importance
    
    # No decay for collective, lineage, semantic
    if not config.decays:
        return memory.importance
    
    # Calculate age
    memory_time = memory.created_at
    if memory_time.tzinfo is None:
        memory_time = memory_time.replace(tzinfo=timezone.utc)
    
    age_seconds = (current_time - memory_time).total_seconds()
    age_days = age_seconds / 86400
    
    # Apply decay
    if memory.memory_type == MemoryType.WORKING:
        # Working memory: sharp cutoff after TTL
        age_hours = age_seconds / 3600
        if age_hours > WORKING_MEMORY_TTL_HOURS:
            return 0.0
        return memory.importance
    
    elif memory.memory_type == MemoryType.EPISODIC:
        # Episodic: gradual Ebbinghaus decay
        decay_factor = calculate_decay_factor(age_days)
        return memory.importance * decay_factor
    
    return memory.importance


def apply_decay_to_memories(memories: List[Memory], current_time: datetime = None) -> List[Memory]:
    """
    Apply decay scoring to a list of memories.
    
    Modifies importance in-place and returns sorted by importance.
    """
    if current_time is None:
        current_time = datetime.now(timezone.utc)
    
    for memory in memories:
        memory.importance = calculate_importance(memory, current_time)
    
    # Sort by importance descending
    return sorted(memories, key=lambda m: m.importance, reverse=True)


def filter_expired_memories(memories: List[Memory], min_importance: float = 0.1) -> List[Memory]:
    """
    Remove memories that have decayed below threshold.
    
    Args:
        memories: List of memories to filter
        min_importance: Minimum importance to keep (default 0.1)
        
    Returns:
        Filtered list of memories
    """
    return [m for m in memories if m.importance >= min_importance]

