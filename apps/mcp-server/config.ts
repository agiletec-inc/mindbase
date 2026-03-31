/**
 * MindBase MCP Server - Configuration
 *
 * Environment variable loading and validation.
 */

export interface MCPServerConfig {
  databaseUrl: string;
  ollamaUrl: string;
  embeddingModel: string;
  memoryBaseDir?: string;
  openaiApiKey?: string;
  openaiEmbeddingModel: string;
}

/**
 * Load and validate required environment variables.
 * Exits the process with a clear error message if any required vars are missing.
 */
export function loadConfig(): MCPServerConfig {
  const databaseUrl = process.env.DATABASE_URL;
  const ollamaUrl = process.env.OLLAMA_URL;
  const embeddingModel = process.env.EMBEDDING_MODEL;

  if (!databaseUrl || !ollamaUrl || !embeddingModel) {
    console.error('ERROR: Required environment variables not set:');
    if (!databaseUrl) console.error('  - DATABASE_URL');
    if (!ollamaUrl) console.error('  - OLLAMA_URL');
    if (!embeddingModel) console.error('  - EMBEDDING_MODEL');
    console.error('\nSee .env.example for required configuration.');
    process.exit(1);
  }

  return {
    databaseUrl,
    ollamaUrl,
    embeddingModel,
    memoryBaseDir: process.env.MEMORY_BASE_DIR,
    openaiApiKey: process.env.OPENAI_API_KEY || undefined,
    openaiEmbeddingModel: process.env.OPENAI_EMBEDDING_MODEL || 'text-embedding-3-large',
  };
}
