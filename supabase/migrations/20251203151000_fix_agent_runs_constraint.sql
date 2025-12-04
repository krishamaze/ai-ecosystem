-- Fix agent_runs constraint - allow null agent_role
-- Migration: 20251203151000_fix_agent_runs_constraint

-- Make agent_role nullable since code uses agent_name instead
ALTER TABLE agent_runs ALTER COLUMN agent_role DROP NOT NULL;

-- Ensure agent_name backfills to agent_role for compatibility
CREATE OR REPLACE FUNCTION sync_agent_role_from_name()
RETURNS TRIGGER AS $$
BEGIN
    IF NEW.agent_role IS NULL AND NEW.agent_name IS NOT NULL THEN
        NEW.agent_role = NEW.agent_name;
    END IF;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

DROP TRIGGER IF EXISTS sync_agent_role_trigger ON agent_runs;
CREATE TRIGGER sync_agent_role_trigger
    BEFORE INSERT ON agent_runs
    FOR EACH ROW
    EXECUTE FUNCTION sync_agent_role_from_name();

