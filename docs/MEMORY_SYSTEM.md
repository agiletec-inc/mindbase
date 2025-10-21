# MindBase Memory System

**Date**: 2025-10-19
**Status**: ✅ Implemented (Phase 1)
**Inspiration**: Serena MCP Server

## Overview

MindBase now features a **hybrid memory storage system** that combines the best of Serena's approach (human-readable markdown files) with MindBase's strengths (PostgreSQL + pgvector semantic search).

## Architecture

### Hybrid Storage Strategy

```
┌─────────────────────────────────────────────────────────────┐
│                    Memory Write Operation                    │
└─────────────────────────────────────────────────────────────┘
                             │
                    ┌────────┴────────┐
                    ▼                 ▼
          ┌──────────────┐   ┌──────────────┐
          │   Markdown   │   │  PostgreSQL  │
          │     File     │   │  + pgvector  │
          └──────────────┘   └──────────────┘
          Primary Storage    Secondary Storage
          (Human-readable)   (Semantic search)
```

**Storage Locations**:
- **Markdown**: `~/Library/Application Support/mindbase/memories/`
- **Database**: `memories` table in PostgreSQL

### File Format

Markdown files with YAML frontmatter:

```markdown
---
category: decision
project: mindbase
tags: [architecture, mcp, serena]
createdAt: 2025-10-19T10:00:00Z
updatedAt: 2025-10-19T10:00:00Z
---

# Memory Title

Markdown content with full formatting support.

## Sections

- Code blocks
- Lists
- Links
- Everything markdown supports
```

## MCP Tools

### memory_write

**Purpose**: Save a memory to both markdown file and database.

**Parameters**:
- `name` (required): Memory name (becomes filename)
- `content` (required): Markdown content
- `category` (optional): architecture | decision | pattern | guide | onboarding | note
- `project` (optional): Project identifier for scoping
- `tags` (optional): Array of tags for categorization

**Returns**:
```json
{
  "path": "/Users/kazuki/Library/Application Support/mindbase/memories/mindbase/architecture_decisions.md",
  "name": "architecture_decisions"
}
```

### memory_read

**Purpose**: Read a memory by name.

**Parameters**:
- `name` (required): Memory name to read
- `project` (optional): Project identifier

**Returns**: Full memory object with content and metadata.

### memory_list

**Purpose**: List all memories with optional filtering.

**Parameters**:
- `project` (optional): Filter by project
- `category` (optional): Filter by category
- `tags` (optional): Filter by tags (any match)

**Returns**:
```json
{
  "memories": [
    {
      "name": "architecture_decisions",
      "category": "decision",
      "project": "mindbase",
      "tags": ["architecture", "mcp"],
      "size": 1234,
      "createdAt": "2025-10-19T10:00:00Z",
      "updatedAt": "2025-10-19T10:00:00Z"
    }
  ],
  "total": 1
}
```

### memory_delete

**Purpose**: Delete memory from both markdown and database.

**Parameters**:
- `name` (required): Memory name to delete
- `project` (optional): Project identifier

**Returns**:
```json
{
  "success": true,
  "name": "architecture_decisions"
}
```

### memory_search

**Purpose**: Semantic search across all memories using pgvector.

**Parameters**:
- `query` (required): Search query
- `limit` (optional): Maximum results (default: 10)
- `threshold` (optional): Similarity threshold 0-1 (default: 0.7)
- `project` (optional): Filter by project
- `category` (optional): Filter by category

**Returns**:
```json
{
  "results": [
    {
      "name": "architecture_decisions",
      "content": "# Architecture Decisions\n\n...",
      "category": "decision",
      "similarity": 0.89,
      "path": "/path/to/file.md"
    }
  ],
  "query": "How should MCP tools be organized?",
  "total": 1
}
```

## Usage Examples

### Basic Memory Operations

```typescript
// 1. Write a memory
await memory_write({
  name: "mcp_architecture",
  content: `# MCP Architecture

## Separation of Concerns

- Storage backend handles data persistence
- Tools layer provides MCP interface
- Server orchestrates tool execution
`,
  category: "architecture",
  project: "mindbase",
  tags: ["mcp", "architecture"]
});

// 2. Read it back
const memory = await memory_read({
  name: "mcp_architecture",
  project: "mindbase"
});

// 3. List all architecture memories
const { memories } = await memory_list({
  project: "mindbase",
  category: "architecture"
});

// 4. Search semantically
const { results } = await memory_search({
  query: "How is MCP organized?",
  project: "mindbase",
  threshold: 0.7
});
```

### Cross-Session Continuation

```typescript
// Session 1: Work on feature
await memory_write({
  name: "session_context",
  content: `# Session Context: MCP Memory Implementation

## Progress
- ✅ Designed hybrid storage
- ✅ Implemented markdown backend
- ⏳ Testing in progress

## Next Steps
1. Test hybrid storage
2. Add auto-onboarding
3. Implement thinking tools
`,
  category: "progress",
  project: "mindbase"
});

// Session 2: Resume work
const context = await memory_read({
  name: "session_context",
  project: "mindbase"
});
// Now you know exactly where you left off!
```

### Project Onboarding

```typescript
// Store project knowledge
await memory_write({
  name: "onboarding",
  content: `# MindBase Project Onboarding

## Technology Stack
- FastAPI (Python backend)
- TypeScript (MCP server)
- PostgreSQL + pgvector (storage)
- Ollama (embeddings)

## Key Commands
- \`make up\`: Start dev services
- \`make test\`: Run tests
- \`pnpm mcp:dev\`: Start MCP server

## Important Conventions
- Async/await for all I/O
- Type hints required
- ESM modules for TypeScript
`,
  category: "onboarding",
  project: "mindbase"
});
```

## Advantages

### vs Database-Only (Old MindBase)

| Feature | Database-Only | Hybrid (New) |
|---------|---------------|--------------|
| Human-readable | ❌ | ✅ Markdown files |
| Editable | ❌ | ✅ Any text editor |
| Version control | ❌ | ✅ Git-trackable |
| Semantic search | ✅ | ✅ Still available |
| Portable | ❌ Requires DB | ✅ Files work alone |

### vs File-Only (Serena)

| Feature | File-Only | Hybrid (MindBase) |
|---------|-----------|-------------------|
| Human-readable | ✅ | ✅ |
| Editable | ✅ | ✅ |
| Semantic search | ❌ | ✅ pgvector |
| Cross-project search | ❌ | ✅ Database |
| Temporal decay | ❌ | ✅ (planned) |

## Database Schema

```sql
CREATE TABLE memories (
    name TEXT NOT NULL,
    content TEXT NOT NULL,
    category TEXT CHECK (category IN ('architecture', 'decision', 'pattern', 'guide', 'onboarding', 'note')),
    project TEXT,
    tags TEXT[] DEFAULT '{}',
    embedding vector(1024),  -- qwen3-embedding:8b
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,

    PRIMARY KEY (name, COALESCE(project, ''))
);

-- Indexes for efficient queries
CREATE INDEX idx_memories_project ON memories(project);
CREATE INDEX idx_memories_category ON memories(category);
CREATE INDEX idx_memories_tags ON memories USING GIN(tags);
CREATE INDEX idx_memories_embedding ON memories USING ivfflat (embedding vector_cosine_ops);
```

## Future Enhancements

### Phase 2: Auto-Onboarding (Planned)

```typescript
// Auto-detect project structure and create onboarding memory
project_onboard({
  projectPath: "/Users/kazuki/github/mindbase"
}) → {
  - Detect languages (Python, TypeScript)
  - Find test commands
  - Find build commands
  - Create onboarding.md automatically
}
```

### Phase 3: Thinking Tools (Planned)

```typescript
// Meta-cognitive tools from Serena
think_about_collected_information()
think_about_task_adherence()
think_about_whether_you_are_done()
```

### Phase 4: Temporal Decay Scoring (Planned)

```sql
-- Exponential decay: newer = more relevant
SELECT *,
  (1 - (embedding <=> $1::vector)) *
  EXP(-0.1 * EXTRACT(EPOCH FROM (NOW() - created_at)) / 86400) AS decayed_score
FROM memories
ORDER BY decayed_score DESC
```

## Testing

### Unit Tests

See `tests/test_memory_storage.py` (to be created).

### Integration Test

```bash
# Start dev environment
make up

# Test memory operations
pnpm mcp:dev

# In another terminal, test with MCP client
# (Claude Desktop, Windsurf, etc.)
```

## Migration Guide

### From Database-Only Conversations

```typescript
// Old: conversation_save stores in database only
conversation_save({
  title: "Important decision",
  content: {...}
})

// New: Also save as memory for long-term reference
memory_write({
  name: "decision_mcp_architecture",
  content: "# Decision: MCP Architecture\n\n...",
  category: "decision",
  project: "mindbase"
})
```

## References

- **Serena MCP Server**: https://github.com/oraios/serena
- **Analysis**: `docs/research/serena_vs_mindbase_analysis_2025-10-19.md`
- **Architecture**: `claudedocs/architecture_memory_vs_mindbase_2025-10-17.md`
