-- Mind-Base: AI Conversation Knowledge Management System
-- Initial schema for conversations, thought patterns, and book structure

-- Enable necessary extensions
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
CREATE EXTENSION IF NOT EXISTS "vector";
CREATE EXTENSION IF NOT EXISTS "pg_trgm";

-- ===================================
-- 1. CONVERSATIONS TABLE
-- ===================================
-- Stores all AI conversations from various sources
CREATE TABLE conversations (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    
    -- Source information
    source TEXT NOT NULL CHECK (source IN ('claude-desktop', 'chatgpt', 'cursor', 'windsurf', 'claude-code')),
    source_conversation_id TEXT, -- Original conversation ID from source
    
    -- Content
    title TEXT,
    content JSONB NOT NULL, -- Full conversation content (messages array)
    raw_content TEXT, -- Raw text content for full-text search
    
    -- Metadata
    metadata JSONB DEFAULT '{}', -- Custom metadata (project, tags, etc.)
    participant_count INTEGER DEFAULT 2, -- Number of participants
    message_count INTEGER DEFAULT 0, -- Number of messages in conversation
    
    -- Vector search
    embedding VECTOR(1536), -- OpenAI ada-002 embeddings (1536 dimensions)
    
    -- Timestamps
    source_created_at TIMESTAMP WITH TIME ZONE, -- Original creation time
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    
    -- Search indexes
    UNIQUE(source, source_conversation_id) -- Prevent duplicates
);

-- Create indexes for performance
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
-- Extracted patterns from conversations
CREATE TABLE thought_patterns (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    
    -- Pattern information
    pattern_type TEXT NOT NULL CHECK (pattern_type IN (
        'business-idea', 'technical-solution', 'creative-concept', 
        'problem-analysis', 'architectural-design', 'optimization-strategy',
        'learning-insight', 'decision-framework', 'workflow-improvement'
    )),
    title TEXT NOT NULL,
    description TEXT,
    extracted_content TEXT NOT NULL, -- The actual thought pattern content
    
    -- Relationships
    source_conversations UUID[] DEFAULT '{}', -- Array of conversation IDs
    
    -- Analysis metadata
    confidence_score FLOAT DEFAULT 0.0 CHECK (confidence_score >= 0.0 AND confidence_score <= 1.0),
    keywords TEXT[] DEFAULT '{}', -- Extracted keywords
    themes TEXT[] DEFAULT '{}', -- High-level themes
    
    -- Categorization
    business_viability_score FLOAT CHECK (business_viability_score >= 0.0 AND business_viability_score <= 1.0),
    technical_feasibility_score FLOAT CHECK (technical_feasibility_score >= 0.0 AND technical_feasibility_score <= 1.0),
    innovation_score FLOAT CHECK (innovation_score >= 0.0 AND innovation_score <= 1.0),
    
    -- Vector search
    embedding VECTOR(1536),
    
    -- Timestamps
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    
    -- Constraints
    CONSTRAINT thought_patterns_conversations_exist 
        CHECK (array_length(source_conversations, 1) > 0)
);

-- Create indexes
CREATE INDEX idx_thought_patterns_type ON thought_patterns(pattern_type);
CREATE INDEX idx_thought_patterns_confidence ON thought_patterns(confidence_score DESC);
CREATE INDEX idx_thought_patterns_business_score ON thought_patterns(business_viability_score DESC);
CREATE INDEX idx_thought_patterns_technical_score ON thought_patterns(technical_feasibility_score DESC);
CREATE INDEX idx_thought_patterns_innovation_score ON thought_patterns(innovation_score DESC);
CREATE INDEX idx_thought_patterns_embedding ON thought_patterns USING ivfflat (embedding vector_cosine_ops);
CREATE INDEX idx_thought_patterns_keywords_gin ON thought_patterns USING gin(keywords);
CREATE INDEX idx_thought_patterns_themes_gin ON thought_patterns USING gin(themes);
CREATE INDEX idx_thought_patterns_content_gin ON thought_patterns USING gin(to_tsvector('english', extracted_content));

-- ===================================
-- 3. BOOK STRUCTURE TABLE
-- ===================================
-- Hierarchical book/document structure
CREATE TABLE book_structure (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    
    -- Hierarchy
    parent_id UUID REFERENCES book_structure(id) ON DELETE CASCADE,
    order_index INTEGER NOT NULL DEFAULT 0,
    level INTEGER NOT NULL DEFAULT 1 CHECK (level >= 1 AND level <= 10), -- 1=book, 2=part, 3=chapter, 4=section, etc.
    
    -- Content
    title TEXT NOT NULL,
    content TEXT DEFAULT '',
    content_type TEXT DEFAULT 'markdown' CHECK (content_type IN ('markdown', 'html', 'text')),
    
    -- Relationships to patterns
    source_patterns UUID[] DEFAULT '{}', -- Array of thought pattern IDs
    
    -- Metadata
    word_count INTEGER DEFAULT 0,
    target_word_count INTEGER,
    completion_percentage FLOAT DEFAULT 0.0 CHECK (completion_percentage >= 0.0 AND completion_percentage <= 100.0),
    
    -- Status
    status TEXT DEFAULT 'draft' CHECK (status IN ('draft', 'in_progress', 'review', 'final', 'published')),
    
    -- Book metadata (for root level items)
    book_metadata JSONB DEFAULT '{}', -- Genre, target audience, publication info, etc.
    
    -- Timestamps
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    
    -- Constraints
    CONSTRAINT book_structure_hierarchy_check 
        CHECK ((parent_id IS NULL AND level = 1) OR (parent_id IS NOT NULL AND level > 1))
);

-- Create indexes
CREATE INDEX idx_book_structure_parent ON book_structure(parent_id);
CREATE INDEX idx_book_structure_level ON book_structure(level);
CREATE INDEX idx_book_structure_order ON book_structure(parent_id, order_index);
CREATE INDEX idx_book_structure_status ON book_structure(status);
CREATE INDEX idx_book_structure_completion ON book_structure(completion_percentage DESC);
CREATE INDEX idx_book_structure_patterns_gin ON book_structure USING gin(source_patterns);
CREATE INDEX idx_book_structure_content_gin ON book_structure USING gin(to_tsvector('english', content));

-- ===================================
-- 4. CONVERSATION ANALYSIS JOBS
-- ===================================
-- Track background analysis jobs
CREATE TABLE conversation_analysis_jobs (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    conversation_id UUID NOT NULL REFERENCES conversations(id) ON DELETE CASCADE,
    
    -- Job details
    job_type TEXT NOT NULL CHECK (job_type IN ('embedding', 'pattern_extraction', 'classification', 'full_analysis')),
    status TEXT DEFAULT 'pending' CHECK (status IN ('pending', 'processing', 'completed', 'failed')),
    
    -- Results
    result JSONB DEFAULT '{}',
    error_message TEXT,
    
    -- Progress tracking
    progress_percentage FLOAT DEFAULT 0.0 CHECK (progress_percentage >= 0.0 AND progress_percentage <= 100.0),
    
    -- Timestamps
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    started_at TIMESTAMP WITH TIME ZONE,
    completed_at TIMESTAMP WITH TIME ZONE,
    
    -- Constraints
    UNIQUE(conversation_id, job_type) -- One job per type per conversation
);

-- Create indexes
CREATE INDEX idx_analysis_jobs_conversation ON conversation_analysis_jobs(conversation_id);
CREATE INDEX idx_analysis_jobs_status ON conversation_analysis_jobs(status);
CREATE INDEX idx_analysis_jobs_type ON conversation_analysis_jobs(job_type);
CREATE INDEX idx_analysis_jobs_created ON conversation_analysis_jobs(created_at DESC);

-- ===================================
-- 5. VECTOR SEARCH FUNCTIONS
-- ===================================

-- Function to search similar conversations
CREATE OR REPLACE FUNCTION search_similar_conversations(
    query_embedding VECTOR(1536),
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

-- Function to search similar thought patterns
CREATE OR REPLACE FUNCTION search_similar_patterns(
    query_embedding VECTOR(1536),
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
-- 6. AUTO-UPDATE TRIGGERS
-- ===================================

-- Function to update word count and completion percentage
CREATE OR REPLACE FUNCTION update_book_metrics()
RETURNS TRIGGER AS $$
BEGIN
    -- Update word count
    NEW.word_count = array_length(string_to_array(NEW.content, ' '), 1);
    
    -- Update completion percentage based on word count vs target
    IF NEW.target_word_count IS NOT NULL AND NEW.target_word_count > 0 THEN
        NEW.completion_percentage = LEAST(100.0, (NEW.word_count::FLOAT / NEW.target_word_count::FLOAT) * 100.0);
    END IF;
    
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- Apply trigger to book_structure
CREATE TRIGGER trigger_update_book_metrics
    BEFORE UPDATE OF content, target_word_count ON book_structure
    FOR EACH ROW
    EXECUTE FUNCTION update_book_metrics();

-- Function to update message count in conversations
CREATE OR REPLACE FUNCTION update_conversation_metrics()
RETURNS TRIGGER AS $$
BEGIN
    -- Update message count from JSONB content
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

-- Apply trigger to conversations
CREATE TRIGGER trigger_update_conversation_metrics
    BEFORE INSERT OR UPDATE OF content ON conversations
    FOR EACH ROW
    EXECUTE FUNCTION update_conversation_metrics();

-- ===================================
-- 7. ROW LEVEL SECURITY (RLS)
-- ===================================

-- Enable RLS on all tables
ALTER TABLE conversations ENABLE ROW LEVEL SECURITY;
ALTER TABLE thought_patterns ENABLE ROW LEVEL SECURITY;
ALTER TABLE book_structure ENABLE ROW LEVEL SECURITY;
ALTER TABLE conversation_analysis_jobs ENABLE ROW LEVEL SECURITY;

-- Allow all operations for authenticated users (single user system for now)
CREATE POLICY "Allow all for authenticated users" ON conversations
    FOR ALL USING (auth.role() = 'authenticated' OR auth.role() = 'service_role');

CREATE POLICY "Allow all for authenticated users" ON thought_patterns
    FOR ALL USING (auth.role() = 'authenticated' OR auth.role() = 'service_role');

CREATE POLICY "Allow all for authenticated users" ON book_structure
    FOR ALL USING (auth.role() = 'authenticated' OR auth.role() = 'service_role');

CREATE POLICY "Allow all for authenticated users" ON conversation_analysis_jobs
    FOR ALL USING (auth.role() = 'authenticated' OR auth.role() = 'service_role');

-- ===================================
-- 8. INITIAL DATA
-- ===================================

-- Create a root book structure for the main book
INSERT INTO book_structure (title, level, content, book_metadata, target_word_count)
VALUES (
    'Mind Patterns: AI-Assisted Knowledge Management and Creative Synthesis',
    1,
    '# Mind Patterns: AI-Assisted Knowledge Management and Creative Synthesis

This book explores the intersection of AI conversation analysis and knowledge management, documenting the patterns that emerge from human-AI collaboration.

## Overview

This work is generated through analysis of thousands of AI conversations, extracting recurring thought patterns, creative insights, and problem-solving approaches.
',
    '{
        "genre": "Technology/AI",
        "target_audience": "AI researchers, knowledge workers, creative professionals",
        "publication_status": "draft",
        "author": "AI-Human Collaborative Analysis",
        "keywords": ["AI", "knowledge management", "thought patterns", "creativity", "human-AI collaboration"]
    }'::jsonb,
    50000
);

-- Create initial chapters structure
INSERT INTO book_structure (parent_id, title, level, order_index, target_word_count, content)
SELECT 
    (SELECT id FROM book_structure WHERE level = 1 LIMIT 1),
    chapter_title,
    2,
    chapter_order,
    chapter_word_count,
    chapter_content
FROM (VALUES
    (1, 'Introduction: The Age of AI-Human Thought Partnership', 3000, '# Introduction: The Age of AI-Human Thought Partnership

## The Evolution of Human-AI Collaboration
## Methodology: Mining Conversations for Patterns
## Structure of This Work'),
    
    (2, 'Technical Patterns: Architecture and Problem-Solving', 8000, '# Technical Patterns: Architecture and Problem-Solving

## Recurring Technical Solutions
## Architectural Thinking Patterns
## Problem Decomposition Strategies'),
    
    (3, 'Creative Patterns: Innovation and Ideation', 8000, '# Creative Patterns: Innovation and Ideation

## Business Idea Generation Patterns
## Creative Problem-Solving Approaches
## Innovation Framework Emergence'),
    
    (4, 'Learning Patterns: Knowledge Acquisition and Synthesis', 8000, '# Learning Patterns: Knowledge Acquisition and Synthesis

## Information Processing Strategies
## Knowledge Connection Patterns
## Synthesis and Integration Methods'),
    
    (5, 'Decision Patterns: Frameworks and Heuristics', 8000, '# Decision Patterns: Frameworks and Heuristics

## Decision-Making Frameworks
## Risk Assessment Patterns
## Trade-off Analysis Methods'),
    
    (6, 'Meta-Patterns: Thinking About Thinking', 8000, '# Meta-Patterns: Thinking About Thinking

## Metacognitive Strategies
## Self-Reflection Patterns
## Continuous Improvement Frameworks'),
    
    (7, 'Future Directions: Scaling Human-AI Collaboration', 5000, '# Future Directions: Scaling Human-AI Collaboration

## Emerging Patterns
## Scaling Considerations
## Future Research Directions'),
    
    (8, 'Conclusion: Toward Augmented Intelligence', 2000, '# Conclusion: Toward Augmented Intelligence

## Key Insights
## Practical Applications
## Final Thoughts')
) AS chapters(chapter_order, chapter_title, chapter_word_count, chapter_content);

-- ===================================
-- COMMENTS AND DOCUMENTATION
-- ===================================

COMMENT ON TABLE conversations IS 'Stores AI conversations from various sources (Claude Desktop, ChatGPT, Cursor, etc.)';
COMMENT ON TABLE thought_patterns IS 'Extracted and analyzed thought patterns from conversations';
COMMENT ON TABLE book_structure IS 'Hierarchical structure for organizing content into books, chapters, sections';
COMMENT ON TABLE conversation_analysis_jobs IS 'Background job tracking for conversation analysis tasks';

COMMENT ON COLUMN conversations.embedding IS 'OpenAI ada-002 embedding (1536 dimensions) for semantic search';
COMMENT ON COLUMN conversations.content IS 'Full conversation in structured JSONB format';
COMMENT ON COLUMN conversations.raw_content IS 'Plain text content for full-text search';

COMMENT ON COLUMN thought_patterns.confidence_score IS 'AI confidence in pattern extraction (0.0-1.0)';
COMMENT ON COLUMN thought_patterns.business_viability_score IS 'Assessed business viability (0.0-1.0)';
COMMENT ON COLUMN thought_patterns.technical_feasibility_score IS 'Assessed technical feasibility (0.0-1.0)';

COMMENT ON COLUMN book_structure.level IS 'Hierarchy level: 1=book, 2=part, 3=chapter, 4=section, etc.';
COMMENT ON COLUMN book_structure.completion_percentage IS 'Content completion based on word count vs target';

-- Create a view for book outline
CREATE VIEW book_outline AS
SELECT 
    bs.id,
    bs.parent_id,
    bs.level,
    bs.order_index,
    bs.title,
    bs.word_count,
    bs.target_word_count,
    bs.completion_percentage,
    bs.status,
    ARRAY_LENGTH(bs.source_patterns, 1) as pattern_count
FROM book_structure bs
ORDER BY bs.level, bs.order_index;