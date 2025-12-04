"""
Dynamic Taxonomy System - AI-powered evolving classification.
Categories, entity types, intents grow organically through usage.
"""
import os
import json
import asyncio
from typing import Dict, List, Any, Optional, Tuple
from enum import Enum
from functools import lru_cache
from datetime import datetime, timedelta

import google.generativeai as genai

# Taxonomy types
class TaxonomyType(str, Enum):
    CATEGORY = "category"
    ENTITY_TYPE = "entity_type"
    INTENT = "intent"
    CONTEXT_TYPE = "context_type"
    TONE = "tone"
    ACTION = "action"


# In-memory cache with TTL
_taxonomy_cache: Dict[str, Tuple[List[str], datetime]] = {}
CACHE_TTL_SECONDS = 300  # 5 minutes


# Lazy Supabase client
_supabase_client = None

def _get_supabase():
    global _supabase_client
    if _supabase_client is None:
        from supabase import create_client
        url = os.getenv("SUPABASE_URL")
        key = os.getenv("SUPABASE_SERVICE_KEY")
        if url and key:
            _supabase_client = create_client(url, key)
        else:
            print("Warning: Supabase not configured for taxonomy")
            _supabase_client = False
    return _supabase_client if _supabase_client else None


# Lazy Gemini model
_taxonomy_model = None

def _get_model():
    global _taxonomy_model
    if _taxonomy_model is None:
        api_key = os.getenv("GEMINI_API_KEY")
        if api_key:
            genai.configure(api_key=api_key.strip())
            _taxonomy_model = genai.GenerativeModel("gemini-2.0-flash-exp")
        else:
            _taxonomy_model = False
    return _taxonomy_model if _taxonomy_model else None


async def get_taxonomy_values(taxonomy_type: TaxonomyType) -> List[str]:
    """Fetch all values for a taxonomy type from Supabase (cached)."""
    cache_key = taxonomy_type.value
    
    # Check cache
    if cache_key in _taxonomy_cache:
        values, cached_at = _taxonomy_cache[cache_key]
        if datetime.utcnow() - cached_at < timedelta(seconds=CACHE_TTL_SECONDS):
            return values
    
    # Fetch from Supabase
    client = _get_supabase()
    if not client:
        return _get_fallback_values(taxonomy_type)
    
    try:
        result = await asyncio.to_thread(
            lambda: client.table("taxonomies")
                .select("value")
                .eq("taxonomy_type", taxonomy_type.value)
                .order("usage_count", desc=True)
                .execute()
        )
        values = [row["value"] for row in result.data]
        _taxonomy_cache[cache_key] = (values, datetime.utcnow())
        return values
    except Exception as e:
        print(f"Taxonomy fetch error: {e}")
        return _get_fallback_values(taxonomy_type)


def _get_fallback_values(taxonomy_type: TaxonomyType) -> List[str]:
    """Fallback values when Supabase unavailable."""
    fallbacks = {
        TaxonomyType.CATEGORY: ["personal", "business", "project", "preference", "task", "technical"],
        TaxonomyType.ENTITY_TYPE: ["person", "organization", "project", "product", "technology"],
        TaxonomyType.INTENT: ["generate_code", "explain", "chat", "plan", "debug", "recall"],
        TaxonomyType.CONTEXT_TYPE: ["project", "role", "domain", "goal"],
        TaxonomyType.TONE: ["professional", "casual", "technical"],
        TaxonomyType.ACTION: ["execute", "respond", "clarify"],
    }
    return fallbacks.get(taxonomy_type, [])


async def add_taxonomy_value(
    taxonomy_type: TaxonomyType, 
    value: str, 
    description: str = None,
    created_by: str = "ai"
) -> bool:
    """Add new taxonomy value to Supabase."""
    client = _get_supabase()
    if not client:
        return False
    
    try:
        await asyncio.to_thread(
            lambda: client.table("taxonomies").upsert({
                "taxonomy_type": taxonomy_type.value,
                "value": value.lower().replace(" ", "_"),
                "description": description,
                "created_by": created_by,
                "usage_count": 1
            }, on_conflict="taxonomy_type,value").execute()
        )
        # Invalidate cache
        if taxonomy_type.value in _taxonomy_cache:
            del _taxonomy_cache[taxonomy_type.value]
        print(f"📚 New {taxonomy_type.value} added: {value}")
        return True
    except Exception as e:
        print(f"Taxonomy add error: {e}")
        return False


async def increment_usage(taxonomy_type: TaxonomyType, value: str) -> None:
    """Increment usage count for a taxonomy value."""
    client = _get_supabase()
    if not client:
        return
    try:
        await asyncio.to_thread(
            lambda: client.rpc("increment_taxonomy_usage", {
                "p_type": taxonomy_type.value,
                "p_value": value
            }).execute()
        )
    except:
        pass  # Non-critical


MATCH_PROMPT = """You are a taxonomy classifier. Given existing values and context, either match or suggest new.

Taxonomy Type: {taxonomy_type}
Existing Values: {existing_values}
Context: {context}

Rules:
1. If context matches an existing value with 90%+ confidence, return that value
2. If no good match, suggest a NEW concise snake_case value
3. New values should be general enough for reuse, not too specific
4. Prefer existing values when reasonable

Return ONLY valid JSON:
{{
    "matched": "existing_value_or_null",
    "confidence": 0.0-1.0,
    "suggested_new": "new_value_or_null",
    "description": "brief description if new"
}}"""


async def match_or_create(
    taxonomy_type: TaxonomyType,
    context: str,
    threshold: float = 0.9
) -> str:
    """
    AI-powered taxonomy matching. Returns existing value if 90%+ match,
    otherwise creates and returns new value.
    """
    # Get existing values
    existing = await get_taxonomy_values(taxonomy_type)

    # If no model, use simple keyword matching
    model = _get_model()
    if not model:
        return _simple_match(existing, context) or existing[0] if existing else "general"

    prompt = MATCH_PROMPT.format(
        taxonomy_type=taxonomy_type.value,
        existing_values=json.dumps(existing),
        context=context[:500]
    )

    try:
        response = await asyncio.to_thread(model.generate_content, prompt)
        result = _parse_json(response.text)

        matched = result.get("matched")
        confidence = result.get("confidence", 0)
        suggested = result.get("suggested_new")
        description = result.get("description")

        # High confidence match - use existing
        if matched and confidence >= threshold and matched in existing:
            asyncio.create_task(increment_usage(taxonomy_type, matched))
            return matched

        # Low confidence or no match - create new if suggested
        if suggested and suggested not in existing:
            await add_taxonomy_value(taxonomy_type, suggested, description, "ai")
            return suggested.lower().replace(" ", "_")

        # Fallback to best match or first existing
        if matched and matched in existing:
            asyncio.create_task(increment_usage(taxonomy_type, matched))
            return matched

        return existing[0] if existing else "general"

    except Exception as e:
        print(f"Taxonomy match error: {e}")
        return existing[0] if existing else "general"


def _simple_match(existing: List[str], context: str) -> Optional[str]:
    """Simple keyword-based matching fallback."""
    context_lower = context.lower()
    for value in existing:
        if value in context_lower:
            return value
    return None


def _parse_json(text: str) -> Dict:
    """Extract JSON from LLM response."""
    import re
    text = text.strip()

    # Try ```json block
    json_block = re.search(r'```json\s*([\s\S]*?)\s*```', text)
    if json_block:
        return json.loads(json_block.group(1).strip())

    # Try ``` block
    code_block = re.search(r'```\s*([\s\S]*?)\s*```', text)
    if code_block:
        candidate = code_block.group(1).strip()
        if candidate.startswith('{'):
            return json.loads(candidate)

    # Try raw JSON
    if text.startswith('{'):
        return json.loads(text)

    # Find JSON object
    json_match = re.search(r'\{[\s\S]*\}', text)
    if json_match:
        return json.loads(json_match.group())

    return {}


# =============================================================================
# Specialized matchers for common use cases
# =============================================================================

async def match_category(user_message: str, assistant_response: str) -> str:
    """Match or create memory category."""
    context = f"User said: {user_message}\nAssistant replied about: {assistant_response[:200]}"
    return await match_or_create(TaxonomyType.CATEGORY, context)


async def match_entity_type(entity_name: str, context: str) -> str:
    """Match or create entity type."""
    full_context = f"Entity '{entity_name}' mentioned in: {context}"
    return await match_or_create(TaxonomyType.ENTITY_TYPE, full_context)


async def match_intent(user_message: str) -> str:
    """Match or create user intent."""
    return await match_or_create(TaxonomyType.INTENT, user_message)


async def match_context_type(context_description: str) -> str:
    """Match or create context type for fingerprinting."""
    return await match_or_create(TaxonomyType.CONTEXT_TYPE, context_description)


async def match_tone(content_description: str) -> str:
    """Match or create tone for content generation."""
    return await match_or_create(TaxonomyType.TONE, content_description)

