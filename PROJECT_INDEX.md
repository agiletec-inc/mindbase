# Project Index: MindBase

**Generated:** 2025-11-13
**Version:** 1.1.0
**Description:** AI Conversation Knowledge Management - Local-First, Privacy-Focused

---

## 📁 Project Structure

```
mindbase/
├── apps/                    # Deployable applications
│   ├── api/                # FastAPI backend (Python)
│   ├── mcp-server/         # MCP Server (TypeScript)
│   ├── settings/           # Settings UI (React + Vite)
│   ├── menubar/            # Menubar companion app (Electron)
│   └── cli/                # CLI application
├── libs/                    # Shared libraries
│   ├── collectors/         # Conversation collectors (Python)
│   ├── processors/         # Content processors (TypeScript)
│   ├── generators/         # Article generators (TypeScript)
│   └── shared/             # Shared utilities
├── packages/                # Infrastructure packages
│   └── database/           # PostgreSQL migrations & functions
├── tests/                   # Test suite
├── scripts/                 # Utility scripts
├── Formula/                 # Homebrew formula
└── docs/                    # Documentation

Code Stats:
- Python: ~5,000 LOC (FastAPI + Collectors)
- TypeScript: ~3,500 LOC (MCP Server + UI + Generators)
```

---

## 🚀 Entry Points

### Production (Homebrew)
- **CLI:** `mindbase` command (via Formula/mindbase.rb)
  - `mindbase setup` - Initialize database, pull Ollama models
  - `mindbase serve` - Start API server
  - `mindbase health` - Health check
  - `mindbase collect` - Collect conversations from AI platforms

### Development
- **API Server:** `apps/api/main.py` - FastAPI backend (port configured via env)
- **MCP Server:** `apps/mcp-server/index.ts` - Model Context Protocol server (stdio)
- **Settings UI:** `apps/settings/src/main.tsx` - React settings interface
- **Menubar App:** `apps/menubar/main.js` - Electron status monitor

### Scripts
- `scripts/collect-conversations.py` - Batch conversation collection
- `scripts/sync-daemon.py` - Background sync daemon
- `pnpm dev:api` - Run FastAPI in development mode
- `pnpm dev:mcp` - Run MCP server in development mode
- `pnpm dev` - Run Settings UI

---

## 📦 Core Modules

### API Layer (apps/api/)
- **main.py** - FastAPI application entry point
  - Exports: `app` (FastAPI instance)
  - Purpose: REST API server with CORS, health checks, route registration

- **config.py** - Application configuration
  - Exports: `Settings`, `get_settings()`
  - Purpose: Environment-based configuration (DATABASE_URL, OLLAMA_URL, etc.)

- **database.py** - Database engine
  - Exports: `engine`, `get_db()`, `init_db()`
  - Purpose: SQLAlchemy async engine with pgvector support

- **ollama_client.py** - Embedding generation
  - Exports: `OllamaClient`, `get_ollama_client()`
  - Purpose: Generate embeddings via Ollama (nomic-embed-text, 768-dim)

### API Routes (apps/api/api/routes/)
- **conversations.py** - Conversation CRUD + search
- **settings.py** - Shared settings API
- **control.py** - Control endpoints (start/stop workers)
- **embeddings.py** - Embedding generation endpoints
- **health.py** - Health check endpoint

### CRUD Operations (apps/api/crud/)
- **conversation.py** - Database operations for conversations
  - `create_conversation()`, `get_conversations()`, `search_conversations()`

### Services (apps/api/services/)
- **classifier.py** - Conversation classification (category/priority)
- **deriver.py** - Derive structured data from raw conversations
- **pipelines.py** - Processing pipeline orchestration
- **settings_store.py** - Persistent settings storage

### Workers (apps/api/workers/)
- **raw_deriver.py** - Background worker for raw conversation processing

### MCP Server (apps/mcp-server/)
- **index.ts** - MCP Server main entry (stdio transport)
  - Tools: conversation_save, conversation_get, conversation_search, conversation_delete
  - Tools: session_create, session_start, session_list, session_delete
  - Tools: memory_write, memory_read, memory_list, memory_delete, memory_search

### MCP Storage Backends (apps/mcp-server/storage/)
- **postgres.ts** - PostgreSQL + pgvector storage
  - Exports: `PostgresStorageBackend`
  - Purpose: Conversation storage with semantic search

- **memory-fs.ts** - Hybrid markdown + database storage
  - Exports: `FileSystemMemoryBackend`
  - Purpose: Human-readable markdown memories with database fallback

- **interface.ts** - Storage interface definitions
- **memory-interface.ts** - Memory storage interface

### MCP Tools (apps/mcp-server/tools/)
- **conversation.ts** - Conversation management tool handlers
- **memory.ts** - Memory management tool handlers (Serena-inspired)

### Collectors (libs/collectors/)
- **base_collector.py** - Abstract base class
  - Exports: `BaseCollector`, `Conversation`, `Message`
  - Purpose: Common validation, deduplication, checkpoint system

- **claude_collector.py** - Claude Desktop/Code conversations
- **chatgpt_collector.py** - ChatGPT conversations
- **cursor_collector.py** - Cursor AI conversations
- **windsurf_collector.py** - Windsurf conversations
- **data_normalizer.py** - Cross-platform normalization

### Processors (libs/processors/)
- **extract-modules.ts** - Topic classification and keyword extraction
  - Purpose: Extract topics, modules, keywords from conversations

### Generators (libs/generators/)
- **generate-article.ts** - Markdown article generation
  - Purpose: Generate blog articles from extracted topics

- **publish-qiita.ts** - Qiita API publishing
  - Purpose: Publish articles to Qiita platform

---

## 🔧 Configuration

**Environment Variables** (see `.env.example`):
- `DATABASE_URL` - PostgreSQL connection string (REQUIRED)
- `OLLAMA_URL` - Ollama API endpoint (REQUIRED)
- `EMBEDDING_MODEL` - Embedding model name (REQUIRED, default: nomic-embed-text)
- `EMBEDDING_DIMENSIONS` - Embedding dimensions (REQUIRED, default: 768)
- `API_PORT` - API server port (configured per environment)
- `DEBUG` - Debug mode (true/false)
- `MEMORY_BASE_DIR` - Memory storage directory
- `DERIVE_ON_STORE` - Auto-derive on conversation store (true/false)

**Build Configuration:**
- `package.json` - Root monorepo configuration (pnpm workspace)
- `pnpm-workspace.yaml` - Workspace package definitions
- `tsconfig.json` - Root TypeScript configuration
- `tsconfig.mcp.json` - MCP Server specific TypeScript config
- `docker-compose.yml` - Development environment (PostgreSQL, API)

**Production:**
- `Formula/mindbase.rb` - Homebrew formula for production install
- `.env` - Environment configuration (not in Git)

---

## 📚 Documentation

### Root Documentation
- **README.md** - Project overview, quick start
- **CLAUDE.md** - Claude Code instructions (project conventions, architecture)
- **ARCHITECTURE.md** - System architecture and design decisions
- **MONOREPO.md** - Monorepo migration guide (old→new path mappings)
- **INTEGRATION_PLAN.md** - Integration of dot-claude-optimizer + claude-blog-automation
- **INSTALL.md** - Installation instructions
- **ROADMAP.md** - Feature roadmap
- **CONTRIBUTING.md** - Contribution guidelines
- **SECURITY.md** - Security policy
- **CHANGELOG.md** - Version history
- **AGENTS.md** - AI agent workflows

### Research Documents (docs/research/)
- **serena_vs_mindbase_analysis_2025-10-19.md** - Comparison with Serena memory system
- **data-sources-research-2025-10-14.md** - Data source research

### Topic Documentation (docs/)
- **MEMORY_SYSTEM.md** - Memory system design (Serena-inspired)
- **AIRIS_MCP_INTEGRATION.md** - AIRIS MCP gateway integration
- **conversation-data-sources.md** - Conversation data source specifications
- **TASKS.md** - Development task tracking

---

## 🧪 Test Coverage

**Test Structure:**
- Unit tests: `pytest -m unit`
- Integration tests: `pytest -m integration`
- E2E tests: `pytest -m e2e`

**Test Files:**
- `tests/conftest.py` - Test configuration and fixtures
- `tests/test_health.py` - Health endpoint tests
- `tests/test_classifier.py` - Classification service tests
- `tests/test_settings_api.py` - Settings API tests
- `tests/test_control_api.py` - Control API tests
- `tests/integration/test_conversations.py` - Conversation CRUD tests

**Test Commands:**
```bash
make test              # All tests
make test-unit         # Unit tests only
make test-integration  # Integration tests only
make test-cov          # Coverage report
```

---

## 🔗 Key Dependencies

### Python (apps/api/)
- **FastAPI** - Modern async web framework
- **SQLAlchemy** - ORM with async support
- **pgvector** - PostgreSQL vector extension for semantic search
- **Pydantic** - Data validation and settings management
- **httpx** - Async HTTP client (Ollama communication)
- **pytest** - Testing framework
- **uvicorn** - ASGI server

### TypeScript (apps/mcp-server/, apps/settings/)
- **@modelcontextprotocol/sdk** (^1.20.0) - MCP protocol implementation
- **pg** (^8.16.3) - PostgreSQL client
- **pgvector** (^0.2.1) - Vector operations for PostgreSQL
- **uuid** (^13.0.0) - UUID generation
- **React** (^19) - UI framework (Settings app)
- **Vite** (^6) - Build tool
- **Tailwind CSS** (^3) - Styling
- **react-i18next** - Internationalization

### Infrastructure
- **PostgreSQL** (16+) - Primary database with pgvector extension
- **Ollama** - Local LLM inference (embeddings)
- **pnpm** - Monorepo package manager
- **Docker** - Development environment

---

## 📝 Quick Start

### Production Mode (Homebrew)
```bash
# Install
brew tap agiletec-inc/mindbase
brew install mindbase

# Setup (one-time)
mindbase setup

# Start service
mindbase serve              # Foreground
brew services start mindbase  # Background

# Health check
mindbase health
```

### Development Mode (Docker)
```bash
# Initial setup
make init                   # Start services + pull Ollama model + migrations

# Service management
make up                     # Start dev services
make down                   # Stop services
make health                 # Check health

# Development
make api-shell              # Enter FastAPI container
make db-shell               # PostgreSQL shell
make logs                   # View logs

# Testing
make test                   # Run all tests
make test-cov               # Coverage report
```

### Monorepo Workflows (pnpm)
```bash
# Development servers
pnpm dev                    # Settings UI
pnpm dev:api                # FastAPI backend
pnpm dev:mcp                # MCP Server

# Build and quality
pnpm build                  # Build all packages
pnpm typecheck              # Type check
pnpm lint                   # Lint all packages

# Content generation pipeline
pnpm extract                # Extract modules/topics
pnpm generate <category>    # Generate blog article
pnpm publish <file>         # Publish to Qiita
```

---

## 🏗️ Architecture Overview

**Hybrid Python/TypeScript Monorepo:**
- **Backend:** FastAPI (Python) - REST API, CRUD, embeddings
- **MCP Server:** TypeScript - Model Context Protocol integration
- **Collectors:** Python - Multi-platform conversation collection
- **Processors:** TypeScript - Content extraction and classification
- **Generators:** TypeScript - Blog article generation
- **UI:** React + Vite - Settings interface
- **Storage:** PostgreSQL + pgvector - Semantic search
- **Embeddings:** Ollama (nomic-embed-text, 768-dim)

**Data Separation:**
- **Source Code:** `~/github/mindbase/` (Git-tracked, Claude-readable)
- **Data:** `~/Library/Application Support/mindbase/` (Private, excluded from Git)
  - `conversations/` - Archived conversations by platform
  - `memories/` - Markdown-based memories (Serena-inspired)
  - `db/` - Database persistence

**Key Design Principles:**
1. **Environment-based configuration** - No hardcoded ports/URLs
2. **Modular architecture** - Apps (deployable) + Libs (shared)
3. **Privacy-first** - Local storage, no cloud dependencies
4. **Semantic search** - pgvector embeddings for knowledge retrieval
5. **Multi-platform** - Supports Claude, ChatGPT, Cursor, Windsurf

---

## 🎯 Use Cases

1. **Conversation Management**
   - Collect conversations from multiple AI platforms
   - Store with automatic embedding generation
   - Semantic search across conversation history

2. **Knowledge Extraction**
   - Extract topics, modules, keywords
   - Classify by category (task, decision, progress, etc.)
   - Track progress and decisions over time

3. **Content Generation**
   - Generate blog articles from conversations
   - Publish to Qiita/Zenn platforms
   - Automate technical writing workflow

4. **MCP Integration**
   - Claude Desktop/Windsurf/Cursor integration
   - Session management
   - Memory system (markdown + database hybrid)

5. **LLM Runaway Prevention**
   - Error/warning history tracking
   - Repeated mistake detection
   - Past solution suggestions

---

## 📊 Database Schema

**Key Tables:**
- `conversations` - Main conversation storage with pgvector embeddings
- `raw_conversations` - Append-only raw storage
- `sessions` - Session hierarchy and temporal tracking
- `memories` - Markdown-based memory storage (Serena-inspired)
- `thought_patterns` - Pattern extraction and analysis
- `book_structure` - Book/article structure generation

**Migrations:** `packages/database/migrations/` (formerly `supabase/migrations/`)

---

## 🔐 Security

- Environment-based secrets (never hardcoded)
- Local-first architecture (no cloud dependencies)
- Private data directory (excluded from Git)
- CORS configuration for API access
- Database connection pooling

See `SECURITY.md` for security policy.

---

## 🚦 Status

**Current Version:** 1.1.0
**Stability:** Production-ready
**Monorepo Migration:** ✅ Complete
**Next:** Enhanced classification, multi-tenant support

See `ROADMAP.md` for future plans.
