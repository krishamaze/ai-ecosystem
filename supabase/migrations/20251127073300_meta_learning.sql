-- TASK TELEMETRY (structured outcomes for learning)
create table task_telemetry (
  id uuid primary key default gen_random_uuid(),
  task_id uuid references tasks(id) on delete cascade,
  agent_role text not null,
  dna_version text not null default '1.0.0',
  success boolean not null,
  time_taken_seconds int,
  confidence_final numeric,
  human_feedback text check (human_feedback in ('accepted', 'rejected', 'revised', null)),
  failure_reason text,
  created_at timestamptz default now()
);

create index idx_telemetry_task on task_telemetry(task_id);
create index idx_telemetry_agent on task_telemetry(agent_role);
create index idx_telemetry_feedback on task_telemetry(human_feedback);

-- AUDIT REPORTS (from agent_auditor)
create table audit_reports (
  id uuid primary key default gen_random_uuid(),
  time_range_start timestamptz not null,
  time_range_end timestamptz not null,
  agents_analyzed text[] not null,
  total_runs int not null,
  failure_count int not null,
  low_confidence_count int not null,
  findings jsonb not null,
  recommendations jsonb not null,
  created_at timestamptz default now()
);

-- DNA PROPOSALS (from meta_reasoner)
create table dna_proposals (
  id uuid primary key default gen_random_uuid(),
  audit_report_id uuid references audit_reports(id),
  target_role text not null,
  change_type text not null check (change_type in ('add_rule', 'modify_rule', 'remove_rule')),
  change_content text not null,
  risk_level text not null check (risk_level in ('low', 'medium', 'high', 'critical')),
  confidence numeric not null,
  rollback_strategy text not null,
  status text not null default 'pending' check (status in ('pending', 'approved', 'rejected', 'applied', 'rolled_back')),
  reviewed_by text,
  reviewed_at timestamptz,
  applied_at timestamptz,
  created_at timestamptz default now()
);

create index idx_proposals_status on dna_proposals(status);
create index idx_proposals_role on dna_proposals(target_role);

-- DNA VERSION HISTORY (audit trail)
create table dna_versions (
  id uuid primary key default gen_random_uuid(),
  version text not null,
  snapshot_json jsonb not null,
  applied_by text not null,
  proposal_id uuid references dna_proposals(id),
  created_at timestamptz default now()
);