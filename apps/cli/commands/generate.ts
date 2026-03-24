/**
 * generate command — Search conversations and generate an article via LLM.
 *
 * Usage: mindbase generate --topic "Docker-First" --platform note [--style beginner-friendly] [--limit 10]
 */

import { parseArgs } from 'node:util';
import { writeFile, mkdir } from 'fs/promises';
import { join } from 'path';
import { existsSync } from 'fs';
import { createStorage } from '../db.js';
import { ArticleGenerator, type ConversationSource } from '../../../libs/generators/article-generator.js';
import { OpenAIClient } from '../../../libs/generators/llm-client.js';
import type { Platform } from '../../../libs/generators/platform-prompts.js';

export async function run() {
  const { values } = parseArgs({
    args: process.argv.slice(3),
    options: {
      topic: { type: 'string', short: 't' },
      platform: { type: 'string', short: 'p' },
      style: { type: 'string', short: 's' },
      limit: { type: 'string', short: 'l' },
      'dry-run': { type: 'boolean' },
    },
    strict: true,
  });

  if (!values.topic || !values.platform) {
    console.error('Usage: mindbase generate --topic <topic> --platform <note|qiita|zenn> [--style <style>]');
    process.exit(1);
  }

  const platform = values.platform as Platform;
  if (!['note', 'qiita', 'zenn'].includes(platform)) {
    console.error(`Unknown platform: ${platform}. Supported: note, qiita, zenn`);
    process.exit(1);
  }

  const storage = createStorage();
  const searchLimit = parseInt(values.limit || '10', 10);

  console.log(`Searching conversations for: "${values.topic}" (limit: ${searchLimit})...`);

  const results = await storage.semanticSearch(values.topic, searchLimit, 0.5);

  if (results.length === 0) {
    console.error(`No conversations found for topic: "${values.topic}"`);
    console.error('Try a different query, or collect conversations first with: mindbase collect');
    await storage.close();
    process.exit(1);
  }

  console.log(`Found ${results.length} relevant conversations`);

  // Convert to ArticleGenerator format
  const sources: ConversationSource[] = results.map((r) => {
    const rawMessages = r.item.content?.messages || [];
    return {
      title: r.item.title,
      source: r.item.source,
      date: r.item.createdAt instanceof Date
        ? r.item.createdAt.toISOString().split('T')[0]
        : String(r.item.createdAt).split('T')[0],
      messages: rawMessages
        .filter((m: any) => m.role === 'user' || m.role === 'assistant')
        .slice(0, 20)
        .map((m: any) => ({
          role: m.role as string,
          content: typeof m.content === 'string' ? m.content : JSON.stringify(m.content),
        })),
    };
  });

  console.log(`Generating ${platform} article via LLM...`);

  const llm = new OpenAIClient();
  const generator = new ArticleGenerator(llm);
  const article = await generator.generate({
    topic: values.topic,
    platform,
    conversations: sources,
    style: values.style,
  });

  if (values['dry-run']) {
    console.log('\n--- Preview ---');
    console.log(article.content.substring(0, 1000));
    console.log('--- (truncated) ---');
    await storage.close();
    return;
  }

  // Write to file
  const outputDir = join(process.cwd(), 'generated', platform);
  if (!existsSync(outputDir)) {
    await mkdir(outputDir, { recursive: true });
  }

  const date = new Date().toISOString().split('T')[0];
  const slug = values.topic
    .toLowerCase()
    .replace(/[^a-z0-9\u3000-\u9fff]/g, '-')
    .replace(/-+/g, '-')
    .substring(0, 40);
  const filename = `${date}-${slug}.md`;
  const filePath = join(outputDir, filename);

  await writeFile(filePath, article.content, 'utf-8');

  console.log(`\nArticle generated:`);
  console.log(`  Title:    ${article.title}`);
  console.log(`  Platform: ${platform}`);
  console.log(`  File:     ${filePath}`);
  console.log(`  Sources:  ${article.metadata.sourceConversations} conversations`);
  console.log(`\nNext: mindbase publish --file ${filePath} --platform ${platform} --draft`);

  await storage.close();
}
