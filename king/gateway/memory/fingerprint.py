"""
KING Contextual Fingerprinting - Multi-persona user context tracking.

Solves the "my project" problem: users have multiple projects, roles, interests.
Tracks which context user is referring to with confidence scoring.
Detects identity anomalies (different person using same account).
"""
import os
import json
import asyncio
from typing import Dict, Any, List, Optional
from dataclasses import dataclass, field
from datetime import datetime

# Lazy imports
_gemini_model = None


def _get_model():
    global _gemini_model
    if _gemini_model is None:
        import google.generativeai as genai
        api_key = os.getenv("GEMINI_API_KEY")
        if api_key:
            genai.configure(api_key=api_key.strip())
            _gemini_model = genai.GenerativeModel("gemini-2.0-flash-exp")
    return _gemini_model


@dataclass
class UserContext:
    """A specific context/persona for a user (project, role, interest area)."""
    context_id: str
    context_type: str  # project, role, interest, business
    name: str
    attributes: Dict[str, Any] = field(default_factory=dict)
    confidence: float = 0.5
    last_referenced: datetime = field(default_factory=datetime.utcnow)
    mention_count: int = 1


@dataclass 
class ContextMatch:
    """Result of matching a message to user contexts."""
    matched_context: Optional[UserContext]
    confidence: float
    is_new_context: bool
    extracted_attributes: Dict[str, Any]
    reasoning: str


@dataclass
class AnomalySignal:
    """A potential identity anomaly detected."""
    anomaly_type: str  # contradiction, style_change, knowledge_gap
    expected: str
    received: str
    suspicion_score: float  # 0-1, accumulates over time
    occurrences: int = 1
    first_seen: datetime = field(default_factory=datetime.utcnow)


CONTEXT_EXTRACTION_PROMPT = """Extract context fingerprint from this message.

User Message: {message}
Known User Contexts: {known_contexts}
Previous Messages: {session_history}
Known Context Types: {known_context_types}

Identify:
1. Which known context (if any) is being referenced
2. New context signals (new project, role, interest)
3. Attributes mentioned (language, company, topic, preference)
4. Contradictions with known contexts (anomaly signals)

Return JSON:
{{
    "matched_context_id": "id or null if no match",
    "match_confidence": 0.0-1.0,
    "is_new_context": true/false,
    "new_context": {{
        "type": "from known_context_types or suggest new",
        "name": "suggested name",
        "attributes": {{"key": "value"}}
    }} or null,
    "extracted_attributes": {{"language": "python", "topic": "web dev", etc}},
    "anomalies": [
        {{"type": "contradiction", "expected": "...", "received": "...", "severity": 0.0-1.0}}
    ],
    "reasoning": "brief explanation"
}}"""


async def extract_context(
    message: str,
    known_contexts: List[UserContext],
    session_history: List[str] = None
) -> Dict[str, Any]:
    """AI-powered context extraction with dynamic context types."""
    from memory.taxonomy import get_taxonomy_values, add_taxonomy_value, TaxonomyType

    model = _get_model()
    if not model:
        return {"matched_context_id": None, "match_confidence": 0, "extracted_attributes": {}}

    # Fetch dynamic context types
    context_types = await get_taxonomy_values(TaxonomyType.CONTEXT_TYPE)

    contexts_json = [
        {"id": c.context_id, "type": c.context_type, "name": c.name,
         "attributes": c.attributes, "confidence": c.confidence}
        for c in known_contexts
    ]

    prompt = CONTEXT_EXTRACTION_PROMPT.format(
        message=message[:500],
        known_contexts=json.dumps(contexts_json, indent=2) if contexts_json else "None yet",
        session_history="\n".join(session_history[-5:]) if session_history else "New session",
        known_context_types=json.dumps(context_types)
    )

    try:
        response = await asyncio.to_thread(model.generate_content, prompt)
        text = response.text.strip()
        # Parse JSON from response
        if "```json" in text:
            text = text.split("```json")[1].split("```")[0]
        elif "```" in text:
            text = text.split("```")[1].split("```")[0]
        result = json.loads(text.strip())

        # If AI suggested new context type, add to taxonomy
        new_ctx = result.get("new_context")
        if new_ctx and new_ctx.get("type"):
            ctx_type = new_ctx["type"]
            if ctx_type not in context_types:
                await add_taxonomy_value(
                    TaxonomyType.CONTEXT_TYPE,
                    ctx_type,
                    f"AI-detected from: {message[:50]}",
                    "ai"
                )

        return result
    except Exception as e:
        return {"error": str(e), "matched_context_id": None, "match_confidence": 0}


async def match_context(
    message: str,
    user_id: str,
    session_history: List[str] = None
) -> ContextMatch:
    """Match message to user's known contexts, return best match with confidence."""
    # Fetch known contexts from Mem0 graph
    known_contexts = await _fetch_user_contexts(user_id)
    
    # Extract context from message
    extraction = await extract_context(message, known_contexts, session_history)
    
    matched = None
    if extraction.get("matched_context_id"):
        for ctx in known_contexts:
            if ctx.context_id == extraction["matched_context_id"]:
                matched = ctx
                break
    
    return ContextMatch(
        matched_context=matched,
        confidence=extraction.get("match_confidence", 0),
        is_new_context=extraction.get("is_new_context", False),
        extracted_attributes=extraction.get("extracted_attributes", {}),
        reasoning=extraction.get("reasoning", "")
    )


async def _fetch_user_contexts(user_id: str) -> List[UserContext]:
    """Fetch user's known contexts from Mem0 graph memory."""
    from mem0 import MemoryClient
    api_key = os.getenv("MEM0_API_KEY")
    if not api_key:
        return []

    try:
        client = MemoryClient(api_key=api_key.strip())
        # Fetch memories with context metadata
        result = await asyncio.to_thread(
            client.get_all,
            filters={"user_id": user_id},
            limit=100
        )
        memories = result.get("results", []) if isinstance(result, dict) else result

        # Extract contexts from memories with context_type metadata
        contexts = []
        seen_ids = set()
        for m in memories:
            meta = m.get("metadata", {})
            if meta.get("context_type") and meta.get("context_id"):
                ctx_id = meta["context_id"]
                if ctx_id not in seen_ids:
                    seen_ids.add(ctx_id)
                    contexts.append(UserContext(
                        context_id=ctx_id,
                        context_type=meta.get("context_type", "unknown"),
                        name=meta.get("context_name", "unnamed"),
                        attributes=meta.get("attributes", {}),
                        confidence=meta.get("confidence", 0.5),
                        mention_count=meta.get("mention_count", 1)
                    ))
        return contexts
    except Exception as e:
        print(f"⚠️ Context fetch failed: {e}")
        return []


async def store_context(
    user_id: str,
    context: UserContext,
    message: str,
    response: str
) -> bool:
    """Store/update a user context in Mem0 with graph enabled."""
    from mem0 import MemoryClient
    api_key = os.getenv("MEM0_API_KEY")
    if not api_key:
        return False

    try:
        client = MemoryClient(api_key=api_key.strip())
        messages = [
            {"role": "user", "content": message},
            {"role": "assistant", "content": response}
        ]

        metadata = {
            "context_type": context.context_type,
            "context_id": context.context_id,
            "context_name": context.name,
            "attributes": context.attributes,
            "confidence": context.confidence,
            "mention_count": context.mention_count
        }

        await asyncio.to_thread(
            client.add,
            messages,
            user_id=user_id,
            metadata=metadata,
            enable_graph=True  # Enable graph for entity relationships
        )
        print(f"💾 Context stored: {context.name} ({context.context_type})")
        return True
    except Exception as e:
        print(f"⚠️ Context store failed: {e}")
        return False


async def detect_anomalies(
    user_id: str,
    extraction: Dict[str, Any],
    known_contexts: List[UserContext]
) -> List[AnomalySignal]:
    """Detect identity anomalies from extracted context vs known history."""
    anomalies = []
    raw_anomalies = extraction.get("anomalies", [])

    for a in raw_anomalies:
        if a.get("severity", 0) > 0.3:  # Only track significant anomalies
            anomalies.append(AnomalySignal(
                anomaly_type=a.get("type", "unknown"),
                expected=a.get("expected", ""),
                received=a.get("received", ""),
                suspicion_score=a.get("severity", 0.5)
            ))

    # TODO: Persist anomalies and accumulate suspicion over time
    return anomalies


async def get_context_summary(user_id: str) -> str:
    """Get a summary of user's known contexts for the router."""
    contexts = await _fetch_user_contexts(user_id)
    if not contexts:
        return "New user - no known contexts"

    summary = []
    for ctx in sorted(contexts, key=lambda c: c.confidence, reverse=True)[:5]:
        attrs = ", ".join([f"{k}={v}" for k, v in list(ctx.attributes.items())[:3]])
        summary.append(f"- {ctx.name} ({ctx.context_type}): {attrs} [conf: {ctx.confidence:.1f}]")

    return "\n".join(summary)

