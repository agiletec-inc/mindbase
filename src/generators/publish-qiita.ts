#!/usr/bin/env node
/**
 * Qiita Auto Publisher
 *
 * Purpose: Publish articles to Qiita via API
 * Input: ~/github/mindbase/generated/*.md
 * API: https://qiita.com/api/v2/docs
 */

import { readFile } from 'fs/promises'
import { join } from 'path'
import { homedir } from 'os'

interface QiitaArticle {
  title: string
  body: string
  tags: Array<{ name: string }>
  private: boolean
  tweet?: boolean
  gist?: boolean
  slide?: boolean
}

interface QiitaResponse {
  id: string
  url: string
  title: string
  created_at: string
  updated_at: string
}

const GENERATED_DIR = join(homedir(), 'github', 'mindbase', 'generated')
const QIITA_API_ENDPOINT = 'https://qiita.com/api/v2/items'

/**
 * Markdownから frontmatter を抽出
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
    const [key, ...valueParts] = line.split(':')
    if (key && valueParts.length > 0) {
      const value = valueParts.join(':').trim().replace(/^["']|["']$/g, '')

      if (key === 'topics') {
        // topics: ["Docker", "Makefile"] → ["Docker", "Makefile"]
        metadata[key] = value
          .replace(/^\[|\]$/g, '')
          .split(',')
          .map(t => t.trim().replace(/^["']|["']$/g, ''))
      } else {
        metadata[key] = value
      }
    }
  }

  return { metadata, body }
}

/**
 * Qiita API にリクエスト
 */
async function publishToQiita(
  article: QiitaArticle,
  token: string,
  dryRun: boolean = false
): Promise<QiitaResponse | null> {
  if (dryRun) {
    console.log('🔍 Dry run mode - article preview:')
    console.log(JSON.stringify(article, null, 2))
    return null
  }

  const response = await fetch(QIITA_API_ENDPOINT, {
    method: 'POST',
    headers: {
      'Authorization': `Bearer ${token}`,
      'Content-Type': 'application/json'
    },
    body: JSON.stringify(article)
  })

  if (!response.ok) {
    const error = await response.text()
    throw new Error(`Qiita API error: ${response.status} - ${error}`)
  }

  return response.json() as Promise<QiitaResponse>
}

/**
 * メイン処理
 */
async function main() {
  const args = process.argv.slice(2)

  if (args.length === 0) {
    console.log('Usage: publish-qiita.ts <filename> [--dry-run] [--private]')
    console.log('')
    console.log('Environment variables:')
    console.log('  QIITA_TOKEN: Your Qiita personal access token')
    console.log('')
    console.log('Example:')
    console.log('  publish-qiita.ts 2025-10-09-docker-first.md --dry-run')
    process.exit(1)
  }

  const filename = args[0]
  const dryRun = args.includes('--dry-run')
  const isPrivate = args.includes('--private')

  const filePath = join(GENERATED_DIR, filename)

  console.log(`📖 Reading: ${filename}`)

  const content = await readFile(filePath, 'utf-8')
  const { metadata, body } = parseFrontmatter(content)

  // Qiita記事オブジェクト作成
  const article: QiitaArticle = {
    title: metadata.title || 'Untitled',
    body: body.trim(),
    tags: (metadata.topics || []).slice(0, 5).map((name: string) => ({ name })),
    private: isPrivate,
    tweet: false
  }

  console.log('')
  console.log(`📝 Article:`)
  console.log(`   Title: ${article.title}`)
  console.log(`   Tags: ${article.tags.map(t => t.name).join(', ')}`)
  console.log(`   Private: ${article.private}`)
  console.log(`   Length: ${article.body.length} characters`)

  if (dryRun) {
    console.log('')
    console.log('🔍 Dry run mode - skipping publish')
    console.log('')
    console.log('Preview:')
    console.log('─'.repeat(50))
    console.log(article.body.slice(0, 500) + '...')
    console.log('─'.repeat(50))
    return
  }

  const token = process.env.QIITA_TOKEN

  if (!token) {
    console.error('')
    console.error('❌ QIITA_TOKEN environment variable not set')
    console.error('')
    console.error('Get your token at: https://qiita.com/settings/tokens/new')
    console.error('Then run: export QIITA_TOKEN=your_token_here')
    process.exit(1)
  }

  console.log('')
  console.log('🚀 Publishing to Qiita...')

  const result = await publishToQiita(article, token, false)

  if (result) {
    console.log('')
    console.log('✅ Published successfully!')
    console.log(`   URL: ${result.url}`)
    console.log(`   ID: ${result.id}`)
    console.log(`   Created: ${result.created_at}`)
  }
}

main().catch((error) => {
  console.error('')
  console.error('❌ Error:', error.message)
  process.exit(1)
})
