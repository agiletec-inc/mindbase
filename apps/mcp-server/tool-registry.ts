/**
 * MindBase MCP Server - Tool Registry
 *
 * All MCP tool schema definitions in one place.
 */

import type { Tool } from '@modelcontextprotocol/sdk/types.js';

// Conversation tools
const CONVERSATION_TOOLS: Tool[] = [
  {
    name: 'conversation_save',
    description: 'Save a conversation with automatic embedding generation for semantic search',
    inputSchema: {
      type: 'object',
      properties: {
        source: {
          type: 'string',
          enum: ['claude-code', 'claude-desktop', 'chatgpt', 'cursor', 'windsurf', 'gemini'],
          description: 'Source platform of the conversation',
        },
        title: {
          type: 'string',
          description: 'Title or summary of the conversation',
        },
        content: {
          type: 'object',
          description: 'Conversation content (messages, context, etc.)',
        },
        metadata: {
          type: 'object',
          description: 'Additional metadata (project, tags, etc.)',
        },
        category: {
          type: 'string',
          enum: ['task', 'decision', 'progress', 'note', 'warning', 'error'],
          description: 'Conversation category',
        },
        priority: {
          type: 'string',
          enum: ['critical', 'high', 'normal', 'low'],
          description: 'Conversation priority',
        },
        channel: {
          type: 'string',
          description: 'Channel or workspace identifier',
        },
        sessionId: {
          type: 'string',
          description: 'Session ID to associate with (optional)',
        },
      },
      required: ['source', 'title', 'content'],
    },
  },
  {
    name: 'conversation_get',
    description: 'Retrieve conversations with filtering and pagination',
    inputSchema: {
      type: 'object',
      properties: {
        id: {
          type: 'string',
          description: 'Get specific conversation by ID',
        },
        source: {
          type: 'string',
          enum: ['claude-code', 'claude-desktop', 'chatgpt', 'cursor', 'windsurf', 'gemini'],
          description: 'Filter by source platform',
        },
        category: {
          type: 'string',
          enum: ['task', 'decision', 'progress', 'note', 'warning', 'error'],
          description: 'Filter by category',
        },
        priority: {
          type: 'string',
          enum: ['critical', 'high', 'normal', 'low'],
          description: 'Filter by priority',
        },
        channel: {
          type: 'string',
          description: 'Filter by channel',
        },
        sessionId: {
          type: 'string',
          description: 'Filter by session ID',
        },
        limit: {
          type: 'number',
          description: 'Maximum number of results (default: 100)',
        },
        offset: {
          type: 'number',
          description: 'Pagination offset (default: 0)',
        },
        createdAfter: {
          type: 'string',
          description: 'Filter by creation date (ISO 8601)',
        },
        createdBefore: {
          type: 'string',
          description: 'Filter by creation date (ISO 8601)',
        },
      },
    },
  },
  {
    name: 'conversation_search',
    description: 'Semantic search across conversations using pgvector cosine similarity with recency ranking',
    inputSchema: {
      type: 'object',
      properties: {
        query: {
          type: 'string',
          description: 'Search query (will be embedded for semantic search)',
        },
        threshold: {
          type: 'number',
          description: 'Similarity threshold 0-1 (default: 0.7)',
          minimum: 0,
          maximum: 1,
        },
        limit: {
          type: 'number',
          description: 'Maximum number of results (default: 10)',
        },
        source: {
          type: 'string',
          enum: ['claude-code', 'claude-desktop', 'chatgpt', 'cursor', 'windsurf', 'gemini'],
          description: 'Filter results by source platform',
        },
        recencyWeight: {
          type: 'number',
          description: 'Weight for recency in ranking (default: 0.15). Higher values favor recent conversations.',
          minimum: 0,
          maximum: 1,
        },
        recencyTauSeconds: {
          type: 'number',
          description: 'Decay time constant in seconds (default: 1209600 = 14 days)',
        },
        recencyBoostDays: {
          type: 'number',
          description: 'Days within which items get a recency boost (default: 3)',
        },
        recencyBoostValue: {
          type: 'number',
          description: 'Boost value for recent items (default: 0.05)',
          minimum: 0,
          maximum: 1,
        },
      },
      required: ['query'],
    },
  },
  {
    name: 'conversation_hybrid_search',
    description: 'Hybrid search combining keyword (full-text), semantic (vector), and recency with configurable weights. Weights are auto-normalized to sum to 1.0.',
    inputSchema: {
      type: 'object',
      properties: {
        query: {
          type: 'string',
          description: 'Search query (used for both keyword and semantic search)',
        },
        keywordWeight: {
          type: 'number',
          description: 'Weight for keyword search (default: 0.30). Normalized with other weights.',
          minimum: 0,
        },
        semanticWeight: {
          type: 'number',
          description: 'Weight for semantic search (default: 0.55). Normalized with other weights.',
          minimum: 0,
        },
        recencyWeight: {
          type: 'number',
          description: 'Weight for recency ranking (default: 0.15). Normalized with other weights.',
          minimum: 0,
        },
        threshold: {
          type: 'number',
          description: 'Minimum score threshold 0-1 (default: 0.6)',
          minimum: 0,
          maximum: 1,
        },
        limit: {
          type: 'number',
          description: 'Maximum number of results (default: 10)',
        },
        source: {
          type: 'string',
          enum: ['claude-code', 'claude-desktop', 'chatgpt', 'cursor', 'windsurf', 'gemini'],
          description: 'Filter results by source platform',
        },
        recencyTauSeconds: {
          type: 'number',
          description: 'Decay time constant in seconds (default: 1209600 = 14 days)',
        },
        recencyBoostDays: {
          type: 'number',
          description: 'Days within which items get a recency boost (default: 3)',
        },
        recencyBoostValue: {
          type: 'number',
          description: 'Boost value for recent items (default: 0.05)',
          minimum: 0,
          maximum: 1,
        },
      },
      required: ['query'],
    },
  },
  {
    name: 'conversation_delete',
    description: 'Delete a conversation by ID',
    inputSchema: {
      type: 'object',
      properties: {
        id: {
          type: 'string',
          description: 'Conversation ID to delete',
        },
      },
      required: ['id'],
    },
  },
];

// Session tools
const SESSION_TOOLS: Tool[] = [
  {
    name: 'session_create',
    description: 'Create a new session for organizing conversations',
    inputSchema: {
      type: 'object',
      properties: {
        name: {
          type: 'string',
          description: 'Session name',
        },
        description: {
          type: 'string',
          description: 'Session description',
        },
        parentId: {
          type: 'string',
          description: 'Parent session ID for hierarchical sessions',
        },
      },
      required: ['name'],
    },
  },
  {
    name: 'session_start',
    description: 'Start or resume a session (sets as current context)',
    inputSchema: {
      type: 'object',
      properties: {
        sessionId: {
          type: 'string',
          description: 'Existing session ID to resume',
        },
        name: {
          type: 'string',
          description: 'Name for new session (if not resuming)',
        },
        description: {
          type: 'string',
          description: 'Description for new session',
        },
      },
    },
  },
  {
    name: 'session_list',
    description: 'List recent sessions with metadata',
    inputSchema: {
      type: 'object',
      properties: {
        limit: {
          type: 'number',
          description: 'Maximum number of sessions (default: 10)',
        },
      },
    },
  },
  {
    name: 'session_delete',
    description: 'Delete a session (conversations will be orphaned, not deleted)',
    inputSchema: {
      type: 'object',
      properties: {
        id: {
          type: 'string',
          description: 'Session ID to delete',
        },
      },
      required: ['id'],
    },
  },
];

// Cross-source tools
const CROSS_SOURCE_TOOLS: Tool[] = [
  {
    name: 'conversation_timeline',
    description: 'Get a chronological timeline of conversations across all sources (claude-code, chatgpt, cursor, etc.)',
    inputSchema: {
      type: 'object',
      properties: {
        sources: {
          type: 'array',
          items: { type: 'string' },
          description: 'Filter by sources (e.g. ["claude-code", "chatgpt"]). Empty = all sources.',
        },
        project: {
          type: 'string',
          description: 'Filter by project name',
        },
        createdAfter: {
          type: 'string',
          description: 'Filter by creation date (ISO 8601)',
        },
        createdBefore: {
          type: 'string',
          description: 'Filter by creation date (ISO 8601)',
        },
        limit: {
          type: 'number',
          description: 'Maximum number of results (default: 50)',
        },
        offset: {
          type: 'number',
          description: 'Pagination offset (default: 0)',
        },
      },
    },
  },
  {
    name: 'conversation_topics',
    description: 'Get topic groups across all conversation sources. Shows which topics span multiple sources and time periods.',
    inputSchema: {
      type: 'object',
      properties: {
        limit: {
          type: 'number',
          description: 'Maximum number of topic groups (default: 20)',
        },
        minCount: {
          type: 'number',
          description: 'Minimum conversation count per topic (default: 1)',
        },
      },
    },
  },
];

// Content generation tools
const CONTENT_TOOLS: Tool[] = [
  {
    name: 'content_generate',
    description: 'Generate article draft from conversation data for Qiita, Zenn, or Note platforms',
    inputSchema: {
      type: 'object',
      properties: {
        topic: {
          type: 'string',
          description: 'Article topic (used for semantic search if no IDs provided)',
        },
        platform: {
          type: 'string',
          enum: ['qiita', 'zenn', 'note'],
          description: 'Target platform',
        },
        conversationIds: {
          type: 'array',
          items: { type: 'string' },
          description: 'Specific conversation IDs to use as source material (optional)',
        },
        style: {
          type: 'string',
          description: 'Writing style hint (e.g. "technical", "beginner-friendly", "essay")',
        },
      },
      required: ['topic', 'platform'],
    },
  },
  {
    name: 'content_publish',
    description: 'Publish generated article to target platform (note.com, Qiita, or Zenn)',
    inputSchema: {
      type: 'object',
      properties: {
        content: {
          type: 'string',
          description: 'Article content in markdown',
        },
        platform: {
          type: 'string',
          enum: ['qiita', 'zenn', 'note'],
          description: 'Target publishing platform',
        },
        title: {
          type: 'string',
          description: 'Article title',
        },
        tags: {
          type: 'array',
          items: { type: 'string' },
          description: 'Article tags/topics',
        },
        draft: {
          type: 'boolean',
          description: 'Publish as draft (default: true)',
        },
      },
      required: ['content', 'platform', 'title'],
    },
  },
];

// Memory tools
const MEMORY_TOOLS: Tool[] = [
  {
    name: 'memory_write',
    description: 'Write a memory to markdown file and database for future reference. Inspired by Serena MCP Server.',
    inputSchema: {
      type: 'object',
      properties: {
        name: {
          type: 'string',
          description: 'Memory name (becomes filename)',
        },
        content: {
          type: 'string',
          description: 'Markdown content of the memory',
        },
        category: {
          type: 'string',
          enum: ['architecture', 'decision', 'pattern', 'guide', 'onboarding', 'note'],
          description: 'Memory category',
        },
        project: {
          type: 'string',
          description: 'Project identifier (optional, for project-specific memories)',
        },
        tags: {
          type: 'array',
          items: { type: 'string' },
          description: 'Tags for categorization',
        },
      },
      required: ['name', 'content'],
    },
  },
  {
    name: 'memory_read',
    description: 'Read a memory by name from markdown file or database',
    inputSchema: {
      type: 'object',
      properties: {
        name: {
          type: 'string',
          description: 'Memory name to read',
        },
        project: {
          type: 'string',
          description: 'Project identifier (optional)',
        },
      },
      required: ['name'],
    },
  },
  {
    name: 'memory_list',
    description: 'List all available memories with optional filtering',
    inputSchema: {
      type: 'object',
      properties: {
        project: {
          type: 'string',
          description: 'Filter by project',
        },
        category: {
          type: 'string',
          enum: ['architecture', 'decision', 'pattern', 'guide', 'onboarding', 'note'],
          description: 'Filter by category',
        },
        tags: {
          type: 'array',
          items: { type: 'string' },
          description: 'Filter by tags (any match)',
        },
      },
    },
  },
  {
    name: 'memory_delete',
    description: 'Delete a memory from both markdown file and database',
    inputSchema: {
      type: 'object',
      properties: {
        name: {
          type: 'string',
          description: 'Memory name to delete',
        },
        project: {
          type: 'string',
          description: 'Project identifier (optional)',
        },
      },
      required: ['name'],
    },
  },
  {
    name: 'memory_search',
    description: 'Semantic search across memories using pgvector similarity',
    inputSchema: {
      type: 'object',
      properties: {
        query: {
          type: 'string',
          description: 'Search query',
        },
        limit: {
          type: 'number',
          description: 'Maximum number of results (default: 10)',
        },
        threshold: {
          type: 'number',
          description: 'Similarity threshold 0-1 (default: 0.7)',
          minimum: 0,
          maximum: 1,
        },
        project: {
          type: 'string',
          description: 'Filter by project',
        },
        category: {
          type: 'string',
          enum: ['architecture', 'decision', 'pattern', 'guide', 'onboarding', 'note'],
          description: 'Filter by category',
        },
      },
      required: ['query'],
    },
  },
];

/** All registered MCP tools */
export const TOOLS: Tool[] = [
  ...CONVERSATION_TOOLS,
  ...SESSION_TOOLS,
  ...CROSS_SOURCE_TOOLS,
  ...CONTENT_TOOLS,
  ...MEMORY_TOOLS,
];
