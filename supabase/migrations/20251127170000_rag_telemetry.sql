-- Add RAG telemetry to task_telemetry
ALTER TABLE task_telemetry
ADD COLUMN rag_enabled BOOLEAN DEFAULT FALSE,
ADD COLUMN rag_query TEXT,
ADD COLUMN rag_source_count INTEGER;

-- Add RAG telemetry to conversation_feedback
ALTER TABLE conversation_feedback
ADD COLUMN rag_enabled BOOLEAN DEFAULT FALSE,
ADD COLUMN rag_query TEXT,
ADD COLUMN rag_source_count INTEGER,
ADD COLUMN confidence_delta NUMERIC;

