-- Fix agent_registry URLs and agent_runs schema
-- Migration: 20251203150000_fix_agent_registry_and_runs

-- 1. Fix agent_runs schema to match code expectations
ALTER TABLE agent_runs ADD COLUMN IF NOT EXISTS agent_name TEXT;
ALTER TABLE agent_runs ADD COLUMN IF NOT EXISTS input JSONB;
ALTER TABLE agent_runs ADD COLUMN IF NOT EXISTS output JSONB;
ALTER TABLE agent_runs ADD COLUMN IF NOT EXISTS success BOOLEAN DEFAULT FALSE;
ALTER TABLE agent_runs ADD COLUMN IF NOT EXISTS error TEXT;
ALTER TABLE agent_runs ADD COLUMN IF NOT EXISTS duration_ms INTEGER;

-- Backfill agent_name from agent_role if needed
UPDATE agent_runs SET agent_name = agent_role WHERE agent_name IS NULL AND agent_role IS NOT NULL;

-- 2. Fix agent_registry with correct Cloud Run URLs
UPDATE agent_registry SET 
  service_url = 'https://king-code-writer-250524159533.us-central1.run.app',
  updated_at = NOW()
WHERE agent_name = 'code_writer';

UPDATE agent_registry SET 
  service_url = 'https://king-code-reviewer-250524159533.us-central1.run.app',
  updated_at = NOW()
WHERE agent_name = 'code_reviewer';

UPDATE agent_registry SET 
  service_url = 'https://king-video-planner-250524159533.us-central1.run.app',
  updated_at = NOW()
WHERE agent_name = 'video_planner';

UPDATE agent_registry SET 
  service_url = 'https://king-script-writer-250524159533.us-central1.run.app',
  updated_at = NOW()
WHERE agent_name = 'script_writer';

UPDATE agent_registry SET 
  service_url = 'https://king-memory-selector-250524159533.us-central1.run.app',
  updated_at = NOW()
WHERE agent_name = 'memory_selector';

UPDATE agent_registry SET 
  service_url = 'https://king-ambedkar-250524159533.us-central1.run.app',
  updated_at = NOW()
WHERE agent_name = 'ambedkar';

-- 3. Delete any old entries with wrong URLs (Docker internal names)
DELETE FROM agent_registry 
WHERE service_url LIKE 'http://%service:%' 
   OR service_url LIKE 'http://localhost%';

-- 4. Ensure all agents have correct URLs (upsert remaining)
INSERT INTO agent_registry (agent_name, service_url, status) VALUES
  ('code_writer', 'https://king-code-writer-250524159533.us-central1.run.app', 'active'),
  ('code_reviewer', 'https://king-code-reviewer-250524159533.us-central1.run.app', 'active'),
  ('video_planner', 'https://king-video-planner-250524159533.us-central1.run.app', 'active'),
  ('script_writer', 'https://king-script-writer-250524159533.us-central1.run.app', 'active'),
  ('memory_selector', 'https://king-memory-selector-250524159533.us-central1.run.app', 'active'),
  ('ambedkar', 'https://king-ambedkar-250524159533.us-central1.run.app', 'active')
ON CONFLICT (agent_name) DO UPDATE SET
  service_url = EXCLUDED.service_url,
  status = EXCLUDED.status,
  updated_at = NOW();

