/**
 * MindBase MCP Server - Search Service
 *
 * Semantic and hybrid search using pgvector + full-text search.
 */

import type { Pool } from 'pg';
import type { EmbeddingClient } from '../../../libs/embedding/embedding-client.js';
import type {
  ConversationItem,
  HybridSearchOptions,
  SearchResult,
} from './interface.js';

const DEFAULT_WEIGHTS = {
  keyword: 0.30,
  semantic: 0.55,
  recency: 0.15,
};

export class SearchService {
  constructor(
    private pool: Pool,
    private embeddingClient: EmbeddingClient,
    private mapRowToItem: (row: any) => ConversationItem,
  ) {}

  /**
   * Search conversations (defaults to semantic search)
   */
  async search(query: string, threshold: number = 0.7): Promise<SearchResult[]> {
    return this.semanticSearch(query, 10, threshold);
  }

  /**
   * Semantic search using pgvector cosine similarity with optional recency weighting
   *
   * Note: pgvector's <=> returns cosine distance (0-2), so we use GREATEST(0, 1 - distance)
   * to ensure semantic_score is always in [0, 1] range.
   */
  async semanticSearch(
    query: string,
    limit: number = 10,
    threshold: number = 0.7,
    recencyWeight: number = 0.15,
    recencyTauSeconds: number = 1209600,
    recencyBoostDays: number = 3,
    recencyBoostValue: number = 0.05,
  ): Promise<SearchResult[]> {
    try {
      const queryEmbedding = await this.embeddingClient.generate(query);

      let semanticW = 1 - recencyWeight;
      let recencyW = recencyWeight;
      const sum = semanticW + recencyW;
      if (sum <= 0) {
        semanticW = 1 - DEFAULT_WEIGHTS.recency;
        recencyW = DEFAULT_WEIGHTS.recency;
      } else {
        semanticW /= sum;
        recencyW /= sum;
      }

      const safeTauSeconds = Math.max(1, recencyTauSeconds);
      const safeBoostDays = Math.max(0, recencyBoostDays);
      const safeBoostValue = Math.max(0, Math.min(1, recencyBoostValue));

      const sqlQuery = `
        SELECT
          c.*,
          GREATEST(0, 1 - (c.embedding <=> $1::vector)) AS semantic_score,
          LEAST(
            1.0,
            EXP(-EXTRACT(EPOCH FROM (NOW() - COALESCE(c.created_at, to_timestamp(0)))) / $4)
            + CASE WHEN c.created_at >= NOW() - ($5::int * INTERVAL '1 day') THEN $6 ELSE 0 END
          ) AS recency_score,
          (
            GREATEST(0, 1 - (c.embedding <=> $1::vector)) * $7
            + LEAST(
                1.0,
                EXP(-EXTRACT(EPOCH FROM (NOW() - COALESCE(c.created_at, to_timestamp(0)))) / $4)
                + CASE WHEN c.created_at >= NOW() - ($5::int * INTERVAL '1 day') THEN $6 ELSE 0 END
              ) * $8
          ) AS combined_score
        FROM conversations c
        WHERE c.embedding IS NOT NULL
          AND GREATEST(0, 1 - (c.embedding <=> $1::vector)) > $2
        ORDER BY combined_score DESC
        LIMIT $3
      `;

      const result = await this.pool.query(sqlQuery, [
        `[${queryEmbedding.join(',')}]`,
        threshold,
        limit,
        safeTauSeconds,
        safeBoostDays,
        safeBoostValue,
        semanticW,
        recencyW,
      ]);

      return result.rows.map((row) => ({
        item: this.mapRowToItem(row),
        similarity: row.semantic_score,
        semanticScore: row.semantic_score,
        recencyScore: row.recency_score,
        combinedScore: row.combined_score,
      }));
    } catch (error) {
      const msg = error instanceof Error ? error.message : String(error);
      throw new Error(`Failed to perform semantic search: ${msg}`);
    }
  }

  /**
   * Hybrid search combining keyword (FTS), semantic search (pgvector), and recency
   */
  async hybridSearch(query: string, options?: HybridSearchOptions): Promise<SearchResult[]> {
    try {
      let keywordWeight = options?.keywordWeight ?? DEFAULT_WEIGHTS.keyword;
      let semanticWeight = options?.semanticWeight ?? DEFAULT_WEIGHTS.semantic;
      let recencyWeight = options?.recencyWeight ?? DEFAULT_WEIGHTS.recency;
      const threshold = options?.threshold ?? 0.6;
      const limit = options?.limit ?? 10;

      const safeTauSeconds = Math.max(1, options?.recencyTauSeconds ?? 1209600);
      const safeBoostDays = Math.max(0, options?.recencyBoostDays ?? 3);
      const safeBoostValue = Math.max(0, Math.min(1, options?.recencyBoostValue ?? 0.05));

      const weightSum = keywordWeight + semanticWeight + recencyWeight;
      if (weightSum <= 0) {
        keywordWeight = DEFAULT_WEIGHTS.keyword;
        semanticWeight = DEFAULT_WEIGHTS.semantic;
        recencyWeight = DEFAULT_WEIGHTS.recency;
      } else {
        keywordWeight /= weightSum;
        semanticWeight /= weightSum;
        recencyWeight /= weightSum;
      }

      const queryEmbedding = await this.embeddingClient.generate(query);

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
            GREATEST(0, 1 - (embedding <=> $2::vector)) AS semantic_score
          FROM conversations
          WHERE embedding IS NOT NULL
        ),
        combined AS (
          SELECT
            c.*,
            COALESCE(k.keyword_rank, 0) / (COALESCE(k.keyword_rank, 0) + 1.0) AS keyword_score,
            COALESCE(s.semantic_score, 0) AS semantic_score,
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
        query,
        `[${queryEmbedding.join(',')}]`,
        keywordWeight,
        semanticWeight,
        recencyWeight,
        threshold,
        safeTauSeconds,
        safeBoostDays,
        safeBoostValue,
        limit,
      ]);

      return result.rows.map((row) => ({
        item: this.mapRowToItem(row),
        similarity: row.semantic_score,
        keywordScore: row.keyword_score,
        semanticScore: row.semantic_score,
        recencyScore: row.recency_score,
        combinedScore: row.combined_score,
      }));
    } catch (error) {
      const msg = error instanceof Error ? error.message : String(error);
      throw new Error(`Failed to perform hybrid search: ${msg}`);
    }
  }
}
