-- Agent Specs Table: Add missing columns for orchestrator
-- Table already exists from prior migration, this adds is_active, version, timestamps

-- Add missing columns (idempotent)
ALTER TABLE agent_specs ADD COLUMN IF NOT EXISTS is_active BOOLEAN DEFAULT TRUE;
ALTER TABLE agent_specs ADD COLUMN IF NOT EXISTS version INTEGER DEFAULT 1;
ALTER TABLE agent_specs ADD COLUMN IF NOT EXISTS updated_at TIMESTAMPTZ DEFAULT NOW();

-- Index for fast lookups (idempotent)
CREATE INDEX IF NOT EXISTS idx_agent_specs_name ON agent_specs(agent_name);
CREATE INDEX IF NOT EXISTS idx_agent_specs_active ON agent_specs(is_active) WHERE is_active = TRUE;

-- Trigger to update updated_at
CREATE OR REPLACE FUNCTION update_agent_specs_timestamp()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    NEW.version = COALESCE(OLD.version, 0) + 1;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

DROP TRIGGER IF EXISTS agent_specs_updated ON agent_specs;
CREATE TRIGGER agent_specs_updated
    BEFORE UPDATE ON agent_specs
    FOR EACH ROW
    EXECUTE FUNCTION update_agent_specs_timestamp();

-- RLS policies (idempotent with DROP IF EXISTS)
ALTER TABLE agent_specs ENABLE ROW LEVEL SECURITY;

DROP POLICY IF EXISTS "Allow read access to agent_specs" ON agent_specs;
CREATE POLICY "Allow read access to agent_specs" ON agent_specs
    FOR SELECT USING (true);

DROP POLICY IF EXISTS "Allow service role full access to agent_specs" ON agent_specs;
CREATE POLICY "Allow service role full access to agent_specs" ON agent_specs
    FOR ALL USING (auth.role() = 'service_role');

