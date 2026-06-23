/**
 * install command — Install MindBase memory hooks into Claude Code.
 *
 * Writes SessionStart + SessionEnd hook entries into ~/.claude/settings.json so
 * that, with no manual steps, every Claude Code session:
 *   - SessionEnd   -> ingests its transcript into MindBase
 *   - SessionStart -> injects relevant past context for the workspace
 *
 * Idempotent and non-destructive: only entries owned by THIS MindBase checkout
 * (identified by the absolute CLI path in the command) are added/replaced. Any
 * other hooks the user has are left untouched. `uninstall` reverses it exactly.
 *
 * Usage:
 *   mindbase install [--api-url http://localhost:18002] [--settings <path>]
 *
 * ~/.claude is NOT version-controlled, so this installer lives in the MindBase
 * repo and regenerates the exact configuration on demand — that is the source
 * of reproducibility, not the hand-edited settings file.
 */

import { parseArgs } from 'node:util';
import { readFile, writeFile, access } from 'fs/promises';
import { join, dirname, resolve } from 'path';
import { homedir } from 'os';
import { fileURLToPath } from 'url';

interface HookCommand { type: 'command'; command: string }
interface HookEntry { matcher?: string; hooks: HookCommand[] }

const CLI_ENTRY = resolve(dirname(fileURLToPath(import.meta.url)), '..', 'index.ts');
const REPO_ROOT = resolve(dirname(fileURLToPath(import.meta.url)), '..', '..', '..');
const TSX = join(REPO_ROOT, 'node_modules', '.bin', 'tsx');

/** A hook entry belongs to this installer if its command references our CLI_ENTRY. */
function isOurs(entry: HookEntry): boolean {
  return entry.hooks?.some((h) => typeof h.command === 'string' && h.command.includes(CLI_ENTRY));
}

function hookCommand(sub: string, apiUrl: string): string {
  return `MINDBASE_API_URL=${apiUrl} "${TSX}" "${CLI_ENTRY}" hook ${sub}`;
}

export async function run() {
  const { values } = parseArgs({
    args: process.argv.slice(3),
    options: {
      'api-url': { type: 'string', default: process.env.MINDBASE_API_URL || 'http://localhost:18002' },
      settings: { type: 'string' },
    },
    strict: true,
  });

  const apiUrl = values['api-url']!;
  const settingsPath = values.settings || join(homedir(), '.claude', 'settings.json');

  // Warn (don't fail) if tsx isn't installed yet — hooks need it to run.
  await access(TSX).catch(() => {
    console.warn(`⚠️  tsx not found at ${TSX}`);
    console.warn('   Run `pnpm install` in the MindBase repo so the hooks can execute.');
  });

  let settings: Record<string, any> = {};
  try {
    settings = JSON.parse(await readFile(settingsPath, 'utf-8'));
  } catch {
    // missing or empty -> start fresh, preserving nothing to clobber
  }

  settings.hooks ??= {};
  const hooks = settings.hooks as Record<string, HookEntry[]>;

  const install = (event: string, matcher: string, sub: string) => {
    const existing = (hooks[event] ?? []).filter((e) => !isOurs(e));
    existing.push({ matcher, hooks: [{ type: 'command', command: hookCommand(sub, apiUrl) }] });
    hooks[event] = existing;
  };

  install('SessionEnd', '', 'session-end');
  install('SessionStart', 'startup|resume', 'session-start');

  await writeFile(settingsPath, JSON.stringify(settings, null, 2) + '\n', 'utf-8');

  console.log(`Installed MindBase memory hooks → ${settingsPath}`);
  console.log(`  API: ${apiUrl}`);
  console.log('  SessionEnd   → ingest transcript');
  console.log('  SessionStart → inject relevant past context (startup|resume)');
  console.log('Run `mindbase uninstall` to remove.');
}
