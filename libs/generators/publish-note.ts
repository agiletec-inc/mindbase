#!/usr/bin/env node
/**
 * Note Auto Publisher
 *
 * Purpose: Publish articles to note.com via API
 * Input: ~/github/mindbase/generated/*.md
 * API: https://note.com/api (unofficial — note does not provide public API)
 *
 * Strategy:
 *   1. Generate note-optimized markdown
 *   2. Output to clipboard or file for manual paste
 *   3. Future: Use note API when/if available
 */

import { readFile, writeFile, mkdir } from 'fs/promises'
import { join } from 'path'
import { homedir } from 'os'
import { existsSync } from 'fs'
import { execSync } from 'child_process'

interface NoteArticle {
  title: string
  body: string
  status: 'draft' | 'published'
  tags: string[]
  category: 'text' | 'talk' | 'image' | 'sound' | 'movie'
}

const GENERATED_DIR = join(homedir(), 'github', 'mindbase', 'generated')
const NOTE_OUTPUT_DIR = join(homedir(), 'github', 'mindbase', 'generated', 'note')

/**
 * Parse frontmatter from markdown content
 */
function parseFrontmatter(content: string): {
  metadata: Record<string, any>
  body: string
} {
  const frontmatterRegex = /^---\n([\s\S]*?)\n---\n([\s\S]*)$/
  const match = content.match(frontmatterRegex)

  if (!match) {
    return { metadata: {}, body: content }
  }

  const frontmatter = match[1]
  const body = match[2]

  const metadata: Record<string, any> = {}

  for (const line of frontmatter.split('\n')) {
    const colonIndex = line.indexOf(':')
    if (colonIndex === -1) continue
    const key = line.substring(0, colonIndex).trim()
    const value = line.substring(colonIndex + 1).trim().replace(/^["']|["']$/g, '')

    if (key === 'topics' || key === 'tags') {
      metadata[key] = value
        .replace(/^\[|\]$/g, '')
        .split(',')
        .map(t => t.trim().replace(/^["']|["']$/g, ''))
    } else if (value === 'true') {
      metadata[key] = true
    } else if (value === 'false') {
      metadata[key] = false
    } else {
      metadata[key] = value
    }
  }

  return { metadata, body }
}

/**
 * Transform markdown for note.com style
 *
 * note.com prefers:
 * - Shorter paragraphs
 * - More whitespace
 * - Less code-heavy content
 * - Conversational tone
 * - Emoji in headings
 */
function transformForNote(body: string): string {
  let transformed = body

  // Remove code blocks that are too long (note readers prefer shorter code)
  transformed = transformed.replace(
    /```[\s\S]{500,}?```/g,
    '\n> （コードは省略 — 詳細は技術ブログで）\n'
  )

  // Add extra line breaks between sections for readability
  transformed = transformed.replace(/\n(#{1,3} )/g, '\n\n$1')

  // Convert raw URLs to markdown links
  transformed = transformed.replace(
    /(?<![(\[])(https?:\/\/\S+)/g,
    '[$1]($1)'
  )

  return transformed.trim()
}

/**
 * Format article for note.com output
 */
function formatNoteArticle(article: NoteArticle): string {
  const header = [
    `# ${article.title}`,
    '',
    article.tags.map(t => `#${t}`).join(' '),
    '',
    '---',
    '',
  ].join('\n')

  return `${header}${article.body}\n`
}

/**
 * Output note article (clipboard + file)
 */
async function publishToNote(
  article: NoteArticle,
  dryRun: boolean = false
): Promise<{ filePath: string } | null> {
  const formatted = formatNoteArticle(article)

  if (dryRun) {
    console.log('Preview:')
    console.log('─'.repeat(50))
    console.log(formatted.slice(0, 500) + '...')
    console.log('─'.repeat(50))
    return null
  }

  // Ensure output directory exists
  if (!existsSync(NOTE_OUTPUT_DIR)) {
    await mkdir(NOTE_OUTPUT_DIR, { recursive: true })
  }

  // Generate filename
  const date = new Date().toISOString().split('T')[0]
  const slug = article.title
    .toLowerCase()
    .replace(/[^a-z0-9\u3000-\u9fff]/g, '-')
    .replace(/-+/g, '-')
    .substring(0, 40)
  const filename = `${date}-${slug}.md`
  const filePath = join(NOTE_OUTPUT_DIR, filename)

  await writeFile(filePath, formatted, 'utf-8')
  console.log(`Written to: ${filePath}`)

  // Copy to clipboard (macOS)
  try {
    execSync(`pbcopy`, { input: formatted })
    console.log('Copied to clipboard — paste into note.com editor')
  } catch {
    console.log('Clipboard copy failed — use the file directly')
  }

  return { filePath }
}

/**
 * Main entry point
 */
async function main() {
  const args = process.argv.slice(2)

  if (args.length === 0) {
    console.log('Usage: publish-note.ts <filename> [--dry-run]')
    console.log('')
    console.log('Note: note.com does not provide a public API.')
    console.log('This script generates note-optimized markdown and copies to clipboard.')
    console.log('')
    console.log('Example:')
    console.log('  publish-note.ts 2025-10-09-ai-thoughts.md --dry-run')
    process.exit(1)
  }

  const filename = args[0]
  const dryRun = args.includes('--dry-run')

  const filePath = join(GENERATED_DIR, filename)
  console.log(`Reading: ${filename}`)

  const content = await readFile(filePath, 'utf-8')
  const { metadata, body } = parseFrontmatter(content)

  const noteBody = transformForNote(body)

  const article: NoteArticle = {
    title: metadata.title || 'Untitled',
    body: noteBody,
    status: 'draft',
    tags: (metadata.topics || metadata.tags || ['AI']).slice(0, 10),
    category: 'text',
  }

  console.log('')
  console.log(`Article:`)
  console.log(`   Title: ${article.title}`)
  console.log(`   Tags: ${article.tags.join(', ')}`)
  console.log(`   Category: ${article.category}`)
  console.log(`   Length: ${article.body.length} characters`)

  if (dryRun) {
    console.log('')
    console.log('Dry run mode — skipping publish')
    const formatted = formatNoteArticle(article)
    console.log('')
    console.log('Preview:')
    console.log('─'.repeat(50))
    console.log(formatted.slice(0, 500) + '...')
    console.log('─'.repeat(50))
    return
  }

  console.log('')
  console.log('Publishing to note.com...')

  const result = await publishToNote(article, dryRun)

  if (result) {
    console.log('')
    console.log('Article ready!')
    console.log(`   File: ${result.filePath}`)
    console.log('   Next: Open note.com and paste from clipboard')
    console.log('   URL: https://note.com/new')
  }
}

main().catch((error) => {
  console.error('Error:', error.message)
  process.exit(1)
})
