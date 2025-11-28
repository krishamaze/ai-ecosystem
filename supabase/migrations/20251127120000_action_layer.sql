-- Action layer: track actions taken on pipeline outputs

-- Add action_taken to telemetry
ALTER TABLE task_telemetry 
ADD COLUMN IF NOT EXISTS action_taken TEXT DEFAULT NULL,
ADD COLUMN IF NOT EXISTS action_executed_at TIMESTAMPTZ DEFAULT NULL,
ADD COLUMN IF NOT EXISTS action_executed_by TEXT DEFAULT NULL;

-- Deployed artifacts table
CREATE TABLE IF NOT EXISTS deployed_artifacts (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    pipeline_id TEXT NOT NULL,
    task_id TEXT,
    artifact_type TEXT NOT NULL CHECK (artifact_type IN ('code', 'script', 'config')),
    file_path TEXT NOT NULL,
    content TEXT NOT NULL,
    language TEXT,
    
    -- Review metadata
    reviewer_verdict TEXT,
    security_score FLOAT,
    quality_score FLOAT,
    
    -- Deployment status
    status TEXT NOT NULL DEFAULT 'pending' CHECK (status IN ('pending', 'deployed', 'draft', 'rejected', 'rolled_back')),
    deployed_at TIMESTAMPTZ,
    deployed_by TEXT,
    
    -- Audit
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- Index for quick lookups
CREATE INDEX IF NOT EXISTS idx_deployed_artifacts_pipeline ON deployed_artifacts(pipeline_id);
CREATE INDEX IF NOT EXISTS idx_deployed_artifacts_status ON deployed_artifacts(status);

-- Draft scripts storage
CREATE TABLE IF NOT EXISTS draft_scripts (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    pipeline_id TEXT NOT NULL,
    task_id TEXT,
    script_type TEXT NOT NULL CHECK (script_type IN ('video', 'content', 'other')),
    content JSONB NOT NULL,
    confidence FLOAT,
    
    status TEXT NOT NULL DEFAULT 'draft' CHECK (status IN ('draft', 'approved', 'rejected')),
    approved_by TEXT,
    approved_at TIMESTAMPTZ,
    
    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_draft_scripts_status ON draft_scripts(status);

-- Action audit log
CREATE TABLE IF NOT EXISTS action_audit_log (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    action_type TEXT NOT NULL,
    pipeline_id TEXT,
    artifact_id UUID,
    executed_by TEXT NOT NULL,
    previous_state JSONB,
    new_state JSONB,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

COMMENT ON TABLE deployed_artifacts IS 'Production-ready code artifacts from pipeline execution';
COMMENT ON TABLE draft_scripts IS 'Scripts pending approval or stored as drafts';
COMMENT ON TABLE action_audit_log IS 'Audit trail for all action executions';

