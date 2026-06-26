-- Add summary column for AI-generated Japanese session summaries.
-- Populated by the deriver pipeline; NULL for records ingested before this migration.
ALTER TABLE conversations ADD COLUMN IF NOT EXISTS summary TEXT;
