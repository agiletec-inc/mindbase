# MindBase Monorepo Restructuring Plan

## Current Structure (Messy)
```
mindbase/
├── app/                    # FastAPI backend
├── collectors/             # Python collectors
├── src/                    # TypeScript (MCP server, processors, generators)
├── scripts/                # Bash scripts
├── supabase/               # PostgreSQL migrations (not Supabase-specific)
├── apps/settings/          # React Settings UI
├── apps/                   # Empty parent
└── libs/                   # Empty parent
```

## Target Monorepo Structure
```
mindbase/
├── apps/
│   ├── api/                # FastAPI backend (from app/)
│   ├── mcp-server/         # MCP Server (from src/mcp-server/)
│   ├── settings/           # Settings UI (already exists)
│   └── cli/                # CLI tools (from scripts/)
├── libs/
│   ├── collectors/         # Python collectors (from collectors/)
│   ├── processors/         # TypeScript processors (from src/processors/)
│   ├── generators/         # TypeScript generators (from src/generators/)
│   └── shared/             # Shared types/utils
├── packages/
│   └── database/           # Migrations + schemas (from supabase/)
├── docs/                   # Documentation (keep)
├── tests/                  # Tests (keep)
├── pnpm-workspace.yaml     # Monorepo config
├── turbo.json              # Turborepo config (optional)
└── package.json            # Root package.json
```

## Migration Steps
1. Create monorepo structure
2. Move app/ → apps/api/
3. Move src/mcp-server/ → apps/mcp-server/
4. Move collectors/ → libs/collectors/
5. Move src/processors/ → libs/processors/
6. Move src/generators/ → libs/generators/
7. Move supabase/ → packages/database/
8. Move scripts/ → apps/cli/
9. Update import paths
10. Configure pnpm workspace
11. Test builds

## Benefits
- Clear separation: apps (deployable) vs libs (shared code)
- Easier dependency management
- Better code reusability
- Simpler CI/CD pipelines
