/**
 * collect command — Collect conversations from Claude Code JSONL files.
 *
 * TypeScript native implementation (no Python dependency).
 * Reads JSONL directly from ~/.claude/projects/ and POSTs to the MindBase API.
 *
 * Usage:
 *   mindbase collect [--source claude-code] [--since 2026-01-01] [--dry-run]
 *   mindbase collect --file ~/.claude/projects/<proj>/<session>.jsonl   # single session
 *
 * The single-file mode is used by the SessionEnd hook to ingest just the
 * session that ended. Dedup on the API side ((source, source_conversation_id))
 * makes both modes idempotent.
 */

import { parseArgs } from 'node:util';
import { readdir, stat } from 'fs/promises';
import { join, basename, dirname } from 'path';
import { homedir } from 'os';
import {
  type CollectedConversation,
  buildConversation,
  storeConversation,
} from '../claude-code.js';

export async function run() {
  const { values } = parseArgs({
    args: process.argv.slice(3),
    options: {
      source: { type: 'string', short: 's', default: 'claude-code' },
      since: { type: 'string' },
      file: { type: 'string' },
      'dry-run': { type: 'boolean' },
    },
    strict: true,
  });

  if (values.source !== 'claude-code') {
    console.error(`Only "claude-code" source is supported in CLI. Got: ${values.source}`);
    console.error('For other sources, use the Python collector: scripts/collect-conversations.py');
    process.exit(1);
  }

  // Single-file mode: ingest just one session transcript (used by the SessionEnd hook).
  if (values.file) {
    const filePath = values.file;
    const jsonlFile = basename(filePath);
    const entry = basename(dirname(filePath));

    let conv: CollectedConversation | null;
    try {
      conv = await buildConversation(filePath, entry, jsonlFile);
    } catch (err) {
      const msg = err instanceof Error ? err.message : String(err);
      console.error(`Cannot read ${filePath}: ${msg}`);
      process.exit(1);
    }

    if (!conv) {
      console.log(`No user/assistant messages in ${jsonlFile} — nothing to store`);
      return;
    }

    if (values['dry-run']) {
      console.log(`Dry run — [${conv.project}] ${conv.title} (${conv.content.messages.length} messages)`);
      return;
    }

    const ok = await storeConversation(conv);
    console.log(ok ? `Stored: ${conv.title}` : 'Store failed');
    if (!ok) process.exit(1);
    return;
  }

  const sinceDate = values.since ? new Date(values.since) : undefined;
  const projectsDir = join(homedir(), '.claude', 'projects');

  console.log(`Collecting from ${values.source}...`);
  console.log(`  Path: ${projectsDir}`);
  if (sinceDate) console.log(`  Since: ${sinceDate.toISOString()}`);

  let entries: string[];
  try {
    entries = await readdir(projectsDir);
  } catch {
    console.error(`Cannot read directory: ${projectsDir}`);
    console.error('Is Claude Code installed?');
    process.exit(1);
  }

  const conversations: CollectedConversation[] = [];

  for (const entry of entries) {
    const projectPath = join(projectsDir, entry);
    const projectStat = await stat(projectPath).catch(() => null);
    if (!projectStat?.isDirectory()) continue;

    const files = await readdir(projectPath).catch(() => []);
    const jsonlFiles = files.filter((f) => f.endsWith('.jsonl'));

    for (const jsonlFile of jsonlFiles) {
      const filePath = join(projectPath, jsonlFile);
      const fileStat = await stat(filePath).catch(() => null);

      // Filter by date
      if (sinceDate && fileStat && fileStat.mtime < sinceDate) continue;

      try {
        const conv = await buildConversation(filePath, entry, jsonlFile);
        if (conv) conversations.push(conv);
      } catch (err) {
        const msg = err instanceof Error ? err.message : String(err);
        console.error(`  Error reading ${filePath}: ${msg}`);
      }
    }
  }

  console.log(`\nCollected ${conversations.length} conversations`);

  if (values['dry-run']) {
    console.log('\nDry run — not syncing to API');
    for (const conv of conversations.slice(0, 5)) {
      console.log(`  [${conv.project}] ${conv.title} (${conv.content.messages.length} messages)`);
    }
    if (conversations.length > 5) {
      console.log(`  ... and ${conversations.length - 5} more`);
    }
    return;
  }

  // Sync to API
  let successes = 0;
  let failures = 0;

  for (const conv of conversations) {
    try {
      const ok = await storeConversation(conv);
      if (ok) successes++;
      else failures++;
    } catch (err) {
      failures++;
      const msg = err instanceof Error ? err.message : String(err);
      console.error(`  Failed to store "${conv.title}": ${msg}`);
    }
  }

  console.log(`\nSync complete: ${successes} success, ${failures} failures`);
}
