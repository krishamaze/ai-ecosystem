-- Register Ambedkar (Constitutional Architect) in agent_registry
-- Migration: 20251203140000_register_ambedkar

INSERT INTO agent_registry (agent_name, service_url, status) VALUES
  ('ambedkar', 'https://king-ambedkar-250524159533.us-central1.run.app', 'active')
ON CONFLICT (agent_name) DO UPDATE SET
  service_url = EXCLUDED.service_url,
  status = EXCLUDED.status,
  updated_at = NOW();

