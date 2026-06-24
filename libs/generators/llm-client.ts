/**
 * LLM Client abstraction for article generation.
 *
 * Config-driven dual provider (mirrors the embedding strategy):
 *   LLM_PROVIDER=ollama (default, local — no API key) | openai
 * No implicit fallback — a misconfigured provider raises immediately.
 */

export interface LLMClient {
  generate(prompt: string, systemPrompt?: string): Promise<string>;
}

/** Strip <think>...</think> reasoning blocks emitted by thinking models (qwen3). */
function stripThinking(text: string): string {
  return text.replace(/<think>[\s\S]*?<\/think>/g, '').trim();
}

/**
 * Local LLM via Ollama (`/api/chat`). Default — needs no API key; talks to the
 * Ollama at OLLAMA_URL (host Metal or the self-hosted k3s instance over Tailscale).
 */
export class OllamaClient implements LLMClient {
  private url: string;
  private model: string;

  constructor(url?: string, model?: string) {
    this.url = url || process.env.OLLAMA_URL || 'http://localhost:11434';
    this.model = model || process.env.LLM_MODEL || 'qwen3:14b';
  }

  async generate(prompt: string, systemPrompt?: string): Promise<string> {
    const messages: Array<{ role: string; content: string }> = [];
    if (systemPrompt) {
      messages.push({ role: 'system', content: systemPrompt });
    }
    messages.push({ role: 'user', content: prompt });

    const response = await fetch(`${this.url}/api/chat`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        model: this.model,
        messages,
        stream: false,
        think: false,
        options: { temperature: 0.7, num_ctx: 16384, num_predict: 8192 },
      }),
    });

    if (!response.ok) {
      const errorText = await response.text();
      throw new Error(`Ollama API error (${response.status}): ${errorText}`);
    }

    const data = (await response.json()) as { message?: { content?: string } };
    const content = data.message?.content;
    if (!content) {
      throw new Error('Ollama returned empty response');
    }

    return stripThinking(content);
  }
}

export class OpenAIClient implements LLMClient {
  private apiKey: string;
  private model: string;

  constructor(apiKey?: string, model?: string) {
    this.apiKey = apiKey || process.env.OPENAI_API_KEY || '';
    this.model = model || process.env.LLM_MODEL || 'gpt-4o';

    if (!this.apiKey) {
      throw new Error(
        'OPENAI_API_KEY is required for article generation. ' +
        'Set it in your environment or .env file.'
      );
    }
  }

  async generate(prompt: string, systemPrompt?: string): Promise<string> {
    const messages: Array<{ role: string; content: string }> = [];

    if (systemPrompt) {
      messages.push({ role: 'system', content: systemPrompt });
    }
    messages.push({ role: 'user', content: prompt });

    const response = await fetch('https://api.openai.com/v1/chat/completions', {
      method: 'POST',
      headers: {
        'Authorization': `Bearer ${this.apiKey}`,
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({
        model: this.model,
        messages,
        temperature: 0.7,
        max_tokens: 4096,
      }),
    });

    if (!response.ok) {
      const errorText = await response.text();
      throw new Error(`OpenAI API error (${response.status}): ${errorText}`);
    }

    const data = await response.json() as {
      choices: Array<{ message: { content: string } }>;
    };

    const content = data.choices?.[0]?.message?.content;
    if (!content) {
      throw new Error('OpenAI returned empty response');
    }

    return content;
  }
}

/**
 * Create LLM client from environment. Defaults to local Ollama (no API key);
 * set LLM_PROVIDER=openai to opt into OpenAI.
 */
export function createLLMClient(): LLMClient {
  const provider = process.env.LLM_PROVIDER || 'ollama';
  switch (provider) {
    case 'ollama':
      return new OllamaClient();
    case 'openai':
      return new OpenAIClient();
    default:
      throw new Error(`Unknown LLM_PROVIDER: ${provider}. Supported: ollama, openai`);
  }
}
