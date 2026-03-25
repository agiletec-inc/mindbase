/**
 * search command — Search conversations in the database.
 *
 * Usage: mindbase search --query "Docker" [--limit 10]
 */

import { parseArgs } from 'node:util';
import { createStorage } from '../db.js';

export async function run() {
  const { values } = parseArgs({
    args: process.argv.slice(3),
    options: {
      query: { type: 'string', short: 'q' },
      limit: { type: 'string', short: 'l' },
      source: { type: 'string', short: 's' },
    },
    strict: true,
  });

  if (!values.query) {
    console.error('Usage: mindbase search --query <query> [--limit 10] [--source claude-code]');
    process.exit(1);
  }

  const storage = createStorage();
  const limit = parseInt(values.limit || '10', 10);

  console.log(`Searching: "${values.query}" (limit: ${limit})...\n`);

  const results = await storage.hybridSearch(values.query, {
    limit,
    threshold: 0.3,
  });

  // Filter by source if specified
  const filtered = values.source
    ? results.filter((r) => r.item.source === values.source)
    : results;

  if (filtered.length === 0) {
    console.log('No results found.');
    await storage.close();
    return;
  }

  for (const result of filtered) {
    const item = result.item;
    const date = item.createdAt instanceof Date
      ? item.createdAt.toISOString().split('T')[0]
      : String(item.createdAt).split('T')[0];
    const score = result.combinedScore?.toFixed(3) || '-';
    const msgCount = item.content?.messages?.length || 0;

    console.log(`[${score}] ${item.title}`);
    console.log(`       ${item.source} | ${date} | ${msgCount} messages | ${item.id}`);
    console.log('');
  }

  console.log(`${filtered.length} results found.`);
  await storage.close();
}
