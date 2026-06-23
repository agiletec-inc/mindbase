# ===========================================
# MindBase - Multi-stage Dockerfile
# ===========================================
# Usage: compose.yml の build.target で切り替え
#   workspace → Node.js dev shell (airis shell)
#   cli       → Content generation CLI
#   api       → FastAPI backend
# ===========================================

# --- Node.js workspace (dev shell) ---
FROM node:24-slim AS workspace
RUN corepack enable
WORKDIR /app
CMD ["sleep", "infinity"]

# --- CLI (content generation) ---
FROM node:24-slim AS cli
RUN corepack enable
WORKDIR /app
COPY package.json pnpm-lock.yaml pnpm-workspace.yaml .npmrc* ./
COPY apps/cli/package.json apps/cli/
COPY apps/mcp-server/package.json apps/mcp-server/
COPY libs/generators/package.json libs/generators/
RUN pnpm install --frozen-lockfile
COPY . .
ENTRYPOINT ["npx", "tsx", "apps/cli/index.ts"]

# --- FastAPI backend ---
FROM python:3.12-slim AS api
COPY --from=ghcr.io/astral-sh/uv:0.11.23 /uv /uvx /bin/
WORKDIR /app
# Keep the venv outside /app so a dev bind-mount of the source does not shadow it.
ENV UV_PROJECT_ENVIRONMENT=/opt/venv \
    UV_COMPILE_BYTECODE=1 \
    UV_LINK_MODE=copy \
    PATH=/opt/venv/bin:$PATH
RUN apt-get update && apt-get install -y \
    postgresql-client \
    curl \
    wget \
    jq \
    && rm -rf /var/lib/apt/lists/*
# Install workspace dependencies first. Members are package=false (deps only,
# not built), so the source tree is not needed at this layer — keeps cache warm.
COPY pyproject.toml uv.lock .python-version ./
COPY apps/api/pyproject.toml apps/api/
COPY libs/collectors/pyproject.toml libs/collectors/
RUN uv sync --all-packages --frozen --no-dev
# Application source — imported in place as `apps.api` / `libs.collectors`.
COPY apps ./apps
COPY libs ./libs
HEALTHCHECK --interval=30s --timeout=10s --start-period=40s --retries=3 \
  CMD wget --no-verbose --tries=1 --spider http://localhost:8000/health || exit 1
CMD ["python", "-m", "uvicorn", "apps.api.main:app", "--host", "0.0.0.0", "--port", "8000"]
