-- MindBase Conversation Enrichment Migration
-- Adds project/topics metadata support and aligns embedding dimensions

-- Drop strict source constraint to allow new collectors
DO $$
BEGIN
    ALTER TABLE conversations DROP CONSTRAINT IF EXISTS valid_source;
EXCEPTION WHEN undefined_object THEN
    NULL;
END
$$;

-- Drop legacy ivfflat index (exceeds dimension limit for 4096)
DROP INDEX IF EXISTS idx_conversations_embedding;

-- Ensure embedding column matches 4096-dimension vectors (qwen3-embedding:8b)
ALTER TABLE conversations
    ALTER COLUMN embedding TYPE vector(4096);

-- Add explicit project/topics columns for filtering
ALTER TABLE conversations
    ADD COLUMN IF NOT EXISTS project TEXT,
    ADD COLUMN IF NOT EXISTS topics TEXT[] DEFAULT '{}';

-- Create helpful indexes (idempotent)
CREATE INDEX IF NOT EXISTS idx_conversations_project
    ON conversations(project);

CREATE INDEX IF NOT EXISTS idx_conversations_topics_gin
    ON conversations USING gin(topics);
