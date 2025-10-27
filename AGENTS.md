# Repository Guidelines

## Project Structure & Module Organization
- `apps/api/` contains the FastAPI service, shared schemas, and database access code that powers the REST API.
- `libs/` hosts TypeScript processors and generators (`libs/processors`, `libs/generators`), while `packages/` holds reusable workspace modules.
- `collectors/` captures platform-specific ingestion scripts; keep new collectors Pythonic and colocated with related assets.
- `supabase/` stores SQL migrations and Edge Functions; run every schema adjustment through this tree.
- `scripts/` provides operational helpers (archive, optimize, research). Treat them as the single source for repetitive CLI flows.
- Tests live in `tests/{unit,integration,e2e}` for Python coverage and under package-specific folders for TypeScript utilities.
- Details on raw conversation storage formats and ingestion rules live in `docs/conversation-data-sources.md`.

## Build, Test, and Development Commands
- `pnpm install` syncs the Turborepo-style workspace; rerun after dependency edits.
- `make up` boots PostgreSQL, the API, and Ollama; use `make down` or `make restart` to cycle services.
- `pnpm dev:api` and `pnpm dev:mcp` start hot-reload loops for the API and MCP server without Docker overhead.
- `make migrate` applies Supabase migrations and seeds; follow with `make health` to verify container orchestration.
- `pnpm build`, `pnpm typecheck`, and `pnpm lint` ensure the TypeScript side compiles, types, and lints cleanly.

## Coding Style & Naming Conventions
- TypeScript files use two-space indentation, ESLint/Prettier via `pnpm lint`, camelCase for functions, and PascalCase for exported classes.
- Python modules prefer snake_case filenames, `black` for formatting, `ruff` for linting (`ruff check collectors/ apps/api/`), and `mypy` for type coverage.
- Keep environment-specific configuration in `.env`; avoid hardcoded URLs—inject via `config/` or the settings service.

## Testing Guidelines
- `make test` runs the full battery (unit, integration, e2e) inside containers; scope with `make test-unit`, `make test-integration`, or `make test-e2e`.
- For quick API checks, enter `make api-shell` and run `pytest tests/unit -v`; target files with `pytest tests/unit/test_routes.py::TestHealth`.
- TypeScript libraries rely on workspace tests (`pnpm test`); colocate specs alongside sources as `*.test.ts` for Vitest discovery.
- Generate coverage with `make test-cov`; upload or attach the HTML summary when validating complex changes.

## Commit & Pull Request Guidelines
- Follow Conventional Commits (`feat:`, `fix:`, `docs:`) as seen in recent history (e.g., `feat: Complete monorepo migration and fix embedding model`).
- Every PR should summarize the change, list validation commands (`make test`, `pnpm lint`), and link related issues or roadmap items.
- Include screenshots or API responses when UI or endpoint behavior changes, and note any new environment variables or migrations.
- Keep branches rebased on `main` before review and ensure generated artifacts (`generated/`, `modules/`) stay out of commits unless explicitly required.

## Security & Configuration Tips
- Duplicate `.env.example` to `.env`, adjusting service credentials locally; never commit secret overrides.
- Persistent data resides in `~/Library/Application Support/mindbase/`; verify backups when touching archive or migration logic.
- When extending collectors or processors, validate inputs against unexpected payloads and prefer centralized config over inline credentials.
