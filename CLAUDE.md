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

Host package manager commands are forbidden. Use `airis` commands:

```bash
# ❌ FORBIDDEN on host
npm install / pnpm install / yarn install

# ✅ USE INSTEAD
airis up              # Start services
airis api-shell       # Enter container, then run commands inside
```

---

## Project Overview

**MindBase** is the memory substrate of the AIRIS ecosystem - a local-first AI conversation knowledge management system with semantic search via PostgreSQL + pgvector + Ollama.

**Key Integration**: Part of [AIRIS MCP Gateway](https://github.com/agiletec-inc/airis-mcp-gateway) which provides unified MCP access. MindBase exposes `mindbase_search` and `mindbase_store` tools.

**Stack**: Hybrid Python/TypeScript pnpm monorepo
- **Storage**: PostgreSQL 17 + pgvector
- **Embeddings**: OpenAI text-embedding-3-large (3072-dim, primary) → Ollama qwen3-embedding:8b (1024-dim, fallback)
- **API**: FastAPI (Python)
- **MCP Server**: TypeScript (stdio transport)

## Quick Reference

### Development Setup

```bash
cp .env.example .env          # Configure environment
airis up                      # Start PostgreSQL + API
airis model-pull              # Download embedding model (~4.7GB, first time only)
airis migrate                 # Run database migrations
airis health                  # Verify all services running
```

### Common Commands

| Command | Description |
|---------|-------------|
| `airis up` | Start all services |
| `airis down` | Stop all services |
| `airis restart` | Restart all services |
| `airis logs` | View all logs |
| `airis ps` | Show container status |
| `airis api-shell` | Enter API container for Python work |
| `airis db-shell` | Enter PostgreSQL shell |
| `airis test` | Run all tests |
| `airis health` | Check service health |
| `airis migrate` | Run database migrations |
| `airis model-pull` | Download embedding model |

### Service Endpoints (configured via .env)

- API: `http://localhost:${API_PORT}` (default: 18003)
- API Docs: `http://localhost:${API_PORT}/docs`
- PostgreSQL: `localhost:${POSTGRES_PORT}` (default: 15434)
- Ollama: `http://localhost:${OLLAMA_PORT}` (default: 11434)

## Codebase Structure

```
apps/
├── api/              # FastAPI backend (Python) - main entry: main.py
├── cli/              # CLI tool (TypeScript) - content generation pipeline
├── mcp-server/       # MCP Server (TypeScript) - main entry: index.ts
├── settings/         # Settings UI (React + Vite + Tailwind)
└── menubar-swift/    # Native macOS menubar app with auto-collection

libs/
├── collectors/       # Python conversation collectors (Claude, Cursor, ChatGPT, etc.)
├── generators/       # TypeScript article generators (Qiita, Zenn, Note publishing)
├── processors/       # TypeScript content processors
└── shared/           # Shared TypeScript types

supabase/migrations/  # PostgreSQL migrations (sequential SQL files)
tests/                # pytest tests (unit/integration/e2e markers)
```

### Key Entry Points

- **API**: `apps/api/main.py` → routes in `apps/api/api/routes/`
- **MCP Server**: `apps/mcp-server/index.ts` → tools in `tools/`, storage in `storage/`
- **CLI**: `apps/cli/index.ts` → uses `libs/generators/` for article generation
- **Collectors**: `libs/collectors/base_collector.py` (abstract) → source-specific implementations

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

### Embedding Strategy (Dual Provider)

- **Primary**: OpenAI `text-embedding-3-large` (3072-dim) — requires `OPENAI_API_KEY`
- **Fallback**: Ollama `qwen3-embedding:8b` (1024-dim) — local, free
- Both Python (`ollama_client.py`) and TypeScript (`storage/postgres.ts`) implement the same fallback logic
- Dimensions auto-detected; override with `EMBEDDING_DIMENSIONS`
- Index: ivfflat for pgvector similarity search

### Data Pipeline (Raw → Derived)

1. `conversation_save` (MCP) or `POST /conversations/store` (API) receives raw data
2. `RawConversation` stored append-only (immutable payload)
3. Deriver (`services/deriver.py`) processes: embedding generation, topic extraction, metadata enrichment
4. `Conversation` created with vector embedding for semantic search
5. `DERIVE_ON_STORE=true` (default) triggers derivation immediately; otherwise background worker processes

### Hybrid Search

Three scoring components combined with auto-normalized weights:
- **Keyword**: PostgreSQL full-text search (`ts_rank`)
- **Semantic**: pgvector cosine similarity on embedding vectors
- **Recency**: Exponential decay `exp(-age / tau)` with boost for recent items

Tuning via env vars: `SEARCH_RECENCY_TAU_SECONDS` (14d default), `SEARCH_RECENCY_WEIGHT` (0.15), `SEARCH_RECENCY_BOOST_DAYS` (3), `SEARCH_RECENCY_BOOST_VALUE` (0.05)

### Content Generation Pipeline

会話データから記事を生成し、プラットフォームに公開:

1. `apps/cli/` - CLI エントリポイント (`mindbase` コマンド)
2. `libs/generators/article-generator.ts` - LLM (OpenAI) で記事生成
3. `libs/generators/platform-prompts.ts` - プラットフォーム固有プロンプト
4. `libs/generators/publishers/` - Qiita, Zenn, Note パブリッシャー

実行: `docker compose run --rm cli pnpm generate` / `pnpm publish`

### CI/CD

- Push to `next` or PR to `main` で CI 実行 (pnpm install → test → build)
- `next` → `main` はCI成功時に自動マージ
- ワークフロー: `.github/workflows/ci.yml` (auto-generated from manifest.toml)

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
# Inside Docker container (airis api-shell)
pytest tests/ -v                          # All tests
pytest -m unit -v                         # Unit tests only
pytest -m integration -v                  # Integration tests
pytest tests/unit/test_collectors/test_base_collector.py -v  # Specific file
pytest tests/ -k "test_embedding" -v      # Pattern match

# Code quality
black apps/api/ libs/collectors/          # Format
ruff check apps/api/ libs/collectors/     # Lint
mypy apps/api/ libs/collectors/           # Type check

# TypeScript
airis typecheck
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

**"Ollama model not found"**: `airis model-pull`

**"Database connection refused"**: `airis health` then `airis restart`

**"Permission denied for Application Support"**:
```bash
mkdir -p "$HOME/Library/Application Support/mindbase/conversations"
```

## Execution Mode

Default mode is **operator**, not advisor. Prioritize action (edit, execute, test) over explanation. See `AGENTS.md` for detailed execution rules.
