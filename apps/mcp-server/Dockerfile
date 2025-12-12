FROM node:24-alpine AS builder

WORKDIR /app

# Copy package files
COPY package.json ./

# Install all dependencies (including devDependencies for build)
RUN npm install

# Copy source
COPY . .

# Build TypeScript
RUN npm run build

# Production stage
FROM node:24-alpine

WORKDIR /app

# Default environment variables for MCP gateway
ENV DATABASE_URL="postgresql://mindbase:mindbase@mindbase-postgres-dev:5432/mindbase"
ENV OLLAMA_URL="http://host.docker.internal:11434"
ENV EMBEDDING_MODEL="nomic-embed-text"

COPY package.json ./
RUN npm install --omit=dev

COPY --from=builder /app/dist ./dist

ENTRYPOINT ["node", "dist/index.js"]
