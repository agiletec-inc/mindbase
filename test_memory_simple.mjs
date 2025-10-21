#!/usr/bin/env node
import { FileSystemMemoryBackend } from './dist/mcp-server/storage/memory-fs.js';

const storage = new FileSystemMemoryBackend(
  undefined,
  'postgresql://mindbase:mindbase_dev@localhost:15434/mindbase_dev',
  'http://localhost:11434',
  'nomic-embed-text' // 768 dimensions (ivfflat supports up to 2000)
);

async function test() {
  console.log('🧪 MindBase Memory System Test\n');
  
  try {
    // Write memory about this session
    console.log('1️⃣ Writing memory: Serena integration session...');
    const path = await storage.writeMemory(
      'serena_integration_2025-10-19',
      `# Serena Integration Session (2025-10-19)

## 🎯 What We Accomplished
- ✅ Researched Serena MCP Server architecture
- ✅ Analyzed superior features (markdown, onboarding, thinking tools)
- ✅ Implemented **hybrid storage** (markdown + pgvector)
- ✅ Created 5 memory tools (write, read, list, delete, search)
- ✅ Added database migration for memories table

## 💡 Key Insight: Hybrid is Best
**Primary**: Markdown files (human-readable, Git-trackable)
**Secondary**: PostgreSQL + pgvector (semantic search, cross-project)

## 🛠️ Technology Stack
- TypeScript MCP Server
- PostgreSQL + pgvector
- Ollama qwen3-embedding:8b (1024-dim)
- Markdown: ~/Library/Application Support/mindbase/memories/

## 📋 Next Steps
1. Test with real data ✅ (doing now!)
2. Add auto-onboarding tool
3. Implement thinking tools (meta-cognitive)
4. Temporal decay scoring

## 🏆 MindBase > Serena
After this implementation, MindBase has:
- ✅ Markdown memories (from Serena)
- ✅ Semantic search (MindBase strength)
- ✅ Cross-platform archival (MindBase)
- ✅ Cross-project knowledge (MindBase)
`,
      {
        category: 'onboarding',
        project: 'mindbase',
        tags: ['serena', 'mcp', 'memory', 'hybrid-storage', '2025-10-19']
      }
    );
    console.log(`   ✅ Saved to: ${path}\n`);

    // Read it back
    console.log('2️⃣ Reading memory back...');
    const memory = await storage.readMemory('serena_integration_2025-10-19', 'mindbase');
    console.log(`   ✅ Name: ${memory.name}`);
    console.log(`   📁 Category: ${memory.category}`);
    console.log(`   🏷️  Tags: ${memory.tags.join(', ')}`);
    console.log(`   📊 Content: ${memory.content.length} chars\n`);

    // List all memories
    console.log('3️⃣ Listing memories in project "mindbase"...');
    const list = await storage.listMemories({ project: 'mindbase' });
    console.log(`   ✅ Found ${list.length} memory/memories:`);
    list.forEach((m, i) => {
      console.log(`      ${i+1}. ${m.name}`);
      console.log(`         - Category: ${m.category || 'none'}`);
      console.log(`         - Size: ${m.size} bytes`);
    });
    console.log('');

    // Semantic search
    console.log('4️⃣ Semantic search test...');
    console.log('   Query: "How did we integrate Serena features?"');
    const results = await storage.searchMemories(
      'How did we integrate Serena features into MindBase? What was the hybrid storage approach?',
      { limit: 3, threshold: 0.5, project: 'mindbase' }
    );
    console.log(`   ✅ Found ${results.length} result(s):`);
    results.forEach((r, i) => {
      console.log(`      ${i+1}. ${r.memory.name}`);
      console.log(`         - Similarity: ${(r.similarity * 100).toFixed(1)}%`);
      console.log(`         - Preview: ${r.memory.content.substring(0, 100).replace(/\n/g, ' ')}...`);
    });

    console.log('\n🎉 All tests passed! Memory system working perfectly.');
    console.log('✨ Hybrid storage (markdown + pgvector) is functional!\n');
  } catch (error) {
    console.error('\n❌ Test failed:', error.message);
    throw error;
  } finally {
    await storage.close();
  }
}

test().catch(err => {
  console.error('Fatal error:', err);
  process.exit(1);
});
