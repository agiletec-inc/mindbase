/**
 * Zenn Publisher
 *
 * Publishes via GitHub repository sync.
 * Writes article to Zenn content repo and pushes.
 * https://zenn.dev/zenn/articles/connect-to-github
 *
 * Environment variables:
 *   ZENN_REPO_PATH - Path to local Zenn content repository
 */

import { writeFile, mkdir } from 'fs/promises';
import { join } from 'path';
import { existsSync } from 'fs';
import { execSync } from 'child_process';
import type { Article, PublishOptions, PublishResult, Publisher } from './publisher-interface.js';

export class ZennPublisher implements Publisher {
  private repoPath: string | undefined;

  constructor() {
    this.repoPath = process.env.ZENN_REPO_PATH;
  }

  preview(article: Article): string {
    const topics = article.tags.slice(0, 5).map((t) => `"${t}"`).join(', ');
    return `---\ntitle: "${article.title}"\nemoji: "📝"\ntype: "tech"\ntopics: [${topics}]\npublished: false\n---\n\n${article.content}`;
  }

  async publish(article: Article, options: PublishOptions): Promise<PublishResult> {
    if (!this.repoPath) {
      throw new Error(
        'ZENN_REPO_PATH is required. Set it to your Zenn content repository path.'
      );
    }

    const articlesDir = join(this.repoPath, 'articles');
    if (!existsSync(articlesDir)) {
      await mkdir(articlesDir, { recursive: true });
    }

    const slug = this.generateSlug(article.title);
    const filePath = join(articlesDir, `${slug}.md`);
    const content = this.formatZennArticle(article, options);

    await writeFile(filePath, content, 'utf-8');

    // Git commit & push
    try {
      execSync(`git add "${filePath}"`, { cwd: this.repoPath });
      execSync(`git commit -m "article: ${article.title}"`, { cwd: this.repoPath });
      execSync('git push', { cwd: this.repoPath });
    } catch (error) {
      const msg = error instanceof Error ? error.message : String(error);
      return {
        success: true,
        method: 'git',
        filePath,
        error: `File written but git push failed: ${msg}. Push manually.`,
      };
    }

    return {
      success: true,
      url: `https://zenn.dev/articles/${slug}`,
      method: 'git',
      filePath,
    };
  }

  private generateSlug(title: string): string {
    const base = title
      .toLowerCase()
      .replace(/[^a-z0-9]/g, '-')
      .replace(/-+/g, '-')
      .replace(/^-|-$/g, '')
      .substring(0, 40);

    const date = new Date().toISOString().split('T')[0].replace(/-/g, '');
    return `${date}-${base}`.substring(0, 50);
  }

  private formatZennArticle(article: Article, options: PublishOptions): string {
    const topics = article.tags.slice(0, 5).map((t) => `"${t}"`).join(', ');
    const frontmatter = [
      '---',
      `title: "${article.title}"`,
      `emoji: "📝"`,
      `type: "tech"`,
      `topics: [${topics}]`,
      `published: ${options.draft === false ? 'true' : 'false'}`,
      '---',
    ].join('\n');

    return `${frontmatter}\n\n${article.content.trim()}\n`;
  }
}
