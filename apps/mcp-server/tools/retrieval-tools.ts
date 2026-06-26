/**
 * MindBase MCP Server - Retrieval Tools
 *
 * Retrieval-pack assembly for article writing. NO LLM calls — this only
 * gathers, organizes, and budgets past conversations into a structured
 * context pack. The calling agent writes the actual content.
 */

import type { StorageBackend, ConversationItem } from '../storage/interface.js';

export type DraftPlatform = 'zenn' | 'qiita' | 'note' | 'blog';

export interface MindbaseDraftArgs {
  topic?: string;
  conversationIds?: string[];
  project?: string;
  source?: string;
  limit?: number;
  platform?: DraftPlatform;
  maxExcerptChars?: number;
  maxTotalChars?: number;
}

export interface DraftSource {
  id: string;
  title: string;
  source: string;
  project?: string;
  occurredAt: string;
  similarity?: number;
}

export interface DraftExcerpt {
  conversationId: string;
  occurredAt: string;
  text: string;
  truncated: boolean;
}

export interface DraftCoverage {
  found: number;
  included: number;
  truncatedCount: number;
  droppedIds: string[];
}

export interface DraftPack {
  frontmatterSkeleton: string;
  writingNotes: string[];
  sources: DraftSource[];
  excerpts: DraftExcerpt[];
  coverage: DraftCoverage;
}

const DEFAULT_LIMIT = 8;
const MAX_LIMIT = 20;
const DEFAULT_MAX_EXCERPT_CHARS = 1200;
const DEFAULT_MAX_TOTAL_CHARS = 24000;
/** Same threshold as content_generate's semantic search. */
const SEARCH_THRESHOLD = 0.5;

/**
 * Frontmatter skeletons mirror the field sets used by the publishers in
 * libs/generators/publishers/ (zenn-publisher.ts formatZennArticle,
 * qiita-publisher.ts preview, note-publisher.ts preview). The publishers do
 * not export their frontmatter builders, so the field sets are minimally
 * duplicated here — keep them in sync with those files.
 */
const FRONTMATTER_SKELETONS: Record<DraftPlatform, string> = {
  zenn: [
    '---',
    'title: "TODO: 記事タイトル（50文字以内、検索を意識した具体的な形）"',
    'emoji: "📝"',
    'type: "tech"',
    'topics: ["TODO-topic1", "TODO-topic2"]',
    'published: false',
    '---',
  ].join('\n'),
  qiita: [
    '---',
    'title: "TODO: 「〇〇で△△する方法」形式のタイトル"',
    'tags:',
    '  - name: "TODO-tag1"',
    '  - name: "TODO-tag2"',
    'private: true',
    '---',
  ].join('\n'),
  // note.com articles do not use YAML frontmatter (see note-publisher.ts
  // preview and platform-prompts.ts NOTE_PROMPT): title heading + hashtags.
  note: [
    '# TODO: タイトル（30文字以内、好奇心を刺激する形）',
    '',
    '#TODOタグ1 #TODOタグ2',
  ].join('\n'),
  blog: [
    '---',
    'title: "TODO: article title"',
    'date: "TODO: YYYY-MM-DD"',
    'tags: ["TODO-tag1", "TODO-tag2"]',
    'draft: true',
    '---',
  ].join('\n'),
};

/**
 * Platform conventions distilled from libs/generators/platform-prompts.ts
 * (source of truth for the full prompts).
 */
const WRITING_NOTES: Record<DraftPlatform, string[]> = {
  zenn: [
    '中〜上級エンジニア向けに正確で再現可能な手順を書く。環境情報（OS、言語バージョン等）を冒頭に明記する',
    'Zenn独自記法（:::message, :::details, :::warning）と言語指定・コメント付きコードブロックを活用する',
    '「問題 → 調査 → 解決 → 学び」の流れでまとめ、最後に要点を箇条書きにする',
  ],
  qiita: [
    '冒頭に「TL;DR」で結論を先出しし、環境・前提条件セクションを必ず置く',
    '手順は番号付きでコマンドはコピペ可能に。コードブロックにはファイル名を付ける',
    'エラーメッセージとその解決策をセットで示し、「参考リンク」セクションで締める',
  ],
  note: [
    '非エンジニア読者も想定し、専門用語は噛み砕いて「〜してみました」など柔らかい語尾で語りかける',
    'パラグラフは3行以内・空行多め・コードブロックは最小限にし、個人的な体験や感想を織り交ぜる',
    'リード文で「何が得られるか」を明示し、最後に「まとめ」と次のアクションを提示する',
  ],
  blog: [
    '対象読者と記事から得られるものを冒頭で明示する',
    '見出しで構造化し、コードブロックには言語指定を付ける',
  ],
};

function toIso(value: Date | string): string {
  return value instanceof Date ? value.toISOString() : new Date(value).toISOString();
}

function toTime(value: Date | string): number {
  return value instanceof Date ? value.getTime() : new Date(value).getTime();
}

/**
 * Extract full text from conversation content, following the same content
 * shape handling as content-tools.ts (content.messages with role/content).
 */
function extractText(item: ConversationItem): string {
  const rawMessages = item.content?.messages;
  if (Array.isArray(rawMessages) && rawMessages.length > 0) {
    return rawMessages
      .filter((m: any) => m.role === 'user' || m.role === 'assistant')
      .map((m: any) => `${m.role}: ${typeof m.content === 'string' ? m.content : JSON.stringify(m.content)}`)
      .join('\n');
  }
  return typeof item.content === 'string' ? item.content : JSON.stringify(item.content ?? '');
}

export class RetrievalTools {
  constructor(private storage: StorageBackend) {}

  async mindbaseDraft(args: MindbaseDraftArgs): Promise<DraftPack> {
    const hasTopic = typeof args.topic === 'string' && args.topic.trim().length > 0;
    const hasIds = Array.isArray(args.conversationIds) && args.conversationIds.length > 0;
    if (hasTopic === hasIds) {
      throw new Error('Exactly one of "topic" or "conversationIds" is required');
    }
    if (hasIds && (args.project || args.source)) {
      throw new Error('"project" and "source" filters are only valid with "topic"');
    }

    const limit = Math.min(Math.max(args.limit ?? DEFAULT_LIMIT, 1), MAX_LIMIT);
    const platform = args.platform ?? 'blog';
    if (!(platform in FRONTMATTER_SKELETONS)) {
      throw new Error(`Unknown platform: ${platform}. Supported: ${Object.keys(FRONTMATTER_SKELETONS).join(', ')}`);
    }
    const maxExcerptChars = args.maxExcerptChars ?? DEFAULT_MAX_EXCERPT_CHARS;
    const maxTotalChars = args.maxTotalChars ?? DEFAULT_MAX_TOTAL_CHARS;

    const droppedIds: string[] = [];
    let selected: Array<{ item: ConversationItem; similarity?: number }> = [];
    let found = 0;

    if (hasIds) {
      for (const id of args.conversationIds!) {
        const item = await this.storage.getById(id);
        if (item) {
          selected.push({ item });
        } else {
          // Requested but not found — surface instead of silently skipping.
          droppedIds.push(id);
        }
      }
      found = selected.length;
    } else {
      // Over-fetch when post-hoc filters apply (semanticSearch has no
      // project/source filters), so filtering does not starve the result set.
      const fetchLimit = args.project || args.source ? Math.min(limit * 3, 60) : limit;
      const results = await this.storage.semanticSearch(args.topic!, fetchLimit, SEARCH_THRESHOLD);

      let filtered = results;
      if (args.source) {
        filtered = filtered.filter((r) => r.item.source === args.source);
      }
      if (args.project) {
        filtered = filtered.filter((r) => r.item.metadata?.project === args.project);
      }
      found = filtered.length;
      selected = filtered.map((r) => ({ item: r.item, similarity: r.similarity }));
    }

    // Enforce limit visibly: anything beyond it goes to droppedIds.
    if (selected.length > limit) {
      for (const extra of selected.slice(limit)) {
        droppedIds.push(extra.item.id);
      }
      selected = selected.slice(0, limit);
    }

    // Chronological order (oldest first). The schema has no separate
    // occurred_at column; created_at is the conversation's occurrence time.
    selected.sort((a, b) => toTime(a.item.createdAt) - toTime(b.item.createdAt));

    const sources: DraftSource[] = [];
    const excerpts: DraftExcerpt[] = [];
    let truncatedCount = 0;
    let remaining = maxTotalChars;

    for (const { item, similarity } of selected) {
      if (remaining <= 0) {
        // Total budget exhausted — drop visibly.
        droppedIds.push(item.id);
        continue;
      }

      const fullText = extractText(item);
      const cap = Math.min(maxExcerptChars, remaining);
      const truncated = fullText.length > cap;
      const text = truncated ? fullText.slice(0, cap) : fullText;
      remaining -= text.length;
      if (truncated) truncatedCount++;

      const occurredAt = toIso(item.createdAt);
      sources.push({
        id: item.id,
        title: item.title,
        source: item.source,
        project: item.metadata?.project,
        occurredAt,
        similarity,
      });
      excerpts.push({ conversationId: item.id, occurredAt, text, truncated });
    }

    return {
      frontmatterSkeleton: FRONTMATTER_SKELETONS[platform],
      writingNotes: WRITING_NOTES[platform],
      sources,
      excerpts,
      coverage: {
        found,
        included: excerpts.length,
        truncatedCount,
        droppedIds,
      },
    };
  }
}
