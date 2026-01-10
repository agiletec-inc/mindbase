# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

---

## CRITICAL RULES

### 1. Never Hardcode Configuration

**All ports, URLs, and connection strings MUST come from environment variables.**

```python
# ❌ NEVER
DATABASE_URL = "postgresql://localhost:5432/db"

# ✅ ALWAYS
DATABASE_URL = os.getenv("DATABASE_URL")  # Required - fail fast if missing
```

See `.env.example` for all required variables. Apps must fail fast with clear errors if env vars are missing.

### 2. Auto-Generated Files - Do Not Edit

These files are generated from `manifest.toml` via `airis init`:
- `package.json` (root)
- `pnpm-workspace.yaml`

**Edit `manifest.toml` instead, then run `airis init` to regenerate.**

### 3. Docker-First Development

Host package manager commands are forbidden. Use `make` or `airis` commands:

```bash
# ❌ FORBIDDEN on host
npm install / pnpm install / yarn install

# ✅ USE INSTEAD
make up              # Start services
make api-shell       # Enter container, then run commands inside
```

---

## Project Overview

**MindBase** is the memory substrate of the AIRIS ecosystem - a local-first AI conversation knowledge management system with semantic search via PostgreSQL + pgvector + Ollama.

**Key Integration**: Part of [AIRIS MCP Gateway](https://github.com/agiletec-inc/airis-mcp-gateway) which provides unified MCP access. MindBase exposes `mindbase_search` and `mindbase_store` tools.

**Stack**: Hybrid Python/TypeScript pnpm monorepo
- **Storage**: PostgreSQL 17 + pgvector (1024-dim vectors)
- **Embeddings**: Ollama with qwen3-embedding:8b (local, free)
- **API**: FastAPI (Python)
- **MCP Server**: TypeScript (stdio transport)

## Quick Reference

### Development Setup

```bash
cp .env.example .env          # Configure environment
make up                       # Start PostgreSQL + API + Ollama
make model-pull               # Download embedding model (~4.7GB, first time only)
make migrate                  # Run database migrations
make health                   # Verify all services running
```

### Common Commands

| Make Command | AIRIS Equivalent | Description |
|--------------|------------------|-------------|
| `make up` | `airis up` | Start all services |
| `make down` | `airis down` | Stop all services |
| `make logs` | `airis logs` | View all logs |
| `make api-shell` | - | Enter API container for Python work |
| `make db-shell` | - | Enter PostgreSQL shell |
| `make test` | `airis test` | Run all tests |
| `make test-unit` | - | Run unit tests only |
| `make test-integration` | - | Run integration tests |
| `make test-cov` | - | Tests with coverage report |

**Note**: `airis` commands are preferred when available. Use `make` for Python/database-specific tasks.

### Service Endpoints (configured via .env)

- API: `http://localhost:${API_PORT}` (default: 18003)
- API Docs: `http://localhost:${API_PORT}/docs`
- PostgreSQL: `localhost:${POSTGRES_PORT}` (default: 15434)
- Ollama: `http://localhost:${OLLAMA_PORT}` (default: 11434)

## Codebase Structure

```
apps/
├── api/              # FastAPI backend (Python) - main entry: main.py
├── mcp-server/       # MCP Server (TypeScript) - main entry: index.ts
├── settings/         # Settings UI (React + Vite + Tailwind)
└── menubar-swift/    # Native macOS menubar app with auto-collection

libs/
├── collectors/       # Python conversation collectors (Claude, Cursor, ChatGPT, etc.)
├── processors/       # TypeScript content processors
└── generators/       # TypeScript article generators

supabase/migrations/  # PostgreSQL migrations (will move to packages/database/)
tests/                # pytest tests (unit/integration/e2e markers)
```

### Key Files

**Python API (`apps/api/`)**:
- `main.py` - FastAPI app with CORS, route registration
- `config.py` - Pydantic settings from environment
- `database.py` - SQLAlchemy async engine with pgvector
- `ollama_client.py` - Embedding client (qwen3-embedding:8b, 1024-dim)

**MCP Server (`apps/mcp-server/`)**:
- `index.ts` - MCP entry point (stdio transport)
- `storage/postgres.ts` - Conversation storage backend
- `storage/memory-fs.ts` - Markdown memory storage (Serena-inspired)
- `tools/conversation.ts` - conversation_save, conversation_get, conversation_search, conversation_delete
- `tools/memory.ts` - memory_write, memory_read, memory_list, memory_search, memory_delete

**Collectors (`libs/collectors/`)**:
- `base_collector.py` - Abstract base with `Conversation` and `Message` dataclasses
- Source-specific: `claude_collector.py`, `cursor_collector.py`, `chatgpt_collector.py`, etc.

## Architecture Notes

### Data Separation

```
~/Library/Application Support/mindbase/  # User data (NOT in git)
├── conversations/                        # Archived conversations by source
└── memories/                             # Markdown memories with frontmatter

~/github/mindbase/                        # Source code (Git-tracked)
```

### MCP Server Design

- **Transport**: stdio (for Claude Desktop/Windsurf/Cursor integration)
- **Storage backends**: Interface-based, swappable (PostgresStorageBackend, FileSystemMemoryBackend)
- **Error handling**: All tools return `{error: message}` on failure (no exceptions to client)
- **Hybrid memory**: Markdown files (human-readable) + PostgreSQL (semantic search)

### Embedding Model

- **Model**: qwen3-embedding:8b via Ollama
- **Dimensions**: 1024 (auto-detected, can override via EMBEDDING_DIMENSIONS)
- **Index**: ivfflat for pgvector similarity search

## Development Conventions

### Monorepo Rules
- **Work from root**: Never `cd` into subdirectories
- **Package naming**: `@mindbase/[name]`
- **Shared code**: Place in `libs/`, not individual apps

### Python (apps/api/, libs/collectors/)
- Async/await for all I/O (FastAPI, database, Ollama)
- Pydantic for settings and validation
- Dataclasses for conversation data structures
- Type hints required
- Testing: pytest with async support, use markers (`@pytest.mark.unit`, `@pytest.mark.integration`, `@pytest.mark.e2e`)

### TypeScript (apps/mcp-server/, apps/settings/, libs/)
- ESM modules (`"type": "module"`)
- Use `tsx` for running TypeScript directly
- React 19 patterns for UI (apps/settings)

### Testing

```bash
# Inside Docker container (make api-shell)
pytest tests/ -v                          # All tests
pytest -m unit -v                         # Unit tests only
pytest -m integration -v                  # Integration tests
pytest tests/unit/test_collectors/test_base_collector.py -v  # Specific file
pytest tests/ -k "test_embedding" -v      # Pattern match

# Code quality
black apps/api/ libs/collectors/          # Format
ruff check apps/api/ libs/collectors/     # Lint
mypy apps/api/ libs/collectors/           # Type check
```

## Common Tasks

### Adding New MCP Tools
1. Define schema in `apps/mcp-server/index.ts` TOOLS array
2. Implement handler in `apps/mcp-server/tools/*.ts`
3. Add switch case in `setupHandlers()` method
4. Test with Claude Desktop/Cursor

### Adding New Conversation Sources
1. Create `libs/collectors/[source]_collector.py` inheriting from `BaseCollector`
2. Implement `get_data_paths()` and `collect()` methods
3. Add to source enum in MCP tool schemas
4. Test: `python -m libs.collectors.[source]_collector`

## Troubleshooting

**"Ollama model not found"**: `make model-pull`

**"Database connection refused"**: `make health` then `make restart`

**"Permission denied for Application Support"**:
```bash
mkdir -p "$HOME/Library/Application Support/mindbase/conversations"
```

## Execution Mode

Default mode is **operator**, not advisor. Prioritize action (edit, execute, test) over explanation. See `AGENTS.md` for detailed execution rules.
