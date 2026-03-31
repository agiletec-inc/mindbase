/**
 * MindBase MCP Server - File System Memory Storage
 *
 * Markdown-based memory storage with optional PostgreSQL for semantic search.
 * Delegates embedding to shared EmbeddingClient and DB ops to MemoryDBRepository.
 */

import { promises as fs } from 'fs';
import { join, basename } from 'path';
import { homedir } from 'os';
import type { Memory, MemoryMetadata, MemorySearchResult, MemoryStorageBackend } from './memory-interface.js';
import { Pool } from 'pg';
import { EmbeddingClient } from '../../../libs/embedding/embedding-client.js';
import { parseFrontmatter, serializeFrontmatter } from '../../../libs/markdown/frontmatter.js';
import { MemoryDBRepository } from './memory-db-repository.js';

export class FileSystemMemoryBackend implements MemoryStorageBackend {
  private baseDir: string;
  private pool?: Pool;
  private embeddingClient?: EmbeddingClient;
  private dbRepo?: MemoryDBRepository;

  constructor(
    baseDir?: string,
    connectionString?: string,
    ollamaUrl?: string,
    embeddingModel?: string,
  ) {
    this.baseDir =
      baseDir || join(homedir(), 'Library', 'Application Support', 'mindbase', 'memories');

    if (connectionString) {
      this.pool = new Pool({ connectionString });
    }

    if (ollamaUrl && embeddingModel) {
      this.embeddingClient = new EmbeddingClient({
        ollamaUrl,
        embeddingModel,
        openaiApiKey: process.env.OPENAI_API_KEY || undefined,
        openaiModel: process.env.OPENAI_EMBEDDING_MODEL || 'text-embedding-3-large',
      });
    }

    if (this.pool && this.embeddingClient) {
      this.dbRepo = new MemoryDBRepository(
        this.pool,
        this.embeddingClient,
        (name, project) => this.getMemoryPath(name, project),
      );
    }
  }

  getMemoryPath(name: string, project?: string): string {
    const fileName = name.endsWith('.md') ? name : `${name}.md`;
    return project ? join(this.baseDir, project, fileName) : join(this.baseDir, fileName);
  }

  async ensureMemoryDir(project?: string): Promise<string> {
    const dir = project ? join(this.baseDir, project) : this.baseDir;
    await fs.mkdir(dir, { recursive: true });
    return dir;
  }

  async writeMemory(
    name: string,
    content: string,
    options?: { category?: Memory['category']; project?: string; tags?: string[] },
  ): Promise<string> {
    const now = new Date();
    const filePath = this.getMemoryPath(name, options?.project);

    let createdAt = now;
    try {
      const existing = await this.readMemory(name, options?.project);
      if (existing) createdAt = existing.createdAt;
    } catch {
      // New file
    }

    const memory: Omit<Memory, 'embedding'> = {
      name,
      content,
      category: options?.category,
      project: options?.project,
      tags: options?.tags,
      createdAt,
      updatedAt: now,
    };

    const embedding = this.embeddingClient
      ? await this.embeddingClient.generateOptional(content)
      : undefined;

    // Write markdown file
    await this.ensureMemoryDir(options?.project);
    const fields: Record<string, any> = {};
    if (memory.category) fields.category = memory.category;
    if (memory.project) fields.project = memory.project;
    if (memory.tags && memory.tags.length > 0) fields.tags = memory.tags;
    fields.createdAt = memory.createdAt;
    fields.updatedAt = memory.updatedAt;
    const markdown = serializeFrontmatter(fields, memory.content);
    await fs.writeFile(filePath, markdown, 'utf-8');

    // Save to database
    if (this.dbRepo) {
      await this.dbRepo.saveToDatabase({ ...memory, embedding });
    }

    return filePath;
  }

  async readMemory(name: string, project?: string): Promise<Memory | null> {
    const filePath = this.getMemoryPath(name, project);

    try {
      const markdown = await fs.readFile(filePath, 'utf-8');
      const { metadata, body } = parseFrontmatter(markdown);

      return {
        name,
        content: body.trim(),
        category: metadata.category as Memory['category'],
        project: metadata.project || project,
        tags: metadata.tags,
        createdAt: metadata.createdAt ? new Date(metadata.createdAt) : new Date(),
        updatedAt: metadata.updatedAt ? new Date(metadata.updatedAt) : new Date(),
      };
    } catch {
      // File doesn't exist, try database fallback
      if (this.dbRepo) {
        return this.dbRepo.findByName(name, project);
      }
      return null;
    }
  }

  async listMemories(filters?: {
    project?: string;
    category?: string;
    tags?: string[];
  }): Promise<MemoryMetadata[]> {
    const dir = filters?.project ? join(this.baseDir, filters.project) : this.baseDir;

    try {
      await fs.access(dir);
    } catch {
      return [];
    }

    const files = await fs.readdir(dir);
    const memories: MemoryMetadata[] = [];

    for (const file of files) {
      if (!file.endsWith('.md')) continue;

      const filePath = join(dir, file);
      const stats = await fs.stat(filePath);
      const content = await fs.readFile(filePath, 'utf-8');
      const { metadata } = parseFrontmatter(content);

      if (filters?.category && metadata.category !== filters.category) continue;
      if (filters?.tags && (!metadata.tags || !filters.tags.some((tag) => metadata.tags.includes(tag)))) continue;

      memories.push({
        name: basename(file, '.md'),
        category: metadata.category,
        project: metadata.project || filters?.project,
        tags: metadata.tags,
        size: stats.size,
        createdAt: metadata.createdAt ? new Date(metadata.createdAt) : stats.birthtime,
        updatedAt: metadata.updatedAt ? new Date(metadata.updatedAt) : stats.mtime,
      });
    }

    return memories.sort((a, b) => b.updatedAt.getTime() - a.updatedAt.getTime());
  }

  async deleteMemory(name: string, project?: string): Promise<boolean> {
    const filePath = this.getMemoryPath(name, project);

    try {
      await fs.unlink(filePath);
      if (this.dbRepo) {
        await this.dbRepo.deleteByName(name, project);
      }
      return true;
    } catch {
      return false;
    }
  }

  async searchMemories(
    query: string,
    options?: { limit?: number; threshold?: number; project?: string; category?: string },
  ): Promise<MemorySearchResult[]> {
    if (!this.dbRepo) {
      throw new Error('Database not configured for semantic search');
    }
    return this.dbRepo.searchMemories(query, options);
  }

  async close(): Promise<void> {
    if (this.pool) {
      await this.pool.end();
    }
  }
}
