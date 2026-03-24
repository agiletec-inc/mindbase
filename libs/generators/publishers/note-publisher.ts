/**
 * Note.com Publisher
 *
 * Uses note.com's internal (unofficial) API with cookie-based authentication.
 * Falls back to file generation + clipboard copy if API auth is unavailable.
 *
 * Environment variables:
 *   NOTE_EMAIL    - note.com login email
 *   NOTE_PASSWORD - note.com login password
 */

import { writeFile, mkdir } from 'fs/promises';
import { join } from 'path';
import { homedir } from 'os';
import { existsSync } from 'fs';
import { execSync } from 'child_process';
import type { Article, PublishOptions, PublishResult, Publisher } from './publisher-interface.js';

const NOTE_API_BASE = 'https://note.com/api';
const NOTE_OUTPUT_DIR = join(homedir(), 'github', 'mindbase', 'generated', 'note');

/**
 * Convert markdown to simple HTML for note.com's API.
 * note.com expects HTML in the body field.
 */
function markdownToSimpleHtml(markdown: string): string {
  let html = markdown;

  // Headings
  html = html.replace(/^### (.+)$/gm, '<h3>$1</h3>');
  html = html.replace(/^## (.+)$/gm, '<h2>$1</h2>');
  html = html.replace(/^# (.+)$/gm, '<h1>$1</h1>');

  // Bold and italic
  html = html.replace(/\*\*(.+?)\*\*/g, '<strong>$1</strong>');
  html = html.replace(/\*(.+?)\*/g, '<em>$1</em>');

  // Code blocks
  html = html.replace(/```[\w]*\n([\s\S]*?)```/g, '<pre><code>$1</code></pre>');

  // Inline code
  html = html.replace(/`([^`]+)`/g, '<code>$1</code>');

  // Line breaks → paragraphs
  html = html
    .split('\n\n')
    .filter((p) => p.trim())
    .map((p) => {
      if (p.startsWith('<h') || p.startsWith('<pre>')) return p;
      return `<p>${p.replace(/\n/g, '<br>')}</p>`;
    })
    .join('\n');

  return html;
}

export class NotePublisher implements Publisher {
  private email: string | undefined;
  private password: string | undefined;
  private sessionCookie: string | undefined;

  constructor() {
    this.email = process.env.NOTE_EMAIL;
    this.password = process.env.NOTE_PASSWORD;
  }

  preview(article: Article): string {
    const tags = article.tags.map((t) => `#${t}`).join(' ');
    return `# ${article.title}\n\n${tags}\n\n---\n\n${article.content}`;
  }

  async publish(article: Article, options: PublishOptions): Promise<PublishResult> {
    // Try API if credentials are available
    if (this.email && this.password) {
      try {
        return await this.publishViaAPI(article, options);
      } catch (error) {
        const msg = error instanceof Error ? error.message : String(error);
        console.error(`note.com API publish failed: ${msg}. Falling back to file output.`);
      }
    }

    // Fallback: file + clipboard
    return this.publishToFile(article);
  }

  private async publishViaAPI(article: Article, options: PublishOptions): Promise<PublishResult> {
    // Step 1: Login to get session cookie
    if (!this.sessionCookie) {
      await this.login();
    }

    // Step 2: Create note
    const htmlBody = markdownToSimpleHtml(article.content);

    const response = await fetch(`${NOTE_API_BASE}/v3/notes`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'Cookie': this.sessionCookie!,
      },
      body: JSON.stringify({
        note_type: 'TextNote',
        name: article.title,
        body: htmlBody,
        status: options.draft ? 'draft' : 'published',
        hashtag_notes: article.tags.map((tag) => ({ hashtag: { name: tag } })),
      }),
    });

    if (!response.ok) {
      const errorText = await response.text();
      throw new Error(`note.com API error (${response.status}): ${errorText}`);
    }

    const data = await response.json() as { data?: { key?: string; id?: number } };
    const noteKey = data?.data?.key;
    const noteId = data?.data?.id;

    return {
      success: true,
      url: noteKey ? `https://note.com/notes/${noteKey}` : undefined,
      id: noteId ? String(noteId) : undefined,
      method: 'api',
    };
  }

  private async login(): Promise<void> {
    const response = await fetch(`${NOTE_API_BASE}/v1/sessions/sign_in`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        login: this.email,
        password: this.password,
      }),
    });

    if (!response.ok) {
      throw new Error(`note.com login failed (${response.status})`);
    }

    // Extract session cookie from Set-Cookie headers
    const cookies = response.headers.getSetCookie?.() || [];
    this.sessionCookie = cookies.join('; ');

    if (!this.sessionCookie) {
      throw new Error('No session cookie received from note.com login');
    }
  }

  private async publishToFile(article: Article): Promise<PublishResult> {
    if (!existsSync(NOTE_OUTPUT_DIR)) {
      await mkdir(NOTE_OUTPUT_DIR, { recursive: true });
    }

    const date = new Date().toISOString().split('T')[0];
    const slug = article.title
      .toLowerCase()
      .replace(/[^a-z0-9\u3000-\u9fff]/g, '-')
      .replace(/-+/g, '-')
      .substring(0, 40);
    const filename = `${date}-${slug}.md`;
    const filePath = join(NOTE_OUTPUT_DIR, filename);

    const formatted = this.preview(article);
    await writeFile(filePath, formatted, 'utf-8');

    // Try clipboard copy (macOS)
    try {
      execSync('pbcopy', { input: formatted });
    } catch {
      // Clipboard not available (Docker, Linux, etc.)
    }

    return {
      success: true,
      method: 'file',
      filePath,
    };
  }
}
