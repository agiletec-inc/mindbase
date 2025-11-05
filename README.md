# MindBase – Local Memory Substrate for AIRIS MCP

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Docker](https://img.shields.io/badge/docker-ready-blue.svg)](https://www.docker.com/)

> **100 % local, zero vendor lock-in.** PostgreSQL 17 + pgvector + FastAPI + Ollama (qwen3-embedding:8b). No API keys, no hosted dependencies, completely free to run on your own machine.

## Position in the AIRIS stack

MindBase is the durable conversation memory service that the AIRIS MCP Gateway taps into. AIRIS acts as the gateway and tool orchestrator, while MindBase focuses on storing and retrieving conversations with semantic recall. That separation keeps responsibilities crisp:

- **AIRIS MCP Gateway** – registers any MCP server (including MindBase), handles the “tool roster” problem by lazily streaming tool descriptions to the LLM, and keeps overall context windows under control.
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
```

All conversation data lives in the PostgreSQL volume declared in `docker-compose.yml` (`postgres_data_dev`). Remove that volume when you want a clean slate; nothing is written to random App Support folders.

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

## License

MindBase is released under the [MIT License](LICENSE).
