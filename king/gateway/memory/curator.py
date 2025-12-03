"""
Context Curator - AI-powered memory search strategist.
No hardcoded rules. Pure AI decision making.
"""
import os
import json
import asyncio
from typing import Dict, Any, Optional
import google.generativeai as genai

# Configure Gemini
api_key = os.getenv("GEMINI_API_KEY")
if api_key:
    genai.configure(api_key=api_key)
    curator_model = genai.GenerativeModel("gemini-2.0-flash-exp")
else:
    print("Warning: GEMINI_API_KEY not set. Context Curator will use fallback.")
    curator_model = None

CURATOR_PROMPT = """You are KING's Context Curator. Analyze this request and create an optimal memory search plan.

User ID: {user_id}
Agent: {agent_name}  
Query: {query}
Session Context: {session_context}

Create a search plan. Consider:
- Which memory tiers are relevant (collective, lineage, episodic, semantic, working)
- Time relevance (recent vs all-time)
- User-specific vs global knowledge
- Agent expertise needed
- Keywords to search

CRITICAL FOR CONVERSATIONAL QUERIES:
- If the user asks about "last message", "previous", "repeat", or "history", you MUST prioritize 'working' and 'episodic' tiers with high limits.
- Set 'time_range_days' to 1 for immediate recall tasks.

Respond ONLY with valid JSON:
{{
    "tiers": ["episodic", "lineage"],  // which tiers to search, in priority order
    "filters": {{
        "user_id": "string or null",
        "agent_id": "string or null", 
        "time_range_days": null or number,
        "keywords": ["extracted", "keywords"]
    }},
    "limit_per_tier": 5,
    "early_stop": true,  // stop if enough context found
    "reasoning": "brief explanation"
}}
"""

async def create_search_plan(
    query: str,
    user_id: Optional[str],
    agent_name: str,
    session_context: Optional[Dict] = None
) -> Dict[str, Any]:
    """AI generates the memory search strategy."""
    
    if not curator_model:
        return _get_fallback_plan(user_id)

    prompt = CURATOR_PROMPT.format(
        user_id=user_id or "anonymous",
        agent_name=agent_name,
        query=query,
        session_context=json.dumps(session_context or {})
    )
    
    try:
        response = await asyncio.to_thread(
            curator_model.generate_content, 
            prompt
        )
        
        text = response.text.strip()
        if text.startswith("```json"):
            text = text[7:]
        if text.endswith("```"):
            text = text[:-3]
            
        return json.loads(text.strip())
        
    except Exception as e:
        # Fallback: search all tiers (never fail silently)
        print(f"Curator error: {e}")
        return _get_fallback_plan(user_id)

def _get_fallback_plan(user_id: Optional[str]) -> Dict[str, Any]:
    """Return a safe default search plan."""
    return {
        "tiers": ["working", "episodic", "semantic", "lineage", "collective"],
        "filters": {"user_id": user_id},
        "limit_per_tier": 5,
        "early_stop": False,
        "reasoning": "fallback - curator unavailable"
    }

