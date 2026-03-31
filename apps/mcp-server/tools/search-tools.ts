/**
 * MindBase MCP Server - Search Tools
 *
 * Semantic and hybrid search tool handlers.
 */

import type { StorageBackend, ConversationItem, HybridSearchOptions } from '../storage/interface.js';

export class SearchTools {
  constructor(
    private storage: StorageBackend,
    private formatItem: (item: ConversationItem) => any,
  ) {}

  async conversationSearch(args: {
    query: string;
    threshold?: number;
    limit?: number;
    source?: string;
    recencyWeight?: number;
    recencyTauSeconds?: number;
    recencyBoostDays?: number;
    recencyBoostValue?: number;
  }): Promise<{
    items: any[];
    query: string;
    weights: { semantic: number; recency: number };
  }> {
    const threshold = args.threshold ?? 0.7;
    const limit = args.limit ?? 10;
    const recencyWeight = args.recencyWeight ?? 0.15;

    const results = await this.storage.semanticSearch(
      args.query,
      limit,
      threshold,
      recencyWeight,
      args.recencyTauSeconds ?? 1209600,
      args.recencyBoostDays ?? 3,
      args.recencyBoostValue ?? 0.05,
    );

    let filteredResults = results;
    if (args.source) {
      filteredResults = results.filter((r) => r.item.source === args.source);
    }

    return {
      items: filteredResults.map((result) => ({
        ...this.formatItem(result.item),
        similarity: result.similarity,
        semanticScore: result.semanticScore,
        recencyScore: result.recencyScore,
        combinedScore: result.combinedScore,
      })),
      query: args.query,
      weights: {
        semantic: 1 - recencyWeight,
        recency: recencyWeight,
      },
    };
  }

  async conversationHybridSearch(args: {
    query: string;
    keywordWeight?: number;
    semanticWeight?: number;
    recencyWeight?: number;
    threshold?: number;
    limit?: number;
    source?: string;
    recencyTauSeconds?: number;
    recencyBoostDays?: number;
    recencyBoostValue?: number;
  }): Promise<{
    items: any[];
    query: string;
    weights: { keyword: number; semantic: number; recency: number };
  }> {
    const options: HybridSearchOptions = {
      keywordWeight: args.keywordWeight ?? 0.30,
      semanticWeight: args.semanticWeight ?? 0.55,
      recencyWeight: args.recencyWeight ?? 0.15,
      threshold: args.threshold ?? 0.6,
      limit: args.limit ?? 10,
      recencyTauSeconds: args.recencyTauSeconds ?? 1209600,
      recencyBoostDays: args.recencyBoostDays ?? 3,
      recencyBoostValue: args.recencyBoostValue ?? 0.05,
    };

    const results = await this.storage.hybridSearch(args.query, options);

    let filteredResults = results;
    if (args.source) {
      filteredResults = results.filter((r) => r.item.source === args.source);
    }

    const kw = options.keywordWeight!;
    const sw = options.semanticWeight!;
    const rw = options.recencyWeight!;
    const sum = kw + sw + rw;

    return {
      items: filteredResults.map((result) => ({
        ...this.formatItem(result.item),
        keywordScore: result.keywordScore,
        semanticScore: result.semanticScore,
        recencyScore: result.recencyScore,
        combinedScore: result.combinedScore,
      })),
      query: args.query,
      weights: {
        keyword: kw / sum,
        semantic: sw / sum,
        recency: rw / sum,
      },
    };
  }
}
