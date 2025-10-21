# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

**MindBase** is an AI conversation knowledge management system that collects, analyzes, and transforms conversations from multiple AI platforms (Claude Code, Claude Desktop, ChatGPT, Cursor, Windsurf) into structured content for blog generation and publishing.

**Architecture**: Hybrid Python/TypeScript monorepo with PostgreSQL + pgvector for storage and Ollama for embeddings.

**Structure**: pnpm monorepo with apps (deployable) and libs (shared code). See `MONOREPO.md` for migration details.

## MCP Server Integration

**MindBase MCP Server** provides Model Context Protocol integration, enabling Claude Desktop/Windsurf/Cursor to directly access MindBase's conversation knowledge management capabilities.

### Core Capabilities

```yaml
Short-Term Memory:
  - Direct access to recent session conversations
  - Latest decision tracking (category: decision)
  - Real-time progress updates (category: progress)

Long-Term Memory:
  - Semantic search across all sessions (pgvector)
  - Temporal decay scoring (older = lower relevance)
  - Cross-session knowledge retrieval

LLM Runaway Prevention:
  - Error/warning history tracking
  - Repeated mistake detection
  - Past solution suggestions
```

### Memory vs MindBase Responsibility Separation

**Critical Understanding**: memory (Built-in) and mindbase serve **different responsibilities**.

| Feature | memory (Built-in) | mindbase |
|---------|-------------------|----------|
| **Data Structure** | Entities + Relationships (Knowledge Graph) | Conversations + Sessions + Categories |
| **Time Management** | ❌ No temporal concept | ✅ Sessions hierarchy + timestamps |
| **Short-Term Memory** | ⚠️ Session-only (volatile) | ✅ Recent session conversations (persistent) |
| **Long-Term Memory** | ⚠️ Unknown cross-session persistence | ✅ All sessions + pgvector search |
| **Information Update** | ❌ No update mechanism | ✅ Category-based latest state tracking |
| **Failure Learning** | ❌ No error tracking | ✅ error/warning categories |
| **LLM Runaway Prevention** | ❌ No prevention | ✅ Prevents repeated mistakes |
| **Temporal Decay** | ❌ No decay | ✅ Exponential decay scoring |
| **Lifespan** | Session-scoped (volatile) | Persistent (with decay) |

### Use Cases

**Use memory (Built-in) for**:
- ✅ "What did I just say about ○○?"
- ✅ Immediate session context
- ✅ Entity relationship tracking (knowledge graph)
- ✅ Volatile short-term memory

**Use mindbase for**:
- ✅ "What did we discuss yesterday about architecture?"
- ✅ "Did we encounter this error before?"
- ✅ "What's the latest decision?"
- ✅ "This implementation failed before, right?"
- ✅ Blog/book generation from knowledge
- ✅ Cross-project knowledge search

### Integration with PM Agent (SuperClaude Framework)

**mindbase responsibility**: Provide MCP Tools (API) for memory management
**PM Agent responsibility**: Read from mindbase and integrate into development workflow

PM Agent can access mindbase via MCP Tools:
- Read past errors/warnings to prevent repeated mistakes
- Track decision history for consistency
- Restore session context from long-term memory

**Note**: Workflow integration code lives in SuperClaude Framework, not mindbase.

### MCP Server Tools

**Available Tools**:
```yaml
Conversation Management:
  - conversation_save: Save with automatic embedding generation
  - conversation_get: Filter search (ID/source/category/priority)
  - conversation_search: Semantic search (pgvector cosine similarity)
  - conversation_delete: Delete conversation

Session Management:
  - session_create: Create new session
  - session_start: Start/resume session (sets as current context)
  - session_list: List recent sessions
  - session_delete: Delete session

Memory Management (Serena-inspired):
  - memory_write: Write markdown memory with hybrid storage (file + database)
  - memory_read: Read memory by name (markdown file or database fallback)
  - memory_list: List all memories with filtering (project/category/tags)
  - memory_delete: Delete memory from both markdown and database
  - memory_search: Semantic search across memories (pgvector similarity)
```

**Setup**: See `claudedocs/claude_desktop_config_example.json` for Claude Desktop configuration.

**Documentation**:
- Architecture: `claudedocs/architecture_memory_vs_mindbase_2025-10-17.md`
- Serena Analysis: `docs/research/serena_vs_mindbase_analysis_2025-10-19.md`

**MCP Server Architecture**:
```
apps/mcp-server/index.ts                    # Main entry (stdio transport)
├── storage/postgres.ts                     # Conversation storage backend
├── storage/memory-fs.ts                    # Memory (markdown) storage backend
├── storage/interface.ts                    # Storage interface definitions
├── storage/memory-interface.ts             # Memory storage interface
├── tools/conversation.ts                   # Conversation management tools
└── tools/memory.ts                         # Memory management tools

Storage Backends:
- PostgresStorageBackend: Database operations + Ollama embeddings
- FileSystemMemoryBackend: Hybrid markdown + database storage

Transport: stdio (Claude Desktop/Windsurf/Cursor communicate via stdin/stdout)
```

**Key Design Decisions**:
- Storage backends are abstracted (interface-based, swappable)
- Environment variables: `DATABASE_URL`, `OLLAMA_URL`, `EMBEDDING_MODEL`, `MEMORY_BASE_DIR`
- Error handling: All tools return `{error: message}` on failure (no exceptions to client)
- **Embedding model**: nomic-embed-text (768-dim, ivfflat compatible)

### Memory System (Serena-Inspired)

**NEW**: MindBase now includes Serena-inspired markdown-based memory storage with hybrid approach.

**Hybrid Storage Strategy**:
```
Primary: Markdown files in ~/Library/Application Support/mindbase/memories/
         - Human-readable and editable
         - Git-trackable (optional)
         - Project-specific organization

Secondary: PostgreSQL with pgvector embeddings
          - Semantic search across all memories
          - Cross-project knowledge retrieval
          - Temporal decay scoring (planned)
```

**Memory File Format**:
```markdown
---
category: decision
project: mindbase
tags: [architecture, mcp, serena]
createdAt: 2025-10-19T10:00:00Z
updatedAt: 2025-10-19T10:00:00Z
---

# Memory Content

Your markdown content here with full formatting support.

## Code Examples
\`\`\`typescript
// Code blocks preserved
\`\`\`
```

**Usage Examples**:
```typescript
// Write memory
memory_write({
  name: "architecture_decisions",
  content: "# Architecture Decisions\n\n...",
  category: "decision",
  project: "mindbase",
  tags: ["architecture", "mcp"]
})

// Read memory
memory_read({ name: "architecture_decisions", project: "mindbase" })

// List memories
memory_list({ project: "mindbase", category: "decision" })

// Semantic search
memory_search({
  query: "How should MCP tools be organized?",
  threshold: 0.7,
  project: "mindbase"
})
```

**Advantages over Database-Only Approach**:
- ✅ Human-readable and editable (can refine AI-generated memories)
- ✅ Git version control (track memory evolution)
- ✅ No database required for basic operations (portable)
- ✅ Semantic search available (when database configured)
- ✅ Project-specific organization (no cross-project noise)

## Data Separation Philosophy

**Critical**: Conversation data lives in `~/Library/Application Support/mindbase/` (invisible to Claude) while source code lives in `~/github/mindbase/` (Git-tracked, readable by Claude).

```
~/Library/Application Support/mindbase/  # Data (Claude cannot read)
├── conversations/claude-code/           # Archived conversations
├── conversations/claude-desktop/
├── conversations/chatgpt/
├── memories/                            # Serena-inspired markdown memories
└── db/                                  # Database persistence

~/github/mindbase/                       # Source code (Git-managed)
├── apps/
│   ├── api/                             # ✅ FastAPI backend (migrated from app/)
│   ├── mcp-server/                      # ✅ MCP Server (migrated from src/mcp-server/)
│   └── settings/                        # ✅ Settings UI (React + Vite)
├── libs/
│   ├── collectors/                      # ✅ Python conversation collectors
│   ├── processors/                      # ✅ TypeScript content processors
│   └── generators/                      # ✅ TypeScript article generators
├── packages/
│   └── database/                        # PostgreSQL migrations (planned)
├── supabase/migrations/                 # ⚠️ Current migration location (will move to packages/database/)
├── tests/                               # Test suite (unit/integration/e2e)
├── scripts/                             # Shell scripts for workflows
└── Formula/                             # Homebrew formula for production install
```

**Why this design?** Keeps conversation data out of Claude's context to prevent noise and maintain focus on code.

## Current Codebase Structure

**Monorepo structure (apps, libs, packages):**

### Active Paths
```
Python API:        apps/api/                     # ✅ Migrated from app/
MCP Server:        apps/mcp-server/              # ✅ Migrated from src/mcp-server/
Settings UI:       apps/settings/                # ✅ React + Vite
Collectors:        libs/collectors/              # ✅ Python conversation collectors
Processors:        libs/processors/              # ✅ TypeScript content processors
Generators:        libs/generators/              # ✅ TypeScript article generators
Migrations:        supabase/migrations/          # ⚠️ Will move to packages/database/
Tests:             tests/                        # unit/integration/e2e
Homebrew Formula:  Formula/mindbase.rb           # Production install
```

### Environment-Specific Configuration

| Environment | Database Name | Database Port | API Port | Ollama |
|-------------|---------------|---------------|----------|--------|
| **Production** | `mindbase` | 5432 (local) | 18002 | brew (11434) |
| **Development** | `mindbase_dev` | 15434 (Docker) | 18003 | host brew (11434) |

## Development Modes

**MindBase supports two execution modes with complete separation:**

| Mode | Use Case | Port | Database | Ollama | Data |
|------|----------|------|----------|--------|------|
| **Production** | Daily use, MCP Server | 18002 | Local PostgreSQL (5432) | brew (GPU) | Application Support |
| **Development** | Feature development | 18003 | Docker (15434) | Host brew | Docker volumes |

### Production Mode (Homebrew Installation)

**For end users and daily MCP server usage.**

```bash
# Installation
brew tap agiletec-inc/mindbase
brew install mindbase

# Or install from source
git clone https://github.com/agiletec-inc/mindbase.git
cd mindbase
bash scripts/install-local.sh

# Setup (one-time)
mindbase setup              # Creates DB, pulls Ollama model, runs migrations

# Start service
mindbase serve              # Foreground
brew services start mindbase  # Background service

# Health check
mindbase health
curl http://localhost:18002/health

# MCP Server configuration
# Add to ~/.config/claude/claude_desktop_config.json:
{
  "mcpServers": {
    "mindbase": {
      "command": "mindbase",
      "args": ["serve"]
    }
  }
}
```

**Production endpoints:**
- API: http://localhost:18002
- Docs: http://localhost:18002/docs
- Database: postgresql://$(whoami)@localhost:5432/mindbase
- Ollama: http://localhost:11434 (brew install ollama, GPU-enabled)

### Development Mode (Docker)

**For contributors and feature development. Completely isolated from production.**

```bash
# Initial setup
make init                    # Start services + pull Ollama model + run migrations

# Service management
make up                      # Start dev services (port 18003)
make down                    # Stop all services
make restart                 # Restart services
make ps                      # Show container status
make health                  # Check health (port 18003)

# Development
make api-shell               # Enter FastAPI container for Python work
make db-shell                # Enter PostgreSQL shell
make logs                    # View all logs (or logs-api, logs-postgres, logs-ollama)

# Database
make migrate                 # Run database migrations

# Cleanup
make clean                   # Remove local artifacts (__pycache__, node_modules)
make clean-all               # Delete everything including volumes (⚠️ data loss)
```

**Development endpoints:**
- API: http://localhost:18003 (dev port, production: 18002)
- Docs: http://localhost:18003/docs
- Database: postgresql://mindbase:mindbase_dev@localhost:15434/mindbase_dev
- Ollama: http://host.docker.internal:11434 (uses host brew Ollama)

### Port Separation (No Conflicts)

```yaml
Production (brew install):
  API: 18002
  PostgreSQL: 5432 (default)
  Ollama: 11434 (brew)

Development (Docker):
  API: 18003  # +1 from production
  PostgreSQL: 15434  # +1 from 15433
  Ollama: 11434 (host.docker.internal)  # Uses production brew Ollama
```

**Why this works:** Development and production can run simultaneously without conflicts. Test E2E by installing brew version while developing in Docker.

### Testing Workflow

```bash
# 1. Develop in Docker (port 18003)
make up
make api-shell
# ... make changes ...
pytest tests/

# 2. Test locally installed version (port 18002)
brew install --build-from-source Formula/mindbase.rb
brew services start mindbase
curl http://localhost:18002/health  # Production
curl http://localhost:18003/health  # Development

# 3. Both running simultaneously
# Development changes don't affect production instance
```

### Monorepo Workflows (pnpm)

**Root-level commands** run from `/Users/kazuki/github/mindbase/`:

```bash
# Development servers
pnpm dev                     # Run Settings UI (React)
pnpm dev:api                 # Run FastAPI backend
pnpm dev:mcp                 # Run MCP Server

# Build and quality
pnpm build                   # Build all packages
pnpm typecheck               # Type check all TypeScript
pnpm lint                    # Lint all packages
pnpm test                    # Run all tests

# Content generation pipeline
pnpm extract                 # Extract modules/topics (uses libs/processors)
pnpm generate <category>     # Generate blog article (uses libs/generators)
pnpm publish <file>          # Publish article to Qiita (requires QIITA_TOKEN)

# Package-specific (using --filter)
pnpm --filter @mindbase/settings dev
pnpm --filter @mindbase/mcp-server build
pnpm --filter @mindbase/processors extract
```

**Never `cd` into subdirectories** - use `pnpm --filter` for package-specific operations.

### Service Endpoints

Production (Homebrew):
```
API:        http://localhost:18002        (FastAPI backend)
API Docs:   http://localhost:18002/docs   (Swagger UI)
Ollama:     http://localhost:11434        (Embedding service, brew)
PostgreSQL: localhost:5432                (Local PostgreSQL, database: mindbase)
Health:     http://localhost:18002/health (API health check)
```

Development (Docker):
```
API:        http://localhost:18003        (FastAPI backend)
API Docs:   http://localhost:18003/docs   (Swagger UI)
Ollama:     http://localhost:11434        (Embedding service, host brew)
PostgreSQL: localhost:15434               (Docker PostgreSQL, database: mindbase_dev)
Health:     http://localhost:18003/health (API health check)
```

### API Endpoints

**Conversation Storage**:
```bash
POST /conversations/store
# Store conversation with automatic embedding generation
# Development:
curl -X POST http://localhost:18003/conversations/store \
  -H "Content-Type: application/json" \
  -d '{
    "source": "claude-code",
    "title": "Feature Implementation",
    "content": {"messages": [{"role": "user", "content": "..."}]},
    "metadata": {"project": "mindbase"}
  }'
```

**Semantic Search**:
```bash
POST /conversations/search
# Search conversations by semantic similarity
# Development:
curl -X POST http://localhost:18003/conversations/search \
  -H "Content-Type: application/json" \
  -d '{
    "query": "database migration PostgreSQL",
    "limit": 10,
    "threshold": 0.7,
    "source": "claude-code"
  }'
```

**Note**: For production (Homebrew), use port `18002` instead of `18003`.

## Architecture Layers

### 1. Apps (Deployable Applications)

**apps/api/** - FastAPI Backend (Python) ✅ **Migrated**
- `main.py` - FastAPI app with CORS, health check, route registration
- `config.py` - Pydantic settings (database, Ollama, API config)
- `database.py` - SQLAlchemy async engine with pgvector support
- `ollama_client.py` - Ollama embedding client (nomic-embed-text, 768-dim)
- `api/routes/` - REST API endpoints (conversations, health, search)
- `crud/` - Database CRUD operations
- `models/` - SQLAlchemy models with pgvector
- `schemas/` - Pydantic schemas for validation

**apps/mcp-server/** - MCP Server (TypeScript) ✅ **Migrated**
- `index.ts` - MCP Server main entry point (stdio transport)
- `storage/postgres.ts` - PostgreSQL storage backend (conversations)
- `storage/memory-fs.ts` - Filesystem storage backend (memories)
- `storage/interface.ts` - Storage interface definitions
- `storage/memory-interface.ts` - Memory storage interface
- `tools/conversation.ts` - Conversation management tools
- `tools/memory.ts` - Memory management tools (Serena-inspired)

**apps/settings/** - Settings UI (React + Vite)
- React 19 + Vite + Tailwind CSS
- i18n support (react-i18next)
- Future: Mac menu bar app integration via Tauri

**Environment Variables**:

Development (Docker):
```bash
DATABASE_URL=postgresql+asyncpg://mindbase:mindbase_dev@postgres:5432/mindbase_dev
OLLAMA_URL=http://host.docker.internal:11434  # Uses host brew Ollama
EMBEDDING_MODEL=qwen3-embedding:8b
EMBEDDING_DIMENSIONS=1024
DEBUG=true
API_PORT=18003  # Development port
MEMORY_BASE_DIR=~/Library/Application Support/mindbase/memories  # Optional
```

Production (Homebrew):
```bash
DATABASE_URL=postgresql+asyncpg://$(whoami)@localhost:5432/mindbase
OLLAMA_URL=http://localhost:11434
EMBEDDING_MODEL=qwen3-embedding:8b
EMBEDDING_DIMENSIONS=1024
DEBUG=false
API_PORT=18002  # Production port
MEMORY_BASE_DIR=~/Library/Application Support/mindbase/memories  # Optional
```

### 2. Libs (Shared Libraries)

**libs/collectors/** - Python Conversation Collectors
- `base_collector.py` - Abstract base class with `Conversation` and `Message` dataclasses
- `claude_collector.py` - Claude Desktop conversations
- `chatgpt_collector.py` - ChatGPT conversations
- `cursor_collector.py` - Cursor AI conversations
- `data_normalizer.py` - Cross-platform normalization

**Key Classes**:
- `Message`: Individual message (auto-generated message_id, timezone-aware timestamps)
- `Conversation`: Complete conversation (auto-generated ID, validation methods)
- `BaseCollector`: Abstract collector (validation, deduplication, checkpoint system)

**libs/processors/** - TypeScript Content Processors
- `extract-modules.ts` - Topic classification and keyword extraction

**libs/generators/** - TypeScript Article Generators
- `generate-article.ts` - Markdown article generation
- `publish-qiita.ts` - Qiita API publishing

**Topic Categories**:
- Docker-First Development, Turborepo Monorepo, Supabase Self-Host
- Multi-Tenancy Architecture, SuperClaude Framework
- AlmaLinux HomeServer, Performance Optimization

### 3. Packages (Infrastructure)

**packages/database/** - PostgreSQL Migrations
- Database schema definitions (formerly `supabase/migrations/`)
- Key tables: `conversations`, `memories`, `sessions`, `thought_patterns`, `book_structure`

**Vector Search**: pgvector extension for semantic search
**Embedding Model**: qwen3-embedding:8b via Ollama
- **Model**: qwen3-embedding:8b (MTEB #1 multilingual, 2025)
- **Dimensions**: 1024-dimensional vectors
- **Performance**: State-of-the-art multilingual semantic understanding
- **Cost**: Free, runs locally on CPU/GPU via Ollama
- **Download size**: ~4.7GB (initial pull only)

## Development Workflows

### Complete Blog Generation Pipeline

```bash
# 1. Archive old conversations (90+ days)
pnpm archive 90

# 2. Extract topics and modules
pnpm extract

# 3. Generate article for specific category
pnpm generate docker-first-development
# Output: generated/2025-10-14-docker-first-development.md

# 4. Publish to Qiita (dry-run first)
export QIITA_TOKEN=your_token_here
pnpm publish generated/2025-10-14-docker-first.md --dry-run

# 5. Actual publish
pnpm publish generated/2025-10-14-docker-first.md
```

### Python Development (Inside Docker)

```bash
# Enter API container
make api-shell

# Inside container - Testing (by markers)
pytest tests/ -v                           # Run all tests with verbose output
pytest -m unit -v                          # Run unit tests only
pytest -m integration -v                   # Run integration tests only
pytest -m e2e -v                           # Run E2E tests only

# Inside container - Testing (specific files/patterns)
pytest tests/unit/test_collectors/test_base_collector.py -v  # Specific file
pytest tests/ -k "test_embedding" -v       # Tests matching pattern
pytest tests/integration/test_database.py::test_connection -v  # Specific test

# Inside container - Coverage
pytest tests/ --cov=app --cov=libs.collectors --cov-report=html  # HTML report
pytest tests/ --cov=app --cov-report=term-missing  # Terminal with missing lines

# Inside container - Code Quality
black app/ libs/collectors/                # Format code with Black
ruff check app/ libs/collectors/           # Lint with Ruff
ruff check app/ libs/collectors/ --fix     # Auto-fix linting issues
mypy app/ libs/collectors/                 # Type check with mypy

# Inside container - Collectors (run directly)
python -m libs.collectors.claude_collector      # Run Claude Code collector
python -m libs.collectors.chatgpt_collector     # Run ChatGPT collector
python -m libs.collectors.cursor_collector      # Run Cursor collector
python -m libs.collectors.windsurf_collector    # Run Windsurf collector

# Inside container - Ollama Testing
python -m app.ollama_client                # Test Ollama connection
```

### Database Operations

```bash
# Access PostgreSQL
make db-shell

# Inside psql
\dt                                        # List tables
\d conversations                           # Show table schema
SELECT COUNT(*) FROM conversations;        # Query data
```

### Testing Ollama Embeddings

```bash
# Pull embedding model (required for first run)
make model-pull

# Test embedding generation
docker compose exec ollama ollama list     # Show installed models
curl http://localhost:11434/api/embeddings \
  -d '{"model":"qwen3-embedding:8b","prompt":"test"}' # Generate embedding
```

## Project Integration History

**MindBase** integrates two previous projects:

1. **dot-claude-optimizer** → `scripts/archive/` and `scripts/optimize-dotclaude/`
   - Responsibility: `~/.claude/` optimization and conversation archiving
   - Change: Archive destination moved to Application Support (data separation)

2. **claude-blog-automation** → `src/processors/` and `src/generators/`
   - Responsibility: Conversation → blog article automation
   - Change: Reads from archived conversations instead of live `~/.claude/`

See `INTEGRATION_PLAN.md` for complete integration details.

## Key Conventions

### Monorepo Development
- **Always work from root**: Never `cd` into subdirectories
- **Use `pnpm --filter`**: For package-specific operations
- **Package naming**: `@mindbase/[name]` (e.g., `@mindbase/settings`, `@mindbase/mcp-server`)
- **Shared code**: Place in `libs/` (not in individual apps)
- **Migration paths**: See `MONOREPO.md` for old→new path mappings

### Python Code Style (apps/api/, libs/collectors/)
- Use async/await for all I/O operations (FastAPI, database, Ollama)
- Pydantic for settings and data validation
- Dataclasses for structured conversation data
- Type hints required for all functions
- Testing: pytest with async support (`pytest-asyncio`)

### TypeScript Code Style (apps/mcp-server/, apps/settings/, libs/processors/, libs/generators/)
- ESM modules (`"type": "module"` in package.json)
- Use `tsx` for running TypeScript directly
- Async/await for file I/O and API calls
- React 19 patterns for UI components (apps/settings)
- MCP Server: stdio transport for Claude Desktop/Windsurf/Cursor integration

### File Organization
- **Never** commit conversation data to Git
- **Data storage**: `~/Library/Application Support/mindbase/` (not in Git repo)
- Keep collectors source-agnostic (use `BaseCollector` abstraction)
- Archive scripts output to Application Support only
- Generated articles go to `generated/` directory

### Testing Strategy
- **Python**: pytest with async support (unit, integration, e2e markers)
  - Markers: `@pytest.mark.unit`, `@pytest.mark.integration`, `@pytest.mark.e2e`
  - Run specific: `pytest -m unit`, `pytest -m integration`, `pytest -m e2e`
- **Database**: Use Docker PostgreSQL (dev mode), not local installation
- **Ollama**: Mock in unit tests, real service in integration tests
- **Coverage**: Use `make test-cov` for HTML coverage reports
- **Makefile shortcuts**:
  - `make test` - All tests
  - `make test-unit` - Unit tests only
  - `make test-integration` - Integration tests only
  - `make test-e2e` - E2E tests only
  - `make test-cov` - Coverage report (HTML + terminal)

## Common Issues

**"Ollama model not found"**
```bash
make model-pull  # Downloads qwen3-embedding:8b (~4.7GB)
```

**"Database connection refused"**
```bash
make health      # Check service status
make logs-postgres  # Check PostgreSQL logs
make restart     # Restart services
```

**"Permission denied for Application Support"**
```bash
# Ensure archive directory exists and is writable
mkdir -p "$HOME/Library/Application Support/mindbase/conversations"
```

**"pnpm command not found"**
```bash
# Install pnpm globally (workspace convention)
npm install -g pnpm
```

## Common Development Tasks

### Adding New MCP Tools
1. Define tool schema in `apps/mcp-server/index.ts` TOOLS array
2. Implement handler in `apps/mcp-server/tools/*.ts`
3. Add switch case in `setupHandlers()` method
4. Test with Claude Desktop/Windsurf/Cursor
5. Document in CLAUDE.md and `claudedocs/`

### Adding New Conversation Sources
1. Create new collector in `libs/collectors/[source]_collector.py`
2. Inherit from `BaseCollector` (validation, deduplication built-in)
3. Implement `get_data_paths()` and `collect()` methods
4. Add to `source` enum in MCP tool schemas
5. Test with `python -m libs.collectors.[source]_collector`

### Working with Memories
- Write: `memory_write` tool (creates markdown + database entry)
- Read: `memory_read` tool (checks markdown first, falls back to database)
- Search: `memory_search` tool (semantic search via pgvector)
- Location: `~/Library/Application Support/mindbase/memories/`
- Format: Markdown with frontmatter (category, project, tags, timestamps)

### Monorepo Migration Status

**✅ Migration Complete:**
- [x] Move Python libs: `collectors/` → `libs/collectors/`
- [x] Move TypeScript libs: `src/processors/` → `libs/processors/`, `src/generators/` → `libs/generators/`
- [x] Create monorepo structure with pnpm workspace
- [x] Setup Settings UI in `apps/settings/`
- [x] Move Python app: `app/` → `apps/api/` ✅
- [x] Move MCP Server: `src/mcp-server/` → `apps/mcp-server/` ✅
- [x] Update docker-compose.yml to use `apps/api/`
- [x] Update test scripts to use `apps/mcp-server/`

**🔜 Remaining (Minor):**
- [ ] Move migrations: `supabase/migrations/` → `packages/database/migrations/`
- [ ] Update Homebrew formula to use new paths (when releasing)

**Use these paths:**
- Python API: `apps/api/` ✅
- MCP Server: `apps/mcp-server/` ✅
- Migrations: `supabase/migrations/` (will move to `packages/database/` eventually)
