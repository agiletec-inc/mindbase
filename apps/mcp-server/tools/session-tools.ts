/**
 * MindBase MCP Server - Session Tools
 *
 * Session creation, listing, start/resume, and deletion.
 */

import type { StorageBackend } from '../storage/interface.js';

export class SessionTools {
  private currentSessionId?: string;

  constructor(private storage: StorageBackend) {}

  getCurrentSessionId(): string | undefined {
    return this.currentSessionId;
  }

  setCurrentSession(sessionId: string | undefined) {
    this.currentSessionId = sessionId;
  }

  async sessionCreate(args: {
    name: string;
    description?: string;
    parentId?: string;
  }): Promise<{ id: string; name: string; createdAt: string }> {
    const id = await this.storage.createSession(args.name, args.description, args.parentId);
    const session = await this.storage.getSession(id);

    if (!session) {
      throw new Error('Failed to retrieve created session');
    }

    return {
      id: session.id,
      name: session.name,
      createdAt: session.createdAt.toISOString(),
    };
  }

  async sessionStart(args: {
    sessionId?: string;
    name?: string;
    description?: string;
  }): Promise<{
    id: string;
    name: string;
    description?: string;
    itemCount: number;
    createdAt: string;
  }> {
    let sessionId = args.sessionId;

    if (!sessionId && args.name) {
      sessionId = await this.storage.createSession(args.name, args.description);
    }

    if (!sessionId) {
      throw new Error('Either sessionId or name must be provided');
    }

    const session = await this.storage.getSession(sessionId);
    if (!session) {
      throw new Error(`Session not found: ${sessionId}`);
    }

    this.currentSessionId = session.id;

    return {
      id: session.id,
      name: session.name,
      description: session.description,
      itemCount: session.itemCount || 0,
      createdAt: session.createdAt.toISOString(),
    };
  }

  async sessionList(args?: { limit?: number }): Promise<{
    sessions: any[];
    total: number;
  }> {
    const limit = args?.limit || 10;
    const sessions = await this.storage.listSessions(limit);

    return {
      sessions: sessions.map((s) => ({
        id: s.id,
        name: s.name,
        description: s.description,
        parentId: s.parentId,
        itemCount: s.itemCount || 0,
        createdAt: s.createdAt.toISOString(),
        updatedAt: s.updatedAt.toISOString(),
      })),
      total: sessions.length,
    };
  }

  async sessionDelete(args: { id: string }): Promise<{ success: boolean; deletedId?: string }> {
    const success = await this.storage.deleteSession(args.id);

    if (success && this.currentSessionId === args.id) {
      this.currentSessionId = undefined;
    }

    return {
      success,
      deletedId: success ? args.id : undefined,
    };
  }
}
