-- MindBase Memory Storage Schema
-- Hybrid storage: Markdown files + PostgreSQL with pgvector for semantic search
-- Inspired by Serena MCP Server's memory system

-- Create memories table
CREATE TABLE IF NOT EXISTS memories (
    name TEXT NOT NULL,
    content TEXT NOT NULL,
    category TEXT CHECK (category IN ('architecture', 'decision', 'pattern', 'guide', 'onboarding', 'note')),
    project TEXT,
    tags TEXT[] DEFAULT '{}',
    embedding vector(1024), -- qwen3-embedding:8b
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,

    -- Composite primary key: name must be unique per project
    PRIMARY KEY (name, COALESCE(project, ''))
);

-- Create indexes for efficient queries
CREATE INDEX IF NOT EXISTS idx_memories_project ON memories(project);
CREATE INDEX IF NOT EXISTS idx_memories_category ON memories(category);
CREATE INDEX IF NOT EXISTS idx_memories_tags ON memories USING GIN(tags);
CREATE INDEX IF NOT EXISTS idx_memories_created_at ON memories(created_at DESC);
CREATE INDEX IF NOT EXISTS idx_memories_updated_at ON memories(updated_at DESC);

-- Create vector index for semantic search (cosine distance)
CREATE INDEX IF NOT EXISTS idx_memories_embedding ON memories USING ivfflat (embedding vector_cosine_ops)
WITH (lists = 100);

-- Create function to update updated_at timestamp
CREATE OR REPLACE FUNCTION update_memories_updated_at()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = CURRENT_TIMESTAMP;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- Create trigger to auto-update updated_at
DROP TRIGGER IF EXISTS trigger_update_memories_updated_at ON memories;
CREATE TRIGGER trigger_update_memories_updated_at
    BEFORE UPDATE ON memories
    FOR EACH ROW
    EXECUTE FUNCTION update_memories_updated_at();

-- Add comment for documentation
COMMENT ON TABLE memories IS 'Hybrid memory storage: Primary storage is markdown files in .mindbase/memories/, this table provides semantic search and metadata';
COMMENT ON COLUMN memories.name IS 'Memory name (becomes filename without .md extension)';
COMMENT ON COLUMN memories.content IS 'Full markdown content including frontmatter';
COMMENT ON COLUMN memories.category IS 'Memory type: architecture, decision, pattern, guide, onboarding, note';
COMMENT ON COLUMN memories.project IS 'Project identifier (null for global memories)';
COMMENT ON COLUMN memories.tags IS 'Free-form tags for categorization';
COMMENT ON COLUMN memories.embedding IS '1024-dimensional vector from qwen3-embedding:8b';
