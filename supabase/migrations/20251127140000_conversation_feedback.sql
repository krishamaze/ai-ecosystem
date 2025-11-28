-- Conversation feedback storage for learning
-- Tracks user reactions and system performance per request

CREATE TABLE IF NOT EXISTS conversation_feedback (
    id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    trace_id uuid NOT NULL,
    user_id text NOT NULL,
    message_hash text,  -- SHA256 of original message (privacy)
    intent text NOT NULL,
    success boolean NOT NULL DEFAULT true,
    latency_ms integer,
    feedback_type text,  -- 'positive', 'negative', 'report'
    feedback_text text,
    pipeline_id text,
    agent_role text,
    error_code text,
    created_at timestamptz DEFAULT now()
);

-- Indexes for analytics
CREATE INDEX IF NOT EXISTS idx_feedback_user ON conversation_feedback(user_id);
CREATE INDEX IF NOT EXISTS idx_feedback_trace ON conversation_feedback(trace_id);
CREATE INDEX IF NOT EXISTS idx_feedback_intent ON conversation_feedback(intent);
CREATE INDEX IF NOT EXISTS idx_feedback_created ON conversation_feedback(created_at DESC);
CREATE INDEX IF NOT EXISTS idx_feedback_type ON conversation_feedback(feedback_type) WHERE feedback_type IS NOT NULL;

-- View: Success rate by intent
CREATE OR REPLACE VIEW intent_success_rates AS
SELECT 
    intent,
    COUNT(*) as total_requests,
    SUM(CASE WHEN success THEN 1 ELSE 0 END) as successful,
    ROUND(100.0 * SUM(CASE WHEN success THEN 1 ELSE 0 END) / COUNT(*), 2) as success_rate,
    AVG(latency_ms) as avg_latency_ms
FROM conversation_feedback
WHERE created_at > now() - interval '7 days'
GROUP BY intent
ORDER BY total_requests DESC;

-- View: User engagement metrics
CREATE OR REPLACE VIEW user_engagement AS
SELECT 
    user_id,
    COUNT(*) as total_requests,
    COUNT(DISTINCT DATE(created_at)) as active_days,
    SUM(CASE WHEN feedback_type = 'positive' THEN 1 ELSE 0 END) as positive_feedback,
    SUM(CASE WHEN feedback_type = 'negative' THEN 1 ELSE 0 END) as negative_feedback,
    MAX(created_at) as last_active
FROM conversation_feedback
WHERE created_at > now() - interval '30 days'
GROUP BY user_id
ORDER BY total_requests DESC;

-- Comment
COMMENT ON TABLE conversation_feedback IS 'Stores request traces and user feedback for system improvement';

