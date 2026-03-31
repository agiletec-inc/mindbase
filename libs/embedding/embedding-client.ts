/**
 * Shared embedding client — OpenAI primary with Ollama fallback.
 *
 * Used by both PostgresStorageBackend and FileSystemMemoryBackend
 * to eliminate duplicated embedding generation logic.
 */

export interface EmbeddingClientConfig {
  ollamaUrl: string;
  embeddingModel: string;
  openaiApiKey?: string;
  openaiModel?: string;
}

export class EmbeddingClient {
  private ollamaUrl: string;
  private embeddingModel: string;
  private openaiApiKey: string | undefined;
  private openaiModel: string;

  constructor(config: EmbeddingClientConfig) {
    this.ollamaUrl = config.ollamaUrl;
    this.embeddingModel = config.embeddingModel;
    this.openaiApiKey = config.openaiApiKey;
    this.openaiModel = config.openaiModel || 'text-embedding-3-large';
  }

  /**
   * Generate embedding vector for the given text.
   * Tries OpenAI first if configured, falls back to Ollama.
   */
  async generate(text: string): Promise<number[]> {
    if (this.openaiApiKey) {
      try {
        return await this.openaiEmbed(text);
      } catch (error) {
        console.error('OpenAI embedding failed, falling back to Ollama:', error);
      }
    }

    return await this.ollamaEmbed(text);
  }

  /**
   * Generate embedding, returning undefined on failure instead of throwing.
   * Useful for optional embedding contexts (e.g. memory storage without DB).
   */
  async generateOptional(text: string): Promise<number[] | undefined> {
    try {
      return await this.generate(text);
    } catch (error) {
      console.error('Failed to generate embedding:', error);
      return undefined;
    }
  }

  private async openaiEmbed(text: string): Promise<number[]> {
    const response = await fetch('https://api.openai.com/v1/embeddings', {
      method: 'POST',
      headers: {
        'Authorization': `Bearer ${this.openaiApiKey}`,
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({
        model: this.openaiModel,
        input: text,
      }),
    });

    if (!response.ok) {
      const errorText = await response.text();
      throw new Error(`OpenAI API error: ${response.status} ${errorText}`);
    }

    const data = await response.json() as { data: Array<{ embedding: number[]; index: number }> };
    return data.data[0].embedding;
  }

  private async ollamaEmbed(text: string): Promise<number[]> {
    const response = await fetch(`${this.ollamaUrl}/api/embeddings`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        model: this.embeddingModel,
        prompt: text,
      }),
    });

    if (!response.ok) {
      throw new Error(`Ollama API error: ${response.statusText}`);
    }

    const data = await response.json() as { embedding: number[] };
    return data.embedding;
  }
}
