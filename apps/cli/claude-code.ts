/**
 * Shared helpers for Claude Code transcript handling.
 *
 * Used by:
 *   - commands/collect.ts  (full scan + single-file ingest)
 *   - commands/hook.ts      (SessionEnd ingest, SessionStart recall)
 *
 * Claude Code stores one JSONL transcript per session at
 *   ~/.claude/projects/<encoded-cwd>/<session-id>.jsonl
 * where <encoded-cwd> is the absolute cwd with every "/" replaced by "-".
 */

import { readFile } from 'fs/promises';

const API_URL = process.env.MINDBASE_API_URL || 'http://api:18003';

export interface CollectedConversation {
  source: string;
  title: string;
  content: { messages: Array<{ role: string; content: string; timestamp?: string }> };
  metadata: Record<string, any>;
  source_conversation_id: string;
  project?: string;
}

export interface SearchResult {
  id: string;
  title: string | null;
  source: string;
  similarity: number;
  workspace_path: string | null;
  created_at: string;
  content_preview: string | null;
}

/** Decode a Claude Code project directory name back into an approximate path. */
export function decodeProjectName(entry: string): string {
  return decodeURIComponent(entry.replace(/-/g, '/'));
}

/** Encode an absolute cwd into the Claude Code project directory name. */
export function encodeProjectDir(cwd: string): string {
  return cwd.replace(/\//g, '-');
}

/**
 * Parse one Claude Code session JSONL into a CollectedConversation.
 * Returns null when the file has no user/assistant messages.
 * `entry` is the project directory name (used for the dedup id).
 */
export async function buildConversation(
  filePath: string,
  entry: string,
  jsonlFile: string,
): Promise<CollectedConversation | null> {
  const content = await readFile(filePath, 'utf-8');
  const lines = content.trim().split('\n').filter((l) => l.trim());

  const messages: Array<{ role: string; content: string; timestamp?: string }> = [];

  for (const line of lines) {
    try {
      const data = JSON.parse(line);
      if (data.type === 'user' || data.type === 'assistant') {
        const msgContent = typeof data.message?.content === 'string'
          ? data.message.content
          : typeof data.message === 'string'
            ? data.message
            : JSON.stringify(data.message || data.content || '');

        if (msgContent) {
          messages.push({
            role: data.type,
            content: msgContent,
            timestamp: data.timestamp,
          });
        }
      }
    } catch {
      // Skip invalid JSON lines
    }
  }

  if (messages.length === 0) return null;

  const firstUser = messages.find((m) => m.role === 'user');
  const title = firstUser
    ? firstUser.content.substring(0, 100) + (firstUser.content.length > 100 ? '...' : '')
    : `Claude Code session (${jsonlFile})`;

  return {
    source: 'claude-code',
    title,
    content: { messages },
    metadata: { file: jsonlFile },
    source_conversation_id: `${entry}/${jsonlFile}`,
    project: decodeProjectName(entry),
  };
}

/** POST a conversation to the MindBase API. Returns true on success. */
export async function storeConversation(conv: CollectedConversation): Promise<boolean> {
  const response = await fetch(`${API_URL}/conversations/store`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(conv),
  });
  if (response.ok) return true;
  const errText = await response.text();
  console.error(`  Failed to store "${conv.title}": ${response.status} ${errText}`);
  return false;
}

/**
 * Semantic search via the MindBase API, optionally scoped to a workspace path.
 * `timeoutMs` keeps a SessionStart hook from stalling shell startup when the
 * API is slow or down — on timeout/error it throws and the caller no-ops.
 */
export async function searchConversations(
  query: string,
  opts: { workspacePath?: string; limit?: number; threshold?: number; timeoutMs?: number } = {},
): Promise<SearchResult[]> {
  const controller = new AbortController();
  const timer = setTimeout(() => controller.abort(), opts.timeoutMs ?? 3000);
  try {
    const response = await fetch(`${API_URL}/conversations/search`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        query,
        limit: opts.limit ?? 5,
        threshold: opts.threshold ?? 0.5,
        workspace_path: opts.workspacePath,
      }),
      signal: controller.signal,
    });
    if (!response.ok) throw new Error(`search failed: ${response.status}`);
    return (await response.json()) as SearchResult[];
  } finally {
    clearTimeout(timer);
  }
}
