/**
 * status command — Check service status and database stats.
 *
 * Usage: mindbase status
 */

import { createStorage } from '../db.js';

export async function run() {
  const storage = createStorage();

  console.log('MindBase Status\n');

  // Database connection
  try {
    const total = await storage.count({});
    console.log(`  Database:     connected`);
    console.log(`  Conversations: ${total}`);

    // Count by source
    const sources = ['claude-code', 'claude-desktop', 'chatgpt', 'cursor', 'windsurf', 'gemini'];
    const counts: string[] = [];

    for (const source of sources) {
      const count = await storage.count({ source });
      if (count > 0) {
        counts.push(`${source}: ${count}`);
      }
    }

    if (counts.length > 0) {
      console.log(`  By source:     ${counts.join(', ')}`);
    }
  } catch (err) {
    const msg = err instanceof Error ? err.message : String(err);
    console.error(`  Database:     ERROR - ${msg}`);
  }

  // Embedding provider
  const openaiKey = process.env.OPENAI_API_KEY;
  const ollamaUrl = process.env.OLLAMA_URL;
  const model = process.env.EMBEDDING_MODEL;

  console.log(`\n  Embeddings:    ${openaiKey ? 'OpenAI (primary)' : 'Ollama only'}`);
  console.log(`  Ollama:        ${ollamaUrl || 'not configured'}`);
  console.log(`  Model:         ${model || 'not configured'}`);

  // LLM for generation
  console.log(`  LLM:           ${openaiKey ? `OpenAI ${process.env.LLM_MODEL || 'gpt-4o'}` : 'not configured (OPENAI_API_KEY required)'}`);

  // Publishing credentials
  console.log(`\n  Publishers:`);
  console.log(`    note:  ${process.env.NOTE_EMAIL ? 'API (credentials set)' : 'file output only'}`);
  console.log(`    qiita: ${process.env.QIITA_TOKEN ? 'API ready' : 'not configured'}`);
  console.log(`    zenn:  ${process.env.ZENN_REPO_PATH ? `git (${process.env.ZENN_REPO_PATH})` : 'not configured'}`);

  await storage.close();
}
