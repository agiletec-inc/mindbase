/**
 * MindBase MCP Server - File System Memory Storage
 *
 * Markdown-based memory storage inspired by Serena's approach.
 * Stores memories as .md files in .mindbase/memories/
 */

import { promises as fs } from 'fs';
import { join, dirname, basename, extname } from 'path';
import { homedir } from 'os';
import type { Memory, MemoryMetadata, MemorySearchResult, MemoryStorageBackend } from './memory-interface.js';
import { Pool } from 'pg';

export class FileSystemMemoryBackend implements MemoryStorageBackend {
  private baseDir: string;
  private pool?: Pool;
  private ollamaUrl: string;
  private embeddingModel: string;

  constructor(
    baseDir?: string,
    connectionString?: string,
    ollamaUrl = 'http://localhost:11434',
    embeddingModel = 'qwen3-embedding:8b'
  ) {
    // Default: ~/Library/Application Support/mindbase/memories
    this.baseDir =
      baseDir || join(homedir(), 'Library', 'Application Support', 'mindbase', 'memories');
    this.ollamaUrl = ollamaUrl;
    this.embeddingModel = embeddingModel;

    // Optional: PostgreSQL for semantic search
    if (connectionString) {
      this.pool = new Pool({ connectionString });
    }
  }

  /**
   * Get memory directory path
   */
  getMemoryPath(name: string, project?: string): string {
    const fileName = name.endsWith('.md') ? name : `${name}.md`;

    if (project) {
      return join(this.baseDir, project, fileName);
    }

    return join(this.baseDir, fileName);
  }

  /**
   * Ensure memory directory exists
   */
  async ensureMemoryDir(project?: string): Promise<string> {
    const dir = project ? join(this.baseDir, project) : this.baseDir;
    await fs.mkdir(dir, { recursive: true });
    return dir;
  }

  /**
   * Parse markdown frontmatter and content
   */
  private parseFrontmatter(content: string): {
    frontmatter: Record<string, any>;
    body: string;
  } {
    const frontmatterRegex = /^---\n([\s\S]*?)\n---\n([\s\S]*)$/;
    const match = content.match(frontmatterRegex);

    if (!match) {
      return { frontmatter: {}, body: content };
    }

    const frontmatterText = match[1];
    const body = match[2];
    const frontmatter: Record<string, any> = {};

    // Simple YAML parsing (key: value)
    frontmatterText.split('\n').forEach((line) => {
      const [key, ...valueParts] = line.split(':');
      if (key && valueParts.length > 0) {
        const value = valueParts.join(':').trim();
        // Handle arrays (tags: [tag1, tag2])
        if (value.startsWith('[') && value.endsWith(']')) {
          frontmatter[key.trim()] = value
            .slice(1, -1)
            .split(',')
            .map((v) => v.trim());
        } else {
          frontmatter[key.trim()] = value;
        }
      }
    });

    return { frontmatter, body };
  }

  /**
   * Serialize memory to markdown with frontmatter
   */
  private serializeMemory(memory: Omit<Memory, 'embedding'>): string {
    const frontmatter: string[] = [];

    if (memory.category) {
      frontmatter.push(`category: ${memory.category}`);
    }
    if (memory.project) {
      frontmatter.push(`project: ${memory.project}`);
    }
    if (memory.tags && memory.tags.length > 0) {
      frontmatter.push(`tags: [${memory.tags.join(', ')}]`);
    }
    frontmatter.push(`createdAt: ${memory.createdAt.toISOString()}`);
    frontmatter.push(`updatedAt: ${memory.updatedAt.toISOString()}`);

    if (frontmatter.length === 0) {
      return memory.content;
    }

    return `---\n${frontmatter.join('\n')}\n---\n\n${memory.content}`;
  }

  /**
   * Generate embedding using Ollama
   */
  private async generateEmbedding(text: string): Promise<number[] | undefined> {
    if (!this.pool) {
      return undefined; // Skip embedding if no database
    }

    try {
      const response = await fetch(`${this.ollamaUrl}/api/embeddings`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          model: this.embeddingModel,
          prompt: text,
        }),
      });

      if (!response.ok) {
        console.error(`Ollama API error: ${response.statusText}`);
        return undefined;
      }

      const data = await response.json() as { embedding: number[] };
      // Truncate to 2000 dimensions (pgvector limit)
      return data.embedding.slice(0, 2000);
    } catch (error) {
      console.error('Failed to generate embedding:', error);
      return undefined;
    }
  }

  /**
   * Save memory to PostgreSQL
   */
  private async saveToDatabase(memory: Memory): Promise<void> {
    if (!this.pool) {
      return; // Skip database if not configured
    }

    const query = `
      INSERT INTO memories (name, content, category, project, tags, embedding, created_at, updated_at)
      VALUES ($1, $2, $3, $4, $5, $6, $7, $8)
      ON CONFLICT (name, project) DO UPDATE SET
        content = EXCLUDED.content,
        category = EXCLUDED.category,
        tags = EXCLUDED.tags,
        embedding = EXCLUDED.embedding,
        updated_at = EXCLUDED.updated_at
    `;

    await this.pool.query(query, [
      memory.name,
      memory.content,
      memory.category || null,
      memory.project || null,
      memory.tags || [],
      memory.embedding ? `[${memory.embedding.join(',')}]` : null,
      memory.createdAt,
      memory.updatedAt,
    ]);
  }

  /**
   * Write memory to both markdown and database
   */
  async writeMemory(
    name: string,
    content: string,
    options?: {
      category?: Memory['category'];
      project?: string;
      tags?: string[];
    }
  ): Promise<string> {
    const now = new Date();
    const filePath = this.getMemoryPath(name, options?.project);

    // Check if file exists to preserve createdAt
    let createdAt = now;
    try {
      const existing = await this.readMemory(name, options?.project);
      if (existing) {
        createdAt = existing.createdAt;
      }
    } catch {
      // New file, use current time
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

    // Generate embedding for database search
    const embedding = await this.generateEmbedding(content);

    // 1. Write to markdown file
    await this.ensureMemoryDir(options?.project);
    const markdown = this.serializeMemory(memory);
    await fs.writeFile(filePath, markdown, 'utf-8');

    // 2. Save to database with embedding
    await this.saveToDatabase({ ...memory, embedding });

    return filePath;
  }

  /**
   * Read memory by name
   */
  async readMemory(name: string, project?: string): Promise<Memory | null> {
    const filePath = this.getMemoryPath(name, project);

    try {
      const markdown = await fs.readFile(filePath, 'utf-8');
      const { frontmatter, body } = this.parseFrontmatter(markdown);

      return {
        name,
        content: body.trim(),
        category: frontmatter.category as Memory['category'],
        project: frontmatter.project || project,
        tags: frontmatter.tags,
        createdAt: frontmatter.createdAt ? new Date(frontmatter.createdAt) : new Date(),
        updatedAt: frontmatter.updatedAt ? new Date(frontmatter.updatedAt) : new Date(),
      };
    } catch (error) {
      // File doesn't exist, try database fallback
      if (this.pool) {
        const query = `SELECT * FROM memories WHERE name = $1 AND (project = $2 OR project IS NULL)`;
        const result = await this.pool.query(query, [name, project || null]);

        if (result.rows.length > 0) {
          const row = result.rows[0];
          return {
            name: row.name,
            content: row.content,
            category: row.category,
            project: row.project,
            tags: row.tags,
            createdAt: row.created_at,
            updatedAt: row.updated_at,
          };
        }
      }

      return null;
    }
  }

  /**
   * List all memories with optional filtering
   */
  async listMemories(filters?: {
    project?: string;
    category?: string;
    tags?: string[];
  }): Promise<MemoryMetadata[]> {
    const dir = filters?.project ? join(this.baseDir, filters.project) : this.baseDir;

    try {
      await fs.access(dir);
    } catch {
      return []; // Directory doesn't exist
    }

    const files = await fs.readdir(dir);
    const memories: MemoryMetadata[] = [];

    for (const file of files) {
      if (!file.endsWith('.md')) {
        continue;
      }

      const filePath = join(dir, file);
      const stats = await fs.stat(filePath);
      const content = await fs.readFile(filePath, 'utf-8');
      const { frontmatter } = this.parseFrontmatter(content);

      // Apply filters
      if (filters?.category && frontmatter.category !== filters.category) {
        continue;
      }
      if (
        filters?.tags &&
        (!frontmatter.tags ||
          !filters.tags.some((tag) => frontmatter.tags.includes(tag)))
      ) {
        continue;
      }

      memories.push({
        name: basename(file, '.md'),
        category: frontmatter.category,
        project: frontmatter.project || filters?.project,
        tags: frontmatter.tags,
        size: stats.size,
        createdAt: frontmatter.createdAt ? new Date(frontmatter.createdAt) : stats.birthtime,
        updatedAt: frontmatter.updatedAt ? new Date(frontmatter.updatedAt) : stats.mtime,
      });
    }

    return memories.sort((a, b) => b.updatedAt.getTime() - a.updatedAt.getTime());
  }

  /**
   * Delete memory from both markdown and database
   */
  async deleteMemory(name: string, project?: string): Promise<boolean> {
    const filePath = this.getMemoryPath(name, project);

    try {
      // Delete markdown file
      await fs.unlink(filePath);

      // Delete from database
      if (this.pool) {
        await this.pool.query(`DELETE FROM memories WHERE name = $1 AND (project = $2 OR project IS NULL)`, [
          name,
          project || null,
        ]);
      }

      return true;
    } catch {
      return false;
    }
  }

  /**
   * Semantic search across memories (requires database)
   */
  async searchMemories(
    query: string,
    options?: {
      limit?: number;
      threshold?: number;
      project?: string;
      category?: string;
    }
  ): Promise<MemorySearchResult[]> {
    if (!this.pool) {
      throw new Error('Database not configured for semantic search');
    }

    const limit = options?.limit ?? 10;
    const threshold = options?.threshold ?? 0.7;

    // Generate query embedding
    const queryEmbedding = await this.generateEmbedding(query);
    if (!queryEmbedding) {
      return [];
    }

    const conditions: string[] = ['embedding IS NOT NULL'];
    const params: any[] = [`[${queryEmbedding.join(',')}]`, threshold, limit];
    let paramIndex = 4;

    if (options?.project) {
      conditions.push(`project = $${paramIndex++}`);
      params.push(options.project);
    }

    if (options?.category) {
      conditions.push(`category = $${paramIndex++}`);
      params.push(options.category);
    }

    const whereClause = conditions.join(' AND ');
    const sqlQuery = `
      SELECT
        *,
        1 - (embedding <=> $1::vector) as similarity
      FROM memories
      WHERE ${whereClause}
        AND 1 - (embedding <=> $1::vector) > $2
      ORDER BY embedding <=> $1::vector
      LIMIT $3
    `;

    const result = await this.pool.query(sqlQuery, params);

    return result.rows.map((row) => ({
      memory: {
        name: row.name,
        content: row.content,
        category: row.category,
        project: row.project,
        tags: row.tags,
        createdAt: row.created_at,
        updatedAt: row.updated_at,
      },
      similarity: row.similarity,
      path: this.getMemoryPath(row.name, row.project),
    }));
  }

  /**
   * Close database connection
   */
  async close(): Promise<void> {
    if (this.pool) {
      await this.pool.end();
    }
  }
}
