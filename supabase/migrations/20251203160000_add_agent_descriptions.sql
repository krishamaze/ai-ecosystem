-- Add descriptions to agent_registry so router knows what each agent does
-- Migration: 20251203160000_add_agent_descriptions

-- 1. Add description column
ALTER TABLE agent_registry ADD COLUMN IF NOT EXISTS description TEXT;

-- 2. Populate descriptions for existing agents
UPDATE agent_registry SET description = 'Writes production-ready code in any language. Use for: coding tasks, functions, scripts, algorithms' WHERE agent_name = 'code_writer';
UPDATE agent_registry SET description = 'Reviews code for bugs, security, performance. Use for: code review, audit, quality checks' WHERE agent_name = 'code_reviewer';
UPDATE agent_registry SET description = 'Plans video content with scenes, shots, timing. Use for: video planning, storyboarding, content structure' WHERE agent_name = 'video_planner';
UPDATE agent_registry SET description = 'Writes scripts, prompts, narratives. Use for: writing prompts, dialogue, scripts, creative text' WHERE agent_name = 'script_writer';
UPDATE agent_registry SET description = 'Selects relevant memories from context. Use for: memory queries, context retrieval, history' WHERE agent_name = 'memory_selector';
UPDATE agent_registry SET description = 'Constitutional Architect - drafts and maintains Kingdom Constitution. Use for: governance, constitution, laws, rules' WHERE agent_name = 'ambedkar';

