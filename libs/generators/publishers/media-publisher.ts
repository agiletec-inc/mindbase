/**
 * Media output target — Agile Technology Media (agiletec/apps/corporate, served
 * at agiletec.net/media).
 *
 * Owned media is a structured file-based CMS: each article is an `.mdx` file
 * read by `apps/corporate/src/lib/media.ts` (`getOwnedArticles`). This module
 * emits that exact frontmatter schema and writes into the corporate repo's
 * content tree (path supplied via MEDIA_CONTENT_PATH), mirroring how
 * ZennPublisher writes into an external repo via ZENN_REPO_PATH.
 *
 * The corporate owned schema is single-language and minimal:
 *   title / date / category(ai|product|ceo-blog|news) / tags / summary + MDX body.
 * (No language/translationKey/authors/description/image — those belong to the
 * retired standalone apps/media app.)
 *
 * The article body is produced by the LLM; everything here is deterministic and
 * unit-testable without an API key.
 */

import { writeFile, mkdir } from 'fs/promises';
import { join } from 'path';
import { existsSync } from 'fs';

// Mirrors the union in agiletec/apps/corporate/src/lib/media.ts.
export const MEDIA_CATEGORIES = ['ai', 'product', 'ceo-blog', 'news'] as const;
export type MediaCategory = (typeof MEDIA_CATEGORIES)[number];

export interface MediaArticleInput {
  title: string;
  /** Markdown body as produced by the LLM (starts with its own `# Title`). */
  body: string;
  tags: string[];
  category: MediaCategory;
  /** URL/file slug WITHOUT the date prefix, e.g. "claude-code-senior-engineer". */
  slug: string;
  /** Publish date, YYYY-MM-DD. */
  date: string;
  /** Short card blurb shown on the media cards. */
  summary: string;
}

/** Escape a string for use inside a YAML double-quoted scalar. */
function yamlString(value: string): string {
  return `"${value.replace(/\\/g, '\\\\').replace(/"/g, '\\"')}"`;
}

function yamlStringArray(values: string[]): string {
  return `[${values.map(yamlString).join(', ')}]`;
}

/**
 * Drop a leading "タイトル:" / "Title:" label that the LLM sometimes echoes into
 * the title line (e.g. `# タイトル: 実際のタイトル`).
 */
export function stripTitleLabel(value: string): string {
  return value.replace(/^\s*(?:タイトル|title)\s*[:：]\s*/i, '').trim();
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
  // The site renders the frontmatter `title` as the heading, so drop the body's
  // own leading `# Title` H1 (the LLM is told to open with one) to avoid a
  // duplicate title on the article page.
  const body = input.body.trim().replace(/^#\s+[^\n]*\n+/, '');

  const frontmatter = [
    '---',
    `title: ${yamlString(title)}`,
    `date: ${yamlString(input.date)}`,
    `category: ${yamlString(input.category)}`,
    `tags: ${yamlStringArray(input.tags)}`,
    `summary: ${yamlString(input.summary)}`,
    '---',
  ].join('\n');

  return `${frontmatter}\n\n${body}\n`;
}

/**
 * Write the article into the corporate media content tree:
 *   {contentRoot}/{date}-{slug}.mdx   (flat, single-language)
 * Returns the absolute file path written.
 */
export async function writeMediaArticle(
  input: MediaArticleInput,
  contentRoot: string
): Promise<string> {
  if (!existsSync(contentRoot)) {
    await mkdir(contentRoot, { recursive: true });
  }
  const filePath = join(contentRoot, `${input.date}-${input.slug}.mdx`);
  await writeFile(filePath, formatMediaArticle(input), 'utf-8');
  return filePath;
}
