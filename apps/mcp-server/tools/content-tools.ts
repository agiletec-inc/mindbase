/**
 * MindBase MCP Server - Content Tools
 *
 * Article generation and publishing tool handlers.
 */

import type { StorageBackend, ConversationItem } from '../storage/interface.js';
import { ArticleGenerator, type ConversationSource } from '../../../libs/generators/article-generator.js';
import { OpenAIClient } from '../../../libs/generators/llm-client.js';
import type { Platform } from '../../../libs/generators/platform-prompts.js';

export class ContentTools {
  constructor(private storage: StorageBackend) {}

  async contentGenerate(args: {
    topic: string;
    platform: 'qiita' | 'zenn' | 'note';
    conversationIds?: string[];
    style?: string;
  }): Promise<{
    title: string;
    content: string;
    platform: string;
    metadata: Record<string, any>;
  }> {
    let conversations: ConversationItem[] = [];

    if (args.conversationIds && args.conversationIds.length > 0) {
      for (const id of args.conversationIds) {
        const item = await this.storage.getById(id);
        if (item) conversations.push(item);
      }
    } else {
      const results = await this.storage.semanticSearch(args.topic, 10, 0.5);
      conversations = results.map((r) => r.item);
    }

    if (conversations.length === 0) {
      throw new Error(`No conversations found for topic: ${args.topic}`);
    }

    const sources: ConversationSource[] = conversations.map((c) => {
      const rawMessages = c.content?.messages || [];
      const messages = rawMessages
        .filter((m: any) => m.role === 'user' || m.role === 'assistant')
        .slice(0, 20)
        .map((m: any) => ({
          role: m.role as string,
          content: typeof m.content === 'string' ? m.content : JSON.stringify(m.content),
        }));

      return {
        title: c.title,
        source: c.source,
        date: c.createdAt instanceof Date
          ? c.createdAt.toISOString().split('T')[0]
          : String(c.createdAt).split('T')[0],
        messages,
      };
    });

    const llmClient = new OpenAIClient();
    const generator = new ArticleGenerator(llmClient);
    const article = await generator.generate({
      topic: args.topic,
      platform: args.platform as Platform,
      conversations: sources,
      style: args.style,
    });

    return {
      title: article.title,
      content: article.content,
      platform: args.platform,
      metadata: {
        ...article.metadata,
        sourceIds: conversations.map((c) => c.id),
        style: args.style || 'technical',
      },
    };
  }

  async contentPublish(args: {
    content: string;
    platform: 'qiita' | 'zenn' | 'note';
    title: string;
    tags?: string[];
    draft?: boolean;
  }): Promise<{
    success: boolean;
    platform: string;
    method: string;
    url?: string;
    filePath?: string;
    error?: string;
  }> {
    const { getPublisher } = await import('../../../libs/generators/publishers/index.js');

    const publisher = getPublisher(args.platform);
    const result = await publisher.publish(
      { title: args.title, content: args.content, tags: args.tags || [] },
      { draft: args.draft ?? true },
    );

    return {
      success: result.success,
      platform: args.platform,
      method: result.method,
      url: result.url,
      filePath: result.filePath,
      error: result.error,
    };
  }
}
