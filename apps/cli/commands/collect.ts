/**
 * collect command — Collect conversations from Claude Code JSONL files.
 *
 * TypeScript native implementation (no Python dependency).
 * Reads JSONL directly from ~/.claude/projects/ and POSTs to the MindBase API.
 *
 * Usage: mindbase collect [--source claude-code] [--since 2026-01-01] [--dry-run]
 */

import { parseArgs } from 'node:util';
import { readFile, readdir, stat } from 'fs/promises';
import { join } from 'path';
import { homedir } from 'os';

const API_URL = process.env.MINDBASE_API_URL || 'http://api:18003';

interface CollectedConversation {
  source: string;
  title: string;
  content: { messages: Array<{ role: string; content: string; timestamp?: string }> };
  metadata: Record<string, any>;
  source_conversation_id: string;
  project?: string;
}

export async function run() {
  const { values } = parseArgs({
    args: process.argv.slice(3),
    options: {
      source: { type: 'string', short: 's', default: 'claude-code' },
      since: { type: 'string' },
      'dry-run': { type: 'boolean' },
    },
    strict: true,
  });

  if (values.source !== 'claude-code') {
    console.error(`Only "claude-code" source is supported in CLI. Got: ${values.source}`);
    console.error('For other sources, use the Python collector: scripts/collect-conversations.py');
    process.exit(1);
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

    // Decode project name from path encoding
    const projectName = decodeURIComponent(entry.replace(/-/g, '/'));

    // Find JSONL files
    const files = await readdir(projectPath).catch(() => []);
    const jsonlFiles = files.filter((f) => f.endsWith('.jsonl'));

    for (const jsonlFile of jsonlFiles) {
      const filePath = join(projectPath, jsonlFile);
      const fileStat = await stat(filePath).catch(() => null);

      // Filter by date
      if (sinceDate && fileStat && fileStat.mtime < sinceDate) continue;

      try {
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

        if (messages.length > 0) {
          // Generate title from first user message
          const firstUser = messages.find((m) => m.role === 'user');
          const title = firstUser
            ? firstUser.content.substring(0, 100) + (firstUser.content.length > 100 ? '...' : '')
            : `Claude Code session (${jsonlFile})`;

          conversations.push({
            source: 'claude-code',
            title,
            content: { messages },
            metadata: { file: jsonlFile },
            source_conversation_id: `${entry}/${jsonlFile}`,
            project: projectName,
          });
        }
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
      const response = await fetch(`${API_URL}/conversations/store`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(conv),
      });

      if (response.ok) {
        successes++;
      } else {
        failures++;
        const errText = await response.text();
        console.error(`  Failed to store "${conv.title}": ${response.status} ${errText}`);
      }
    } catch (err) {
      failures++;
      const msg = err instanceof Error ? err.message : String(err);
      console.error(`  Failed to store "${conv.title}": ${msg}`);
    }
  }

  console.log(`\nSync complete: ${successes} success, ${failures} failures`);
}
