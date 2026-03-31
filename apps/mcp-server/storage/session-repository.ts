/**
 * MindBase MCP Server - Session Repository
 *
 * Session CRUD operations.
 */

import type { Pool } from 'pg';
import { v4 as uuidv4 } from 'uuid';
import type { Session } from './interface.js';

export class SessionRepository {
  constructor(private pool: Pool) {}

  async createSession(name: string, description?: string, parentId?: string): Promise<string> {
    try {
      const id = uuidv4();
      const query = `
        INSERT INTO sessions (id, name, description, parent_id, created_at, updated_at)
        VALUES ($1, $2, $3, $4, NOW(), NOW())
        RETURNING id
      `;
      const result = await this.pool.query(query, [id, name, description || null, parentId || null]);
      return result.rows[0].id;
    } catch (error) {
      const msg = error instanceof Error ? error.message : String(error);
      throw new Error(`Failed to create session: ${msg}`);
    }
  }

  async getSession(id: string): Promise<Session | null> {
    try {
      const query = `
        SELECT
          s.id, s.name, s.description, s.parent_id, s.created_at, s.updated_at,
          COUNT(c.id) as item_count
        FROM sessions s
        LEFT JOIN conversations c ON c.session_id = s.id
        WHERE s.id = $1
        GROUP BY s.id
      `;
      const result = await this.pool.query(query, [id]);
      if (result.rows.length === 0) return null;
      return this.mapRowToSession(result.rows[0]);
    } catch (error) {
      const msg = error instanceof Error ? error.message : String(error);
      throw new Error(`Failed to get session: ${msg}`);
    }
  }

  async listSessions(limit: number = 10): Promise<Session[]> {
    try {
      const query = `
        SELECT
          s.id, s.name, s.description, s.parent_id, s.created_at, s.updated_at,
          COUNT(c.id) as item_count
        FROM sessions s
        LEFT JOIN conversations c ON c.session_id = s.id
        GROUP BY s.id
        ORDER BY s.updated_at DESC
        LIMIT $1
      `;
      const result = await this.pool.query(query, [limit]);
      return result.rows.map(this.mapRowToSession);
    } catch (error) {
      const msg = error instanceof Error ? error.message : String(error);
      throw new Error(`Failed to list sessions: ${msg}`);
    }
  }

  async deleteSession(id: string): Promise<boolean> {
    try {
      const query = `DELETE FROM sessions WHERE id = $1`;
      const result = await this.pool.query(query, [id]);
      return result.rowCount !== null && result.rowCount > 0;
    } catch (error) {
      const msg = error instanceof Error ? error.message : String(error);
      throw new Error(`Failed to delete session: ${msg}`);
    }
  }

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
