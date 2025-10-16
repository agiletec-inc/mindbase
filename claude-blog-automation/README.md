# MindBase - Conversation History to Blog Articles

Claude Code会話履歴を自動的にブログ記事に変換するシステム。

## 🎯 概要

- **入力**: `~/.claude/` の会話履歴（103MB、300-500時間分）
- **処理**: トピック分類 → モジュール化 → 記事生成
- **出力**: Qiita/Zenn投稿可能なMarkdown記事

## 📂 ディレクトリ構造

```
~/github/mindbase/
├── modules/              # 抽出された会話モジュール（JSON）
│   ├── docker-first-development.json
│   ├── turborepo-monorepo.json
│   ├── supabase-self-host.json
│   └── _summary.json
│
├── templates/            # 記事テンプレート
│   ├── qiita-template.md
│   └── zenn-template.md
│
├── generated/            # 生成済み記事（Markdown）
│   └── 2025-10-09-docker-first.md
│
└── scripts/              # 実行スクリプト
    ├── extract-modules.ts
    ├── generate-article.ts
    └── publish-qiita.ts
```

## 🚀 使い方

### 1. セットアップ

```bash
cd ~/github/mindbase
pnpm install
```

### 2. 会話履歴の抽出

```bash
# ~/.claude/ から会話を抽出してトピック分類
pnpm extract

# 出力: modules/*.json
```

**処理内容**:
- `~/.claude/projects/` を巡回
- `~/.claude/file-history/` を巡回
- JSONL解析 → トピック検出 → カテゴリ別保存

**カテゴリ例**:
- Docker-First Development
- Turborepo Monorepo
- Supabase Self-Host
- SuperClaude Framework
- AlmaLinux HomeServer

### 3. 記事生成

```bash
# カテゴリから記事生成
pnpm generate docker-first-development

# 出力: generated/2025-10-09-docker-first-development.md
```

**生成内容**:
- タイトル（カテゴリベース）
- 要約（会話から自動生成）
- セクション分割（ユーザー質問→見出し、回答→本文）
- コードブロック抽出
- タグ/メタデータ

### 4. Qiita投稿

```bash
# 1. トークン設定
export QIITA_TOKEN=your_token_here

# 2. Dry run（確認のみ）
pnpm publish 2025-10-09-docker-first.md --dry-run

# 3. 実際に投稿
pnpm publish 2025-10-09-docker-first.md

# 4. 非公開で投稿
pnpm publish 2025-10-09-docker-first.md --private
```

**Qiita Token取得**:
https://qiita.com/settings/tokens/new

**必要な権限**:
- `read_qiita`: 記事読み取り
- `write_qiita`: 記事投稿

## 📊 統計

**会話資産**:
- 合計: 103MB
- projects/: 68MB（14プロジェクト）
- file-history/: 5.5MB（76ファイル）
- 推定: 300-500時間分の技術会話

**記事生成予測**:
- 1カテゴリ = 1-5記事
- 10カテゴリ = 50-100記事分
- 継続的な会話 = 自動追加

## 🎯 活用戦略

### Phase 1: コンテンツ生成
```bash
# 週1回実行
pnpm extract          # 新しい会話を抽出
pnpm generate xxx     # 記事生成
pnpm publish xxx --dry-run  # プレビュー確認
```

### Phase 2: 自動投稿
```bash
# GitHub Actions で自動化
- cron: 毎週月曜 9:00
- 新しいモジュール検出
- 記事生成
- Qiita API投稿
```

### Phase 3: マルチプラットフォーム
- Qiita: API自動投稿
- Zenn: GitHub連携（push → 自動反映）
- note: 手動コピペ（月1-2記事）

## 🔧 カスタマイズ

### トピックキーワード追加

`scripts/extract-modules.ts`:
```typescript
const TOPIC_KEYWORDS: Record<string, string[]> = {
  'Your Topic': ['keyword1', 'keyword2', 'keyword3'],
  // ...
}
```

### 記事テンプレート変更

`scripts/generate-article.ts`:
```typescript
function generateMetadata(category: string, module: ConversationModule) {
  // カスタムメタデータ
}
```

## 🚨 注意事項

- **APIレート制限**: Qiita API は 1000 req/h（認証あり）
- **非公開記事**: `--private` フラグで下書き投稿
- **会話データ**: 個人情報含む会話は除外すること

## 📝 ライセンス

MIT

---

**🤖 Powered by**: Claude Code + MindBase
