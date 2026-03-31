/**
 * Shared markdown frontmatter parser and serializer.
 *
 * Consolidates duplicated frontmatter logic from:
 * - apps/mcp-server/storage/memory-fs.ts
 * - apps/cli/commands/publish.ts
 */

export interface ParsedFrontmatter {
  metadata: Record<string, any>;
  body: string;
}

/**
 * Parse YAML frontmatter from markdown content.
 *
 * Handles:
 * - Simple key: value pairs
 * - Arrays: [item1, item2]
 * - Quoted strings (strips quotes)
 * - Boolean values (true/false)
 */
export function parseFrontmatter(content: string): ParsedFrontmatter {
  const match = content.match(/^---\n([\s\S]*?)\n---\n([\s\S]*)$/);
  if (!match) return { metadata: {}, body: content };

  const metadata: Record<string, any> = {};
  for (const line of match[1].split('\n')) {
    const colonIndex = line.indexOf(':');
    if (colonIndex === -1) continue;

    const key = line.substring(0, colonIndex).trim();
    const rawValue = line.substring(colonIndex + 1).trim();
    const value = rawValue.replace(/^["']|["']$/g, '');

    if (value.startsWith('[') && value.endsWith(']')) {
      metadata[key] = value
        .slice(1, -1)
        .split(',')
        .map((v: string) => v.trim().replace(/^["']|["']$/g, ''));
    } else if (value === 'true') {
      metadata[key] = true;
    } else if (value === 'false') {
      metadata[key] = false;
    } else {
      metadata[key] = value;
    }
  }

  return { metadata, body: match[2] };
}

/**
 * Serialize metadata fields and body into markdown with YAML frontmatter.
 */
export function serializeFrontmatter(
  fields: Record<string, any>,
  body: string,
): string {
  const lines: string[] = [];

  for (const [key, value] of Object.entries(fields)) {
    if (value === undefined || value === null) continue;

    if (Array.isArray(value)) {
      lines.push(`${key}: [${value.join(', ')}]`);
    } else if (value instanceof Date) {
      lines.push(`${key}: ${value.toISOString()}`);
    } else {
      lines.push(`${key}: ${value}`);
    }
  }

  if (lines.length === 0) return body;

  return `---\n${lines.join('\n')}\n---\n\n${body}`;
}
