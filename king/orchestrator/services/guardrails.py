"""
Production Guardrails - Safety filters and failure handling.

Protects the system from:
- Profanity and sensitive content
- LLM failures
- Abusive patterns
"""
import re
import logging
from typing import Optional, Tuple
from uuid import uuid4

logger = logging.getLogger(__name__)

# Profanity/sensitive content patterns (basic filter - extend as needed)
BLOCKED_PATTERNS = [
    # Explicit content requests
    r"\b(porn|xxx|nsfw|nude|naked)\b",
    # Violence
    r"\b(kill|murder|bomb|terror|attack)\s+(people|person|someone|humans)",
    # Hate speech markers
    r"\b(hate|death\s+to)\s+\w+\s*(people|race|religion)",
    # Illegal activities
    r"\b(hack|crack|steal)\s+(password|account|credit|bank)",
    # Self-harm (route to support resources)
    r"\b(suicide|self.?harm|kill\s+myself)\b",
]

# Compiled patterns for performance
_compiled_patterns = [re.compile(p, re.IGNORECASE) for p in BLOCKED_PATTERNS]


def generate_trace_id() -> str:
    """Generate unique trace ID for request tracking."""
    return str(uuid4())


def check_content_safety(message: str) -> Tuple[bool, Optional[str]]:
    """
    Check if message contains blocked content.
    
    Returns:
        Tuple of (is_safe, reason_if_blocked)
    """
    if not message:
        return True, None
    
    for i, pattern in enumerate(_compiled_patterns):
        if pattern.search(message):
            # Log for audit (without exposing the content)
            logger.warning(f"Content blocked by pattern {i}")
            return False, _get_block_reason(i)
    
    return True, None


def _get_block_reason(pattern_index: int) -> str:
    """Get user-friendly reason for content block."""
    reasons = {
        0: "I can't help with adult content.",
        1: "I can't assist with violent content.",
        2: "I can't engage with hateful content.",
        3: "I can't help with illegal activities.",
        4: "If you're struggling, please reach out to a crisis helpline.",
    }
    return reasons.get(pattern_index, "I can't process that request.")


def safe_llm_response(
    call_fn,
    *args,
    fallback_message: str = "I'm having trouble right now. Please try again.",
    **kwargs
):
    """
    Wrap LLM call with failure handling.
    
    Args:
        call_fn: Function to call
        *args: Args for function
        fallback_message: Message if call fails
        **kwargs: Kwargs for function
    
    Returns:
        Response or fallback dict
    """
    try:
        return call_fn(*args, **kwargs)
    except Exception as e:
        logger.error(f"LLM call failed: {e}")
        return {
            "status": "error",
            "error": "llm_failure",
            "fallback": True,
            "output": {
                "message": fallback_message,
                "original_error": str(e)[:100]  # Truncate for safety
            }
        }


class RequestGuard:
    """Guard for incoming requests with trace ID and safety checks."""
    
    def __init__(self, message: str, user_id: str):
        self.trace_id = generate_trace_id()
        self.message = message
        self.user_id = user_id
        self.is_safe = True
        self.block_reason = None
        
        # Run safety check
        self.is_safe, self.block_reason = check_content_safety(message)
    
    def get_blocked_response(self) -> dict:
        """Get response for blocked content."""
        return {
            "reply": self.block_reason or "I can't help with that request.",
            "action": "blocked",
            "intent": "blocked",
            "trace_id": self.trace_id,
            "ui_elements": [],
            "data": {"blocked": True}
        }
    
    def log_request(self, intent: str, success: bool):
        """Log request for audit trail."""
        logger.info(
            f"[{self.trace_id}] user={self.user_id[:20]} "
            f"intent={intent} success={success}"
        )

