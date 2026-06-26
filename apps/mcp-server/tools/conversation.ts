/**
 * MindBase MCP Server - Conversation Tools
 *
 * Facade that delegates to focused tool classes:
 * - SessionTools: session management
 * - SearchTools: semantic and hybrid search
 * - ContentTools: article generation and publishing
 * - RetrievalTools: retrieval-pack assembly (no LLM calls)
 */

import type { StorageBackend, ConversationItem, QueryFilters, TimelineOptions } from '../storage/interface.js';
import { SessionTools } from './session-tools.js';
import { SearchTools } from './search-tools.js';
import { ContentTools } from './content-tools.js';
import { RetrievalTools } from './retrieval-tools.js';

export class ConversationTools {
  private sessionTools: SessionTools;
  private searchTools: SearchTools;
  private contentTools: ContentTools;
  private retrievalTools: RetrievalTools;

  constructor(private storage: StorageBackend) {
    this.sessionTools = new SessionTools(storage);
    this.searchTools = new SearchTools(storage, this.formatItem);
    this.contentTools = new ContentTools(storage);
    this.retrievalTools = new RetrievalTools(storage);
  }

  setCurrentSession(sessionId: string | undefined) {
    this.sessionTools.setCurrentSession(sessionId);
  }

  // --- Conversation CRUD ---

  async conversationSave(args: {
    source: string;
    title: string;
    content: any;
    metadata?: Record<string, any>;
    category?: string;
    priority?: string;
    channel?: string;
    sessionId?: string;
  }): Promise<{ id: string; createdAt: string }> {
    const item: ConversationItem = {
      id: '',
      sessionId: args.sessionId || this.sessionTools.getCurrentSessionId(),
      source: args.source as any,
      title: args.title,
      content: args.content,
      metadata: args.metadata || {},
      category: args.category as any,
      priority: args.priority as any,
      channel: args.channel,
      createdAt: new Date(),
      updatedAt: new Date(),
    };

    const id = await this.storage.save(item);
    return { id, createdAt: item.createdAt.toISOString() };
  }

  async conversationGet(args: {
    id?: string;
    source?: string;
    category?: string;
    priority?: string;
    channel?: string;
    sessionId?: string;
    limit?: number;
    offset?: number;
    createdAfter?: string;
    createdBefore?: string;
  }): Promise<{ items: any[]; total: number; hasMore: boolean }> {
    if (args.id) {
      const item = await this.storage.getById(args.id);
      if (!item) return { items: [], total: 0, hasMore: false };
      return { items: [this.formatItem(item)], total: 1, hasMore: false };
    }

    const filters: QueryFilters = {
      source: args.source,
      category: args.category,
      priority: args.priority,
      channel: args.channel,
      sessionId: args.sessionId || this.sessionTools.getCurrentSessionId(),
      limit: args.limit || 100,
      offset: args.offset || 0,
      createdAfter: args.createdAfter ? new Date(args.createdAfter) : undefined,
      createdBefore: args.createdBefore ? new Date(args.createdBefore) : undefined,
    };

    const { limit, offset, ...countFilters } = filters;
    const [items, total] = await Promise.all([
      this.storage.get(filters),
      this.storage.count(countFilters),
    ]);
    const hasMore = (offset || 0) + items.length < total;

    return { items: items.map(this.formatItem), total, hasMore };
  }

  async conversationDelete(args: { id: string }): Promise<{ success: boolean; deletedId?: string }> {
    const success = await this.storage.delete(args.id);
    return { success, deletedId: success ? args.id : undefined };
  }

  // --- Delegated: Search ---
  conversationSearch = (...a: Parameters<SearchTools['conversationSearch']>) => this.searchTools.conversationSearch(...a);
  conversationHybridSearch = (...a: Parameters<SearchTools['conversationHybridSearch']>) => this.searchTools.conversationHybridSearch(...a);

  // --- Delegated: Sessions ---
  sessionCreate = (...a: Parameters<SessionTools['sessionCreate']>) => this.sessionTools.sessionCreate(...a);
  sessionStart = (...a: Parameters<SessionTools['sessionStart']>) => this.sessionTools.sessionStart(...a);
  sessionList = (...a: Parameters<SessionTools['sessionList']>) => this.sessionTools.sessionList(...a);
  sessionDelete = (...a: Parameters<SessionTools['sessionDelete']>) => this.sessionTools.sessionDelete(...a);

  // --- Delegated: Content ---
  contentGenerate = (...a: Parameters<ContentTools['contentGenerate']>) => this.contentTools.contentGenerate(...a);
  contentPublish = (...a: Parameters<ContentTools['contentPublish']>) => this.contentTools.contentPublish(...a);

  // --- Delegated: Retrieval ---
  mindbaseDraft = (...a: Parameters<RetrievalTools['mindbaseDraft']>) => this.retrievalTools.mindbaseDraft(...a);

  // --- Cross-source ---

  async conversationTimeline(args: {
    sources?: string[];
    project?: string;
    createdAfter?: string;
    createdBefore?: string;
    limit?: number;
    offset?: number;
  }): Promise<{ entries: any[]; total: number }> {
    const options: TimelineOptions = {
      sources: args.sources,
      project: args.project,
      createdAfter: args.createdAfter ? new Date(args.createdAfter) : undefined,
      createdBefore: args.createdBefore ? new Date(args.createdBefore) : undefined,
      limit: args.limit || 50,
      offset: args.offset || 0,
    };

    const entries = await this.storage.getTimeline(options);
    const total = await this.storage.count({
      source: args.sources?.[0],
      createdAfter: options.createdAfter,
      createdBefore: options.createdBefore,
    });

    return {
      entries: entries.map((e) => ({
        id: e.id,
        source: e.source,
        title: e.title,
        project: e.project,
        messageCount: e.messageCount,
        topics: e.topics,
        createdAt: e.createdAt instanceof Date ? e.createdAt.toISOString() : e.createdAt,
        updatedAt: e.updatedAt instanceof Date ? e.updatedAt.toISOString() : e.updatedAt,
      })),
      total,
    };
  }

  async conversationTopics(args?: { limit?: number; minCount?: number }): Promise<{ topics: any[]; total: number }> {
    const limit = args?.limit || 20;
    const minCount = args?.minCount || 1;
    const topics = await this.storage.getTopics(limit, minCount);

    return {
      topics: topics.map((t) => ({
        topic: t.topic,
        conversationCount: t.conversationCount,
        sources: t.sources,
        latestAt: t.latestAt instanceof Date ? t.latestAt.toISOString() : t.latestAt,
        earliestAt: t.earliestAt instanceof Date ? t.earliestAt.toISOString() : t.earliestAt,
        conversationIds: t.conversationIds.slice(0, 10),
      })),
      total: topics.length,
    };
  }

  // --- Formatting ---

  private formatItem(item: ConversationItem): any {
    return {
      id: item.id,
      sessionId: item.sessionId,
      source: item.source,
      title: item.title,
      content: item.content,
      metadata: item.metadata,
      category: item.category,
      priority: item.priority,
      channel: item.channel,
      createdAt: item.createdAt.toISOString(),
      updatedAt: item.updatedAt.toISOString(),
    };
  }
}
