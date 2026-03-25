/**
 * LLM Client abstraction for article generation.
 *
 * Primary: OpenAI GPT-4o
 * No fallback — if OPENAI_API_KEY is missing, throw immediately.
 */

export interface LLMClient {
  generate(prompt: string, systemPrompt?: string): Promise<string>;
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
 * Create LLM client from environment.
 */
export function createLLMClient(): LLMClient {
  return new OpenAIClient();
}
