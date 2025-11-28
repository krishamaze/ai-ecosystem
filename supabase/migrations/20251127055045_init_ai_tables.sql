-- AI Ecosystem Core Tables
-- Migration: init_ai_tables

-- TASK master
create table tasks (
  id uuid primary key default gen_random_uuid(),
  title text not null,
  status text default 'planning',
  created_at timestamptz default now()
);

-- CONTEXT versioning
create table task_context (
  id uuid primary key default gen_random_uuid(),
  task_id uuid references tasks(id) on delete cascade,
  context_json jsonb not null,
  version int default 1,
  is_active boolean default true,
  created_at timestamptz default now()
);

-- AGENT RUN LOG (full trace)
create table agent_runs (
  id uuid primary key default gen_random_uuid(),
  task_id uuid references tasks(id) on delete cascade,
  agent_role text not null,
  input_json jsonb,
  output_json jsonb,
  confidence numeric,
  created_at timestamptz default now()
);

-- Indexes for performance
create index idx_task_context_task_id on task_context(task_id);
create index idx_task_context_active on task_context(task_id, is_active);
create index idx_agent_runs_task_id on agent_runs(task_id);
create index idx_agent_runs_role on agent_runs(agent_role);