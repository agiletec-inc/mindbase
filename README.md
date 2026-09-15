# MindBase – Local Memory Substrate for AIRIS MCP

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Docker](https://img.shields.io/badge/docker-ready-blue.svg)](https://www.docker.com/)

> **Local-first, zero vendor lock-in.** PostgreSQL 17 + pgvector + FastAPI + Ollama (default `bge-m3`, switchable to catalog models such as `qwen3-embedding:8b` and `mxbai-embed-large`). OpenAI Embeddings is also supported as an explicit provider option.

## 🌟 Part of the AIRIS Ecosystem

MindBase is the **memory substrate** of the **AIRIS Suite** - providing persistent, semantic conversation history across all AI coding assistants. See the full [AIRIS Suite](https://github.com/agiletec-inc) on the org page.

### MCP Servers (Included via Gateway)

- **[airis-mcp-supabase-selfhost](https://github.com/agiletec-inc/airis-mcp-supabase-selfhost)** - Self-hosted Supabase MCP with RLS support
- **mindbase** (this repo) - Memory search & storage tools (`mindbase_search`, `mindbase_store`)

### Recommended: Install via AIRIS MCP Gateway

MindBase comes **pre-configured** with AIRIS MCP Gateway. No additional setup required.

```bash
# One command installs everything
curl -fsSL https://raw.githubusercontent.com/agiletec-inc/airis-mcp-gateway/main/scripts/quick-install.sh | bash
```

### Alternative: Standalone Installation

If you need to run MindBase independently:

```bash
git clone https://github.com/agiletec-inc/mindbase.git ~/github/mindbase
cd ~/github/mindbase
cp .env.example .env && uv sync --all-packages && docker compose up -d postgres
uv run python -m uvicorn apps.api.main:app --reload --port 18003   # see Quick start below
```

**What you get with the full suite:**
- ✅ Confidence-gated workflows (prevents wrong-direction coding)
- ✅ Deep research with evidence synthesis
- ✅ 94% token reduction via repository indexing
- ✅ Cross-session memory across all editors
- ✅ Self-review and post-implementation validation

---

## Position in the AIRIS stack

MindBase is the durable conversation memory service that the AIRIS MCP Gateway taps into. AIRIS acts as the gateway and tool orchestrator, while MindBase focuses on storing and retrieving conversations with semantic recall. That separation keeps responsibilities crisp:

- **AIRIS MCP Gateway** – registers any MCP server (including MindBase), handles the "tool roster" problem by lazily streaming tool descriptions to the LLM, and keeps overall context windows under control.
- **MindBase** – provides the `mindbase_search` and `mindbase_store` MCP tools plus an HTTP API. It runs as a Mac-friendly Docker stack so your editors, agents, and AIRIS can persist or query conversations without touching the cloud.

Because AIRIS only loads tool instructions when the model actually chooses MindBase, you avoid the hot-load issue where twenty richly documented tools explode the prompt budget. MindBase simply exposes concise capabilities; AIRIS decides when and how to surface them.

## Core capabilities

1. **Unified timeline** – Collectors pull logs from editors, desktop clients, terminal agents, and any bespoke transcripts. Everything lands in one ordered ledger so you can replay how a project evolved across assistants.
2. **Project & topic intelligence** – Stored metadata keeps conversations grouped by project, topic, and source. You can trace a task from brainstorming in Claude Desktop to implementation inside Cursor without manual tagging.
3. **Semantic memory** – Messages are embedded through the configured provider (Ollama by default; OpenAI is optional) and stored in pgvector. Vectors from different providers and models coexist per conversation, so you can re-embed and compare retrieval quality. MindBase becomes the long-term recall layer for AIRIS tools, MCP servers, or any downstream automation.
4. **Local-first privacy** – Conversations and embeddings are stored in the Dockerized PostgreSQL volume by default. The optional file-based memory backend stores Markdown memories under the configured `MEMORY_BASE_DIR` (by default `~/Library/Application Support/mindbase/memories`). No cloud sync is required.

## Architecture overview

```
┌──────────────────────────────────────────────────────────────────────────┐
│ Menubar App (Swift/SwiftUI) ✨ Auto-Collection                           │
│  - File system watcher (FSEvents) for conversation directories           │
│  - Auto-triggers collectors on new conversation detection                │
│  - Toggle: ✓ Auto-Collection Enabled                                    │
│  - Health monitoring with status indicators (🟢🟡🔴)                     │
└───────────────┬──────────────────────────────────────────────────────────┘
                │ Auto-runs Python collectors
                ▼
┌──────────────────────────────────────────────────────────────────────────┐
│ Collectors (Python)                                                      │
│  - Cursor / Windsurf / VS Code logs                                      │
│  - Claude Desktop / Claude Code exports                                  │
│  - ChatGPT / Gemini / terminal agent transcripts                         │
│  - Custom ingestion scripts (`collectors/`)                              │
└───────────────┬──────────────────────────────────────────────────────────┘
                │ JSON payloads → /conversations/store
                ▼
┌──────────────────────────────────────────────────────────────────────────┐
│ MindBase FastAPI (`apps/api`)                                            │
│  - POST /conversations/store                                             │
│  - POST /conversations/search                                            │
│  - GET  /health                                                          │
└───────────────┬──────────────────────────────────────────────────────────┘
                │ SQL + vector writes
                ▼
┌──────────────────────────────────────────────────────────────────────────┐
│ PostgreSQL 17 + pgvector (Docker volume `postgres_data_dev`)             │
│  - Structured metadata (projects, topics, sources, timestamps)           │
│  - Embedding vectors (768 / 1024 / 3072 / 4096‑dim buckets)              │
└───────────────┬──────────────────────────────────────────────────────────┘
                │ configured embedding provider (Ollama by default)
                ▼
┌──────────────────────────────────────────────────────────────────────────┐
│ Ollama (default bge-m3 · switchable model)                               │
│  - Fully on-device by default                                            │
│  - Optional OpenAI Embeddings provider                                   │
└───────────────┬──────────────────────────────────────────────────────────┘
                │ MCP tool bridge
                ▼
┌──────────────────────────────────────────────────────────────────────────┐
│ AIRIS MCP Gateway                                                        │
│  - Registers MindBase tools                                              │
│  - Streams tool descriptions lazily to LLMs                              │
│  - Keeps prompt context efficient                                        │
└──────────────────────────────────────────────────────────────────────────┘
```

## Quick start

Requirements: Docker (OrbStack works), [uv](https://docs.astral.sh/uv/), and
[Ollama](https://ollama.com) for the default local provider. The quick start runs
the API on the host and PostgreSQL in Docker; `compose.yml` also includes optional
container services for the API and Ollama.

```bash
# 1. Clone (adjust the destination if needed)
git clone https://github.com/agiletec-inc/mindbase.git ~/github/mindbase
cd ~/github/mindbase

# 2. Copy environment defaults
cp .env.example .env

# 3. Install Python deps into one workspace venv (uv reads .python-version → 3.12)
uv sync --all-packages

# 4. Pull the default local embedding model once into your host Ollama
ollama pull bge-m3

# 5. Start Postgres (pgvector). Migrations in supabase/migrations/ apply
#    automatically on first volume init.
docker compose up -d postgres

# 6. Run the API on the host (talks to the host Ollama over localhost)
uv run python -m uvicorn apps.api.main:app --reload --port 18003

# 7. Check health (in another shell)
curl -fsS http://localhost:18003/health   # → ok ; interactive docs at /docs

# 8. (Optional) Run the raw derivation worker
uv run python -m apps.api.workers.raw_deriver
```

Conversation records and embeddings live in the PostgreSQL volume declared in
`compose.yml` (`postgres_data_dev`). The MCP file-based memory backend may also
write Markdown memories to `MEMORY_BASE_DIR`. Remove the PostgreSQL volume
(`docker compose down -v`) when you want a clean database.

### Menu bar companion ✨ Auto-Collection

A lightweight native **Swift / SwiftUI** menu bar app that **automatically collects AI conversations** from Claude Code, Cursor, Windsurf, and ChatGPT. It monitors conversation directories and triggers collectors on file changes.

**Features:**
- **Auto-Collection Toggle**: Enable/disable via menu bar (✓ Auto-Collection Enabled)
- **File System Watcher**: Monitors `~/.claude/`, `~/.cursor/`, `~/Library/Application Support/Windsurf/`, etc.
- **Auto-Collector Execution**: Runs Python collectors when new conversations are detected
- **Health Monitoring**: Shows API, database, and Ollama status (🟢🟡🔴)
- **Quick Commands**: One-click `docker compose up -d postgres` / API start / logs

**Setup:**
```bash
# Homebrew (recommended)
brew tap agiletec-inc/tap
brew install mindbase-menubar

# Or build from source — see apps/menubar-swift/README.md
```

Look for the MindBase icon in your macOS menu bar. Click **"Auto-Collection Disabled"** to toggle ON. The watcher will start monitoring conversation directories and automatically run collectors when new files are detected.

Use **Settings…** to update the API base URL, workspace root, repository path, and custom collector definitions (changes sync to API via `/settings` endpoint).

## API reference

**Store a conversation**

```bash
curl -X POST http://localhost:18003/conversations/store \
  -H "Content-Type: application/json" \
  -d '{
    "source": "cursor",
    "title": "Fix flaky CI pipeline",
    "project": "platform",
    "topic": "deployments",
    "occurred_at": "2025-10-30T08:45:00Z",
    "content": {
      "messages": [
        {"role": "user", "content": "Why is the staging deploy stuck?"},
        {"role": "assistant", "content": "Investigating build logs..."}
      ]
    },
    "metadata": {
      "editor": "Cursor",
      "branch": "fix-staging-deploy"
    }
  }'
```

**Run a semantic search**

```bash
curl -X POST http://localhost:18003/conversations/search \
  -H "Content-Type: application/json" \
  -d '{
    "query": "autonomous PM agent reflection pattern",
    "limit": 8,
    "threshold": 0.75,
    "source": "all",
    "project": "superclaude"
  }'
```

Responses include similarity scores, timestamps, metadata, and the original messages so AIRIS (or any client) can immediately cite the relevant history.

## Integrations & tooling

- **AIRIS MCP Gateway** – Run `make install` inside the AIRIS repo (or `superclaude install`) to expose MindBase's conversation, memory, semantic search, hybrid search, and retrieval-pack tools. The gateway advertises only the selected tool to the LLM, keeping prompts minimal while MindBase delivers embeddings and payloads on demand.
- **Chat RAG API** – `POST /api/chat` retrieves relevant past conversations with the active embedding provider, adds them to the system context, streams an Ollama chat response, and optionally persists the completed turn.
- **Collectors (`collectors/`)** – Python scripts and templates that read local caches (Claude, Cursor, ChatGPT, Windsurf, etc.), normalize them, and push JSON to `/conversations/store`. Extend them to cover any other assistant or internal agent you run.
- **Processors & Generators (`libs/`)** – TypeScript utilities that transform stored conversations into knowledge packs, retrospectives, or other artifacts. The MCP retrieval-pack tool budgets excerpts and source metadata for downstream writing workflows.
- **Schema & migrations (`supabase/`)** – SQL migrations for PostgreSQL live here so the same schema can be applied locally (via Docker) or to a managed Postgres instance. There is no hosted Supabase dependency; the directory simply keeps schema history tidy.

## Data residency & privacy

- Conversations, embeddings, and metadata stay inside the Docker-managed Postgres volume by default. Stop the stack with `docker compose down` and the data remains on disk in the `postgres_data_dev` volume.
- Ollama is the default local embedding provider. If `EMBEDDING_PROVIDER=openai` is selected, embedding inputs are sent to the OpenAI Embeddings API according to that provider configuration.
- The optional MCP file-based memory backend stores Markdown memories under `MEMORY_BASE_DIR`; this is separate from the conversation store.
- If you need off-device backups, dump the database (`pg_dump`) or replicate the Docker volume.

## Roadmap highlights

- More collectors for enterprise chat / ticketing tools.
- Automated Japanese summarization and recap views for long-running projects.
- MCP-side incremental recall so AIRIS can page in only the slices of memory that the LLM asks for.
- Fine-grained retention and redaction policies per source.
- Export pipelines that turn curated threads into blogs, books, or playbooks.

## Contributing

1. Fork the repo and create a feature branch.
2. Follow the style guides in `docs/`, `AGENTS.md`, and `CLAUDE.md`.
3. Run the validations before opening a PR:
   ```bash
   uv run pytest tests/ -v
   uv run black --check apps/api/ libs/collectors/ && uv run ruff check apps/api/ libs/collectors/
   pnpm lint
   ```
4. Open the PR with a Conventional Commit title, describe the change, list the commands you ran, and attach API traces or screenshots when relevant.

---

## 🔗 Related Projects

Explore other tools in the AIRIS ecosystem:

- **[airis-mcp-gateway](https://github.com/agiletec-inc/airis-mcp-gateway)** - Unified MCP hub with 90% token reduction
- **[airis-agent](https://github.com/agiletec-inc/airis-agent)** - Intelligence layer for AI coding (confidence checks, deep research)
- **[airis-mcp-supabase-selfhost](https://github.com/agiletec-inc/airis-mcp-supabase-selfhost)** - Self-hosted Supabase MCP with RLS support
- **[airis-workspace](https://github.com/agiletec-inc/airis-workspace)** - Docker-first monorepo manager
- **[cmd-ime](https://github.com/agiletec-inc/cmd-ime)** - macOS IME switcher (Cmd key toggle)
- **[airis-translate](https://github.com/agiletec-inc/airis-translate)** - Local LLM translation tool (DeepL alternative)
- **[airiscode](https://github.com/agiletec-inc/airiscode)** - Terminal-first autonomous coding agent

---

## License

MindBase is released under the [MIT License](LICENSE).

## 💖 Support

[agiletec](https://github.com/agiletec-inc) is a one-person studio building these tools full-time and open source. If they earn a spot in your workflow, a sponsorship keeps them maintained and independent.

[![Sponsor agiletec](https://img.shields.io/badge/Sponsor-agiletec-ea4aaa?logo=githubsponsors&logoColor=white)](https://github.com/sponsors/agiletec-inc)

---

**Built with ❤️ by the [Agiletec](https://github.com/agiletec-inc) team**

**[Agiletec Inc.](https://github.com/agiletec-inc)** | **[Documentation](docs/)** | **[Issues](https://github.com/agiletec-inc/mindbase/issues)** | **[Discussions](https://github.com/agiletec-inc/mindbase/discussions)**
