# MindBase Monorepo Structure

## Overview
MindBase is now a **pnpm monorepo** with clear separation between deployable apps and shared libraries.

## Structure
```
mindbase/
├── apps/                   # Deployable applications
│   ├── api/                # FastAPI backend (Python)
│   ├── mcp-server/         # MCP Server (TypeScript)
│   ├── settings/           # Settings UI (React + Vite + Tailwind)
│   └── cli/                # CLI tools (future)
├── libs/                   # Shared libraries
│   ├── collectors/         # Python conversation collectors
│   ├── processors/         # TypeScript content processors
│   ├── generators/         # TypeScript article generators
│   └── shared/             # Shared types and utilities
├── packages/               # Infrastructure packages
│   └── database/           # PostgreSQL migrations + schemas
├── docs/                   # Documentation
└── tests/                  # End-to-end tests
```

## Package Naming Convention
- **apps**: `@mindbase/[app-name]` (e.g., `@mindbase/settings`, `@mindbase/mcp-server`)
- **libs**: `@mindbase/[lib-name]` (e.g., `@mindbase/processors`, `@mindbase/collectors`)
- **packages**: `@mindbase/[package-name]` (e.g., `@mindbase/database`)

## Development Commands

### Root-level (run from `/Users/kazuki/github/mindbase/`)
```bash
# Install all dependencies
pnpm install

# Run Settings UI
pnpm dev

# Run FastAPI backend
pnpm dev:api

# Run MCP server
pnpm dev:mcp

# Build all packages
pnpm build

# Type check all TypeScript packages
pnpm typecheck

# Lint all packages
pnpm lint

# Test all packages
pnpm test
```

### Package-specific (using --filter)
```bash
# Run Settings UI dev server
pnpm --filter @mindbase/settings dev

# Build MCP server
pnpm --filter @mindbase/mcp-server build

# Run processors
pnpm --filter @mindbase/processors extract
```

## Technology Stack

### Apps
- **api**: FastAPI + PostgreSQL + pgvector + Ollama
- **mcp-server**: TypeScript + MCP SDK + PostgreSQL
- **settings**: React 19 + Vite + Tailwind CSS + i18n

### Libs
- **collectors**: Python (async, dataclasses)
- **processors**: TypeScript (tsx runtime)
- **generators**: TypeScript (tsx runtime)

## Architecture Principles
- **Local-First**: All data stored locally, no cloud dependencies
- **Privacy-Focused**: Sensitive LLM conversations never leave your machine
- **Monorepo**: Shared code reuse, consistent tooling
- **TypeScript + Python**: Best tool for each job

## Migration Notes
### Old Paths → New Paths
```
app/                → apps/api/
src/mcp-server/     → apps/mcp-server/
collectors/         → libs/collectors/
src/processors/     → libs/processors/
src/generators/     → libs/generators/
supabase/           → packages/database/
```

### Removed Dependencies
- ❌ Firebase (cloud service, privacy violation)
- ❌ Stripe (monetization undecided)
- ❌ Supabase Client (using raw PostgreSQL instead)

## Future Plans
- **Tauri Integration**: Convert to Mac menu bar app
- **apps/cli**: Unified CLI for all operations
- **libs/shared**: Shared TypeScript/Python types
- **Turborepo**: Optional build caching for faster CI/CD

## License
MIT (for self-hosted)
Commercial License (for cloud-hosted AgileTeC version)
