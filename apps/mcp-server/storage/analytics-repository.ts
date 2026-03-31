/**
 * MindBase MCP Server - Analytics Repository
 *
 * Timeline and topic aggregation queries.
 */

import type { Pool } from 'pg';
import type { TimelineOptions, TimelineEntry, TopicGroup } from './interface.js';

export class AnalyticsRepository {
  constructor(private pool: Pool) {}

  async getTimeline(options?: TimelineOptions): Promise<TimelineEntry[]> {
    try {
      const conditions: string[] = [];
      const params: any[] = [];
      let paramIndex = 1;

      if (options?.sources && options.sources.length > 0) {
        conditions.push(`source = ANY($${paramIndex++})`);
        params.push(options.sources);
      }

      if (options?.project) {
        conditions.push(`project = $${paramIndex++}`);
        params.push(options.project);
      }

      if (options?.createdAfter) {
        conditions.push(`created_at >= $${paramIndex++}`);
        params.push(options.createdAfter);
      }

      if (options?.createdBefore) {
        conditions.push(`created_at <= $${paramIndex++}`);
        params.push(options.createdBefore);
      }

      const whereClause = conditions.length > 0 ? `WHERE ${conditions.join(' AND ')}` : '';
      const query = `
        SELECT id, source, title, project, message_count, topics, created_at, updated_at
        FROM conversations
        ${whereClause}
        ORDER BY created_at DESC
        LIMIT $${paramIndex++} OFFSET $${paramIndex}
      `;

      params.push(options?.limit || 50, options?.offset || 0);

      const result = await this.pool.query(query, params);
      return result.rows.map((row: any) => ({
        id: row.id,
        source: row.source,
        title: row.title,
        project: row.project,
        messageCount: row.message_count || 0,
        createdAt: row.created_at,
        updatedAt: row.updated_at,
        topics: row.topics || [],
      }));
    } catch (error) {
      const msg = error instanceof Error ? error.message : String(error);
      throw new Error(`Failed to get timeline: ${msg}`);
    }
  }

  async getTopics(limit: number = 20, minCount: number = 1): Promise<TopicGroup[]> {
    try {
      const query = `
        SELECT
          topic,
          COUNT(DISTINCT c.id) as conversation_count,
          ARRAY_AGG(DISTINCT c.source) as sources,
          MAX(c.created_at) as latest_at,
          MIN(c.created_at) as earliest_at,
          ARRAY_AGG(DISTINCT c.id ORDER BY c.id) as conversation_ids
        FROM conversations c,
             LATERAL unnest(COALESCE(c.topics, ARRAY['Uncategorized'])) AS topic
        GROUP BY topic
        HAVING COUNT(DISTINCT c.id) >= $1
        ORDER BY conversation_count DESC, latest_at DESC
        LIMIT $2
      `;

      const result = await this.pool.query(query, [minCount, limit]);
      return result.rows.map((row: any) => ({
        topic: row.topic,
        conversationCount: parseInt(row.conversation_count, 10),
        sources: row.sources,
        latestAt: row.latest_at,
        earliestAt: row.earliest_at,
        conversationIds: row.conversation_ids,
      }));
    } catch (error) {
      const msg = error instanceof Error ? error.message : String(error);
      throw new Error(`Failed to get topics: ${msg}`);
    }
  }
}
