-- Enhanced telemetry metrics for meaningful learning

-- Create enum for failure reasons
create type failure_reason_type as enum ('formatting', 'factual', 'logic', 'performance', 'timeout', 'unknown');

-- Add structured metric columns to task_telemetry (dna_version already exists from init)
alter table task_telemetry
  add column human_override boolean default false,
  add column failure_category failure_reason_type;

-- Create index for analytics queries
create index idx_telemetry_agent_success on task_telemetry(agent_role, success);
create index idx_telemetry_created on task_telemetry(created_at desc);

-- View for agent performance over time
create or replace view agent_performance as
select
  agent_role,
  count(*) as total_runs,
  sum(case when success then 1 else 0 end) as successes,
  sum(case when not success then 1 else 0 end) as failures,
  round(avg(case when success then 1.0 else 0.0 end) * 100, 2) as success_rate,
  round(avg(confidence_final), 3) as avg_confidence,
  round(avg(time_taken_seconds), 1) as avg_time_seconds,
  sum(case when human_override then 1 else 0 end) as human_overrides,
  count(distinct dna_version) as dna_versions_used
from task_telemetry
group by agent_role;

-- View for DNA version comparison
create or replace view dna_version_performance as
select
  dna_version,
  agent_role,
  count(*) as runs,
  round(avg(case when success then 1.0 else 0.0 end) * 100, 2) as success_rate,
  round(avg(confidence_final), 3) as avg_confidence,
  sum(case when human_override then 1 else 0 end) as overrides
from task_telemetry
where dna_version is not null
group by dna_version, agent_role
order by dna_version desc;

-- View for failure analysis
create or replace view failure_analysis as
select
  agent_role,
  failure_category,
  count(*) as count,
  round(avg(confidence_final), 3) as avg_confidence_at_failure
from task_telemetry
where success = false and failure_category is not null
group by agent_role, failure_category
order by agent_role, count desc;