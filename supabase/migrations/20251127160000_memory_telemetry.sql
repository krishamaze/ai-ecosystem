-- Memory selector telemetry columns
-- Track which memories are used vs rejected to enable future pruning strategy

ALTER TABLE task_telemetry
ADD COLUMN IF NOT EXISTS memory_used INT DEFAULT 0,
ADD COLUMN IF NOT EXISTS memory_rejected INT DEFAULT 0,
ADD COLUMN IF NOT EXISTS memory_sources JSONB;

-- Index for memory analytics
CREATE INDEX IF NOT EXISTS idx_telemetry_memory_stats
ON task_telemetry(memory_used, memory_rejected)
WHERE memory_used > 0 OR memory_rejected > 0;

CREATE INDEX IF NOT EXISTS idx_telemetry_memory_used
ON task_telemetry(memory_used);

COMMENT ON COLUMN task_telemetry.memory_used IS 'Count of memories approved by memory_selector for this task';
COMMENT ON COLUMN task_telemetry.memory_rejected IS 'Count of memories rejected by memory_selector for this task';

