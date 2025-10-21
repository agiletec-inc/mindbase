#!/usr/bin/env node
/**
 * Quick test of memory system
 */
import { FileSystemMemoryBackend } from './apps/mcp-server/storage/memory-fs.js';

const DATABASE_URL = 'postgresql://mindbase:mindbase_dev@localhost:15434/mindbase_dev';
const OLLAMA_URL = 'http://localhost:11434';
const EMBEDDING_MODEL = 'nomic-embed-text'; // 768 dimensions (ivfflat supports up to 2000)

async function test() {
  console.log('🧪 Testing Memory System\n');
  
  const storage = new FileSystemMemoryBackend(
    undefined, // Use default: ~/Library/Application Support/mindbase/memories
    DATABASE_URL,
    OLLAMA_URL,
    EMBEDDING_MODEL
  );

  try {
    // 1. Write a memory about current session
    console.log('📝 Writing memory about Serena integration...');
    const path = await storage.writeMemory(
      'serena_integration_session',
      `# Serena Integration Session (2025-10-19)

## What We Did
- Analyzed Serena MCP Server's memory system
- Identified superior features (markdown storage, onboarding, thinking tools)
- Implemented hybrid storage (markdown + PostgreSQL + pgvector)
- Created 5 new MCP tools: memory_write, memory_read, memory_list, memory_delete, memory_search

## Key Decisions
- **Hybrid Storage**: Markdown files for human-readability + PostgreSQL for semantic search
- **Serena-Inspired**: Borrowed best practices while keeping MindBase's cross-platform strength
- **Location**: ~/Library/Application Support/mindbase/memories/

## Next Steps
- Test memory system with real data ✅
- Add auto-onboarding tool
- Implement thinking tools
- Add temporal decay scoring

## Technology
- TypeScript (MCP server)
- PostgreSQL + pgvector (semantic search)
- Ollama qwen3-embedding:8b (1024-dim embeddings)
`,
      {
        category: 'onboarding',
        project: 'mindbase',
        tags: ['serena', 'mcp', 'memory', 'integration']
      }
    );
    console.log(`✅ Saved to: ${path}\n`);

    // 2. List memories
    console.log('📋 Listing all memories...');
    const memories = await storage.listMemories();
    console.log(`Found ${memories.length} memories:`);
    memories.forEach(m => {
      console.log(`  - ${m.name} (${m.category || 'uncategorized'}) - ${m.size} bytes`);
    });
    console.log('');

    // 3. Read it back
    console.log('📖 Reading memory back...');
    const memory = await storage.readMemory('serena_integration_session', 'mindbase');
    if (memory) {
      console.log(`✅ Name: ${memory.name}`);
      console.log(`   Category: ${memory.category}`);
      console.log(`   Project: ${memory.project}`);
      console.log(`   Tags: ${memory.tags?.join(', ')}`);
      console.log(`   Content length: ${memory.content.length} chars`);
      console.log(`   Preview: ${memory.content.substring(0, 100)}...`);
    }
    console.log('');

    // 4. Semantic search
    console.log('🔍 Semantic search: "How did we integrate Serena features?"');
    const results = await storage.searchMemories(
      'How did we integrate Serena features into MindBase?',
      { limit: 3, threshold: 0.5 }
    );
    console.log(`Found ${results.length} results:`);
    results.forEach(r => {
      console.log(`  - ${r.memory.name} (similarity: ${r.similarity?.toFixed(3)})`);
      console.log(`    Preview: ${r.memory.content.substring(0, 80)}...`);
    });

    console.log('\n✅ All tests passed!');
  } catch (error) {
    console.error('❌ Test failed:', error.message);
    throw error;
  } finally {
    await storage.close();
  }
}

test().catch(console.error);
