CREATE TABLE IF NOT EXISTS entities (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    canonical_name TEXT NOT NULL UNIQUE,
    aliases JSONB DEFAULT '[]'::jsonb,
    type TEXT CHECK (type IN ('Human', 'AI', 'Organization', 'System')),
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_entities_aliases ON entities USING GIN (aliases);
CREATE INDEX IF NOT EXISTS idx_entities_canonical_name ON entities(canonical_name);

