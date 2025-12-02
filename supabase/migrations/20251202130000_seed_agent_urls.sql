-- Seed agent_registry with Cloud Run service URLs
-- Migration: 20251202_seed_agent_urls

INSERT INTO agent_registry (agent_name, service_url, status) VALUES
  ('code_writer', 'https://king-code-writer-d3zysgasgq-uc.a.run.app', 'active'),
  ('code_reviewer', 'https://king-code-reviewer-250524159533.us-central1.run.app', 'active'),
  ('video_planner', 'https://king-video-planner-250524159533.us-central1.run.app', 'active'),
  ('script_writer', 'https://king-script-writer-250524159533.us-central1.run.app', 'active'),
  ('memory_selector', 'https://king-memory-selector-250524159533.us-central1.run.app', 'active')
ON CONFLICT (agent_name) DO UPDATE SET
  service_url = EXCLUDED.service_url,
  status = EXCLUDED.status,
  updated_at = NOW();

