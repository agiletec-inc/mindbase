/**
 * MindBase MCP Server - Memory Database Repository
 *
 * PostgreSQL persistence and semantic search for memories.
 */

import type { Pool } from 'pg';
import type { EmbeddingClient } from '../../../libs/embedding/embedding-client.js';
import type { Memory, MemorySearchResult } from './memory-interface.js';

export class MemoryDBRepository {
  constructor(
    private pool: Pool,
    private embeddingClient: EmbeddingClient,
    private getMemoryPath: (name: string, project?: string) => string,
  ) {}

  async saveToDatabase(memory: Memory): Promise<void> {
    const query = `
      INSERT INTO memories (name, content, category, project, tags, embedding, created_at, updated_at)
      VALUES ($1, $2, $3, $4, $5, $6, $7, $8)
      ON CONFLICT (name, project) DO UPDATE SET
        content = EXCLUDED.content,
        category = EXCLUDED.category,
        tags = EXCLUDED.tags,
        embedding = EXCLUDED.embedding,
        updated_at = EXCLUDED.updated_at
    `;

    await this.pool.query(query, [
      memory.name,
      memory.content,
      memory.category || null,
      memory.project || null,
      memory.tags || [],
      memory.embedding ? `[${memory.embedding.join(',')}]` : null,
      memory.createdAt,
      memory.updatedAt,
    ]);
  }

  async findByName(name: string, project?: string): Promise<Memory | null> {
    const query = `SELECT * FROM memories WHERE name = $1 AND (project = $2 OR project IS NULL)`;
    const result = await this.pool.query(query, [name, project || null]);

    if (result.rows.length === 0) return null;

    const row = result.rows[0];
    return {
      name: row.name,
      content: row.content,
      category: row.category,
      project: row.project,
      tags: row.tags,
      createdAt: row.created_at,
      updatedAt: row.updated_at,
    };
  }

  async deleteByName(name: string, project?: string): Promise<void> {
    await this.pool.query(
      `DELETE FROM memories WHERE name = $1 AND (project = $2 OR project IS NULL)`,
      [name, project || null],
    );
  }

  async searchMemories(
    query: string,
    options?: { limit?: number; threshold?: number; project?: string; category?: string },
  ): Promise<MemorySearchResult[]> {
    const limit = options?.limit ?? 10;
    const threshold = options?.threshold ?? 0.7;

    const queryEmbedding = await this.embeddingClient.generateOptional(query);
    if (!queryEmbedding) return [];

    const conditions: string[] = ['embedding IS NOT NULL'];
    const params: any[] = [`[${queryEmbedding.join(',')}]`, threshold, limit];
    let paramIndex = 4;

    if (options?.project) {
      conditions.push(`project = $${paramIndex++}`);
      params.push(options.project);
    }

    if (options?.category) {
      conditions.push(`category = $${paramIndex++}`);
      params.push(options.category);
    }

    const whereClause = conditions.join(' AND ');
    const sqlQuery = `
      SELECT
        *,
        1 - (embedding <=> $1::vector) as similarity
      FROM memories
      WHERE ${whereClause}
        AND 1 - (embedding <=> $1::vector) > $2
      ORDER BY embedding <=> $1::vector
      LIMIT $3
    `;

    const result = await this.pool.query(sqlQuery, params);

    return result.rows.map((row) => ({
      memory: {
        name: row.name,
        content: row.content,
        category: row.category,
        project: row.project,
        tags: row.tags,
        createdAt: row.created_at,
        updatedAt: row.updated_at,
      },
      similarity: row.similarity,
      path: this.getMemoryPath(row.name, row.project),
    }));
  }
}
