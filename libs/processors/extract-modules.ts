#!/usr/bin/env node
/**
 * MindBase Module Extractor
 *
 * Purpose: Extract conversation modules from Claude Code history
 * Input: ~/.claude/projects/, ~/.claude/file-history/, ~/.claude/history.jsonl
 * Output: ~/github/mindbase/modules/*.json
 */

import { readdir, readFile, writeFile, stat } from 'fs/promises'
import { join } from 'path'
import { homedir } from 'os'

interface ConversationMessage {
  type: 'user' | 'assistant'
  content: string
  timestamp?: string
}

interface ConversationModule {
  id: string
  title: string
  keywords: string[]
  conversations: string[] // UUIDs or file paths
  created: string
  estimatedReadTime: string
  category: string
  topics: string[]
  projectPath?: string
}

const CLAUDE_DIR = join(homedir(), '.claude')
const PROJECTS_DIR = join(CLAUDE_DIR, 'projects')
const FILE_HISTORY_DIR = join(CLAUDE_DIR, 'file-history')
const HISTORY_FILE = join(CLAUDE_DIR, 'history.jsonl')
const OUTPUT_DIR = join(homedir(), 'github', 'mindbase', 'modules')

// キーワード辞書（トピック分類用）
const TOPIC_KEYWORDS: Record<string, string[]> = {
  'Docker-First Development': ['docker', 'docker-compose', 'makefile', 'container', 'workspace'],
  'Turborepo Monorepo': ['turborepo', 'pnpm', 'monorepo', 'workspace', 'package'],
  'Supabase Self-Host': ['supabase', 'kong', 'auth', 'realtime', 'edge functions'],
  'Multi-Tenancy': ['organization_id', 'rls', 'row level security', 'tenant'],
  'Testing Strategy': ['vitest', 'test coverage', 'playwright', 'unit test'],
  'SuperClaude Framework': ['mode', 'persona', 'mcp', 'superclaude'],
  'AlmaLinux HomeServer': ['almalinux', 'samba', 'restic', 'tdarr', 'facefusion'],
  'Performance Optimization': ['performance', 'optimization', 'cache', 'bundle'],
  'API Design': ['rest api', 'graphql', 'endpoint', 'openapi'],
  'Security': ['authentication', 'authorization', 'jwt', 'encryption'],
}

/**
 * JSONL ファイルを読み込んで会話を抽出
 */
async function parseJSONL(filePath: string): Promise<ConversationMessage[]> {
  try {
    const content = await readFile(filePath, 'utf-8')
    const lines = content.trim().split('\n').filter(line => line.trim())

    const messages: ConversationMessage[] = []
    for (const line of lines) {
      try {
        const data = JSON.parse(line)
        if (data.type === 'user' || data.type === 'assistant') {
          messages.push({
            type: data.type,
            content: typeof data.content === 'string'
              ? data.content
              : JSON.stringify(data.content),
            timestamp: data.timestamp
          })
        }
      } catch (e) {
        // Skip invalid JSON lines
      }
    }

    return messages
  } catch (error) {
    console.error(`Error parsing ${filePath}:`, error)
    return []
  }
}

/**
 * 会話からトピックを検出
 */
function detectTopics(messages: ConversationMessage[]): string[] {
  const fullText = messages
    .map(m => m.content)
    .join(' ')
    .toLowerCase()

  const detectedTopics: string[] = []

  for (const [topic, keywords] of Object.entries(TOPIC_KEYWORDS)) {
    const matchCount = keywords.filter(keyword =>
      fullText.includes(keyword.toLowerCase())
    ).length

    // 2つ以上のキーワードにマッチしたらトピックとして認定
    if (matchCount >= 2) {
      detectedTopics.push(topic)
    }
  }

  return detectedTopics.length > 0 ? detectedTopics : ['General']
}

/**
 * 会話から主要キーワードを抽出
 */
function extractKeywords(messages: ConversationMessage[]): string[] {
  const fullText = messages.map(m => m.content).join(' ').toLowerCase()

  const allKeywords = Object.values(TOPIC_KEYWORDS).flat()
  const matched = allKeywords.filter(keyword =>
    fullText.includes(keyword.toLowerCase())
  )

  // 重複削除 & 頻度順（簡易版）
  return [...new Set(matched)].slice(0, 10)
}

/**
 * 読了時間を推定（簡易版）
 */
function estimateReadTime(messages: ConversationMessage[]): string {
  const totalChars = messages.reduce((sum, m) => sum + m.content.length, 0)
  const minutes = Math.ceil(totalChars / 2000) // 2000文字/分と仮定
  return `${minutes}分`
}

/**
 * プロジェクト別の会話を処理
 */
async function processProjectConversations(): Promise<ConversationModule[]> {
  const modules: ConversationModule[] = []

  const projects = await readdir(PROJECTS_DIR)

  for (const projectDir of projects) {
    const projectPath = join(PROJECTS_DIR, projectDir)
    const stats = await stat(projectPath)

    if (!stats.isDirectory()) continue

    const files = await readdir(projectPath)
    const jsonlFiles = files.filter(f => f.endsWith('.jsonl'))

    for (const file of jsonlFiles) {
      const filePath = join(projectPath, file)
      const messages = await parseJSONL(filePath)

      if (messages.length === 0) continue

      const topics = detectTopics(messages)
      const keywords = extractKeywords(messages)
      const uuid = file.replace('.jsonl', '')

      // 最初のユーザーメッセージからタイトル生成（簡易版）
      const firstUserMessage = messages.find(m => m.type === 'user')
      const title = firstUserMessage
        ? firstUserMessage.content.slice(0, 50).replace(/\n/g, ' ').trim() + '...'
        : `Conversation ${uuid.slice(0, 8)}`

      modules.push({
        id: uuid,
        title,
        keywords,
        conversations: [filePath],
        created: new Date().toISOString().split('T')[0],
        estimatedReadTime: estimateReadTime(messages),
        category: topics[0] || 'General',
        topics,
        projectPath: projectDir
      })
    }
  }

  return modules
}

/**
 * file-history の会話を処理
 */
async function processFileHistory(): Promise<ConversationModule[]> {
  const modules: ConversationModule[] = []
  const files = await readdir(FILE_HISTORY_DIR)

  for (const uuid of files) {
    const filePath = join(FILE_HISTORY_DIR, uuid)
    const stats = await stat(filePath)

    if (!stats.isFile()) continue

    const messages = await parseJSONL(filePath)
    if (messages.length === 0) continue

    const topics = detectTopics(messages)
    const keywords = extractKeywords(messages)

    const firstUserMessage = messages.find(m => m.type === 'user')
    const title = firstUserMessage
      ? firstUserMessage.content.slice(0, 50).replace(/\n/g, ' ').trim() + '...'
      : `Conversation ${uuid.slice(0, 8)}`

    modules.push({
      id: uuid,
      title,
      keywords,
      conversations: [filePath],
      created: new Date().toISOString().split('T')[0],
      estimatedReadTime: estimateReadTime(messages),
      category: topics[0] || 'General',
      topics
    })
  }

  return modules
}

/**
 * モジュールをカテゴリ別にグループ化
 */
function groupByCategory(modules: ConversationModule[]): Record<string, ConversationModule[]> {
  const grouped: Record<string, ConversationModule[]> = {}

  for (const module of modules) {
    const category = module.category
    if (!grouped[category]) {
      grouped[category] = []
    }
    grouped[category].push(module)
  }

  return grouped
}

/**
 * メイン処理
 */
async function main() {
  console.log('🔍 Extracting conversation modules from ~/.claude/')
  console.log('')

  console.log('📂 Processing projects...')
  const projectModules = await processProjectConversations()
  console.log(`   Found ${projectModules.length} project conversations`)

  console.log('📂 Processing file-history...')
  const historyModules = await processFileHistory()
  console.log(`   Found ${historyModules.length} archived conversations`)

  const allModules = [...projectModules, ...historyModules]

  console.log('')
  console.log(`📊 Total: ${allModules.length} conversations`)

  // カテゴリ別にグループ化
  const grouped = groupByCategory(allModules)

  console.log('')
  console.log('📁 Categories:')
  for (const [category, modules] of Object.entries(grouped)) {
    console.log(`   ${category}: ${modules.length} conversations`)
  }

  // カテゴリ別に保存
  for (const [category, modules] of Object.entries(grouped)) {
    const filename = category.toLowerCase().replace(/\s+/g, '-') + '.json'
    const outputPath = join(OUTPUT_DIR, filename)

    await writeFile(
      outputPath,
      JSON.stringify(modules, null, 2),
      'utf-8'
    )

    console.log(`   ✅ Saved: ${filename}`)
  }

  // サマリーも保存
  const summary = {
    totalConversations: allModules.length,
    categories: Object.keys(grouped).length,
    categoryBreakdown: Object.fromEntries(
      Object.entries(grouped).map(([cat, mods]) => [cat, mods.length])
    ),
    extractedAt: new Date().toISOString()
  }

  await writeFile(
    join(OUTPUT_DIR, '_summary.json'),
    JSON.stringify(summary, null, 2),
    'utf-8'
  )

  console.log('')
  console.log('✅ Extraction complete!')
  console.log(`📍 Output: ${OUTPUT_DIR}`)
}

main().catch(console.error)
