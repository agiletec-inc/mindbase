FROM node:24-slim

WORKDIR /app

# Install pnpm
RUN corepack enable

# Copy workspace config
COPY package.json pnpm-lock.yaml pnpm-workspace.yaml .npmrc* ./

# Copy package.json files for dependency resolution
COPY apps/cli/package.json apps/cli/
COPY apps/mcp-server/package.json apps/mcp-server/
COPY libs/generators/package.json libs/generators/

# Install dependencies
RUN pnpm install --frozen-lockfile

# Copy source
COPY . .

ENTRYPOINT ["npx", "tsx", "apps/cli/index.ts"]
