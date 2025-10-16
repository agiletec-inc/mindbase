-- MindBase: PostgreSQL + pgvector Migration
-- Supabase依存削除、純粋なPostgreSQL実装

-- Enable extensions
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
CREATE EXTENSION IF NOT EXISTS "vector";
CREATE EXTENSION IF NOT EXISTS "pg_trgm";

-- ===================================
-- 1. CONVERSATIONS TABLE
-- ===================================
CREATE TABLE conversations (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),

    -- Source information
    source TEXT NOT NULL CHECK (source IN ('claude-code', 'claude-desktop', 'chatgpt', 'cursor', 'windsurf', 'slack', 'email', 'google-docs')),
    source_conversation_id TEXT,

    -- Content
    title TEXT,
    content JSONB NOT NULL,
    raw_content TEXT,

    -- Metadata
    metadata JSONB DEFAULT '{}',
    participant_count INTEGER DEFAULT 2,
    message_count INTEGER DEFAULT 0,

    -- Vector search (qwen3-embedding:8b = 1024 dimensions)
    embedding VECTOR(1024),

    -- Timestamps
    source_created_at TIMESTAMP WITH TIME ZONE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),

    -- Unique constraint
    UNIQUE(source, source_conversation_id)
);

-- Indexes
CREATE INDEX idx_conversations_source ON conversations(source);
CREATE INDEX idx_conversations_created_at ON conversations(created_at DESC);
CREATE INDEX idx_conversations_source_created_at ON conversations(source_created_at DESC);
CREATE INDEX idx_conversations_embedding ON conversations USING ivfflat (embedding vector_cosine_ops);
CREATE INDEX idx_conversations_content_gin ON conversations USING gin(content);
CREATE INDEX idx_conversations_metadata_gin ON conversations USING gin(metadata);
CREATE INDEX idx_conversations_raw_content_gin ON conversations USING gin(to_tsvector('english', raw_content));

-- ===================================
-- 2. THOUGHT PATTERNS TABLE
-- ===================================
CREATE TABLE thought_patterns (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),

    pattern_type TEXT NOT NULL CHECK (pattern_type IN (
        'business-idea', 'technical-solution', 'creative-concept',
        'problem-analysis', 'architectural-design', 'optimization-strategy',
        'learning-insight', 'decision-framework', 'workflow-improvement'
    )),
    title TEXT NOT NULL,
    description TEXT,
    extracted_content TEXT NOT NULL,

    source_conversations UUID[] DEFAULT '{}',

    confidence_score FLOAT DEFAULT 0.0 CHECK (confidence_score >= 0.0 AND confidence_score <= 1.0),
    keywords TEXT[] DEFAULT '{}',
    themes TEXT[] DEFAULT '{}',

    business_viability_score FLOAT CHECK (business_viability_score >= 0.0 AND business_viability_score <= 1.0),
    technical_feasibility_score FLOAT CHECK (technical_feasibility_score >= 0.0 AND technical_feasibility_score <= 1.0),
    innovation_score FLOAT CHECK (innovation_score >= 0.0 AND innovation_score <= 1.0),

    embedding VECTOR(1024),

    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),

    CONSTRAINT thought_patterns_conversations_exist
        CHECK (array_length(source_conversations, 1) > 0)
);

-- Indexes
CREATE INDEX idx_thought_patterns_type ON thought_patterns(pattern_type);
CREATE INDEX idx_thought_patterns_confidence ON thought_patterns(confidence_score DESC);
CREATE INDEX idx_thought_patterns_embedding ON thought_patterns USING ivfflat (embedding vector_cosine_ops);
CREATE INDEX idx_thought_patterns_keywords_gin ON thought_patterns USING gin(keywords);
CREATE INDEX idx_thought_patterns_content_gin ON thought_patterns USING gin(to_tsvector('english', extracted_content));

-- ===================================
-- 3. VECTOR SEARCH FUNCTIONS
-- ===================================

-- Search similar conversations
CREATE OR REPLACE FUNCTION search_similar_conversations(
    query_embedding VECTOR(1024),
    similarity_threshold FLOAT DEFAULT 0.8,
    max_results INTEGER DEFAULT 10
)
RETURNS TABLE (
    conversation_id UUID,
    title TEXT,
    source TEXT,
    similarity FLOAT,
    created_at TIMESTAMP WITH TIME ZONE
) AS $$
BEGIN
    RETURN QUERY
    SELECT
        c.id,
        c.title,
        c.source,
        (1 - (c.embedding <=> query_embedding)) AS similarity,
        c.created_at
    FROM conversations c
    WHERE c.embedding IS NOT NULL
        AND (1 - (c.embedding <=> query_embedding)) >= similarity_threshold
    ORDER BY c.embedding <=> query_embedding
    LIMIT max_results;
END;
$$ LANGUAGE plpgsql;

-- Search similar patterns
CREATE OR REPLACE FUNCTION search_similar_patterns(
    query_embedding VECTOR(1024),
    pattern_type_filter TEXT DEFAULT NULL,
    similarity_threshold FLOAT DEFAULT 0.8,
    max_results INTEGER DEFAULT 10
)
RETURNS TABLE (
    pattern_id UUID,
    title TEXT,
    pattern_type TEXT,
    similarity FLOAT,
    confidence_score FLOAT
) AS $$
BEGIN
    RETURN QUERY
    SELECT
        tp.id,
        tp.title,
        tp.pattern_type,
        (1 - (tp.embedding <=> query_embedding)) AS similarity,
        tp.confidence_score
    FROM thought_patterns tp
    WHERE tp.embedding IS NOT NULL
        AND (1 - (tp.embedding <=> query_embedding)) >= similarity_threshold
        AND (pattern_type_filter IS NULL OR tp.pattern_type = pattern_type_filter)
    ORDER BY tp.embedding <=> query_embedding
    LIMIT max_results;
END;
$$ LANGUAGE plpgsql;

-- ===================================
-- 4. AUTO-UPDATE TRIGGERS
-- ===================================

-- Update conversation metrics
CREATE OR REPLACE FUNCTION update_conversation_metrics()
RETURNS TRIGGER AS $$
BEGIN
    -- Update message count
    IF NEW.content ? 'messages' AND jsonb_typeof(NEW.content->'messages') = 'array' THEN
        NEW.message_count = jsonb_array_length(NEW.content->'messages');
    END IF;

    -- Extract raw content for full-text search
    IF NEW.content ? 'messages' THEN
        NEW.raw_content = (
            SELECT string_agg(msg->>'content', ' ')
            FROM jsonb_array_elements(NEW.content->'messages') msg
            WHERE msg ? 'content'
        );
    END IF;

    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER trigger_update_conversation_metrics
    BEFORE INSERT OR UPDATE OF content ON conversations
    FOR EACH ROW
    EXECUTE FUNCTION update_conversation_metrics();

-- ===================================
-- COMMENTS
-- ===================================

COMMENT ON TABLE conversations IS 'AI conversations from various sources (Claude, ChatGPT, Cursor, etc.)';
COMMENT ON TABLE thought_patterns IS 'Extracted thought patterns from conversations';
COMMENT ON COLUMN conversations.embedding IS 'qwen3-embedding:8b (1024 dimensions) for semantic search';
COMMENT ON COLUMN conversations.content IS 'Full conversation in JSONB format';
