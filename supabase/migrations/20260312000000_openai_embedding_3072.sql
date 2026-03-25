-- Migration: Switch embedding dimensions from 4096 to 3072 (OpenAI text-embedding-3-large)
-- This drops existing embeddings as they are incompatible with the new dimension.

-- 1. Drop HNSW indexes (must drop before altering column type)
DROP INDEX IF EXISTS idx_conversations_embedding;
DROP INDEX IF EXISTS idx_memories_embedding;

-- 2. Clear existing embeddings (different dimensions are incompatible)
UPDATE conversations SET embedding = NULL WHERE embedding IS NOT NULL;
UPDATE memories SET embedding = NULL WHERE embedding IS NOT NULL;

-- 3. Alter column types to vector(3072)
ALTER TABLE conversations ALTER COLUMN embedding TYPE vector(3072);
ALTER TABLE memories ALTER COLUMN embedding TYPE vector(3072);

-- 4. Recreate HNSW indexes
CREATE INDEX IF NOT EXISTS idx_conversations_embedding ON conversations
    USING hnsw (embedding vector_cosine_ops);

CREATE INDEX IF NOT EXISTS idx_memories_embedding ON memories
    USING hnsw (embedding vector_cosine_ops);
