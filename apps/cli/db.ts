/**
 * Database connection helper for CLI commands.
 * Reuses PostgresStorageBackend from MCP server.
 */

import { PostgresStorageBackend } from '../mcp-server/storage/postgres.js';
import { createStorageClients, loadConfig } from '../mcp-server/config.js';

export function createStorage(): PostgresStorageBackend {
  const { pool, embeddingClient } = createStorageClients(loadConfig());
  return new PostgresStorageBackend(pool, embeddingClient);
}
