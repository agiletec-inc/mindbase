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
   * Count conversations matching filters
   */
  async count(filters: Omit<QueryFilters, 'limit' | 'offset'>): Promise<number> {
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
    const query = `SELECT COUNT(*) as count FROM conversations ${whereClause}`;

    const result = await this.pool.query(query, params);
    return parseInt(result.rows[0].count, 10);
  }

  /**
   * Search conversations (defaults to semantic search)
   */
  async search(query: string, threshold: number = 0.7): Promise<SearchResult[]> {
    return this.semanticSearch(query, 10, threshold);
  }

  /**
   * Semantic search using pgvector cosine similarity with optional recency weighting
   */
  async semanticSearch(
    query: string,
    limit: number = 10,
    threshold: number = 0.7,
    recencyWeight: number = 0.15,
    recencyTauSeconds: number = 1209600, // 14 days
    recencyBoostDays: number = 3,
    recencyBoostValue: number = 0.05
  ): Promise<SearchResult[]> {
    // Generate query embedding
    const queryEmbedding = await this.generateEmbedding(query);

    // Normalize weights
    const semanticWeight = 1 - recencyWeight;

    const sqlQuery = `
      SELECT
        c.*,
        1 - (c.embedding <=> $1::vector) AS semantic_score,
        LEAST(
          1.0,
          EXP(-EXTRACT(EPOCH FROM (NOW() - COALESCE(c.created_at, to_timestamp(0)))) / $4)
          + CASE WHEN c.created_at >= NOW() - ($5::int * INTERVAL '1 day') THEN $6 ELSE 0 END
        ) AS recency_score,
        (
          (1 - (c.embedding <=> $1::vector)) * $7
          + LEAST(
              1.0,
              EXP(-EXTRACT(EPOCH FROM (NOW() - COALESCE(c.created_at, to_timestamp(0)))) / $4)
              + CASE WHEN c.created_at >= NOW() - ($5::int * INTERVAL '1 day') THEN $6 ELSE 0 END
            ) * $8
        ) AS combined_score
      FROM conversations c
      WHERE c.embedding IS NOT NULL
        AND 1 - (c.embedding <=> $1::vector) > $2
      ORDER BY combined_score DESC
      LIMIT $3
    `;

    const result = await this.pool.query(sqlQuery, [
      `[${queryEmbedding.join(',')}]`, // $1: embedding
      threshold,                        // $2: threshold
      limit,                            // $3: limit
      recencyTauSeconds,                // $4: decay constant (tau)
      recencyBoostDays,                 // $5: boost window
      recencyBoostValue,                // $6: boost value
      semanticWeight,                   // $7: semantic weight
      recencyWeight,                    // $8: recency weight
    ]);

    return result.rows.map((row) => ({
      item: this.mapRowToItem(row),
      similarity: row.semantic_score,
      semanticScore: row.semantic_score,
      recencyScore: row.recency_score,
      combinedScore: row.combined_score,
    }));
  }

  /**
   * Hybrid search combining keyword (FTS), semantic search (pgvector), and recency
   *
   * Score normalization:
   * - keyword: normalized via saturation function x/(x+1) -> 0-1
   * - semantic: cosine similarity -> 0-1
   * - recency: exp decay + boost, capped at 1.0
   * - weights: auto-normalized to sum to 1.0
   */
  async hybridSearch(query: string, options?: HybridSearchOptions): Promise<SearchResult[]> {
    // Default weights (will be normalized)
    let keywordWeight = options?.keywordWeight ?? 0.30;
    let semanticWeight = options?.semanticWeight ?? 0.55;
    let recencyWeight = options?.recencyWeight ?? 0.15;
    const threshold = options?.threshold ?? 0.6;
    const limit = options?.limit ?? 10;

    // Recency parameters (use interface property names)
    const recencyTauSeconds = options?.recencyTauSeconds ?? 1209600; // 14 days
    const recencyBoostDays = options?.recencyBoostDays ?? 3;
    const recencyBoostValue = options?.recencyBoostValue ?? 0.05;

    // Normalize weights to sum to 1.0
    const weightSum = keywordWeight + semanticWeight + recencyWeight;
    if (weightSum > 0) {
      keywordWeight /= weightSum;
      semanticWeight /= weightSum;
      recencyWeight /= weightSum;
    }

    // Generate query embedding for semantic search
    const queryEmbedding = await this.generateEmbedding(query);

    // Hybrid query with:
    // 1. keyword_norm: ts_rank normalized via saturation (x / (x + 1))
    // 2. semantic_score: cosine similarity (already 0-1)
    // 3. recency_score: exp decay + boost, capped at 1.0
    const sqlQuery = `
      WITH keyword_search AS (
        SELECT
          id,
          ts_rank(
            setweight(to_tsvector('english', COALESCE(title, '')), 'A') ||
            setweight(to_tsvector('english', COALESCE(content::text, '')), 'B'),
            plainto_tsquery('english', $1)
          ) AS keyword_rank
        FROM conversations
        WHERE
          to_tsvector('english', COALESCE(title, '')) ||
          to_tsvector('english', COALESCE(content::text, ''))
          @@ plainto_tsquery('english', $1)
      ),
      semantic_search AS (
        SELECT
          id,
          1 - (embedding <=> $2::vector) AS semantic_score
        FROM conversations
        WHERE embedding IS NOT NULL
      ),
      combined AS (
        SELECT
          c.*,
          -- Keyword score: normalized via saturation function (0-1)
          COALESCE(k.keyword_rank, 0) / (COALESCE(k.keyword_rank, 0) + 1.0) AS keyword_score,
          -- Semantic score: already 0-1
          COALESCE(s.semantic_score, 0) AS semantic_score,
          -- Recency score: exp decay + boost, capped at 1.0
          LEAST(
            1.0,
            EXP(-EXTRACT(EPOCH FROM (NOW() - COALESCE(c.created_at, to_timestamp(0)))) / $7)
            + CASE WHEN c.created_at >= NOW() - ($8::int * INTERVAL '1 day') THEN $9 ELSE 0 END
          ) AS recency_score
        FROM conversations c
        LEFT JOIN keyword_search k ON c.id = k.id
        LEFT JOIN semantic_search s ON c.id = s.id
        WHERE k.id IS NOT NULL OR (s.semantic_score IS NOT NULL AND s.semantic_score > $6)
      )
      SELECT
        *,
        (keyword_score * $3 + semantic_score * $4 + recency_score * $5) AS combined_score
      FROM combined
      WHERE (keyword_score * $3 + semantic_score * $4 + recency_score * $5) > 0
      ORDER BY combined_score DESC
      LIMIT $10
    `;

    const result = await this.pool.query(sqlQuery, [
      query,                           // $1: search query
      `[${queryEmbedding.join(',')}]`, // $2: embedding vector
      keywordWeight,                   // $3: normalized keyword weight
      semanticWeight,                  // $4: normalized semantic weight
      recencyWeight,                   // $5: normalized recency weight
      threshold,                       // $6: semantic threshold
      recencyTauSeconds,               // $7: decay constant (tau)
      recencyBoostDays,                // $8: boost window (days)
      recencyBoostValue,               // $9: boost value
      limit,                           // $10: result limit
    ]);

    return result.rows.map((row) => ({
      item: this.mapRowToItem(row),
      similarity: row.semantic_score,
      keywordScore: row.keyword_score,
      semanticScore: row.semantic_score,
      recencyScore: row.recency_score,
      combinedScore: row.combined_score,
    }));
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
