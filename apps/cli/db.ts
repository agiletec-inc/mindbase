/**
 * Database connection helper for CLI commands.
 * Reuses PostgresStorageBackend from MCP server.
 */

import { PostgresStorageBackend } from '../mcp-server/storage/postgres.js';

export function createStorage(): PostgresStorageBackend {
  const dbUrl = process.env.DATABASE_URL;
  const ollamaUrl = process.env.OLLAMA_URL;
  const model = process.env.EMBEDDING_MODEL;

  if (!dbUrl) {
    console.error('ERROR: DATABASE_URL is required');
    process.exit(1);
  }
  if (!ollamaUrl) {
    console.error('ERROR: OLLAMA_URL is required');
    process.exit(1);
  }
  if (!model) {
    console.error('ERROR: EMBEDDING_MODEL is required');
    process.exit(1);
  }

  return new PostgresStorageBackend(dbUrl, ollamaUrl, model);
}
