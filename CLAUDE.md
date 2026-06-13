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

### 2. Workspace files

`pnpm-workspace.yaml` と `package.json` (root) は**手動管理の SSoT** — 直接編集してよい。
(旧記載の「`airis init` で生成」は誤り: `airis init` は存在しない。`airis workspace gen` は
`compose.yaml` / `tsconfig.*` を生成するだけで、これらの workspace ファイルは生成しない。)

### 3. ローカル開発 = docker compose

mindbase の stack はコンテナ(PostgreSQL + pgvector + Ollama + FastAPI)。host-native は org 全体の
既定だが、本 repo は stack がコンテナなのでローカルも `docker compose` で起動するのが parity。
Python は api コンテナ内で動く(`command: uvicorn app.main:app --reload`)。

```bash
docker compose up -d                  # Start services
docker compose exec api bash          # Enter the API container for Python work
```

---

## Project Overview

**MindBase** is the memory substrate of the AIRIS ecosystem - a local-first AI conversation knowledge management system with semantic search via PostgreSQL + pgvector + Ollama.

**Key Integration**: Part of [AIRIS MCP Gateway](https://github.com/agiletec-inc/airis-mcp-gateway) which provides unified MCP access. MindBase exposes `conversation_save`, `conversation_hybrid_search`, and `memory_search` tools.

**Stack**: Hybrid Python/TypeScript pnpm monorepo
- **Storage**: PostgreSQL 17 + pgvector
- **Embeddings**: Config-driven dual-provider — Ollama (default, `EMBEDDING_PROVIDER=ollama`) or OpenAI; default model `bge-m3` (1024-dim). Set `EMBEDDING_PROVIDER=openai` for OpenAI `text-embedding-3-large` (3072-dim)
- **API**: FastAPI (Python)
- **MCP Server**: TypeScript (stdio transport)

## Quick Reference

### Development Setup

```bash
cp .env.example .env                            # Configure environment
docker compose up -d                            # Start PostgreSQL + API + Ollama
docker compose exec ollama ollama pull bge-m3   # Download embedding model (~4.7GB, first time only)
docker compose ps                               # Verify services healthy
```

DB migrations は postgres 起動時に `./supabase/migrations` (initdb.d) から自動適用される。

### Common Commands

| Command | Description |
|---------|-------------|
| `docker compose up -d` | Start all services |
| `docker compose down` | Stop all services |
| `docker compose restart` | Restart all services |
| `docker compose logs -f` | View all logs |
| `docker compose ps` | Show container status & health |
| `docker compose exec api bash` | Enter API container for Python work |
| `docker compose exec postgres psql -U mindbase mindbase_dev` | Enter PostgreSQL shell |
| `docker compose exec api pytest` | Run all tests |
| `curl -fsS localhost:${API_PORT:-18003}/health` | Check API health |
| `docker compose exec ollama ollama pull bge-m3` | Download embedding model |

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
├── embedding/        # TypeScript embedding client
├── generators/       # TypeScript article generators (Qiita, Zenn, Note publishing)
├── markdown/         # TypeScript markdown utilities
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

- **Config-driven**: `EMBEDDING_PROVIDER=ollama` (default) or `EMBEDDING_PROVIDER=openai` — no implicit key-presence fallback; a misconfigured provider raises immediately
- **Ollama** (default): model set by `EMBEDDING_MODEL` (`.env.example` default: `bge-m3`, 1024-dim)
- **OpenAI**: `text-embedding-3-large` (3072-dim) — requires `OPENAI_API_KEY`
- Per-provider vectors coexist in `conversation_embeddings` table; switching provider does not destroy existing vectors. Use `POST /conversations/reembed` to backfill
- Dimensions auto-detected from model name; override with `EMBEDDING_DIMENSIONS`
- Both Python (`apps/api/ollama_client.py`) and TypeScript (`storage/postgres.ts`) use `EMBEDDING_PROVIDER` config
- pgvector index: **no ANN index** on `conversation_embeddings` (pgvector 0.8 caps ivfflat/hnsw at 2000 dims for `vector`; exact cosine scan is used instead)

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

- Push to `main` or PR to `main` で CI 実行 (pnpm install → test → build)
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
# Inside the api container (docker compose exec api bash)
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
docker compose exec workspace pnpm typecheck
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

**"Ollama model not found"**: `docker compose exec ollama ollama pull bge-m3`

**"Database connection refused"**: `docker compose ps` (check health) then `docker compose restart`

**"Permission denied for Application Support"**:
```bash
mkdir -p "$HOME/Library/Application Support/mindbase/conversations"
```

## Execution Mode

Default mode is **operator**, not advisor. Prioritize action (edit, execute, test) over explanation. See `AGENTS.md` for detailed execution rules.
