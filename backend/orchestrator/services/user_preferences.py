"""
User Preferences Service - Per-user personalization for agent behavior.
Injects structured preferences into agent prompts without exposing raw history.
"""
from typing import Dict, Any, Optional, List
from pydantic import BaseModel
from datetime import datetime

from .supabase_client import supabase


class UserPreferences(BaseModel):
    """User preferences model."""
    user_id: str
    display_name: Optional[str] = None
    preferred_medium: str = "api"
    preferred_language: str = "python"
    code_style: str = "clean"
    include_tests: bool = True
    include_docstrings: bool = True
    content_tone: str = "professional"
    target_audience: Optional[str] = None
    auto_deploy_threshold: float = 0.9
    require_confirmation: bool = True
    verbose_responses: bool = False
    daily_request_limit: int = 100
    requests_today: int = 0
    
    def as_prompt_lines(self) -> List[str]:
        """Convert preferences to prompt injection lines."""
        lines = []
        
        # Code preferences
        lines.append(f"User prefers {self.preferred_language} code")
        lines.append(f"Code style: {self.code_style}")
        if self.include_tests:
            lines.append("Always include unit tests")
        if self.include_docstrings:
            lines.append("Include docstrings for all functions")
        
        # Content tone
        lines.append(f"Response tone: {self.content_tone}")
        if self.target_audience:
            lines.append(f"Target audience: {self.target_audience}")
        
        # Behavior
        if self.verbose_responses:
            lines.append("Provide detailed explanations")
        else:
            lines.append("Keep responses concise")
        
        return lines
    
    def can_make_request(self) -> bool:
        """Check if user has requests remaining."""
        return self.requests_today < self.daily_request_limit


def get_user_preferences(user_id: str) -> UserPreferences:
    """Fetch or create user preferences."""
    if not user_id:
        return UserPreferences(user_id="anonymous")
    
    result = supabase.table("user_preferences").select("*").eq("user_id", user_id).execute()
    
    if result.data:
        return UserPreferences(**result.data[0])
    
    # Create default preferences for new user
    default = UserPreferences(user_id=user_id)
    supabase.table("user_preferences").insert(default.model_dump(exclude={"requests_today"})).execute()
    return default


def update_user_preferences(user_id: str, updates: Dict[str, Any]) -> UserPreferences:
    """Update user preferences."""
    allowed_fields = {
        "display_name", "preferred_medium", "preferred_language", "code_style",
        "include_tests", "include_docstrings", "content_tone", "target_audience",
        "auto_deploy_threshold", "require_confirmation", "verbose_responses"
    }
    
    filtered = {k: v for k, v in updates.items() if k in allowed_fields}
    filtered["updated_at"] = datetime.utcnow().isoformat()
    
    supabase.table("user_preferences").update(filtered).eq("user_id", user_id).execute()
    return get_user_preferences(user_id)


def increment_request_count(user_id: str) -> bool:
    """Increment request count, return False if limit exceeded."""
    prefs = get_user_preferences(user_id)
    
    if not prefs.can_make_request():
        return False
    
    supabase.table("user_preferences").update({
        "requests_today": prefs.requests_today + 1,
        "last_request_at": datetime.utcnow().isoformat()
    }).eq("user_id", user_id).execute()
    
    return True


def get_user_context(user_id: str, session_id: Optional[str] = None) -> Dict[str, Any]:
    """Get user's conversation context."""
    query = supabase.table("user_context").select("*").eq("user_id", user_id)
    
    if session_id:
        query = query.eq("session_id", session_id)
    
    result = query.order("created_at", desc=True).limit(1).execute()
    
    if result.data:
        return result.data[0].get("context_data", {})
    return {}


def save_user_context(user_id: str, context: Dict[str, Any], session_id: Optional[str] = None):
    """Save user's conversation context."""
    supabase.table("user_context").insert({
        "user_id": user_id,
        "session_id": session_id,
        "last_intent": context.get("last_intent"),
        "last_pipeline_id": context.get("pipeline_id"),
        "context_data": context
    }).execute()

