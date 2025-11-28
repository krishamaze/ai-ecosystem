-- Service Registry for External APIs
-- Tracks third-party services integrated with the AI ecosystem

CREATE TABLE IF NOT EXISTS service_registry (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name TEXT NOT NULL UNIQUE,
    description TEXT NOT NULL,
    auth_strategy TEXT NOT NULL CHECK (auth_strategy IN ('API_KEY', 'OAUTH2', 'BASIC', 'NONE')),
    env_var TEXT NOT NULL,
    base_url TEXT,
    is_active BOOLEAN DEFAULT true,
    config JSONB DEFAULT '{}',
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- Index for fast lookups
CREATE INDEX IF NOT EXISTS idx_service_registry_name ON service_registry(name);
CREATE INDEX IF NOT EXISTS idx_service_registry_active ON service_registry(is_active);

-- Insert Mem0 as first external service
INSERT INTO service_registry (name, description, auth_strategy, env_var, base_url, config) VALUES (
    'mem0',
    'Hybrid memory graph + vector database for long-term agent recall',
    'API_KEY',
    'MEM0_API_KEY',
    'https://api.mem0.ai/v1',
    '{"features": ["graph_memory", "vector_memory", "user_scoping", "session_scoping", "async_mode"]}'
) ON CONFLICT (name) DO NOTHING;

-- Insert Gemini (already used)
INSERT INTO service_registry (name, description, auth_strategy, env_var, base_url, config) VALUES (
    'gemini',
    'Google Gemini LLM for agent reasoning',
    'API_KEY',
    'GEMINI_API_KEY',
    'https://generativelanguage.googleapis.com/v1beta',
    '{"model": "gemini-2.0-flash"}'
) ON CONFLICT (name) DO NOTHING;

-- Insert Supabase (already used)
INSERT INTO service_registry (name, description, auth_strategy, env_var, base_url, config) VALUES (
    'supabase',
    'PostgreSQL + Auth + Storage for operational data',
    'API_KEY',
    'SUPABASE_SERVICE_KEY',
    NULL,
    '{"features": ["database", "auth", "storage", "realtime"]}'
) ON CONFLICT (name) DO NOTHING;

COMMENT ON TABLE service_registry IS 'Registry of external services integrated with the AI ecosystem';
COMMENT ON COLUMN service_registry.auth_strategy IS 'Authentication method: API_KEY, OAUTH2, BASIC, or NONE';
COMMENT ON COLUMN service_registry.env_var IS 'Environment variable containing the auth credentials';

