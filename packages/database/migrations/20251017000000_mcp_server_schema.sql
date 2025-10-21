-- MindBase MCP Server Schema Extensions
-- Migration: Add sessions table and conversation enhancements for MCP server

-- Create sessions table for conversation organization
CREATE TABLE IF NOT EXISTS sessions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name TEXT NOT NULL,
    description TEXT,
    parent_id UUID REFERENCES sessions(id) ON DELETE SET NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW() NOT NULL,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW() NOT NULL
);

-- Create indexes for sessions
CREATE INDEX IF NOT EXISTS idx_sessions_created_at ON sessions(created_at DESC);
CREATE INDEX IF NOT EXISTS idx_sessions_updated_at ON sessions(updated_at DESC);
CREATE INDEX IF NOT EXISTS idx_sessions_parent_id ON sessions(parent_id);

-- Add session and categorization columns to conversations table
ALTER TABLE conversations
ADD COLUMN IF NOT EXISTS session_id UUID REFERENCES sessions(id) ON DELETE SET NULL,
ADD COLUMN IF NOT EXISTS category TEXT CHECK (category IN ('task', 'decision', 'progress', 'note', 'warning', 'error')),
ADD COLUMN IF NOT EXISTS priority TEXT CHECK (priority IN ('critical', 'high', 'normal', 'low')),
ADD COLUMN IF NOT EXISTS channel TEXT;

-- Create indexes for new conversation columns
CREATE INDEX IF NOT EXISTS idx_conversations_session_id ON conversations(session_id);
CREATE INDEX IF NOT EXISTS idx_conversations_category ON conversations(category);
CREATE INDEX IF NOT EXISTS idx_conversations_priority ON conversations(priority);
CREATE INDEX IF NOT EXISTS idx_conversations_channel ON conversations(channel);

-- Create composite index for common queries
CREATE INDEX IF NOT EXISTS idx_conversations_source_category ON conversations(source, category);
CREATE INDEX IF NOT EXISTS idx_conversations_session_created ON conversations(session_id, created_at DESC);

-- Update function for sessions.updated_at
CREATE OR REPLACE FUNCTION update_sessions_updated_at()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- Create trigger for sessions.updated_at
DROP TRIGGER IF EXISTS trigger_update_sessions_updated_at ON sessions;
CREATE TRIGGER trigger_update_sessions_updated_at
    BEFORE UPDATE ON sessions
    FOR EACH ROW
    EXECUTE FUNCTION update_sessions_updated_at();

-- Comments for documentation
COMMENT ON TABLE sessions IS 'Sessions for organizing conversations in MindBase MCP Server';
COMMENT ON COLUMN conversations.session_id IS 'Session ID for conversation organization';
COMMENT ON COLUMN conversations.category IS 'Conversation category: task, decision, progress, note, warning, error';
COMMENT ON COLUMN conversations.priority IS 'Conversation priority: critical, high, normal, low';
COMMENT ON COLUMN conversations.channel IS 'Channel or workspace identifier';
