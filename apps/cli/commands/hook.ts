/**
 * hook command — Claude Code lifecycle hook handlers.
 *
 * Wired into ~/.claude/settings.json by `mindbase install` (see commands/install.ts):
 *   SessionEnd   -> mindbase hook session-end    (ingest the session that just ended)
 *   SessionStart -> mindbase hook session-start  (inject relevant past context)
 *
 * Both read the hook event JSON from stdin (Claude Code passes session_id,
 * transcript_path, cwd, ...). Both are NON-BLOCKING: any failure (API down,
 * missing file, timeout) exits 0 silently so a session is never broken.
 *
 * Usage (invoked by Claude Code, not by hand):
 *   echo '<hook-json>' | mindbase hook session-end
 *   echo '<hook-json>' | mindbase hook session-start
 */

import { readdir, stat } from 'fs/promises';
import { join, basename, dirname } from 'path';
import { homedir } from 'os';
import {
  buildConversation,
  storeConversation,
  searchConversations,
  encodeProjectDir,
  type SearchResult,
} from '../claude-code.js';

interface HookInput {
  session_id?: string;
  transcript_path?: string;
  cwd?: string;
  hook_event_name?: string;
}

async function readStdin(): Promise<HookInput> {
  const chunks: Buffer[] = [];
  for await (const chunk of process.stdin) chunks.push(chunk as Buffer);
  const raw = Buffer.concat(chunks).toString('utf-8').trim();
  if (!raw) return {};
  try {
    return JSON.parse(raw) as HookInput;
  } catch {
    return {};
  }
}

/** SessionEnd: ingest the transcript of the session that just ended. */
async function sessionEnd(input: HookInput): Promise<void> {
  const filePath = input.transcript_path;
  if (!filePath) return;

  const jsonlFile = basename(filePath);
  const entry = basename(dirname(filePath));

  const conv = await buildConversation(filePath, entry, jsonlFile);
  if (!conv) return;
  await storeConversation(conv);
}

/**
 * SessionStart: find the most recent PRIOR session in this workspace, use its
 * last user message as the query, and inject the top matches as additionalContext.
 */
async function sessionStart(input: HookInput): Promise<void> {
  const cwd = input.cwd;
  if (!cwd) return;

  const projectDir = join(homedir(), '.claude', 'projects', encodeProjectDir(cwd));
  let files: string[];
  try {
    files = (await readdir(projectDir)).filter((f) => f.endsWith('.jsonl'));
  } catch {
    return; // no prior sessions for this workspace
  }

  // Exclude the current session's own transcript, if it already exists.
  const currentFile = input.session_id ? `${input.session_id}.jsonl` : null;
  const candidates = files.filter((f) => f !== currentFile);
  if (candidates.length === 0) return;

  // Most recently modified prior transcript.
  const withMtime = await Promise.all(
    candidates.map(async (f) => {
      const s = await stat(join(projectDir, f)).catch(() => null);
      return { f, mtime: s ? s.mtimeMs : 0 };
    }),
  );
  withMtime.sort((a, b) => b.mtime - a.mtime);
  const recent = withMtime[0].f;

  const conv = await buildConversation(join(projectDir, recent), basename(projectDir), recent);
  if (!conv) return;
  // Use the last genuine user prompt as the query. Skip tool-result turns, which
  // Claude Code also logs as role "user" but whose content is a JSON blob — those
  // make poor semantic queries.
  const lastPrompt = [...conv.content.messages].reverse().find((m) => {
    if (m.role !== 'user') return false;
    const c = m.content.trimStart();
    return c.length > 0 && !c.startsWith('[') && !c.startsWith('{');
  });
  const query = lastPrompt?.content?.trim();
  if (!query) return;

  const results = await searchConversations(query.slice(0, 500), {
    workspacePath: cwd,
    limit: 5,
  });
  if (results.length === 0) return;

  emitContext(results);
}

function emitContext(results: SearchResult[]): void {
  const lines = results.map((r) => {
    const date = (r.created_at || '').slice(0, 10);
    const preview = (r.content_preview || '').replace(/\s+/g, ' ').slice(0, 200);
    return `- [${date}] ${r.title ?? 'untitled'}\n  ${preview}`;
  });
  const additionalContext =
    'Relevant past conversations from this workspace (via MindBase memory):\n' +
    lines.join('\n');

  process.stdout.write(
    JSON.stringify({
      hookSpecificOutput: {
        hookEventName: 'SessionStart',
        additionalContext,
      },
    }),
  );
}

export async function run() {
  const sub = process.argv[3];
  const input = await readStdin();

  try {
    if (sub === 'session-end') {
      await sessionEnd(input);
    } else if (sub === 'session-start') {
      await sessionStart(input);
    } else {
      console.error('Usage: mindbase hook <session-end|session-start>');
      process.exit(1);
    }
  } catch (err) {
    // Non-blocking: never fail a Claude Code session because of memory I/O.
    const msg = err instanceof Error ? err.message : String(err);
    console.error(`mindbase hook ${sub}: ${msg}`);
  }
  process.exit(0);
}
