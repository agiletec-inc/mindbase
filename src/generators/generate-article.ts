#!/usr/bin/env node
/**
 * MindBase Article Generator
 *
 * Purpose: Generate blog articles from conversation modules
 * Input: ~/github/mindbase/modules/*.json
 * Output: ~/github/mindbase/generated/*.md
 */

import { readFile, writeFile, readdir } from 'fs/promises'
import { join } from 'path'
import { homedir } from 'os'

interface ConversationModule {
  id: string
  title: string
  keywords: string[]
  conversations: string[]
  created: string
  estimatedReadTime: string
  category: string
  topics: string[]
  projectPath?: string
}

interface ConversationMessage {
  type: 'user' | 'assistant'
  content: string
  timestamp?: string
}

interface ArticleMetadata {
  title: string
  description: string
  tags: string[]
  category: string
  estimatedReadTime: string
}

const MODULES_DIR = join(homedir(), 'github', 'mindbase', 'modules')
const GENERATED_DIR = join(homedir(), 'github', 'mindbase', 'generated')

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
    return []
  }
}

/**
 * 会話から要約を生成（簡易版）
 */
function generateSummary(messages: ConversationMessage[]): string {
  const userMessages = messages.filter(m => m.type === 'user')
  const assistantMessages = messages.filter(m => m.type === 'assistant')

  const topics: string[] = []

  // ユーザーの質問から主要トピックを抽出
  for (const msg of userMessages.slice(0, 5)) {
    const firstLine = msg.content.split('\n')[0].trim()
    if (firstLine.length > 10 && firstLine.length < 100) {
      topics.push(firstLine)
    }
  }

  if (topics.length === 0) {
    return '技術的な会話とその実装について'
  }

  return topics.slice(0, 3).join('、')
}

/**
 * コードブロックを抽出
 */
function extractCodeBlocks(messages: ConversationMessage[]): string[] {
  const codeBlocks: string[] = []

  for (const msg of messages) {
    const matches = msg.content.matchAll(/```(\w+)?\n([\s\S]*?)```/g)
    for (const match of matches) {
      const lang = match[1] || 'bash'
      const code = match[2].trim()
      if (code.length > 20) {
        codeBlocks.push(`\`\`\`${lang}\n${code}\n\`\`\``)
      }
    }
  }

  return codeBlocks
}

/**
 * 会話から記事セクションを生成
 */
function generateSections(messages: ConversationMessage[]): string[] {
  const sections: string[] = []
  let currentSection = ''
  let sectionTitle = ''

  for (let i = 0; i < messages.length; i++) {
    const msg = messages[i]

    if (msg.type === 'user') {
      // ユーザーの質問を見出しとして使用
      if (currentSection) {
        sections.push(`## ${sectionTitle}\n\n${currentSection}`)
      }
      sectionTitle = msg.content.split('\n')[0].slice(0, 60).trim()
      currentSection = ''
    } else {
      // アシスタントの回答を本文として追加
      const content = msg.content.trim()
      if (content.length > 100) {
        currentSection += content + '\n\n'
      }
    }

    // セクションが長すぎたら分割
    if (currentSection.length > 2000) {
      sections.push(`## ${sectionTitle}\n\n${currentSection}`)
      currentSection = ''
      sectionTitle = `続き ${i}`
    }
  }

  // 最後のセクション
  if (currentSection) {
    sections.push(`## ${sectionTitle}\n\n${currentSection}`)
  }

  return sections.filter(s => s.length > 100).slice(0, 5)
}

/**
 * モジュールから記事を生成
 */
async function generateArticle(
  module: ConversationModule,
  metadata: ArticleMetadata
): Promise<string> {
  const conversationPath = module.conversations[0]
  const messages = await parseJSONL(conversationPath)

  if (messages.length === 0) {
    throw new Error('No messages found in conversation')
  }

  const summary = generateSummary(messages)
  const sections = generateSections(messages)
  const codeBlocks = extractCodeBlocks(messages)

  // 記事のテンプレート
  let article = `---
title: "${metadata.title}"
emoji: "🚀"
type: "tech"
topics: [${metadata.tags.map(t => `"${t}"`).join(', ')}]
published: false
---

# ${metadata.title}

${metadata.description}

## はじめに

この記事では、${summary}について解説します。

**読了時間**: ${metadata.estimatedReadTime}

`

  // セクションを追加
  for (const section of sections) {
    article += section + '\n\n'
  }

  // 主要なコードブロックを追加
  if (codeBlocks.length > 0) {
    article += `## 実装例\n\n`
    article += codeBlocks.slice(0, 3).join('\n\n') + '\n\n'
  }

  // まとめ
  article += `## まとめ

本記事では、${summary}について実践的な解説を行いました。

**キーワード**: ${module.keywords.slice(0, 5).join(', ')}

---

この記事は実際の開発会話から生成されました。
🤖 Generated with [Claude Code](https://claude.com/claude-code) + MindBase
`

  return article
}

/**
 * カテゴリ別に記事メタデータを生成
 */
function generateMetadata(category: string, module: ConversationModule): ArticleMetadata {
  const categoryMap: Record<string, { title: string, description: string, tags: string[] }> = {
    'Docker-First Development': {
      title: 'Docker-First開発環境の構築と運用',
      description: 'Macホストを汚さない、完全コンテナ化された開発環境の実践',
      tags: ['Docker', 'Makefile', '開発環境', 'コンテナ']
    },
    'Turborepo Monorepo': {
      title: 'Turborepoモノレポの実践的構築',
      description: 'pnpm workspace + Turborepoによるスケーラブルなモノレポ運用',
      tags: ['Turborepo', 'pnpm', 'Monorepo', 'フロントエンド']
    },
    'Supabase Self-Host': {
      title: 'Supabase セルフホストの完全ガイド',
      description: 'Kong API Gateway を含むフルスタックSupabase環境構築',
      tags: ['Supabase', 'PostgreSQL', 'Kong', 'セルフホスト']
    },
    'SuperClaude Framework': {
      title: 'SuperClaude Frameworkで開発を加速',
      description: 'Claude Codeの生産性を劇的に向上させるフレームワーク活用術',
      tags: ['Claude', 'AI', 'SuperClaude', '生産性']
    },
    'AlmaLinux HomeServer': {
      title: 'AlmaLinuxでホームサーバー構築',
      description: 'Samba、Restic、GPU対応コンテナを活用したホームサーバー運用',
      tags: ['AlmaLinux', 'HomeServer', 'Samba', 'GPU']
    }
  }

  const defaults = {
    title: `${category}の実践的ガイド`,
    description: `${category}について、実際の開発経験から得られた知見を共有します。`,
    tags: module.keywords.slice(0, 4)
  }

  const meta = categoryMap[category] || defaults

  return {
    ...meta,
    category,
    estimatedReadTime: module.estimatedReadTime
  }
}

/**
 * メイン処理
 */
async function main() {
  const args = process.argv.slice(2)

  if (args.length === 0) {
    console.log('Usage: generate-article.ts <category>')
    console.log('')
    console.log('Available categories:')
    const files = await readdir(MODULES_DIR)
    for (const file of files.filter(f => f.endsWith('.json') && f !== '_summary.json')) {
      console.log(`  - ${file.replace('.json', '')}`)
    }
    process.exit(1)
  }

  const category = args[0]
  const moduleFile = join(MODULES_DIR, `${category}.json`)

  console.log(`📖 Generating article from: ${category}`)

  const modulesData = await readFile(moduleFile, 'utf-8')
  const modules: ConversationModule[] = JSON.parse(modulesData)

  if (modules.length === 0) {
    console.error('❌ No modules found in category')
    process.exit(1)
  }

  // 最初のモジュールから記事生成（デモ）
  const module = modules[0]
  const originalCategory = category.split('-').map(w =>
    w.charAt(0).toUpperCase() + w.slice(1)
  ).join(' ')

  const metadata = generateMetadata(originalCategory, module)
  const article = await generateArticle(module, metadata)

  const outputFile = join(
    GENERATED_DIR,
    `${new Date().toISOString().split('T')[0]}-${category}.md`
  )

  await writeFile(outputFile, article, 'utf-8')

  console.log(`✅ Article generated: ${outputFile}`)
  console.log('')
  console.log(`📊 Stats:`)
  console.log(`   Title: ${metadata.title}`)
  console.log(`   Tags: ${metadata.tags.join(', ')}`)
  console.log(`   Read time: ${metadata.estimatedReadTime}`)
  console.log(`   Length: ${article.length} characters`)
}

main().catch(console.error)
