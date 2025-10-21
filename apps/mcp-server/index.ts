#!/usr/bin/env node
/**
 * MindBase MCP Server
 *
 * Model Context Protocol server for AI conversation knowledge management.
 * Provides tools for storing, searching, and managing conversations with
 * PostgreSQL + pgvector for semantic search.
 */

import { Server } from '@modelcontextprotocol/sdk/server/index.js';
import { StdioServerTransport } from '@modelcontextprotocol/sdk/server/stdio.js';
import {
  CallToolRequestSchema,
  ListToolsRequestSchema,
  Tool,
} from '@modelcontextprotocol/sdk/types.js';
import { PostgresStorageBackend } from './storage/postgres.js';
import { FileSystemMemoryBackend } from './storage/memory-fs.js';
import { ConversationTools } from './tools/conversation.js';
import { MemoryTools } from './tools/memory.js';

// Environment variables
// ⚠️ WARNING: NEVER hardcode ports, URLs, or connection strings.
// All configuration MUST come from environment variables.
const DATABASE_URL = process.env.DATABASE_URL;
const OLLAMA_URL = process.env.OLLAMA_URL;
const EMBEDDING_MODEL = process.env.EMBEDDING_MODEL;
const MEMORY_BASE_DIR = process.env.MEMORY_BASE_DIR;

if (!DATABASE_URL || !OLLAMA_URL || !EMBEDDING_MODEL) {
  console.error('ERROR: Required environment variables not set:');
  if (!DATABASE_URL) console.error('  - DATABASE_URL');
  if (!OLLAMA_URL) console.error('  - OLLAMA_URL');
  if (!EMBEDDING_MODEL) console.error('  - EMBEDDING_MODEL');
  console.error('\nSee .env.example for required configuration.');
  process.exit(1);
}

// Tool definitions
const TOOLS: Tool[] = [
  {
    name: 'conversation_save',
    description: 'Save a conversation with automatic embedding generation for semantic search',
    inputSchema: {
      type: 'object',
      properties: {
        source: {
          type: 'string',
          enum: ['claude-code', 'claude-desktop', 'chatgpt', 'cursor', 'windsurf'],
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
          enum: ['claude-code', 'claude-desktop', 'chatgpt', 'cursor', 'windsurf'],
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
    description: 'Semantic search across conversations using pgvector cosine similarity',
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
          enum: ['claude-code', 'claude-desktop', 'chatgpt', 'cursor', 'windsurf'],
          description: 'Filter results by source platform',
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
  // Memory Management Tools (Serena-inspired)
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

/**
 * Main MCP Server class
 */
class MindBaseMCPServer {
  private server: Server;
  private storage: PostgresStorageBackend;
  private memoryStorage: FileSystemMemoryBackend;
  private tools: ConversationTools;
  private memoryTools: MemoryTools;

  constructor() {
    // Initialize MCP server
    this.server = new Server(
      {
        name: 'mindbase-mcp-server',
        version: '1.0.0',
      },
      {
        capabilities: {
          tools: {},
        },
      }
    );

    // Initialize storage and tools
    this.storage = new PostgresStorageBackend(DATABASE_URL, OLLAMA_URL, EMBEDDING_MODEL);
    this.memoryStorage = new FileSystemMemoryBackend(
      MEMORY_BASE_DIR,
      DATABASE_URL,
      OLLAMA_URL,
      EMBEDDING_MODEL
    );
    this.tools = new ConversationTools(this.storage);
    this.memoryTools = new MemoryTools(this.memoryStorage);

    // Setup request handlers
    this.setupHandlers();

    // Handle cleanup on exit
    process.on('SIGINT', () => this.cleanup());
    process.on('SIGTERM', () => this.cleanup());
  }

  /**
   * Setup MCP request handlers
   */
  private setupHandlers() {
    // List available tools
    this.server.setRequestHandler(ListToolsRequestSchema, async () => ({
      tools: TOOLS,
    }));

    // Handle tool calls
    this.server.setRequestHandler(CallToolRequestSchema, async (request) => {
      const { name, arguments: args } = request.params;

      console.error(`[MindBase MCP] Tool called: ${name}`);

      try {
        let result: any;

        switch (name) {
          case 'conversation_save':
            result = await this.tools.conversationSave(args as any);
            break;

          case 'conversation_get':
            result = await this.tools.conversationGet(args as any);
            break;

          case 'conversation_search':
            result = await this.tools.conversationSearch(args as any);
            break;

          case 'conversation_delete':
            result = await this.tools.conversationDelete(args as any);
            break;

          case 'session_create':
            result = await this.tools.sessionCreate(args as any);
            break;

          case 'session_start':
            result = await this.tools.sessionStart(args as any);
            break;

          case 'session_list':
            result = await this.tools.sessionList(args as any);
            break;

          case 'session_delete':
            result = await this.tools.sessionDelete(args as any);
            break;

          // Memory tools
          case 'memory_write':
            result = await this.memoryTools.memoryWrite(args as any);
            break;

          case 'memory_read':
            result = await this.memoryTools.memoryRead(args as any);
            break;

          case 'memory_list':
            result = await this.memoryTools.memoryList(args as any);
            break;

          case 'memory_delete':
            result = await this.memoryTools.memoryDelete(args as any);
            break;

          case 'memory_search':
            result = await this.memoryTools.memorySearch(args as any);
            break;

          default:
            throw new Error(`Unknown tool: ${name}`);
        }

        return {
          content: [
            {
              type: 'text',
              text: JSON.stringify(result, null, 2),
            },
          ],
        };
      } catch (error) {
        const errorMessage = error instanceof Error ? error.message : String(error);
        console.error(`[MindBase MCP] Error in ${name}:`, errorMessage);

        return {
          content: [
            {
              type: 'text',
              text: JSON.stringify({ error: errorMessage }, null, 2),
            },
          ],
          isError: true,
        };
      }
    });
  }

  /**
   * Start the MCP server
   */
  async run() {
    const transport = new StdioServerTransport();
    await this.server.connect(transport);
    console.error('[MindBase MCP] Server running on stdio');
    console.error(`[MindBase MCP] Database: ${DATABASE_URL.replace(/:[^:]*@/, ':****@')}`);
    console.error(`[MindBase MCP] Ollama: ${OLLAMA_URL}`);
    console.error(`[MindBase MCP] Model: ${EMBEDDING_MODEL}`);
  }

  /**
   * Cleanup resources
   */
  private async cleanup() {
    console.error('[MindBase MCP] Shutting down...');
    await this.storage.close();
    await this.memoryStorage.close();
    process.exit(0);
  }
}

// Start server
const server = new MindBaseMCPServer();
server.run().catch((error) => {
  console.error('[MindBase MCP] Fatal error:', error);
  process.exit(1);
});
