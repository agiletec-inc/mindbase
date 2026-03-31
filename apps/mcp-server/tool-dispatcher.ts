/**
 * MindBase MCP Server - Tool Dispatcher
 *
 * Routes tool calls to the appropriate handler.
 */

import type { ConversationTools } from './tools/conversation.js';
import type { MemoryTools } from './tools/memory.js';

type ToolHandler = (args: any) => Promise<any>;

/**
 * Build a name→handler map from conversation and memory tool instances.
 */
export function createDispatcher(
  tools: ConversationTools,
  memoryTools: MemoryTools,
): Record<string, ToolHandler> {
  return {
    // Conversation CRUD
    conversation_save: (args) => tools.conversationSave(args),
    conversation_get: (args) => tools.conversationGet(args),
    conversation_delete: (args) => tools.conversationDelete(args),

    // Search
    conversation_search: (args) => tools.conversationSearch(args),
    conversation_hybrid_search: (args) => tools.conversationHybridSearch(args),

    // Sessions
    session_create: (args) => tools.sessionCreate(args),
    session_start: (args) => tools.sessionStart(args),
    session_list: (args) => tools.sessionList(args),
    session_delete: (args) => tools.sessionDelete(args),

    // Cross-source
    conversation_timeline: (args) => tools.conversationTimeline(args),
    conversation_topics: (args) => tools.conversationTopics(args),

    // Content generation
    content_generate: (args) => tools.contentGenerate(args),
    content_publish: (args) => tools.contentPublish(args),

    // Memory
    memory_write: (args) => memoryTools.memoryWrite(args),
    memory_read: (args) => memoryTools.memoryRead(args),
    memory_list: (args) => memoryTools.memoryList(args),
    memory_delete: (args) => memoryTools.memoryDelete(args),
    memory_search: (args) => memoryTools.memorySearch(args),
  };
}

/**
 * Dispatch a tool call by name.
 * Throws if the tool name is unknown.
 */
export async function dispatch(
  dispatcher: Record<string, ToolHandler>,
  name: string,
  args: any,
): Promise<any> {
  const handler = dispatcher[name];
  if (!handler) {
    throw new Error(`Unknown tool: ${name}`);
  }
  return handler(args);
}
