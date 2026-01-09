/**
 * MindBase MCP Server - Database Schema Initialization
 *
 * Auto-initializes PostgreSQL schema on first run.
 * Ensures standalone Docker deployment works without manual migration.
 */

import { Pool } from 'pg';

/**
 * Get embedding dimensions from environment or detect from model name
 */
function getEmbeddingDimensions(): number {
  // Check explicit env var first
  const envDimensions = process.env.EMBEDDING_DIMENSIONS;
  if (envDimensions) {
    return parseInt(envDimensions, 10);
  }

  // Detect from model name
  const model = process.env.EMBEDDING_MODEL || '';
  if (model.includes('nomic-embed-text')) {
    return 768;
  }
  if (model.includes('qwen3-embedding') || model.includes('qwen3')) {
    return 1024;
  }
  if (model.includes('text-embedding-ada') || model.includes('ada-002')) {
    return 1536;
  }
  if (model.includes('text-embedding-3-small')) {
    return 1536;
  }
  if (model.includes('text-embedding-3-large')) {
    return 3072;
  }

  // Default to 768 (nomic-embed-text) as it's most commonly used
  return 768;
}

/**
 * Generate schema SQL with proper embedding dimensions
 */
function generateSchemaSQL(dimensions: number): string {
  return `
-- MindBase MCP Server Auto-Migration Schema
-- This schema is auto-applied when tables don't exist

-- Enable required extensions
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
CREATE EXTENSION IF NOT EXISTS "vector";

-- ===================================
-- 1. CONVERSATIONS TABLE
-- ===================================
CREATE TABLE IF NOT EXISTS conversations (
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

    -- MCP Server extensions (session, categorization)
    session_id UUID,
    category TEXT CHECK (category IS NULL OR category IN ('task', 'decision', 'progress', 'note', 'warning', 'error')),
    priority TEXT CHECK (priority IS NULL OR priority IN ('critical', 'high', 'normal', 'low')),
    channel TEXT,

    -- Vector search
    embedding VECTOR(${dimensions}),

    -- Timestamps
    source_created_at TIMESTAMP WITH TIME ZONE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),

    -- Unique constraint
    UNIQUE(source, source_conversation_id)
);

-- Conversations indexes
CREATE INDEX IF NOT EXISTS idx_conversations_source ON conversations(source);
CREATE INDEX IF NOT EXISTS idx_conversations_created_at ON conversations(created_at DESC);
CREATE INDEX IF NOT EXISTS idx_conversations_session_id ON conversations(session_id);
CREATE INDEX IF NOT EXISTS idx_conversations_category ON conversations(category);
CREATE INDEX IF NOT EXISTS idx_conversations_priority ON conversations(priority);
CREATE INDEX IF NOT EXISTS idx_conversations_channel ON conversations(channel);

-- Vector index (HNSW for better performance)
CREATE INDEX IF NOT EXISTS idx_conversations_embedding ON conversations
    USING hnsw (embedding vector_cosine_ops);

-- ===================================
-- 2. SESSIONS TABLE
-- ===================================
CREATE TABLE IF NOT EXISTS sessions (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    name TEXT NOT NULL,
    description TEXT,
    parent_id UUID REFERENCES sessions(id) ON DELETE SET NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW() NOT NULL,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW() NOT NULL
);

-- Sessions indexes
CREATE INDEX IF NOT EXISTS idx_sessions_created_at ON sessions(created_at DESC);
CREATE INDEX IF NOT EXISTS idx_sessions_updated_at ON sessions(updated_at DESC);
CREATE INDEX IF NOT EXISTS idx_sessions_parent_id ON sessions(parent_id);

-- Add foreign key to conversations if not exists
DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.table_constraints
        WHERE constraint_name = 'conversations_session_id_fkey'
        AND table_name = 'conversations'
    ) THEN
        ALTER TABLE conversations
        ADD CONSTRAINT conversations_session_id_fkey
        FOREIGN KEY (session_id) REFERENCES sessions(id) ON DELETE SET NULL;
    END IF;
END $$;

-- ===================================
-- 3. MEMORIES TABLE (Serena-inspired)
-- ===================================
CREATE TABLE IF NOT EXISTS memories (
    name TEXT NOT NULL,
    content TEXT NOT NULL,
    category TEXT CHECK (category IS NULL OR category IN ('architecture', 'decision', 'pattern', 'guide', 'onboarding', 'note')),
    project TEXT,
    tags TEXT[] DEFAULT '{}',
    embedding VECTOR(${dimensions}),
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,

    -- Unique constraint: name must be unique per project (null project = global)
    UNIQUE (name, project)
);

-- Memories indexes
CREATE INDEX IF NOT EXISTS idx_memories_project ON memories(project);
CREATE INDEX IF NOT EXISTS idx_memories_category ON memories(category);
CREATE INDEX IF NOT EXISTS idx_memories_tags ON memories USING GIN(tags);
CREATE INDEX IF NOT EXISTS idx_memories_created_at ON memories(created_at DESC);
CREATE INDEX IF NOT EXISTS idx_memories_updated_at ON memories(updated_at DESC);

-- Vector index for memories
CREATE INDEX IF NOT EXISTS idx_memories_embedding ON memories
    USING hnsw (embedding vector_cosine_ops);

-- ===================================
-- 4. UPDATE TRIGGERS
-- ===================================

-- Sessions updated_at trigger
CREATE OR REPLACE FUNCTION update_sessions_updated_at()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

DROP TRIGGER IF EXISTS trigger_update_sessions_updated_at ON sessions;
CREATE TRIGGER trigger_update_sessions_updated_at
    BEFORE UPDATE ON sessions
    FOR EACH ROW
    EXECUTE FUNCTION update_sessions_updated_at();

-- Memories updated_at trigger
CREATE OR REPLACE FUNCTION update_memories_updated_at()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = CURRENT_TIMESTAMP;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

DROP TRIGGER IF EXISTS trigger_update_memories_updated_at ON memories;
CREATE TRIGGER trigger_update_memories_updated_at
    BEFORE UPDATE ON memories
    FOR EACH ROW
    EXECUTE FUNCTION update_memories_updated_at();

-- ===================================
-- 5. COMMENTS
-- ===================================
COMMENT ON TABLE conversations IS 'AI conversations from various sources (Claude, ChatGPT, Cursor, etc.)';
COMMENT ON TABLE sessions IS 'Sessions for organizing conversations in MindBase MCP Server';
COMMENT ON TABLE memories IS 'Hybrid memory storage: markdown files + PostgreSQL semantic search';
`;
}

/**
 * Check if database schema is initialized
 */
export async function isSchemaInitialized(pool: Pool): Promise<boolean> {
  try {
    const result = await pool.query(`
      SELECT EXISTS (
        SELECT FROM information_schema.tables
        WHERE table_schema = 'public' AND table_name = 'sessions'
      ) AS sessions_exists,
      EXISTS (
        SELECT FROM information_schema.tables
        WHERE table_schema = 'public' AND table_name = 'conversations'
      ) AS conversations_exists,
      EXISTS (
        SELECT FROM information_schema.tables
        WHERE table_schema = 'public' AND table_name = 'memories'
      ) AS memories_exists
    `);

    const { sessions_exists, conversations_exists, memories_exists } = result.rows[0];
    return sessions_exists && conversations_exists && memories_exists;
  } catch (error) {
    // If we can't query information_schema, assume not initialized
    return false;
  }
}

/**
 * Initialize database schema if not already done
 */
export async function ensureSchema(pool: Pool): Promise<void> {
  const initialized = await isSchemaInitialized(pool);

  if (initialized) {
    console.error('[MindBase MCP] Database schema already initialized');
    return;
  }

  console.error('[MindBase MCP] Initializing database schema...');

  const dimensions = getEmbeddingDimensions();
  console.error(`[MindBase MCP] Using ${dimensions}-dimensional embeddings`);

  const schemaSQL = generateSchemaSQL(dimensions);

  try {
    await pool.query(schemaSQL);
    console.error('[MindBase MCP] Database schema initialized successfully');
  } catch (error) {
    // Check if it's a "relation already exists" error (race condition)
    const errorMessage = error instanceof Error ? error.message : String(error);
    if (errorMessage.includes('already exists')) {
      console.error('[MindBase MCP] Schema already exists (concurrent initialization)');
      return;
    }
    throw error;
  }
}
