/**
 * Qiita Publisher
 *
 * Uses Qiita's official REST API v2.
 * https://qiita.com/api/v2/docs
 *
 * Environment variables:
 *   QIITA_TOKEN - Qiita personal access token
 */

import type { Article, PublishOptions, PublishResult, Publisher } from './publisher-interface.js';

const QIITA_API_ENDPOINT = 'https://qiita.com/api/v2/items';

export class QiitaPublisher implements Publisher {
  private token: string | undefined;

  constructor() {
    this.token = process.env.QIITA_TOKEN;
  }

  preview(article: Article): string {
    const tags = article.tags.map((t) => `- name: "${t}"`).join('\n  ');
    return `---\ntitle: "${article.title}"\ntags:\n  ${tags}\nprivate: true\n---\n\n${article.content}`;
  }

  async publish(article: Article, options: PublishOptions): Promise<PublishResult> {
    if (!this.token) {
      throw new Error(
        'QIITA_TOKEN is required. Get your token at: https://qiita.com/settings/tokens/new'
      );
    }

    const body = {
      title: article.title,
      body: article.content,
      tags: article.tags.slice(0, 5).map((name) => ({ name })),
      private: options.draft ?? true,
      tweet: false,
    };

    const response = await fetch(QIITA_API_ENDPOINT, {
      method: 'POST',
      headers: {
        'Authorization': `Bearer ${this.token}`,
        'Content-Type': 'application/json',
      },
      body: JSON.stringify(body),
    });

    if (!response.ok) {
      const errorText = await response.text();
      throw new Error(`Qiita API error (${response.status}): ${errorText}`);
    }

    const data = await response.json() as { id: string; url: string };

    return {
      success: true,
      url: data.url,
      id: data.id,
      method: 'api',
    };
  }
}
