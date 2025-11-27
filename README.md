# MindBase – Local Memory Substrate for AIRIS MCP

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Docker](https://img.shields.io/badge/docker-ready-blue.svg)](https://www.docker.com/)

> **100 % local, zero vendor lock-in.** PostgreSQL 17 + pgvector + FastAPI + Ollama (qwen3-embedding:8b). No API keys, no hosted dependencies, completely free to run on your own machine.

## 🌟 Part of the AIRIS Ecosystem

MindBase is the **memory substrate** of the **AIRIS Suite** - providing persistent, semantic conversation history across all AI coding assistants.

### The AIRIS Suite

| Component | Purpose | For Who |
|-----------|---------|---------|
| **[airis-agent](https://github.com/agiletec-inc/airis-agent)** | 🧠 Intelligence layer for all editors (confidence checks, deep research, self-review) | All developers using Claude Code, Cursor, Windsurf, Codex, Gemini CLI |
| **[airis-mcp-gateway](https://github.com/agiletec-inc/airis-mcp-gateway)** | 🚪 Unified MCP proxy with 90% token reduction via lazy loading | Claude Code users who want faster startup |
| **mindbase** (this repo) | 💾 Local cross-session memory with semantic search | Developers who want persistent conversation history |
| **[airis-workspace](https://github.com/agiletec-inc/airis-workspace)** | 🏗️ Docker-first monorepo manager | Teams building monorepos |
| **[airiscode](https://github.com/agiletec-inc/airiscode)** | 🖥️ Terminal-first autonomous coding agent | CLI-first developers |

### MCP Servers (Included via Gateway)

- **[airis-mcp-supabase-selfhost](https://github.com/agiletec-inc/airis-mcp-supabase-selfhost)** - Self-hosted Supabase MCP with RLS support
- **mindbase** (this repo) - Memory search & storage tools (`mindbase_search`, `mindbase_store`)

### Recommended: Install via AIRIS MCP Gateway

MindBase comes **pre-configured** with AIRIS MCP Gateway. No additional setup required.

```bash
# Install the Gateway (includes MindBase)
brew install agiletec-inc/tap/airis-mcp-gateway

# Start the gateway
airis-mcp-gateway up

# Add to Claude Code
claude mcp add --transport http airis-mcp-gateway http://api.gateway.localhost:9400/api/v1/mcp
```

### Alternative: Standalone Installation

If you need to run MindBase independently:

```bash
git clone https://github.com/agiletec-inc/mindbase.git ~/github/mindbase
cd ~/github/mindbase && make up
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
3. **Semantic memory** – Messages are embedded locally through Ollama’s qwen3-embedding:8b model and stored in pgvector. MindBase becomes the long-term recall layer for AIRIS tools, MCP servers, or any downstream automation.
4. **Local-first privacy** – Conversations reside only inside your Dockerized PostgreSQL volume. Nothing writes to `~/Library/Application Support` or remote services, so your chat history never leaks into cloud sync folders.

## Architecture overview

```
┌──────────────────────────────────────────────────────────────────────────┐
│ Menubar App (Electron) ✨ NEW: Auto-Collection                           │
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
│  - Embedding vectors (1024‑dim)                                          │
└───────────────┬──────────────────────────────────────────────────────────┘
                │ local embedding calls
                ▼
┌──────────────────────────────────────────────────────────────────────────┐
│ Ollama (qwen3-embedding:8b)                                              │
│  - Fully on-device                                                       │
│  - Runs free of charge                                                   │
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

```bash
# 1. Clone (adjust the destination if needed)
git clone https://github.com/kazukinakai/mindbase.git ~/github/mindbase
cd ~/github/mindbase

# 2. Copy environment defaults
cp .env.example .env

# 3. Boot Postgres + API + (optional) Ollama container
make up

# 4. Download the embedding model once (~5–10 minutes)
make model-pull

# 5. Apply database migrations
make migrate

# 6. Check service health
make health  # API lives at http://localhost:18002

# 7. (Optional) Run the raw derivation worker
make worker
```

All conversation data lives in the PostgreSQL volume declared in `docker-compose.yml` (`postgres_data_dev`). Remove that volume when you want a clean slate; nothing is written to random App Support folders.

### Menu bar companion ✨ Auto-Collection

A lightweight Electron menu bar app that **automatically collects AI conversations** from Claude Code, Cursor, Windsurf, and ChatGPT. It monitors conversation directories and triggers collectors on file changes.

**Features:**
- **Auto-Collection Toggle**: Enable/disable via menu bar (✓ Auto-Collection Enabled)
- **File System Watcher**: Monitors `~/.claude/`, `~/.cursor/`, `~/Library/Application Support/Windsurf/`, etc.
- **Auto-Collector Execution**: Runs Python collectors when new conversations are detected
- **Health Monitoring**: Shows API, database, and Ollama status (🟢🟡🔴)
- **Quick Commands**: One-click `make up/down/logs/worker`

**Setup:**
```bash
cd apps/menubar
pnpm install   # first run only
pnpm dev       # or from root: pnpm dev:menubar
```

Look for the MindBase icon in your macOS menu bar. Click **"Auto-Collection Disabled"** to toggle ON. The watcher will start monitoring conversation directories and automatically run collectors when new files are detected.

Use **Settings…** to update the API base URL, workspace root, repository path, and custom collector definitions (changes sync to API via `/settings` endpoint).

## API reference

**Store a conversation**

```bash
curl -X POST http://localhost:18002/conversations/store \
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
curl -X POST http://localhost:18002/conversations/search \
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

- **AIRIS MCP Gateway** – Run `make install` inside the AIRIS repo (or `superclaude install`) to expose `mindbase_search` and `mindbase_store`. The gateway advertises only the selected tool to the LLM, keeping prompts minimal while MindBase delivers embeddings and payloads on demand.
- **Collectors (`collectors/`)** – Python scripts and templates that read local caches (Claude, Cursor, ChatGPT, Windsurf, etc.), normalize them, and push JSON to `/conversations/store`. Extend them to cover any other assistant or internal agent you run.
- **Processors & Generators (`libs/`)** – TypeScript utilities that transform stored conversations into knowledge packs, retrospectives, or other artifacts. They demonstrate how MindBase can power downstream workflows.
- **Schema & migrations (`supabase/`)** – SQL migrations for PostgreSQL live here so the same schema can be applied locally (via Docker) or to a managed Postgres instance. There is no hosted Supabase dependency; the directory simply keeps schema history tidy.

## Data residency & privacy

- Conversations, embeddings, and metadata stay inside the Docker-managed Postgres volume. Stop the stack with `make down` and the data remains encrypted on disk via PostgreSQL.
- All embeddings are generated locally through Ollama, so you never leak prompts or code to third-party APIs.
- If you need off-device backups, dump the database (`pg_dump`) or replicate the Docker volume; there is no hidden shadow copy under `~/Library/Application Support`.

## Roadmap highlights

- More collectors for enterprise chat / ticketing tools.
- Automated summarization and recap views for long-running projects.
- MCP-side incremental recall so AIRIS can page in only the slices of memory that the LLM asks for.
- Fine-grained retention and redaction policies per source.
- Export pipelines that turn curated threads into blogs, books, or playbooks.

## Contributing

1. Fork the repo and create a feature branch.
2. Follow the style guides in `docs/`, `AGENTS.md`, and `CLAUDE.md`.
3. Run the validations before opening a PR:
   ```bash
   make lint
   make health
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
- **[neural](https://github.com/agiletec-inc/neural)** - Local LLM translation tool (DeepL alternative)
- **[airiscode](https://github.com/agiletec-inc/airiscode)** - Terminal-first autonomous coding agent

---

## 💖 Support This Project

If you find MindBase helpful, consider supporting its development:

[![Buy Me A Coffee](https://img.shields.io/badge/Buy%20Me%20A%20Coffee-support-yellow?style=for-the-badge&logo=buy-me-a-coffee)](https://buymeacoffee.com/kazukinakad)
[![GitHub Sponsors](https://img.shields.io/badge/GitHub%20Sponsors-sponsor-pink?style=for-the-badge&logo=github)](https://github.com/sponsors/kazukinakai)

Your support helps maintain and improve all AIRIS projects!

---

## License

MindBase is released under the [MIT License](LICENSE).

---

**Built with ❤️ by the [Agiletec](https://github.com/agiletec-inc) team**

**[Agiletec Inc.](https://github.com/agiletec-inc)** | **[Documentation](docs/)** | **[Issues](https://github.com/agiletec-inc/mindbase/issues)** | **[Discussions](https://github.com/agiletec-inc/mindbase/discussions)**
