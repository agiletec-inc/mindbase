/**
 * MindBase MCP Server - PostgreSQL Storage Backend
 *
 * Storage implementation using PostgreSQL + pgvector for semantic search
 */

import { Pool, PoolClient, QueryResult } from 'pg';
import { v4 as uuidv4 } from 'uuid';
import type {
  StorageBackend,
  ConversationItem,
  Session,
  QueryFilters,
  HybridSearchOptions,
  SearchResult,
} from './interface.js';
import { ensureSchema } from './schema.js';

export class PostgresStorageBackend implements StorageBackend {
  private pool: Pool;
  private ollamaUrl: string;
  private embeddingModel: string;

  constructor(connectionString: string, ollamaUrl: string, embeddingModel: string) {
    this.pool = new Pool({ connectionString });
    this.ollamaUrl = ollamaUrl;
    this.embeddingModel = embeddingModel;
  }

  /**
   * Initialize database schema if not already done
   * Call this before using the storage backend
   */
  async initialize(): Promise<void> {
    await ensureSchema(this.pool);
  }

  /**
   * Generate embedding vector using Ollama
   */
  private async generateEmbedding(text: string): Promise<number[]> {
    try {
      const response = await fetch(`${this.ollamaUrl}/api/embeddings`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          model: this.embeddingModel,
          prompt: text,
        }),
      });

      if (!response.ok) {
        throw new Error(`Ollama API error: ${response.statusText}`);
      }

      const data = await response.json() as { embedding: number[] };
      return data.embedding;
    } catch (error) {
      console.error('Failed to generate embedding:', error);
      throw error;
    }
  }

  /**
   * Save conversation item with automatic embedding generation
   */
  async save(item: ConversationItem): Promise<string> {
    const id = item.id || uuidv4();

    // Generate embedding if not provided
    let embedding = item.embedding;
    if (!embedding && item.content) {
      const text = JSON.stringify(item.content);
      embedding = await this.generateEmbedding(text);
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
  }

  /**
   * Get conversation items with filters and pagination
   */
  async get(filters: QueryFilters): Promise<ConversationItem[]> {
    const conditions: string[] = [];
    const params: any[] = [];
    let paramIndex = 1;

    if (filters.source) {
      conditions.push(`source = $${paramIndex++}`);
      params.push(filters.source);
    }

    if (filters.category) {
      conditions.push(`category = $${paramIndex++}`);
      params.push(filters.category);
    }

    if (filters.priority) {
      conditions.push(`priority = $${paramIndex++}`);
      params.push(filters.priority);
    }

    if (filters.sessionId) {
      conditions.push(`session_id = $${paramIndex++}`);
      params.push(filters.sessionId);
    }

    if (filters.channel) {
      conditions.push(`channel = $${paramIndex++}`);
      params.push(filters.channel);
    }

    if (filters.createdAfter) {
      conditions.push(`created_at >= $${paramIndex++}`);
      params.push(filters.createdAfter);
    }

    if (filters.createdBefore) {
      conditions.push(`created_at <= $${paramIndex++}`);
      params.push(filters.createdBefore);
    }

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
  }

  /**
   * Get conversation item by ID
   */
  async getById(id: string): Promise<ConversationItem | null> {
    const query = `SELECT * FROM conversations WHERE id = $1`;
    const result = await this.pool.query(query, [id]);

    if (result.rows.length === 0) {
      return null;
    }

    return this.mapRowToItem(result.rows[0]);
  }

  /**
   * Delete conversation item
   */
  async delete(id: string): Promise<boolean> {
    const query = `DELETE FROM conversations WHERE id = $1`;
    const result = await this.pool.query(query, [id]);
    return result.rowCount !== null && result.rowCount > 0;
  }

  /**
   * Search conversations (defaults to semantic search)
   */
  async search(query: string, threshold: number = 0.7): Promise<SearchResult[]> {
    return this.semanticSearch(query, 10, threshold);
  }

  /**
   * Semantic search using pgvector cosine similarity
   */
  async semanticSearch(query: string, limit: number = 10, threshold: number = 0.7): Promise<SearchResult[]> {
    // Generate query embedding
    const queryEmbedding = await this.generateEmbedding(query);

    const sqlQuery = `
      SELECT
        *,
        1 - (embedding <=> $1::vector) as similarity
      FROM conversations
      WHERE embedding IS NOT NULL
        AND 1 - (embedding <=> $1::vector) > $2
      ORDER BY embedding <=> $1::vector
      LIMIT $3
    `;

    const result = await this.pool.query(sqlQuery, [
      `[${queryEmbedding.join(',')}]`,
      threshold,
      limit,
    ]);

    return result.rows.map((row) => ({
      item: this.mapRowToItem(row),
      similarity: row.similarity,
      semanticScore: row.similarity,
      combinedScore: row.similarity,
    }));
  }

  /**
   * Hybrid search combining keyword and semantic search
   * TODO: Implement in Phase 2
   */
  async hybridSearch(query: string, options?: HybridSearchOptions): Promise<SearchResult[]> {
    // For now, fall back to semantic search
    // Full implementation: combine PostgreSQL FTS + pgvector
    return this.semanticSearch(query, options?.limit || 10, options?.threshold || 0.6);
  }

  /**
   * Create new session
   */
  async createSession(name: string, description?: string, parentId?: string): Promise<string> {
    const id = uuidv4();
    const query = `
      INSERT INTO sessions (id, name, description, parent_id, created_at, updated_at)
      VALUES ($1, $2, $3, $4, NOW(), NOW())
      RETURNING id
    `;

    const result = await this.pool.query(query, [id, name, description || null, parentId || null]);
    return result.rows[0].id;
  }

  /**
   * Get session by ID
   */
  async getSession(id: string): Promise<Session | null> {
    const query = `
      SELECT
        s.id,
        s.name,
        s.description,
        s.parent_id,
        s.created_at,
        s.updated_at,
        COUNT(c.id) as item_count
      FROM sessions s
      LEFT JOIN conversations c ON c.session_id = s.id
      WHERE s.id = $1
      GROUP BY s.id
    `;

    const result = await this.pool.query(query, [id]);

    if (result.rows.length === 0) {
      return null;
    }

    return this.mapRowToSession(result.rows[0]);
  }

  /**
   * List recent sessions with pagination
   */
  async listSessions(limit: number = 10): Promise<Session[]> {
    const query = `
      SELECT
        s.id,
        s.name,
        s.description,
        s.parent_id,
        s.created_at,
        s.updated_at,
        COUNT(c.id) as item_count
      FROM sessions s
      LEFT JOIN conversations c ON c.session_id = s.id
      GROUP BY s.id
      ORDER BY s.updated_at DESC
      LIMIT $1
    `;

    const result = await this.pool.query(query, [limit]);
    return result.rows.map(this.mapRowToSession);
  }

  /**
   * Delete session (conversations will be orphaned, not deleted)
   */
  async deleteSession(id: string): Promise<boolean> {
    const query = `DELETE FROM sessions WHERE id = $1`;
    const result = await this.pool.query(query, [id]);
    return result.rowCount !== null && result.rowCount > 0;
  }

  /**
   * Close database connection pool
   */
  async close(): Promise<void> {
    await this.pool.end();
  }

  /**
   * Map database row to ConversationItem
   */
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

  /**
   * Map database row to Session
   */
  private mapRowToSession(row: any): Session {
    return {
      id: row.id,
      name: row.name,
      description: row.description,
      parentId: row.parent_id,
      createdAt: row.created_at,
      updatedAt: row.updated_at,
      itemCount: parseInt(row.item_count) || 0,
    };
  }
}
