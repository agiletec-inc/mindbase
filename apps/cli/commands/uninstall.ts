/**
 * uninstall command — Remove MindBase memory hooks from Claude Code.
 *
 * Reverses `install`: drops only the SessionStart/SessionEnd entries owned by
 * THIS MindBase checkout (identified by the absolute CLI path), leaves every
 * other hook intact, and removes an event key entirely if it becomes empty.
 *
 * Usage:
 *   mindbase uninstall [--settings <path>]
 */

import { parseArgs } from 'node:util';
import { readFile, writeFile } from 'fs/promises';
import { join, dirname, resolve } from 'path';
import { homedir } from 'os';
import { fileURLToPath } from 'url';

interface HookCommand { type: 'command'; command: string }
interface HookEntry { matcher?: string; hooks: HookCommand[] }

const CLI_ENTRY = resolve(dirname(fileURLToPath(import.meta.url)), '..', 'index.ts');

function isOurs(entry: HookEntry): boolean {
  return entry.hooks?.some((h) => typeof h.command === 'string' && h.command.includes(CLI_ENTRY));
}

export async function run() {
  const { values } = parseArgs({
    args: process.argv.slice(3),
    options: { settings: { type: 'string' } },
    strict: true,
  });

  const settingsPath = values.settings || join(homedir(), '.claude', 'settings.json');

  let settings: Record<string, any>;
  try {
    settings = JSON.parse(await readFile(settingsPath, 'utf-8'));
  } catch {
    console.log(`No settings file at ${settingsPath} — nothing to remove.`);
    return;
  }

  const hooks = (settings.hooks ?? {}) as Record<string, HookEntry[]>;
  let removed = 0;

  for (const event of ['SessionStart', 'SessionEnd']) {
    const entries = hooks[event];
    if (!Array.isArray(entries)) continue;
    const kept = entries.filter((e) => !isOurs(e));
    removed += entries.length - kept.length;
    if (kept.length === 0) delete hooks[event];
    else hooks[event] = kept;
  }

  if (Object.keys(hooks).length === 0) delete settings.hooks;

  await writeFile(settingsPath, JSON.stringify(settings, null, 2) + '\n', 'utf-8');
  console.log(`Removed ${removed} MindBase hook entr${removed === 1 ? 'y' : 'ies'} from ${settingsPath}`);
}
