/**
 * Media output target — Agile Technology Media (agiletec/apps/media).
 *
 * Unlike note/qiita/zenn (free-form publish targets behind the Publisher
 * interface), the media site is a structured file-based CMS: each article is an
 * `.mdx` file with a fixed frontmatter schema, read by `apps/media/src/lib/
 * articles.ts`. This module emits that exact schema and writes it into the
 * media repo's content tree (path supplied via MEDIA_CONTENT_PATH), mirroring
 * how ZennPublisher writes into an external repo via ZENN_REPO_PATH.
 *
 * The article body is produced by the LLM; everything here is deterministic and
 * unit-testable without an API key.
 */

import { writeFile, mkdir } from 'fs/promises';
import { join } from 'path';
import { existsSync } from 'fs';

export type MediaLanguage = 'ja' | 'en';

// Mirrors the union in agiletec/apps/media/src/lib/categories.ts.
export const MEDIA_CATEGORIES = ['ai', 'product', 'ceo-blog', 'news'] as const;
export type MediaCategory = (typeof MEDIA_CATEGORIES)[number];

export interface MediaArticleInput {
  title: string;
  /** Markdown body as produced by the LLM (starts with its own `# Title`). */
  body: string;
  tags: string[];
  language: MediaLanguage;
  category: MediaCategory;
  /** URL/file slug WITHOUT the date prefix, e.g. "claude-code-senior-engineer". */
  slug: string;
  /** Shared across ja/en so the two link as translations. Defaults to `slug`. */
  translationKey: string;
  authors: string[];
  /** Publish date, YYYY-MM-DD. */
  date: string;
  /** Short card blurb shown on the timeline. */
  summary: string;
  /** Optional long-form meta description for SEO; falls back to summary. */
  description?: string;
}

/** Escape a string for use inside a YAML double-quoted scalar. */
function yamlString(value: string): string {
  return `"${value.replace(/\\/g, '\\\\').replace(/"/g, '\\"')}"`;
}

/**
 * Drop a leading "タイトル:" / "Title:" label that the LLM sometimes echoes into
 * the title line (e.g. `# タイトル: 実際のタイトル`).
 */
export function stripTitleLabel(value: string): string {
  return value.replace(/^\s*(?:タイトル|title)\s*[:：]\s*/i, '').trim();
}

function yamlStringArray(values: string[]): string {
  return `[${values.map(yamlString).join(', ')}]`;
}

/**
 * Derive a card summary from the article body: the first real paragraph with
 * markdown decoration stripped, truncated at a sentence boundary.
 */
export function deriveSummary(body: string, maxLen = 140): string {
  const lines = body.split('\n');
  const paragraph: string[] = [];
  for (const raw of lines) {
    const line = raw.trim();
    if (line === '' || line === '---') {
      if (paragraph.length > 0) break; // end of the first paragraph
      continue;
    }
    if (line.startsWith('#') || line.startsWith('```')) continue; // skip headings/fences
    paragraph.push(line);
  }

  const text = paragraph
    .join(' ')
    .replace(/!?\[([^\]]*)\]\([^)]*\)/g, '$1') // images/links → label
    .replace(/[*_`]+/g, '') // emphasis/code marks
    .replace(/\s+/g, ' ')
    .trim();

  if (text.length <= maxLen) return text;

  const head = text.slice(0, maxLen);
  const lastStop = Math.max(
    head.lastIndexOf('。'),
    head.lastIndexOf('. '),
    head.lastIndexOf('！'),
    head.lastIndexOf('？')
  );
  if (lastStop >= maxLen * 0.5) return head.slice(0, lastStop + 1).trim();
  return `${head.trim()}…`;
}

/** Build the full `.mdx` document (frontmatter + body) for the media site. */
export function formatMediaArticle(input: MediaArticleInput): string {
  const title = stripTitleLabel(input.title);
  // Strip the same label from the body's first heading so the rendered H1 is clean.
  const body = input.body.trim().replace(/^(#{1,6}\s+)(.+)$/m, (_m, hashes, text) => hashes + stripTitleLabel(text));

  const frontmatter = [
    '---',
    `title: ${yamlString(title)}`,
    `date: ${yamlString(input.date)}`,
    `category: ${yamlString(input.category)}`,
    `tags: ${yamlStringArray(input.tags)}`,
    `language: ${yamlString(input.language)}`,
    `translationKey: ${yamlString(input.translationKey)}`,
    `authors: ${yamlStringArray(input.authors)}`,
    `summary: ${yamlString(input.summary)}`,
    ...(input.description ? [`description: ${yamlString(input.description)}`] : []),
    '---',
  ].join('\n');

  return `${frontmatter}\n\n${body}\n`;
}

/**
 * Write the article into the media content tree:
 *   {contentRoot}/{language}/{date}-{slug}.mdx
 * Returns the absolute file path written.
 */
export async function writeMediaArticle(
  input: MediaArticleInput,
  contentRoot: string
): Promise<string> {
  const dir = join(contentRoot, input.language);
  if (!existsSync(dir)) {
    await mkdir(dir, { recursive: true });
  }
  const filePath = join(dir, `${input.date}-${input.slug}.mdx`);
  await writeFile(filePath, formatMediaArticle(input), 'utf-8');
  return filePath;
}
