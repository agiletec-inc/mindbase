/**
 * MindBase MCP Server - Storage Interface
 *
 * Defines the contract for storage backends (PostgreSQL + pgvector)
 */

export interface ConversationItem {
  id: string;
  sessionId?: string;
  source: 'claude-code' | 'claude-desktop' | 'chatgpt' | 'cursor' | 'windsurf';
  title: string;
  content: any;
  metadata: Record<string, any>;
  category?: 'task' | 'decision' | 'progress' | 'note' | 'warning' | 'error';
  priority?: 'critical' | 'high' | 'normal' | 'low';
  channel?: string;
  embedding?: number[];
  createdAt: Date;
  updatedAt: Date;
}

export interface Session {
  id: string;
  name: string;
  description?: string;
  parentId?: string;
  createdAt: Date;
  updatedAt: Date;
  itemCount?: number;
}

export interface QueryFilters {
  source?: string;
  category?: string;
  priority?: string;
  channel?: string;
  sessionId?: string;
  limit?: number;
  offset?: number;
  createdAfter?: Date;
  createdBefore?: Date;
}

export interface HybridSearchOptions {
  keywordWeight?: number; // 0-1, default 0.3
  semanticWeight?: number; // 0-1, default 0.7
  threshold?: number; // 0-1, default 0.6
  limit?: number; // default 10
}

export interface SearchResult {
  item: ConversationItem;
  similarity?: number;
  keywordScore?: number;
  semanticScore?: number;
  combinedScore?: number;
}

/**
 * Storage Backend Interface
 *
 * Abstraction layer for different storage implementations.
 * Current implementation: PostgreSQL + pgvector
 */
export interface StorageBackend {
  // Basic CRUD operations
  save(item: ConversationItem): Promise<string>;
  get(filters: QueryFilters): Promise<ConversationItem[]>;
  getById(id: string): Promise<ConversationItem | null>;
  delete(id: string): Promise<boolean>;

  // Search operations
  search(query: string, threshold?: number): Promise<SearchResult[]>;
  semanticSearch(query: string, limit?: number, threshold?: number): Promise<SearchResult[]>;
  hybridSearch(query: string, options?: HybridSearchOptions): Promise<SearchResult[]>;

  // Session management
  createSession(name: string, description?: string, parentId?: string): Promise<string>;
  getSession(id: string): Promise<Session | null>;
  listSessions(limit?: number): Promise<Session[]>;
  deleteSession(id: string): Promise<boolean>;

  // Utility
  close(): Promise<void>;
}
