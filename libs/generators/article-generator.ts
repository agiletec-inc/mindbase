/**
 * Article Generator — LLM-based article generation from conversation data.
 *
 * Replaces the template-based generate-article.ts with actual LLM generation.
 */

import type { LLMClient } from './llm-client.js';
import { getPlatformPrompt, type Platform } from './platform-prompts.js';

export interface ConversationSource {
  title: string;
  source: string;
  date: string;
  messages: Array<{ role: string; content: string }>;
}

export interface GeneratedArticle {
  title: string;
  content: string;
  platform: Platform;
  metadata: {
    sourceConversations: number;
    generatedAt: string;
    model: string;
  };
}

export interface ArticleGeneratorOptions {
  topic: string;
  platform: Platform;
  conversations: ConversationSource[];
  style?: string;
}

export class ArticleGenerator {
  constructor(private llm: LLMClient) {}

  async generate(options: ArticleGeneratorOptions): Promise<GeneratedArticle> {
    if (options.conversations.length === 0) {
      throw new Error('No conversations provided for article generation');
    }

    // Prepare conversation summary for context
    const conversationContext = this.prepareContext(options.conversations);

    // Build user prompt
    const userPrompt = this.buildUserPrompt(options.topic, conversationContext, options.style);

    // Get platform system prompt
    const systemPrompt = getPlatformPrompt(options.platform);

    // Generate article via LLM
    const content = await this.llm.generate(userPrompt, systemPrompt);

    // Extract title from generated content
    const title = this.extractTitle(content, options.topic);

    return {
      title,
      content,
      platform: options.platform,
      metadata: {
        sourceConversations: options.conversations.length,
        generatedAt: new Date().toISOString(),
        model: process.env.LLM_MODEL || 'gpt-4o',
      },
    };
  }

  private prepareContext(conversations: ConversationSource[]): string {
    const sections: string[] = [];

    for (const conv of conversations) {
      const msgs = conv.messages
        .filter((m) => m.role === 'user' || m.role === 'assistant')
        .slice(0, 15) // Limit messages per conversation
        .map((m) => {
          const truncated = m.content.length > 800
            ? m.content.substring(0, 800) + '...'
            : m.content;
          return `[${m.role}]: ${truncated}`;
        });

      if (msgs.length > 0) {
        sections.push(
          `=== 会話: ${conv.title} (${conv.source}, ${conv.date}) ===\n${msgs.join('\n\n')}`
        );
      }
    }

    return sections.join('\n\n---\n\n');
  }

  private buildUserPrompt(topic: string, context: string, style?: string): string {
    let prompt = `以下の実際の技術会話データを元に、「${topic}」についての記事を書いてください。\n\n`;

    if (style) {
      prompt += `スタイルの指定: ${style}\n\n`;
    }

    prompt += `【会話データ（素材）】\n\n${context}\n\n`;
    prompt += `【指示】\n`;
    prompt += `- 会話データから得られた知見・学びを記事として再構成してください\n`;
    prompt += `- 会話そのものを転記するのではなく、読者にとって価値のある記事にまとめてください\n`;
    prompt += `- 具体的なコード例や手順があれば含めてください\n`;
    prompt += `- 会話から分かる実践的なtipsやハマりポイントを盛り込んでください\n`;
    prompt += `- 記事は2000〜4000文字程度を目安に\n`;

    return prompt;
  }

  private extractTitle(content: string, fallbackTopic: string): string {
    // Try to extract title from frontmatter
    const fmMatch = content.match(/^---\n[\s\S]*?title:\s*"?([^"\n]+)"?\n[\s\S]*?---/);
    if (fmMatch) {
      return fmMatch[1].trim();
    }

    // Try to extract from first heading
    const h1Match = content.match(/^#\s+(.+)$/m);
    if (h1Match) {
      return h1Match[1].trim();
    }

    return fallbackTopic;
  }
}
