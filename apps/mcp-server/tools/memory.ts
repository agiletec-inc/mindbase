/**
 * MindBase MCP Server - Memory Tools
 *
 * Markdown-based memory management tools inspired by Serena.
 * Hybrid storage: Markdown files + PostgreSQL for semantic search.
 */

import type { FileSystemMemoryBackend } from '../storage/memory-fs.js';
import type { Memory, MemoryMetadata, MemorySearchResult } from '../storage/memory-interface.js';

export class MemoryTools {
  constructor(private storage: FileSystemMemoryBackend) {}

  /**
   * memory_write - Write memory to markdown and database
   */
  async memoryWrite(args: {
    name: string;
    content: string;
    category?: 'architecture' | 'decision' | 'pattern' | 'guide' | 'onboarding' | 'note';
    project?: string;
    tags?: string[];
  }): Promise<{ path: string; name: string }> {
    const path = await this.storage.writeMemory(args.name, args.content, {
      category: args.category,
      project: args.project,
      tags: args.tags,
    });

    return {
      path,
      name: args.name,
    };
  }

  /**
   * memory_read - Read memory by name
   */
  async memoryRead(args: {
    name: string;
    project?: string;
  }): Promise<Memory | { error: string }> {
    const memory = await this.storage.readMemory(args.name, args.project);

    if (!memory) {
      return { error: `Memory not found: ${args.name}` };
    }

    return memory;
  }

  /**
   * memory_list - List all memories with optional filtering
   */
  async memoryList(args?: {
    project?: string;
    category?: string;
    tags?: string[];
  }): Promise<{
    memories: MemoryMetadata[];
    total: number;
  }> {
    const memories = await this.storage.listMemories(args);

    return {
      memories,
      total: memories.length,
    };
  }

  /**
   * memory_delete - Delete memory from both markdown and database
   */
  async memoryDelete(args: {
    name: string;
    project?: string;
  }): Promise<{ success: boolean; name?: string; error?: string }> {
    const success = await this.storage.deleteMemory(args.name, args.project);

    if (!success) {
      return {
        success: false,
        error: `Failed to delete memory: ${args.name}`,
      };
    }

    return {
      success: true,
      name: args.name,
    };
  }

  /**
   * memory_search - Semantic search across memories
   */
  async memorySearch(args: {
    query: string;
    limit?: number;
    threshold?: number;
    project?: string;
    category?: string;
  }): Promise<{
    results: Array<{
      name: string;
      content: string;
      category?: string;
      project?: string;
      tags?: string[];
      similarity: number;
      path: string;
    }>;
    query: string;
    total: number;
  }> {
    const results = await this.storage.searchMemories(args.query, {
      limit: args.limit,
      threshold: args.threshold,
      project: args.project,
      category: args.category,
    });

    return {
      results: results.map((r) => ({
        name: r.memory.name,
        content: r.memory.content,
        category: r.memory.category,
        project: r.memory.project,
        tags: r.memory.tags,
        similarity: r.similarity || 0,
        path: r.path,
      })),
      query: args.query,
      total: results.length,
    };
  }
}
