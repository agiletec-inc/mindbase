/**
 * generate command — Search conversations and generate an article via LLM.
 *
 * Usage:
 *   mindbase generate --topic "Docker-First" --platform note [--style ...] [--limit 10]
 *   mindbase generate --topic "Claude Code" --platform media --slug claude-code \
 *     --lang ja --category ceo-blog   (writes an .mdx into $MEDIA_CONTENT_PATH)
 */

import { parseArgs } from 'node:util';
import { writeFile, mkdir } from 'fs/promises';
import { join } from 'path';
import { existsSync } from 'fs';
import { createStorage } from '../db.js';
import { ArticleGenerator, type ConversationSource } from '../../../libs/generators/article-generator.js';
import { OpenAIClient } from '../../../libs/generators/llm-client.js';
import type { Platform } from '../../../libs/generators/platform-prompts.js';
import {
  deriveSummary,
  writeMediaArticle,
  MEDIA_CATEGORIES,
  type MediaCategory,
  type MediaLanguage,
} from '../../../libs/generators/publishers/media-publisher.js';

export async function run() {
  const { values } = parseArgs({
    args: process.argv.slice(3),
    options: {
      topic: { type: 'string', short: 't' },
      platform: { type: 'string', short: 'p' },
      style: { type: 'string', short: 's' },
      limit: { type: 'string', short: 'l' },
      'dry-run': { type: 'boolean' },
      // media-only
      lang: { type: 'string' },
      category: { type: 'string' },
      slug: { type: 'string' },
      tags: { type: 'string' },
      'translation-key': { type: 'string' },
      author: { type: 'string' },
      summary: { type: 'string' },
      description: { type: 'string' },
    },
    strict: true,
  });

  if (!values.topic || !values.platform) {
    console.error('Usage: mindbase generate --topic <topic> --platform <note|qiita|zenn|media> [--style <style>]');
    process.exit(1);
  }

  const platform = values.platform as Platform;
  if (!['note', 'qiita', 'zenn', 'media'].includes(platform)) {
    console.error(`Unknown platform: ${platform}. Supported: note, qiita, zenn, media`);
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

  // media target → write a media-schema .mdx into the agiletec/apps/media repo.
  if (platform === 'media') {
    const contentRoot = process.env.MEDIA_CONTENT_PATH;
    if (!contentRoot) {
      console.error(
        'MEDIA_CONTENT_PATH is required for --platform media. ' +
          'Set it to agiletec/apps/media/content (e.g. export MEDIA_CONTENT_PATH=~/github/agiletec-inc/agiletec/apps/media/content).'
      );
      await storage.close();
      process.exit(1);
    }

    const lang = (values.lang || 'ja') as MediaLanguage;
    if (lang !== 'ja' && lang !== 'en') {
      console.error(`Unknown --lang: ${lang}. Supported: ja, en`);
      await storage.close();
      process.exit(1);
    }

    const category = (values.category || 'ai') as MediaCategory;
    if (!MEDIA_CATEGORIES.includes(category)) {
      console.error(`Unknown --category: ${category}. Supported: ${MEDIA_CATEGORIES.join(', ')}`);
      await storage.close();
      process.exit(1);
    }

    const baseSlug = (values.slug || values.topic)
      .toLowerCase()
      .replace(/[^a-z0-9]+/g, '-')
      .replace(/^-|-$/g, '')
      .substring(0, 60);
    if (!baseSlug) {
      console.error('Could not derive an ASCII slug from the topic. Pass --slug explicitly (e.g. --slug claude-code-senior-engineer).');
      await storage.close();
      process.exit(1);
    }

    const tags = (values.tags || '')
      .split(',')
      .map((t) => t.trim())
      .filter(Boolean);

    const date = new Date().toISOString().split('T')[0];
    const filePath = await writeMediaArticle(
      {
        title: article.title,
        body: article.content,
        tags,
        language: lang,
        category,
        slug: baseSlug,
        translationKey: values['translation-key'] || baseSlug,
        authors: [values.author || 'kazuki'],
        date,
        summary: values.summary || deriveSummary(article.content),
        description: values.description,
      },
      contentRoot
    );

    console.log(`\nMedia article written:`);
    console.log(`  Title:    ${article.title}`);
    console.log(`  Lang:     ${lang}`);
    console.log(`  Category: ${category}`);
    console.log(`  File:     ${filePath}`);
    console.log(`  URL:      /${lang}/blog/${date}-${baseSlug}`);
    console.log(`  Sources:  ${article.metadata.sourceConversations} conversations`);
    console.log(`\nNext: review it in the media app, then open a PR in agiletec.`);

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
