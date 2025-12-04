-- =============================================================================
-- Dynamic Taxonomies - AI-powered evolving classification system
-- Categories, entity types, intents, and other taxonomies grow organically
-- =============================================================================

-- Main taxonomy table
CREATE TABLE IF NOT EXISTS taxonomies (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    taxonomy_type TEXT NOT NULL,  -- 'category', 'entity_type', 'intent', 'context_type', 'tone', 'action'
    value TEXT NOT NULL,
    description TEXT,
    parent_value TEXT,  -- For hierarchical taxonomies
    usage_count INT DEFAULT 1,
    confidence_threshold FLOAT DEFAULT 0.9,  -- Min confidence to auto-match
    created_by TEXT DEFAULT 'system',  -- 'system', 'ai', 'user'
    created_at TIMESTAMPTZ DEFAULT now(),
    last_used_at TIMESTAMPTZ DEFAULT now(),
    metadata JSONB DEFAULT '{}',
    UNIQUE(taxonomy_type, value)
);

-- Index for fast lookups
CREATE INDEX IF NOT EXISTS idx_taxonomies_type ON taxonomies(taxonomy_type);
CREATE INDEX IF NOT EXISTS idx_taxonomies_usage ON taxonomies(taxonomy_type, usage_count DESC);

-- =============================================================================
-- Seed: Memory Categories
-- =============================================================================
INSERT INTO taxonomies (taxonomy_type, value, description, created_by) VALUES
    ('category', 'personal', 'Personal life, family, health, hobbies', 'system'),
    ('category', 'business', 'Work, career, professional matters', 'system'),
    ('category', 'project', 'Specific projects user is working on', 'system'),
    ('category', 'preference', 'User preferences, likes, dislikes', 'system'),
    ('category', 'task', 'Actionable tasks and todos', 'system'),
    ('category', 'social', 'Relationships, social interactions', 'system'),
    ('category', 'technical', 'Technical discussions, coding, systems', 'system'),
    ('category', 'creative', 'Art, music, writing, design', 'system'),
    ('category', 'learning', 'Education, skills, knowledge acquisition', 'system'),
    ('category', 'financial', 'Money, investments, budgets', 'system')
ON CONFLICT (taxonomy_type, value) DO NOTHING;

-- =============================================================================
-- Seed: Entity Types
-- =============================================================================
INSERT INTO taxonomies (taxonomy_type, value, description, created_by) VALUES
    ('entity_type', 'person', 'Human individual', 'system'),
    ('entity_type', 'organization', 'Company, team, group', 'system'),
    ('entity_type', 'project', 'Named project or initiative', 'system'),
    ('entity_type', 'product', 'Software, hardware, service', 'system'),
    ('entity_type', 'technology', 'Programming language, framework, tool', 'system'),
    ('entity_type', 'location', 'City, country, place', 'system'),
    ('entity_type', 'event', 'Meeting, deadline, milestone', 'system'),
    ('entity_type', 'concept', 'Abstract idea, methodology', 'system'),
    ('entity_type', 'ai_agent', 'AI agent or assistant', 'system'),
    ('entity_type', 'document', 'File, report, specification', 'system')
ON CONFLICT (taxonomy_type, value) DO NOTHING;

-- =============================================================================
-- Seed: Intent Types
-- =============================================================================
INSERT INTO taxonomies (taxonomy_type, value, description, created_by) VALUES
    ('intent', 'generate_code', 'User wants code written', 'system'),
    ('intent', 'generate_video', 'User wants video content created', 'system'),
    ('intent', 'generate_image', 'User wants image created', 'system'),
    ('intent', 'review_code', 'User wants code reviewed', 'system'),
    ('intent', 'explain', 'User wants explanation or teaching', 'system'),
    ('intent', 'plan', 'User wants planning or strategy', 'system'),
    ('intent', 'debug', 'User wants help fixing issues', 'system'),
    ('intent', 'deploy', 'User wants deployment assistance', 'system'),
    ('intent', 'search', 'User wants information retrieved', 'system'),
    ('intent', 'remember', 'User wants something stored in memory', 'system'),
    ('intent', 'recall', 'User wants past information retrieved', 'system'),
    ('intent', 'chat', 'General conversation, no specific task', 'system'),
    ('intent', 'clarify', 'User needs clarification or more info', 'system')
ON CONFLICT (taxonomy_type, value) DO NOTHING;

-- =============================================================================
-- Seed: Context Types (for fingerprinting)
-- =============================================================================
INSERT INTO taxonomies (taxonomy_type, value, description, created_by) VALUES
    ('context_type', 'project', 'A software/creative project', 'system'),
    ('context_type', 'role', 'User role (developer, manager, etc)', 'system'),
    ('context_type', 'domain', 'Knowledge domain (AI, web, mobile)', 'system'),
    ('context_type', 'goal', 'Long-term objective', 'system'),
    ('context_type', 'constraint', 'Limitation or requirement', 'system'),
    ('context_type', 'workflow', 'Recurring process or pattern', 'system')
ON CONFLICT (taxonomy_type, value) DO NOTHING;

-- =============================================================================
-- Seed: Tones (for content generation)
-- =============================================================================
INSERT INTO taxonomies (taxonomy_type, value, description, created_by) VALUES
    ('tone', 'professional', 'Formal, business-appropriate', 'system'),
    ('tone', 'casual', 'Friendly, conversational', 'system'),
    ('tone', 'technical', 'Precise, jargon-heavy', 'system'),
    ('tone', 'humorous', 'Light, witty, fun', 'system'),
    ('tone', 'inspirational', 'Motivating, uplifting', 'system'),
    ('tone', 'educational', 'Teaching, explanatory', 'system'),
    ('tone', 'urgent', 'Time-sensitive, action-oriented', 'system')
ON CONFLICT (taxonomy_type, value) DO NOTHING;

-- =============================================================================
-- Seed: Actions (for router decisions)
-- =============================================================================
INSERT INTO taxonomies (taxonomy_type, value, description, created_by) VALUES
    ('action', 'execute', 'Run an agent to complete task', 'system'),
    ('action', 'respond', 'Direct conversational response', 'system'),
    ('action', 'clarify', 'Ask user for more information', 'system'),
    ('action', 'delegate', 'Pass to another agent or system', 'system'),
    ('action', 'defer', 'Schedule for later execution', 'system'),
    ('action', 'reject', 'Decline request with explanation', 'system')
ON CONFLICT (taxonomy_type, value) DO NOTHING;

-- Function to increment usage and update last_used
CREATE OR REPLACE FUNCTION increment_taxonomy_usage(p_type TEXT, p_value TEXT)
RETURNS void AS $$
BEGIN
    UPDATE taxonomies 
    SET usage_count = usage_count + 1, last_used_at = now()
    WHERE taxonomy_type = p_type AND value = p_value;
END;
$$ LANGUAGE plpgsql;

