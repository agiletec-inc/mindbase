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
WORKDIR /app
RUN apt-get update && apt-get install -y \
    postgresql-client \
    curl \
    wget \
    jq \
    && rm -rf /var/lib/apt/lists/*
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY apps/api ./app
HEALTHCHECK --interval=30s --timeout=10s --start-period=40s --retries=3 \
  CMD wget --no-verbose --tries=1 --spider http://localhost:8000/health || exit 1
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
