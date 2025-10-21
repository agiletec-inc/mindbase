/**
 * MindBase MCP Server - Memory Storage Interface
 *
 * Defines the contract for markdown-based memory storage inspired by Serena.
 * Hybrid approach: Markdown files for human readability + PostgreSQL for search.
 */

export interface Memory {
  name: string;
  content: string;
  category?: 'architecture' | 'decision' | 'pattern' | 'guide' | 'onboarding' | 'note';
  project?: string;
  tags?: string[];
  embedding?: number[];
  createdAt: Date;
  updatedAt: Date;
}

export interface MemoryMetadata {
  name: string;
  category?: string;
  project?: string;
  tags?: string[];
  size: number;
  createdAt: Date;
  updatedAt: Date;
}

export interface MemorySearchResult {
  memory: Memory;
  similarity?: number;
  path: string;
}

/**
 * Memory Storage Backend Interface
 *
 * Hybrid storage strategy:
 * - Primary: Markdown files in .mindbase/memories/
 * - Secondary: PostgreSQL with embeddings for semantic search
 */
export interface MemoryStorageBackend {
  /**
   * Write memory to both markdown and database
   * @param name - Memory name (becomes filename)
   * @param content - Markdown content
   * @param options - Category, project, tags
   */
  writeMemory(
    name: string,
    content: string,
    options?: {
      category?: Memory['category'];
      project?: string;
      tags?: string[];
    }
  ): Promise<string>;

  /**
   * Read memory by name
   * Priority: markdown file > database
   */
  readMemory(name: string, project?: string): Promise<Memory | null>;

  /**
   * List all memories with optional filtering
   */
  listMemories(filters?: {
    project?: string;
    category?: string;
    tags?: string[];
  }): Promise<MemoryMetadata[]>;

  /**
   * Delete memory from both markdown and database
   */
  deleteMemory(name: string, project?: string): Promise<boolean>;

  /**
   * Semantic search across memories
   */
  searchMemories(
    query: string,
    options?: {
      limit?: number;
      threshold?: number;
      project?: string;
      category?: string;
    }
  ): Promise<MemorySearchResult[]>;

  /**
   * Get memory file path
   */
  getMemoryPath(name: string, project?: string): string;

  /**
   * Ensure memory directory exists
   */
  ensureMemoryDir(project?: string): Promise<string>;
}
