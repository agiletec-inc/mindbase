/**
 * publish command — Publish a generated article to a platform.
 *
 * Usage: mindbase publish --file article.md --platform note [--draft]
 */

import { parseArgs } from 'node:util';
import { readFile } from 'fs/promises';
import { getPublisher } from '../../../libs/generators/publishers/index.js';
import { parseFrontmatter } from '../../../libs/markdown/frontmatter.js';

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
