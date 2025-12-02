-- TASK TELEMETRY (structured outcomes for learning)
CREATE TABLE IF NOT EXISTS task_telemetry (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  task_id UUID REFERENCES tasks(id) ON DELETE CASCADE,
  agent_role TEXT NOT NULL,
  dna_version TEXT NOT NULL DEFAULT '1.0.0',
  success BOOLEAN NOT NULL,
  time_taken_seconds INT,
  confidence_final NUMERIC,
  human_feedback TEXT CHECK (human_feedback IN ('accepted', 'rejected', 'revised', NULL)),
  failure_reason TEXT,
  created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_telemetry_task ON task_telemetry(task_id);
CREATE INDEX IF NOT EXISTS idx_telemetry_agent ON task_telemetry(agent_role);
CREATE INDEX IF NOT EXISTS idx_telemetry_feedback ON task_telemetry(human_feedback);

-- AUDIT REPORTS (from agent_auditor)
CREATE TABLE IF NOT EXISTS audit_reports (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  time_range_start TIMESTAMPTZ NOT NULL,
  time_range_end TIMESTAMPTZ NOT NULL,
  agents_analyzed TEXT[] NOT NULL,
  total_runs INT NOT NULL,
  failure_count INT NOT NULL,
  low_confidence_count INT NOT NULL,
  findings JSONB NOT NULL,
  recommendations JSONB NOT NULL,
  created_at TIMESTAMPTZ DEFAULT NOW()
);

-- DNA PROPOSALS (from meta_reasoner)
CREATE TABLE IF NOT EXISTS dna_proposals (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  audit_report_id UUID REFERENCES audit_reports(id),
  target_role TEXT NOT NULL,
  change_type TEXT NOT NULL CHECK (change_type IN ('add_rule', 'modify_rule', 'remove_rule')),
  change_content TEXT NOT NULL,
  risk_level TEXT NOT NULL CHECK (risk_level IN ('low', 'medium', 'high', 'critical')),
  confidence NUMERIC NOT NULL,
  rollback_strategy TEXT NOT NULL,
  status TEXT NOT NULL DEFAULT 'pending' CHECK (status IN ('pending', 'approved', 'rejected', 'applied', 'rolled_back')),
  reviewed_by TEXT,
  reviewed_at TIMESTAMPTZ,
  applied_at TIMESTAMPTZ,
  created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_proposals_status ON dna_proposals(status);
CREATE INDEX IF NOT EXISTS idx_proposals_role ON dna_proposals(target_role);

-- DNA VERSION HISTORY (audit trail)
CREATE TABLE IF NOT EXISTS dna_versions (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  version TEXT NOT NULL,
  snapshot_json JSONB NOT NULL,
  applied_by TEXT NOT NULL,
  proposal_id UUID REFERENCES dna_proposals(id),
  created_at TIMESTAMPTZ DEFAULT NOW()
);