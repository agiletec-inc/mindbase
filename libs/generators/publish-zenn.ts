#!/usr/bin/env node
/**
 * Zenn Auto Publisher
 *
 * Purpose: Publish articles to Zenn via GitHub repository
 * Input: ~/github/mindbase/generated/*.md
 * Zenn uses GitHub-based publishing: https://zenn.dev/zenn/articles/connect-to-github
 *
 * Flow:
 *   1. Read generated markdown with frontmatter
 *   2. Copy to Zenn content repo (articles/ directory)
 *   3. Git commit & push → auto-published by Zenn
 */

import { readFile, writeFile, mkdir } from 'fs/promises'
import { join, basename } from 'path'
import { homedir } from 'os'
import { execSync } from 'child_process'
import { existsSync } from 'fs'

interface ZennArticle {
  title: string
  emoji: string
  type: 'tech' | 'idea'
  topics: string[]
  published: boolean
  body: string
}

const GENERATED_DIR = join(homedir(), 'github', 'mindbase', 'generated')

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

    if (key === 'topics') {
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
 * Generate Zenn-compatible slug from title
 */
function generateSlug(title: string): string {
  const base = title
    .toLowerCase()
    .replace(/[^a-z0-9\u3000-\u9fff\uff00-\uffef]/g, '-')
    .replace(/-+/g, '-')
    .replace(/^-|-$/g, '')
    .substring(0, 40)

  // Zenn requires slug pattern: [a-z0-9-_]{12,50}
  const date = new Date().toISOString().split('T')[0].replace(/-/g, '')
  return `${date}-${base}`.substring(0, 50)
}

/**
 * Format article as Zenn-compatible markdown
 */
function formatZennArticle(article: ZennArticle): string {
  const frontmatter = [
    '---',
    `title: "${article.title}"`,
    `emoji: "${article.emoji}"`,
    `type: "${article.type}"`,
    `topics: [${article.topics.map(t => `"${t}"`).join(', ')}]`,
    `published: ${article.published}`,
    '---',
  ].join('\n')

  return `${frontmatter}\n\n${article.body.trim()}\n`
}

/**
 * Publish to Zenn content repository
 */
async function publishToZenn(
  article: ZennArticle,
  slug: string,
  zennRepoPath: string,
  dryRun: boolean = false
): Promise<{ filePath: string; slug: string } | null> {
  const articlesDir = join(zennRepoPath, 'articles')

  if (!existsSync(articlesDir)) {
    await mkdir(articlesDir, { recursive: true })
  }

  const filePath = join(articlesDir, `${slug}.md`)
  const content = formatZennArticle(article)

  if (dryRun) {
    console.log('Preview:')
    console.log('─'.repeat(50))
    console.log(content.slice(0, 500) + '...')
    console.log('─'.repeat(50))
    return null
  }

  await writeFile(filePath, content, 'utf-8')
  console.log(`Written to: ${filePath}`)

  // Git commit & push
  try {
    execSync(`git add "${filePath}"`, { cwd: zennRepoPath })
    execSync(`git commit -m "article: ${article.title}"`, { cwd: zennRepoPath })
    execSync('git push', { cwd: zennRepoPath })
    console.log('Git push complete — Zenn will auto-deploy')
  } catch (error) {
    console.log('Git operations skipped (manual push required)')
  }

  return { filePath, slug }
}

/**
 * Main entry point
 */
async function main() {
  const args = process.argv.slice(2)

  if (args.length === 0) {
    console.log('Usage: publish-zenn.ts <filename> [--dry-run] [--published]')
    console.log('')
    console.log('Environment variables:')
    console.log('  ZENN_REPO_PATH: Path to your Zenn content repository')
    console.log('')
    console.log('Example:')
    console.log('  publish-zenn.ts 2025-10-09-docker-first.md --dry-run')
    process.exit(1)
  }

  const filename = args[0]
  const dryRun = args.includes('--dry-run')
  const published = args.includes('--published')

  const zennRepoPath = process.env.ZENN_REPO_PATH
  if (!zennRepoPath && !dryRun) {
    console.error('ZENN_REPO_PATH environment variable not set')
    console.error('Set it to your Zenn content repository path')
    process.exit(1)
  }

  const filePath = join(GENERATED_DIR, filename)
  console.log(`Reading: ${filename}`)

  const content = await readFile(filePath, 'utf-8')
  const { metadata, body } = parseFrontmatter(content)

  const article: ZennArticle = {
    title: metadata.title || 'Untitled',
    emoji: metadata.emoji || '📝',
    type: metadata.type === 'idea' ? 'idea' : 'tech',
    topics: (metadata.topics || ['AI']).slice(0, 5),
    published,
    body: body.trim(),
  }

  const slug = generateSlug(article.title)

  console.log('')
  console.log(`Article:`)
  console.log(`   Title: ${article.title}`)
  console.log(`   Slug: ${slug}`)
  console.log(`   Type: ${article.type}`)
  console.log(`   Topics: ${article.topics.join(', ')}`)
  console.log(`   Published: ${article.published}`)
  console.log(`   Length: ${article.body.length} characters`)

  if (dryRun) {
    console.log('')
    console.log('Dry run mode — skipping publish')
    const formatted = formatZennArticle(article)
    console.log('')
    console.log('Preview:')
    console.log('─'.repeat(50))
    console.log(formatted.slice(0, 500) + '...')
    console.log('─'.repeat(50))
    return
  }

  console.log('')
  console.log('Publishing to Zenn...')

  const result = await publishToZenn(article, slug, zennRepoPath!, dryRun)

  if (result) {
    console.log('')
    console.log('Published successfully!')
    console.log(`   File: ${result.filePath}`)
    console.log(`   Slug: ${result.slug}`)
    console.log(`   URL: https://zenn.dev/articles/${result.slug} (after deploy)`)
  }
}

main().catch((error) => {
  console.error('Error:', error.message)
  process.exit(1)
})
