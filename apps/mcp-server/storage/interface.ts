/**
 * MindBase MCP Server - Storage Interfaces
 *
 * Composable interfaces split by responsibility.
 * StorageBackend is the union type for backward compatibility.
 */

export interface ConversationItem {
  id: string;
  sessionId?: string;
  source: 'claude-code' | 'claude-desktop' | 'chatgpt' | 'cursor' | 'windsurf' | 'gemini';
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

/**
 * Hybrid search options with recency ranking
 *
 * IMPORTANT: Weights are automatically normalized to sum to 1.0
 * You can pass any values; they will be proportionally adjusted.
 */
export interface HybridSearchOptions {
  keywordWeight?: number; // default 0.30
  semanticWeight?: number; // default 0.55
  recencyWeight?: number; // default 0.15
  threshold?: number; // 0-1, default 0.6
  limit?: number; // default 10
  recencyTauSeconds?: number; // default 1209600 (14 days)
  recencyBoostDays?: number; // default 3
  recencyBoostValue?: number; // default 0.05
}

export interface SearchResult {
  item: ConversationItem;
  similarity?: number;
  keywordScore?: number;
  semanticScore?: number;
  recencyScore?: number;
  combinedScore?: number;
}

export interface TimelineOptions {
  sources?: string[];
  createdAfter?: Date;
  createdBefore?: Date;
  limit?: number;
  offset?: number;
  project?: string;
}

export interface TimelineEntry {
  id: string;
  source: string;
  title: string;
  project?: string;
  messageCount: number;
  createdAt: Date;
  updatedAt: Date;
  topics?: string[];
}

export interface TopicGroup {
  topic: string;
  conversationCount: number;
  sources: string[];
  latestAt: Date;
  earliestAt: Date;
  conversationIds: string[];
}

// Composable interfaces by responsibility

export interface ConversationStorage {
  save(item: ConversationItem): Promise<string>;
  get(filters: QueryFilters): Promise<ConversationItem[]>;
  getById(id: string): Promise<ConversationItem | null>;
  delete(id: string): Promise<boolean>;
  count(filters: Omit<QueryFilters, 'limit' | 'offset'>): Promise<number>;
}

export interface SearchStorage {
  search(query: string, threshold?: number): Promise<SearchResult[]>;
  semanticSearch(query: string, limit?: number, threshold?: number, recencyWeight?: number, recencyTauSeconds?: number, recencyBoostDays?: number, recencyBoostValue?: number): Promise<SearchResult[]>;
  hybridSearch(query: string, options?: HybridSearchOptions): Promise<SearchResult[]>;
}

export interface SessionStorage {
  createSession(name: string, description?: string, parentId?: string): Promise<string>;
  getSession(id: string): Promise<Session | null>;
  listSessions(limit?: number): Promise<Session[]>;
  deleteSession(id: string): Promise<boolean>;
}

export interface AnalyticsStorage {
  getTimeline(options?: TimelineOptions): Promise<TimelineEntry[]>;
  getTopics(limit?: number, minCount?: number): Promise<TopicGroup[]>;
}

/**
 * Full storage backend — union of all composable interfaces.
 * Kept for backward compatibility.
 */
export interface StorageBackend
  extends ConversationStorage, SearchStorage, SessionStorage, AnalyticsStorage {
  close(): Promise<void>;
}
