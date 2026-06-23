-- Allow the in-app chat ("mindbase-chat") as a conversation source so chat turns
-- streamed by POST /api/chat can be persisted as memory. Replaces the existing
-- inline source CHECK constraint (auto-named conversations_source_check).
ALTER TABLE conversations DROP CONSTRAINT IF EXISTS conversations_source_check;
ALTER TABLE conversations ADD CONSTRAINT conversations_source_check
    CHECK (source IN (
        'claude-code', 'claude-desktop', 'chatgpt', 'cursor', 'windsurf',
        'slack', 'email', 'google-docs', 'mindbase-chat'
    ));
