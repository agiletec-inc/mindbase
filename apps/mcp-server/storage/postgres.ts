/**
 * MindBase MCP Server - PostgreSQL Storage Backend
 *
 * Facade that delegates to focused services:
 * - SearchService: semantic and hybrid search
 * - SessionRepository: session CRUD
 * - AnalyticsRepository: timeline and topic queries
 * - EmbeddingClient: embedding generation (shared library)
 */

import { Pool } from 'pg';
import { v4 as uuidv4 } from 'uuid';
import type {
  StorageBackend,
  ConversationItem,
  Session,
  QueryFilters,
  HybridSearchOptions,
  SearchResult,
  TimelineOptions,
  TimelineEntry,
  TopicGroup,
} from './interface.js';
import { ensureSchema } from './schema.js';
import { EmbeddingClient } from '../../../libs/embedding/embedding-client.js';
import { SearchService } from './search-service.js';
import { SessionRepository } from './session-repository.js';
import { AnalyticsRepository } from './analytics-repository.js';

export class PostgresStorageBackend implements StorageBackend {
  private pool: Pool;
  private embeddingClient: EmbeddingClient;
  private searchService: SearchService;
  private sessionRepo: SessionRepository;
  private analyticsRepo: AnalyticsRepository;

  constructor(connectionString: string, ollamaUrl: string, embeddingModel: string) {
    this.pool = new Pool({ connectionString });
    this.embeddingClient = new EmbeddingClient({
      ollamaUrl,
      embeddingModel,
      openaiApiKey: process.env.OPENAI_API_KEY || undefined,
      openaiModel: process.env.OPENAI_EMBEDDING_MODEL || 'text-embedding-3-large',
    });
    this.searchService = new SearchService(this.pool, this.embeddingClient, this.mapRowToItem);
    this.sessionRepo = new SessionRepository(this.pool);
    this.analyticsRepo = new AnalyticsRepository(this.pool);
  }

  async initialize(): Promise<void> {
    await ensureSchema(this.pool);
  }

  // --- Conversation CRUD ---

  async save(item: ConversationItem): Promise<string> {
    try {
      const id = item.id || uuidv4();

      let embedding = item.embedding;
      if (!embedding && item.content) {
        const text = JSON.stringify(item.content);
        embedding = await this.embeddingClient.generate(text);
      }

      const query = `
        INSERT INTO conversations
        (id, session_id, source, title, content, metadata, category, priority, channel, embedding, created_at, updated_at)
        VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11, $12)
        ON CONFLICT (id) DO UPDATE SET
          session_id = EXCLUDED.session_id,
          title = EXCLUDED.title,
          content = EXCLUDED.content,
          metadata = EXCLUDED.metadata,
          category = EXCLUDED.category,
          priority = EXCLUDED.priority,
          channel = EXCLUDED.channel,
          embedding = EXCLUDED.embedding,
          updated_at = EXCLUDED.updated_at
        RETURNING id
      `;

      const now = new Date();
      const result = await this.pool.query(query, [
        id,
        item.sessionId || null,
        item.source,
        item.title,
        JSON.stringify(item.content),
        JSON.stringify(item.metadata),
        item.category || null,
        item.priority || null,
        item.channel || null,
        embedding ? `[${embedding.join(',')}]` : null,
        item.createdAt || now,
        now,
      ]);

      return result.rows[0].id;
    } catch (error) {
      const msg = error instanceof Error ? error.message : String(error);
      throw new Error(`Failed to save conversation: ${msg}`);
    }
  }

  async get(filters: QueryFilters): Promise<ConversationItem[]> {
    try {
      const conditions: string[] = [];
      const params: any[] = [];
      let paramIndex = 1;

      if (filters.source) { conditions.push(`source = $${paramIndex++}`); params.push(filters.source); }
      if (filters.category) { conditions.push(`category = $${paramIndex++}`); params.push(filters.category); }
      if (filters.priority) { conditions.push(`priority = $${paramIndex++}`); params.push(filters.priority); }
      if (filters.sessionId) { conditions.push(`session_id = $${paramIndex++}`); params.push(filters.sessionId); }
      if (filters.channel) { conditions.push(`channel = $${paramIndex++}`); params.push(filters.channel); }
      if (filters.createdAfter) { conditions.push(`created_at >= $${paramIndex++}`); params.push(filters.createdAfter); }
      if (filters.createdBefore) { conditions.push(`created_at <= $${paramIndex++}`); params.push(filters.createdBefore); }

      const whereClause = conditions.length > 0 ? `WHERE ${conditions.join(' AND ')}` : '';
      const query = `
        SELECT * FROM conversations
        ${whereClause}
        ORDER BY created_at DESC
        LIMIT $${paramIndex++} OFFSET $${paramIndex}
      `;
      params.push(filters.limit || 100, filters.offset || 0);

      const result = await this.pool.query(query, params);
      return result.rows.map(this.mapRowToItem);
    } catch (error) {
      const msg = error instanceof Error ? error.message : String(error);
      throw new Error(`Failed to get conversations: ${msg}`);
    }
  }

  async getById(id: string): Promise<ConversationItem | null> {
    try {
      const result = await this.pool.query(`SELECT * FROM conversations WHERE id = $1`, [id]);
      if (result.rows.length === 0) return null;
      return this.mapRowToItem(result.rows[0]);
    } catch (error) {
      const msg = error instanceof Error ? error.message : String(error);
      throw new Error(`Failed to get conversation by ID: ${msg}`);
    }
  }

  async delete(id: string): Promise<boolean> {
    try {
      const result = await this.pool.query(`DELETE FROM conversations WHERE id = $1`, [id]);
      return result.rowCount !== null && result.rowCount > 0;
    } catch (error) {
      const msg = error instanceof Error ? error.message : String(error);
      throw new Error(`Failed to delete conversation: ${msg}`);
    }
  }

  async count(filters: Omit<QueryFilters, 'limit' | 'offset'>): Promise<number> {
    try {
      const conditions: string[] = [];
      const params: any[] = [];
      let paramIndex = 1;

      if (filters.source) { conditions.push(`source = $${paramIndex++}`); params.push(filters.source); }
      if (filters.category) { conditions.push(`category = $${paramIndex++}`); params.push(filters.category); }
      if (filters.priority) { conditions.push(`priority = $${paramIndex++}`); params.push(filters.priority); }
      if (filters.sessionId) { conditions.push(`session_id = $${paramIndex++}`); params.push(filters.sessionId); }
      if (filters.channel) { conditions.push(`channel = $${paramIndex++}`); params.push(filters.channel); }
      if (filters.createdAfter) { conditions.push(`created_at >= $${paramIndex++}`); params.push(filters.createdAfter); }
      if (filters.createdBefore) { conditions.push(`created_at <= $${paramIndex++}`); params.push(filters.createdBefore); }

      const whereClause = conditions.length > 0 ? `WHERE ${conditions.join(' AND ')}` : '';
      const result = await this.pool.query(`SELECT COUNT(*) as count FROM conversations ${whereClause}`, params);
      return parseInt(result.rows[0].count, 10);
    } catch (error) {
      const msg = error instanceof Error ? error.message : String(error);
      throw new Error(`Failed to count conversations: ${msg}`);
    }
  }

  // --- Delegated: Search ---
  search(query: string, threshold?: number): Promise<SearchResult[]> { return this.searchService.search(query, threshold); }
  semanticSearch(query: string, limit?: number, threshold?: number, recencyWeight?: number, recencyTauSeconds?: number, recencyBoostDays?: number, recencyBoostValue?: number): Promise<SearchResult[]> { return this.searchService.semanticSearch(query, limit, threshold, recencyWeight, recencyTauSeconds, recencyBoostDays, recencyBoostValue); }
  hybridSearch(query: string, options?: HybridSearchOptions): Promise<SearchResult[]> { return this.searchService.hybridSearch(query, options); }

  // --- Delegated: Sessions ---
  createSession(name: string, description?: string, parentId?: string): Promise<string> { return this.sessionRepo.createSession(name, description, parentId); }
  getSession(id: string): Promise<Session | null> { return this.sessionRepo.getSession(id); }
  listSessions(limit?: number): Promise<Session[]> { return this.sessionRepo.listSessions(limit); }
  deleteSession(id: string): Promise<boolean> { return this.sessionRepo.deleteSession(id); }

  // --- Delegated: Analytics ---
  getTimeline(options?: TimelineOptions): Promise<TimelineEntry[]> { return this.analyticsRepo.getTimeline(options); }
  getTopics(limit?: number, minCount?: number): Promise<TopicGroup[]> { return this.analyticsRepo.getTopics(limit, minCount); }

  // --- Lifecycle ---
  async close(): Promise<void> { await this.pool.end(); }

  // --- Row mapping ---
  private mapRowToItem(row: any): ConversationItem {
    return {
      id: row.id,
      sessionId: row.session_id,
      source: row.source,
      title: row.title,
      content: typeof row.content === 'string' ? JSON.parse(row.content) : row.content,
      metadata: typeof row.metadata === 'string' ? JSON.parse(row.metadata) : row.metadata,
      category: row.category,
      priority: row.priority,
      channel: row.channel,
      embedding: row.embedding ? (typeof row.embedding === 'string' ? JSON.parse(row.embedding) : row.embedding) : undefined,
      createdAt: row.created_at,
      updatedAt: row.updated_at,
    };
  }
}
