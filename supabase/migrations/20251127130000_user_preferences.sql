-- User preferences for personalized agent behavior

CREATE TABLE IF NOT EXISTS user_preferences (
    user_id TEXT PRIMARY KEY,
    
    -- Identity
    display_name TEXT,
    preferred_medium TEXT DEFAULT 'api' CHECK (preferred_medium IN ('telegram', 'dashboard', 'api')),
    
    -- Code generation preferences
    preferred_language TEXT DEFAULT 'python',
    code_style TEXT DEFAULT 'clean',  -- clean, verbose, minimal
    include_tests BOOLEAN DEFAULT true,
    include_docstrings BOOLEAN DEFAULT true,
    
    -- Content preferences
    content_tone TEXT DEFAULT 'professional',  -- professional, casual, technical
    target_audience TEXT,
    
    -- Behavior preferences
    auto_deploy_threshold FLOAT DEFAULT 0.9,  -- security score threshold for auto-deploy
    require_confirmation BOOLEAN DEFAULT true,
    verbose_responses BOOLEAN DEFAULT false,
    
    -- Rate limiting
    daily_request_limit INTEGER DEFAULT 100,
    requests_today INTEGER DEFAULT 0,
    last_request_at TIMESTAMPTZ,
    
    -- Metadata
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- User interaction history (for context, not full memory)
CREATE TABLE IF NOT EXISTS user_context (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id TEXT NOT NULL REFERENCES user_preferences(user_id) ON DELETE CASCADE,
    
    session_id TEXT,
    last_intent TEXT,
    last_pipeline_id TEXT,
    context_data JSONB DEFAULT '{}',
    
    expires_at TIMESTAMPTZ DEFAULT NOW() + INTERVAL '24 hours',
    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_user_context_user ON user_context(user_id);
CREATE INDEX IF NOT EXISTS idx_user_context_session ON user_context(session_id);

-- Function to reset daily request count
CREATE OR REPLACE FUNCTION reset_daily_requests()
RETURNS void AS $$
BEGIN
    UPDATE user_preferences 
    SET requests_today = 0 
    WHERE DATE(last_request_at) < CURRENT_DATE;
END;
$$ LANGUAGE plpgsql;

COMMENT ON TABLE user_preferences IS 'Per-user settings for personalized agent behavior';
COMMENT ON TABLE user_context IS 'Short-term context for multi-turn conversations';

