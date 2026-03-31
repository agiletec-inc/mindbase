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
} from '@modelcontextprotocol/sdk/types.js';
import { PostgresStorageBackend } from './storage/postgres.js';
import { FileSystemMemoryBackend } from './storage/memory-fs.js';
import { ConversationTools } from './tools/conversation.js';
import { MemoryTools } from './tools/memory.js';
import { loadConfig } from './config.js';
import { TOOLS } from './tool-registry.js';
import { createDispatcher, dispatch } from './tool-dispatcher.js';

const config = loadConfig();

class MindBaseMCPServer {
  private server: Server;
  private storage: PostgresStorageBackend;
  private memoryStorage: FileSystemMemoryBackend;

  constructor() {
    this.server = new Server(
      { name: 'mindbase-mcp-server', version: '1.1.0' },
      { capabilities: { tools: {} } },
    );

    this.storage = new PostgresStorageBackend(config.databaseUrl, config.ollamaUrl, config.embeddingModel);
    this.memoryStorage = new FileSystemMemoryBackend(
      config.memoryBaseDir,
      config.databaseUrl,
      config.ollamaUrl,
      config.embeddingModel,
    );

    const tools = new ConversationTools(this.storage);
    const memoryTools = new MemoryTools(this.memoryStorage);
    const dispatcher = createDispatcher(tools, memoryTools);

    this.server.setRequestHandler(ListToolsRequestSchema, async () => ({
      tools: TOOLS,
    }));

    this.server.setRequestHandler(CallToolRequestSchema, async (request) => {
      const { name, arguments: args } = request.params;
      console.error(`[MindBase MCP] Tool called: ${name}`);

      try {
        const result = await dispatch(dispatcher, name, args);
        return {
          content: [{ type: 'text', text: JSON.stringify(result, null, 2) }],
        };
      } catch (error) {
        const errorMessage = error instanceof Error ? error.message : String(error);
        console.error(`[MindBase MCP] Error in ${name}:`, errorMessage);
        return {
          content: [{ type: 'text', text: JSON.stringify({ error: errorMessage }, null, 2) }],
          isError: true,
        };
      }
    });

    process.on('SIGINT', () => this.cleanup());
    process.on('SIGTERM', () => this.cleanup());
  }

  async run() {
    try {
      await this.storage.initialize();
    } catch (error) {
      const errorMessage = error instanceof Error ? error.message : String(error);
      console.error('[MindBase MCP] Failed to initialize database schema:', errorMessage);
      console.error('[MindBase MCP] Server will continue but database operations may fail');
    }

    const transport = new StdioServerTransport();
    await this.server.connect(transport);
    console.error('[MindBase MCP] Server running on stdio');
    console.error(`[MindBase MCP] Database: ${config.databaseUrl.replace(/:[^:]*@/, ':****@')}`);
    console.error(`[MindBase MCP] Ollama: ${config.ollamaUrl}`);
    console.error(`[MindBase MCP] Model: ${config.embeddingModel}`);
    console.error(`[MindBase MCP] OpenAI: ${config.openaiApiKey ? 'configured' : 'not configured (Ollama only)'}`);
  }

  private async cleanup() {
    console.error('[MindBase MCP] Shutting down...');
    await this.storage.close();
    await this.memoryStorage.close();
    process.exit(0);
  }
}

const server = new MindBaseMCPServer();
server.run().catch((error) => {
  console.error('[MindBase MCP] Fatal error:', error);
  process.exit(1);
});
