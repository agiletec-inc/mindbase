-- MindBase Raw Conversation Storage
-- Separates raw ingestion from derived conversation records

CREATE TABLE IF NOT EXISTS raw_conversations (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    source TEXT NOT NULL,
    source_conversation_id TEXT,
    workspace_path TEXT,
    payload JSONB NOT NULL,
    metadata JSONB NOT NULL DEFAULT '{}'::jsonb,
    captured_at TIMESTAMPTZ,
    inserted_at TIMESTAMPTZ NOT NULL DEFAULT timezone('utc', now())
);

CREATE INDEX IF NOT EXISTS idx_raw_conversations_source
    ON raw_conversations (source);

CREATE INDEX IF NOT EXISTS idx_raw_conversations_workspace
    ON raw_conversations (workspace_path);

ALTER TABLE conversations
    ADD COLUMN IF NOT EXISTS raw_id UUID,
    ADD COLUMN IF NOT EXISTS workspace_path TEXT;

ALTER TABLE conversations
    ADD CONSTRAINT IF NOT EXISTS fk_conversations_raw
        FOREIGN KEY (raw_id) REFERENCES raw_conversations(id) ON DELETE SET NULL;

CREATE INDEX IF NOT EXISTS idx_conversations_workspace_path
    ON conversations(workspace_path);
