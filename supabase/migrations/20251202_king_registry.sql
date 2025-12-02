-- Enable UUID extension if not already enabled
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- Table: agent_registry
CREATE TABLE IF NOT EXISTS agent_registry (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    agent_name TEXT UNIQUE NOT NULL,
    service_url TEXT NOT NULL,
    status TEXT DEFAULT 'active',  -- active | disabled | maintenance
    version TEXT DEFAULT '1.0.0',
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- Table: agent_specs
CREATE TABLE IF NOT EXISTS agent_specs (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    agent_name TEXT UNIQUE NOT NULL,
    purpose TEXT NOT NULL,
    dna_rules JSONB NOT NULL,  -- Array of rules
    output_schema JSONB NOT NULL,  -- Expected output structure
    dependencies JSONB DEFAULT '[]'::jsonb,  -- Array of agent names
    version TEXT DEFAULT '1.0.0',
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- Table: agent_runs (ensure it exists or create if missing from previous migrations)
CREATE TABLE IF NOT EXISTS agent_runs (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    agent_name TEXT NOT NULL,
    input JSONB NOT NULL,
    output JSONB,
    success BOOLEAN DEFAULT false,
    error TEXT,
    duration_ms INT,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

DO $$
BEGIN
    IF EXISTS (
        SELECT 1
        FROM information_schema.columns
        WHERE table_name = 'agent_runs' AND column_name = 'agent_name'
    ) THEN
        CREATE INDEX IF NOT EXISTS idx_agent_runs_agent_name ON agent_runs(agent_name);
    END IF;
END $$;


-- Seed data for agent_registry
INSERT INTO agent_registry (agent_name, service_url) VALUES
    ('code_writer', 'http://code-writer-service:8001'),
    ('code_reviewer', 'http://code-reviewer-service:8002'),
    ('video_planner', 'http://video-planner-service:8003'),
    ('script_writer', 'http://script-writer-service:8004'),
    ('memory_selector', 'http://memory-selector-service:8005')
ON CONFLICT (agent_name) DO UPDATE 
SET service_url = EXCLUDED.service_url;

-- Seed data for agent_specs
-- code_writer
INSERT INTO agent_specs (agent_name, purpose, dna_rules, output_schema, dependencies) VALUES
    ('code_writer', 
     'Generate production-ready code based on structured requirements. Output executable code with tests.',
     '["output code ONLY in specified language — no mixed syntax", "every function must have docstring or comment explaining purpose", "include basic error handling — never assume happy path only", "output must include at least one test case", "no placeholder comments like ''TODO'' or ''implement later''", "code must be complete and runnable — no stubs", "follow language-specific conventions (PEP8 for Python, etc.)", "output valid JSON with code in ''code'' field — no raw code blocks"]'::jsonb,
     '{"language": "string", "code": "string", "tests": "array", "dependencies": "array", "confidence": "float", "explanation": "string"}'::jsonb,
     '["code_reviewer"]'::jsonb)
ON CONFLICT (agent_name) DO UPDATE
SET dna_rules = EXCLUDED.dna_rules, output_schema = EXCLUDED.output_schema;

-- code_reviewer
INSERT INTO agent_specs (agent_name, purpose, dna_rules, output_schema, dependencies) VALUES
    ('code_reviewer', 
     'Review generated code for correctness, security, and best practices. Gate before deployment and recommend action.',
     '["check for security vulnerabilities — SQL injection, XSS, hardcoded secrets", "verify error handling exists for all external calls", "flag any undefined variables or missing imports", "check that tests actually test the code functionality", "verdict must be APPROVE, REQUEST_CHANGES, or REJECT", "issues array must list specific line numbers when possible", "never approve code with critical security issues", "suggested_action must be: DEPLOY if verdict=APPROVE and security_score>=0.8, STORE_DRAFT if confidence<0.6, MANUAL_REVIEW otherwise", "output valid JSON only — no prose"]'::jsonb,
     '{"verdict": "string", "issues": "array", "security_score": "float", "quality_score": "float", "confidence": "float", "summary": "string", "suggested_action": "string"}'::jsonb,
     '[]'::jsonb)
ON CONFLICT (agent_name) DO UPDATE
SET dna_rules = EXCLUDED.dna_rules, output_schema = EXCLUDED.output_schema;

-- video_planner
INSERT INTO agent_specs (agent_name, purpose, dna_rules, output_schema, dependencies) VALUES
    ('video_planner', 
     'Extract structured context through questioning. Gather all required fields before proceeding.',
     '["only ask ONE question at a time", "if a field in known_context is filled, remove it from missing_fields", "when missing_fields is empty, set needs_clarification to false and current_question to null", "when missing_fields <= 2, ask for final confirmation", "no free text — must output valid JSON only", "include confidence score in every output", "confidence increases as more fields are filled", "ALWAYS include timestamp of response in output", "Always validate input length before processing", "Validate dependencies before handoff"]'::jsonb,
     '{"confidence": "float", "known_context": "object", "missing_fields": "array", "current_question": "string", "needs_clarification": "boolean"}'::jsonb,
     '["script_writer"]'::jsonb)
ON CONFLICT (agent_name) DO UPDATE
SET dna_rules = EXCLUDED.dna_rules, output_schema = EXCLUDED.output_schema;

-- script_writer
INSERT INTO agent_specs (agent_name, purpose, dna_rules, output_schema, dependencies) VALUES
    ('script_writer', 
     'Create timestamped reel script.',
     '["must follow context from planner", "no extra creativity", "no missing timestamps"]'::jsonb,
     '{"confidence": "float", "script_blocks": "array", "duration_seconds": "int"}'::jsonb,
     '[]'::jsonb)
ON CONFLICT (agent_name) DO UPDATE
SET dna_rules = EXCLUDED.dna_rules, output_schema = EXCLUDED.output_schema;

-- memory_selector
INSERT INTO agent_specs (agent_name, purpose, dna_rules, output_schema, dependencies) VALUES
    ('memory_selector', 
     'Filter relevant memories from candidates. Reduce noise before injection.',
     '["Approve only memories directly relevant to query", "Reject duplicates and outdated info", "Return confidence score", "output valid JSON only"]'::jsonb,
     '{"approved_memories": "array", "rejected_memories": "array", "confidence": "float"}'::jsonb,
     '[]'::jsonb)
ON CONFLICT (agent_name) DO UPDATE
SET dna_rules = EXCLUDED.dna_rules, output_schema = EXCLUDED.output_schema;

