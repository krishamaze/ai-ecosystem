-- Add RAG telemetry to task_telemetry
ALTER TABLE task_telemetry
ADD COLUMN IF NOT EXISTS rag_enabled BOOLEAN DEFAULT FALSE,
ADD COLUMN IF NOT EXISTS rag_query TEXT,
ADD COLUMN IF NOT EXISTS rag_source_count INTEGER;

-- Add RAG telemetry to conversation_feedback
ALTER TABLE conversation_feedback
ADD COLUMN IF NOT EXISTS rag_enabled BOOLEAN DEFAULT FALSE,
ADD COLUMN IF NOT EXISTS rag_query TEXT,
ADD COLUMN IF NOT EXISTS rag_source_count INTEGER,
ADD COLUMN IF NOT EXISTS confidence_delta NUMERIC;

