# MindBase - AI Conversation Knowledge Management

**完全無料のローカル動作。あなたの思考の言語化を集約する基地。**

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Docker](https://img.shields.io/badge/docker-ready-blue.svg)](https://www.docker.com/)

> **PostgreSQL + pgvector + Ollama (qwen3-embedding:8b)** - API キー不要、完全ローカル、Vector 検索対応

## 🎯 概要

**MindBase = 全AI会話の統合 + セマンティック検索 + コンテンツ生成**

### アーキテクチャ

```
Claude Code / ChatGPT / Cursor / Windsurf / Slack / Gmail / Google Docs
    ↓ Collectors (Python)
PostgreSQL 17 + pgvector (Docker)
    ↓ REST API (http://localhost:18002)
Ollama + qwen3-embedding:8b (Docker)
    ↓ MCP Server (Airis Gateway統合)
SuperClaude PM Agent (会話履歴自動保存・検索)
```

### 特徴

- **完全無料**: OpenAI API不要、Supabase不要、全てローカル
- **高性能Embedding**: qwen3-embedding:8b (MTEB #1 multilingual, 2025最新)
- **セマンティック検索**: pgvector + 1024次元ベクトル
- **REST API**: FastAPI (http://localhost:18002)
- **MCP Server**: Airis Gateway統合でSuperClaude PMAgentから利用可能
- **Docker完結**: Mac環境汚染ゼロ

## 🏗️ アーキテクチャ

### データ分離設計

```
~/Library/Application Support/mindbase/  # データ（Claude読めない）
├── conversations/                       # 会話アーカイブ
│   ├── claude-code/
│   │   ├── by-date/2025/10/09/         # 日付別
│   │   ├── by-project/agiletec/        # プロジェクト別
│   │   ├── agiletec/
│   │   ├── mkk/
│   │   └── global/
│   ├── claude-desktop/
│   ├── chatgpt/
│   ├── cursor/
│   └── ...
└── db/                                  # Supabase データ永続化

~/github/mindbase/                       # ソースコード（Git管理）
├── src/
│   ├── collectors/                      # 会話収集（Python）
│   ├── processors/                      # 会話処理（TypeScript）
│   │   └── extract-modules.ts
│   ├── generators/                      # 記事生成（TypeScript）
│   │   ├── generate-article.ts
│   │   └── publish-qiita.ts
│   └── mcp-server/                      # MCP API
│
├── scripts/
│   ├── archive/                         # アーカイブスクリプト
│   │   └── archive-conversations.sh
│   ├── optimize-dotclaude/              # ~/.claude/ 最適化
│   │   └── optimize.sh
│   └── research/                        # データ調査
│
├── supabase/                            # Supabase設定
│   ├── migrations/                      # DBスキーマ
│   └── functions/                       # Edge Functions
│
├── templates/                           # 記事テンプレート
├── modules/                             # 抽出済みモジュール（JSON）
├── generated/                           # 生成記事（Markdown）
└── README.md
```

**なぜこの設計？**
- `~/github/mindbase/` はGitリポジトリ → Claude Codeが grep/Read で読み込む
- 会話データが大量 → コンテキストノイズになる
- **データを Application Support に隔離** → Claude は読めない、ノイズゼロ

## 🚀 クイックスタート（5分）

```bash
# 1. クローン（既にある場合はスキップ）
git clone https://github.com/kazukinakai/mindbase.git ~/github/mindbase
cd ~/github/mindbase

# 2. 環境変数コピー
cp .env.example .env

# 3. 全サービス起動
make up

# 4. Ollamaモデルダウンロード（初回のみ、5-10分）
make model-pull

# 5. データベースマイグレーション
make migrate

# 6. 動作確認
make health

# ✅ 完了！API: http://localhost:18002
```

### 使い方

**会話を保存**:
```bash
curl -X POST http://localhost:18002/conversations/store \
  -H "Content-Type: application/json" \
  -d '{
    "source": "claude-code",
    "title": "PM Agent Enhancement",
    "content": {
      "messages": [
        {"role": "user", "content": "Implement autonomous PM Agent"},
        {"role": "assistant", "content": "Implementing Phase 0, 1, 2..."}
      ]
    },
    "metadata": {"project": "superclaude"}
  }'
```

**セマンティック検索**:
```bash
curl -X POST http://localhost:18002/conversations/search \
  -H "Content-Type: application/json" \
  -d '{
    "query": "PM Agent autonomous investigation",
    "limit": 10,
    "threshold": 0.8
  }'
```

## 📋 スクリプト詳細

### アーカイブ系

**`pnpm archive [days]`** - Claude Code会話をアーカイブ
```bash
# 90日以上の会話をアーカイブ（推奨）
pnpm archive 90

# 結果: ~/.claude/projects/*.jsonl → Application Support/mindbase/conversations/
```

**`pnpm optimize [days]`** - ~/.claude/ 最適化
```bash
# ドライラン
DRY_RUN=true pnpm optimize 90

# 実行（古い会話移動 + 一時ファイル削除）
DRY_RUN=false pnpm optimize 90
```

### 処理系

**`pnpm extract`** - トピック分類とモジュール抽出
```bash
# アーカイブされた会話を処理
pnpm extract

# 出力: modules/*.json（カテゴリ別）
```

**トピックキーワード**:
- Docker-First Development
- Turborepo Monorepo
- Supabase Self-Host
- Multi-Tenancy
- SuperClaude Framework
- AlmaLinux HomeServer
- Performance Optimization

### 生成系

**`pnpm generate <category>`** - 記事生成
```bash
# 利用可能なカテゴリ確認
pnpm generate

# 記事生成
pnpm generate docker-first-development

# 出力: generated/2025-10-09-docker-first-development.md
```

**`pnpm publish <file> [--dry-run]`** - Qiita投稿
```bash
# Qiita Token設定
export QIITA_TOKEN=your_token_here

# Dry run（確認のみ）
pnpm publish 2025-10-09-docker-first.md --dry-run

# 投稿
pnpm publish 2025-10-09-docker-first.md

# 非公開投稿
pnpm publish 2025-10-09-docker-first.md --private
```

## 📊 統計

**会話データ**（2025-10-09時点）:
```
~/.claude/
  Size: 109MB
  Conversations: 111 files

Archived:
  Application Support/mindbase/conversations/: 0 files（初回実行前）

推定:
  - 300-500時間分の技術会話
  - 50-100記事分のコンテンツ
```

## 🔄 統合元プロジェクト

### dot-claude-optimizer
- **責務**: ~/.claude/ 最適化とアーカイブ管理
- **統合内容**: `scripts/archive/archive-conversations.sh`
- **変更点**: アーカイブ先を Application Support に変更、7日→90日推奨

### claude-blog-automation
- **責務**: 会話 → ブログ記事自動生成
- **統合内容**: `src/processors/`, `src/generators/`, `templates/`
- **変更点**: アーカイブとの連携、Supabase統合準備

## 📚 データベーススキーマ

Supabase（PostgreSQL + pgvector）:

- **conversations**: 全ての会話データ（claude-code, claude-desktop, chatgpt, etc.）
- **thought_patterns**: 会話から抽出されたパターン
- **book_structure**: 本・ブログの階層構造
- **conversation_analysis_jobs**: バックグラウンド分析ジョブ

詳細: `supabase/migrations/20241217120000_mind_base_schema.sql`

## 🎯 活用戦略

### 週次ワークフロー
```bash
# 日曜 23:00 実行（cron/launchd）
pnpm archive 90          # 90日以上をアーカイブ
pnpm extract             # 新会話を処理
pnpm generate --all      # 全カテゴリ記事生成
```

### マルチプラットフォーム
- **Qiita**: API自動投稿（pnpm publish）
- **Zenn**: GitHub連携（push → 自動反映）
- **note**: 手動コピペ（月1-2記事）

### 自動化（GitHub Actions）
```yaml
name: Weekly Blog Generation
on:
  schedule:
    - cron: '0 0 * * 0'  # 毎週日曜0:00
jobs:
  generate:
    - pnpm archive 90
    - pnpm extract
    - pnpm generate --all
    - pnpm publish <file> --dry-run
```

## 📖 詳細ドキュメント

プロジェクトの包括的なドキュメントは `docs/` ディレクトリにあります：

- **[ARCHITECTURE.md](docs/ARCHITECTURE.md)** - システムアーキテクチャの完全な説明
  - コンポーネント設計、データフロー、技術スタック
  - BaseCollector パターン、データ正規化、セキュリティ設計

- **[ROADMAP.md](docs/ROADMAP.md)** - Phase 0-3 開発ロードマップ
  - Phase 0 (完了): 基盤構築
  - Phase 1 (進行中): データソース拡張 + Airis MCP Gateway統合
  - Phase 2-3 (計画中): 高度な機能、本番環境対応

- **[TASKS.md](docs/TASKS.md)** - 実装タスク詳細（優先順位付き）
  - Sprint 1.1: データソース拡張 (2週間)
  - Sprint 1.2: Airis MCP Gateway統合 (2週間)
  - Sprint 1.3: Gmail & Google Drive統合 (3週間)

- **[AIRIS_MCP_INTEGRATION.md](docs/AIRIS_MCP_INTEGRATION.md)** - MCP Gateway統合設計
  - Tool定義、エラーハンドリング、パフォーマンス最適化

- **[research/data-sources-research-2025-10-14.md](docs/research/data-sources-research-2025-10-14.md)** - データソース調査
  - ChatGPT、Grok、Gmail、Google Drive の詳細調査結果

## 🚨 注意事項

- **APIレート制限**: Qiita API は 1000 req/h（認証あり）
- **個人情報**: 会話データに個人情報含む場合は除外すること
- **アーカイブ閾値**: 60-90日推奨（短すぎると頻繁にアーカイブ実行）

## 🤝 コントリビューション

詳細な開発ガイドとアーキテクチャ情報は `docs/` を参照してください。

## 📝 ライセンス

MIT

---

**🤖 Powered by**: Claude Code + MindBase
**🔗 統合元**: dot-claude-optimizer + claude-blog-automation
**📚 Documentation**: [docs/](docs/)
