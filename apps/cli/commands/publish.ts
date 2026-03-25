/**
 * publish command — Publish a generated article to a platform.
 *
 * Usage: mindbase publish --file article.md --platform note [--draft]
 */

import { parseArgs } from 'node:util';
import { readFile } from 'fs/promises';
import { getPublisher } from '../../../libs/generators/publishers/index.js';

/**
 * Parse frontmatter from markdown content.
 */
function parseFrontmatter(content: string): { metadata: Record<string, any>; body: string } {
  const match = content.match(/^---\n([\s\S]*?)\n---\n([\s\S]*)$/);
  if (!match) return { metadata: {}, body: content };

  const metadata: Record<string, any> = {};
  for (const line of match[1].split('\n')) {
    const colonIndex = line.indexOf(':');
    if (colonIndex === -1) continue;
    const key = line.substring(0, colonIndex).trim();
    const value = line.substring(colonIndex + 1).trim().replace(/^["']|["']$/g, '');

    if (key === 'topics' || key === 'tags') {
      metadata[key] = value
        .replace(/^\[|\]$/g, '')
        .split(',')
        .map((t: string) => t.trim().replace(/^["']|["']$/g, ''));
    } else if (value === 'true') {
      metadata[key] = true;
    } else if (value === 'false') {
      metadata[key] = false;
    } else {
      metadata[key] = value;
    }
  }

  return { metadata, body: match[2] };
}

export async function run() {
  const { values } = parseArgs({
    args: process.argv.slice(3),
    options: {
      file: { type: 'string', short: 'f' },
      platform: { type: 'string', short: 'p' },
      title: { type: 'string', short: 't' },
      draft: { type: 'boolean', default: true },
    },
    strict: true,
  });

  if (!values.file || !values.platform) {
    console.error('Usage: mindbase publish --file <path> --platform <note|qiita|zenn> [--draft]');
    process.exit(1);
  }

  const platform = values.platform;
  if (!['note', 'qiita', 'zenn'].includes(platform)) {
    console.error(`Unknown platform: ${platform}. Supported: note, qiita, zenn`);
    process.exit(1);
  }

  const content = await readFile(values.file, 'utf-8');
  const { metadata, body } = parseFrontmatter(content);

  const title = values.title || metadata.title || 'Untitled';
  const tags = metadata.topics || metadata.tags || [];

  console.log(`Publishing to ${platform}...`);
  console.log(`  Title: ${title}`);
  console.log(`  Tags:  ${tags.join(', ') || '(none)'}`);
  console.log(`  Draft: ${values.draft}`);

  const publisher = getPublisher(platform);
  const result = await publisher.publish(
    { title, content: body.trim(), tags },
    { draft: values.draft },
  );

  if (result.success) {
    console.log(`\nPublished successfully!`);
    console.log(`  Method: ${result.method}`);
    if (result.url) console.log(`  URL:    ${result.url}`);
    if (result.filePath) console.log(`  File:   ${result.filePath}`);
  } else {
    console.error(`\nPublish failed: ${result.error}`);
    process.exit(1);
  }
}
