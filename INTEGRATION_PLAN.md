# MindBase統合計画

## 統合対象プロジェクト

### dot-claude-optimizer
**責務**: ~/.claude/ 最適化とアーカイブ管理
**使えるもの**:
- `scripts/optimize.sh` - 7日以上の会話をアーカイブ（基本ロジック良好）
- `archive/by-date/`, `archive/by-project/` - 日付・プロジェクト別アーカイブ構造

**問題点**:
- アーカイブ先が `~/github/dot-claude-backup` → Claude が grep/Read で読み込む
- フルバックアップ思想（会話データ + 設定ファイル全部）
- 7日閾値は短すぎ（mindbaseでは60-90日推奨）

### claude-blog-automation
**責務**: 会話 → ブログ記事自動生成
**使えるもの**:
- `scripts/extract-modules.ts` - トピック分類、キーワード抽出（高品質）
- `scripts/generate-article.ts` - Markdown記事生成（Qiita/Zenn互換）
- `scripts/publish-qiita.ts` - Qiita API投稿

**問題点**:
- 入力元が `~/.claude/` → コンテキストノイズ
- アーカイブとの連携なし
- Supabase DBとの統合なし

## 統合後の構造

```
~/Library/Application Support/mindbase/     # データ（Claude読めない）
├── conversations/                          # 会話アーカイブ
│   ├── claude-code/
│   │   ├── agiletec/
│   │   ├── mkk/
│   │   └── global/
│   ├── claude-desktop/
│   └── ...
└── db/                                     # Supabase永続化

~/github/mindbase/                          # ソースコード（Git管理）
├── src/
│   ├── collectors/                         # 会話収集（Python）
│   │   ├── claude_code.py
│   │   ├── claude_desktop.py
│   │   └── base_collector.py
│   │
│   ├── processors/                         # 会話処理（TypeScript）
│   │   ├── extract-modules.ts             # ← blog-automation から
│   │   ├── topic-classifier.ts            # トピック分類
│   │   └── keyword-extractor.ts           # キーワード抽出
│   │
│   ├── generators/                         # 記事生成（TypeScript）
│   │   ├── article-generator.ts           # ← blog-automation から
│   │   ├── qiita-publisher.ts             # ← blog-automation から
│   │   └── zenn-publisher.ts              # 新規
│   │
│   └── mcp-server/                         # MCP API
│       ├── search.ts
│       └── export.ts
│
├── scripts/
│   ├── archive/                            # アーカイブスクリプト
│   │   ├── claude-code-archiver.sh        # ← 既存（改良版）
│   │   └── optimize-dotclaude.sh          # ← 既存（改良版）
│   │
│   ├── extract/                            # 抽出スクリプト
│   │   └── run-extraction.sh              # ← blog-automation統合
│   │
│   ├── generate/                           # 生成スクリプト
│   │   └── run-generation.sh              # ← blog-automation統合
│   │
│   └── publish/                            # 投稿スクリプト
│       └── run-publish.sh                 # ← blog-automation統合
│
├── supabase/                               # Supabase設定
│   ├── migrations/
│   └── functions/
│
├── templates/                              # 記事テンプレート
├── modules/                                # 抽出済みモジュール（JSON）
├── generated/                              # 生成記事（Markdown）
├── package.json                            # 統合依存関係
├── tsconfig.json                           # TypeScript設定
└── README.md                               # 統合ドキュメント
```

## 統合アプローチ

### Phase 1: ディレクトリ統合
```bash
# dot-claude-optimizer から移動
mv ~/github/dot-claude-optimizer/scripts/* ~/github/mindbase/scripts/archive/

# claude-blog-automation から移動
mv ~/github/claude-blog-automation/scripts/* ~/github/mindbase/src/processors/
mv ~/github/claude-blog-automation/templates ~/github/mindbase/
```

### Phase 2: スクリプト修正
**archive/claude-code-archiver.sh**:
```bash
# 変更前
ARCHIVE_ROOT="$HOME/github/dot-claude-backup"

# 変更後
ARCHIVE_ROOT="$HOME/Library/Application Support/mindbase"
```

**processors/extract-modules.ts**:
```typescript
// 変更前
const CLAUDE_DIR = join(homedir(), '.claude')

// 変更後
const ARCHIVE_DIR = join(homedir(), 'Library/Application Support/mindbase/conversations/claude-code')
```

### Phase 3: package.json統合
```json
{
  "name": "mindbase",
  "scripts": {
    "archive": "bash scripts/archive/claude-code-archiver.sh 90",
    "optimize": "bash scripts/archive/optimize-dotclaude.sh 90",
    "extract": "tsx src/processors/extract-modules.ts",
    "generate": "tsx src/generators/article-generator.ts",
    "publish": "tsx src/generators/qiita-publisher.ts"
  },
  "dependencies": {
    "@types/node": "^24.0.0",
    "tsx": "^4.19.2"
  }
}
```

## ワークフロー統合

### 日次ワークフロー
```bash
# 1. ~/.claude/ 最適化（60日以上をアーカイブ）
pnpm optimize 60

# 2. アーカイブから抽出
pnpm extract

# 3. 記事生成
pnpm generate docker-first-development

# 4. 投稿（dry-run）
pnpm publish 2025-10-09-docker-first.md --dry-run
```

### 週次ワークフロー
```bash
# 週1回実行（日曜23:00）
pnpm archive 90          # 90日以上をアーカイブ
pnpm extract             # 新会話を処理
pnpm generate --all      # 全カテゴリ記事生成
```

## データフロー

```
~/.claude/projects/*.jsonl
    ↓
[optimize-dotclaude.sh: 60日以上検出]
    ↓
~/Library/Application Support/mindbase/conversations/claude-code/
    ↓
[extract-modules.ts: トピック分類]
    ↓
~/github/mindbase/modules/*.json
    ↓
[article-generator.ts: 記事生成]
    ↓
~/github/mindbase/generated/*.md
    ↓
[qiita-publisher.ts: API投稿]
    ↓
Qiita/Zenn公開
```

## 利点

### アーキテクチャ的利点
1. **データとコードの分離** - Application Support（データ）/ github（コード）
2. **コンテキストノイズゼロ** - Claude は会話データを読まない
3. **単一責任** - mindbase = 全ての会話管理

### 運用的利点
1. **ワンストップ** - アーカイブ・抽出・生成・投稿が一箇所
2. **自動化** - cron/launchd で完全自動化可能
3. **拡張性** - 新しいAIアプリ追加が容易

### ビジネス的利点
1. **資産化** - 会話データ → ブログ記事 → 収益化
2. **再利用** - 同じ会話から複数記事生成可能
3. **スケール** - 継続的な会話 = 自動的に記事増加

## 次のステップ

1. **ディレクトリ移動** - スクリプトを mindbase に統合
2. **パス修正** - Application Support パスに変更
3. **package.json** - 依存関係とスクリプト統合
4. **テスト実行** - 全ワークフロー検証
5. **旧リポジトリ削除** - dot-claude-optimizer, claude-blog-automation
