---
title: "Claude Codeが同じミスを繰り返すので、シニアエンジニアに育て直した話"
description: "Claude Codeのループ、幻覚、環境破壊に悩まされた末に辿り着いた、4層の防御アーキテクチャ。CLAUDE.md、Hooks、MCP Gateway、Superpowersプラグインを組み合わせた実践的な設定方法を、失敗談とともに全公開する。"
author: "Kazuki Nakai"
date: "2026-03-28"
tags: ["claude-code", "ai-coding", "mcp", "developer-tools", "productivity"]
language: "ja"
---

# Claude Codeが同じミスを繰り返すので、シニアエンジニアに育て直した話

Claude Codeを使い始めて2年になる。最初の半年は正直、期待はずれだった。

コードは書いてくれる。でも `pnpm install` をホストで実行してDocker環境を壊す。テストを通さずに「完了しました」と報告してくる。同じバグを3回直して3回とも同じ方法で失敗する。指示していないファイルを勝手に作る。`.env` をコミットしそうになる。

「AIってこんなもんか」と思いかけた。

でも違った。Claude Codeが悪いんじゃない。**俺の使い方が悪かった**。人間のジュニアエンジニアだって、ルールを教えずに放り込んだら同じことをする。Claude Codeに足りなかったのは、能力じゃなくて**規律**だった。

この記事では、Claude Codeを「言われたことをなんとなくやるジュニア」から「自分で考えて検証するシニアエンジニア」に変えた、4層の防御アーキテクチャを全部公開する。

---

## 最初の失敗: 「自由にやらせすぎた」

Claude Codeを導入した当初、CLAUDE.mdには「日本語で回答して」くらいしか書いていなかった。

結果:

- **環境破壊**: `npm install` をホストで実行 → Docker環境との不整合でビルドが壊れる → 原因調査に2時間
- **無限ループ**: TypeScriptの型エラーを直そうとして、修正→ビルド→別のエラー→修正→ビルド→最初のエラーに戻る、を5回繰り返す
- **嘘の完了報告**: 「テストが通りました」→ 実際に走らせてみると3件失敗 → 聞くと「テストファイルが見つからなかったのでスキップしました」
- **勝手な改善**: バグ修正を頼んだら、周辺のコードも「ついでにリファクタ」して別のバグを埋め込む

一番痛かったのは、金曜の夜にClaude Codeに「このバグ直して」と頼んで寝て、朝起きたら `node_modules` がホストに生成されていて、Docker環境が完全に壊れていたことだ。土曜の午前中を環境の復旧に費やした。

ここで気づいた。**Claude Codeには「やるべきこと」じゃなくて「やってはいけないこと」を先に教える必要がある。**

---

## 第1層: CLAUDE.md — 憲法を書く

CLAUDE.mdはClaude Codeの「憲法」だ。全ての会話で最初に読み込まれ、全ての行動の基準になる。

俺のCLAUDE.mdのコア部分はこうなっている:

```markdown
# Global Rules

日本語で回答する。コードコメントは英語。

## Docker-First

全てDockerコンテナ内で実行する。ホストでパッケージマネージャやランタイムを直接実行しない。

## Safety

- hookの無効化・削除・迂回をしない（`--no-verify`, `git config core.hooksPath` 変更を含む）
- テスト/lintの失敗はチェックの無効化ではなく原因を修正する
- push/deploy前にユーザーの確認を取る
- 設定ファイルはユーザーの明示的な指示なしに変更しない

## Verify — 完了報告の前に自分で確認する

- 「実装しました」で終わりにせず、Playwrightまたはブラウザで自分の目で動作確認する
- push前に `airis test` を実行してエラー0を確認する
- push後は `gh run watch` でCI完了を待ち、失敗したら自分で修正・re-pushする
- ユーザーをデバッガー代わりにしない
```

### なぜ「Docker-First」を最初に書くのか

これが一番重要なルールだからだ。Claude Codeはデフォルトで `npm install` や `pip install` をホストで実行しようとする。それが「一番簡単」だから。でもDocker環境では、それが致命的な環境破壊になる。

CLAUDE.mdだけでは不十分だった。Claude Codeは長い会話の中でルールを「忘れる」。コンテキストウィンドウの端に追いやられたルールは、新しい指示に負ける。

だから第2層が必要になった。

---

## 第2層: Hooks — 物理的に止める

CLAUDE.mdは「お願い」だ。Hooksは「法律」だ。

Claude Codeには3つのフックポイントがある:

- **PreToolUse**: ツール実行前に割り込む
- **SessionStart**: セッション開始時に実行
- **Stop**: セッション終了時に実行

### Docker-First Guard

一番効果があったのがこれだ:

```bash
#!/bin/bash
# PreToolUse hook for Bash tool
# Block host-level package manager commands

COMMAND="$1"

# Blocked patterns
if echo "$COMMAND" | grep -qE '^\s*(pnpm|npm|yarn)\s+(install|add|remove|update)' ||
   echo "$COMMAND" | grep -qE '^\s*pip\s+install' ||
   echo "$COMMAND" | grep -qE '^\s*brew\s+install'; then
  echo "BLOCKED: Host package manager execution detected."
  echo "Use: docker compose exec <service> <command>"
  exit 1
fi
```

これで `pnpm install` をホストで実行しようとすると、**コマンドが実行される前にブロックされる**。Claude Codeには「ブロックされたよ。`docker compose exec` を使って」というメッセージが返る。

導入前: 週に2〜3回、ホストの `node_modules` を消す作業が発生
導入後: **ゼロ**

### Pre-Push テスト強制

もう一つ、地味だけど効果絶大だったのがpush前のテスト強制:

```bash
# Pre-push hook
# Blocks push if tests fail

if ! airis test; then
  echo "ERROR: Tests failed. Fix before pushing."
  exit 1
fi
```

Claude Codeが「テスト通りました」と嘘をつく問題は、これで完全に消えた。通ってなかったらそもそもpushできないから。

### Session Start: コンテキスト注入

セッション開始時に、プロジェクトの種類とスタックを自動検出して表示する:

```
Project: node | Stack: [supabase, docker, env, github-actions]
Tip: Use airis-route for optimal tool selection
```

これで毎回「このプロジェクトはDockerで動いてて…」と説明する手間が省ける。

---

## 第3層: MCP Gateway — 1コマンドで60以上のツールを手に入れる

ここからが本題だ。

Claude Codeに外部ツールを接続するMCP（Model Context Protocol）は強力だが、素朴に使うと**トークンを大量に消費する**。60個のツールをそれぞれスキーマ付きで登録すると、それだけでコンテキストウィンドウの数千トークンを食う。しかもツールが増えるたびに設定が膨らんで管理が地獄になる。

そこで作ったのが [**airis-mcp-gateway**](https://github.com/agiletec-inc/airis-mcp-gateway) だ。

### セットアップは3行

```bash
git clone https://github.com/agiletec-inc/airis-mcp-gateway.git
cd airis-mcp-gateway && docker compose up -d
claude mcp add --scope user --transport sse airis-mcp-gateway http://localhost:9400/sse
```

これだけ。この3行で、ドキュメント検索（context7）、Web検索（tavily）、データベース操作（supabase）、決済（stripe）、インフラ管理（cloudflare）、デザインファイル（figma）、ブラウザ操作（chrome-devtools）— 60以上のツールが一発で使えるようになる。

### 核心: `airis-exec` — たった1つのツールで全部呼べる

従来のMCPでは、60個のツールを個別に登録する必要があった。airis-mcp-gatewayの発想は逆だ。**Claude Codeに見せるのは `airis-exec` という1つのメタツールだけ**。

```
Claude Code
    ↓ "airis-exec を1回呼ぶだけ"
airis-mcp-gateway (FastAPI)
    ↓ 内部で適切なサーバーにルーティング
┌─────────────────────────────────┐
│ context7  tavily  supabase      │
│ stripe  cloudflare  figma       │
│ chrome-devtools  memory  ...    │
│         25+ servers             │
└─────────────────────────────────┘
```

`airis-exec` のツール説明文の中に、利用可能な全ツールのリストが埋め込まれている。Claude Codeはこの説明文を読むだけで「何が使えるか」を把握し、そのまま呼び出せる。**ツール検索のステップすら不要**。

```
Claude Codeの思考:
「Next.jsのドキュメントを調べたい」
→ airis-execの説明文を見る
→ [context7] resolve-library-id, query-docs がある
→ airis-exec("context7:resolve-library-id", { "libraryName": "next.js" })
→ 公式ドキュメントが返ってくる
→ それを元にコードを書く
```

1回のツール呼び出しで、公式ドキュメントにアクセスしてからコードを書く。**これだけで幻覚が激減する**。

### トークン削減効果

- Before: 60ツール × 平均700トークン/スキーマ = **42,000トークン**（常時消費）
- After: `airis-exec` 含む7メタツール = **約1,400トークン**

**97%削減**。これは誇張じゃない。実測値だ。

コンテキストウィンドウの4万トークンが空くということは、その分だけ長い会話ができる。大規模なリファクタリングや、複数ファイルにまたがる作業で違いが出る。

### HOT/COLD ライフサイクル

全サーバーを常時起動しておく必要はない。よく使うもの（context7, tavily）はHOT（常時起動）、たまに使うもの（figma, stripe）はCOLD（オンデマンド起動）にする。

COLDサーバーは `airis-exec` で初めて呼ばれた時に**自動起動**する。無効化されたサーバーすら、`airis-exec` で呼べば自動的に有効化→起動→実行まで走る。使い終わったらスリープ。設定を手動で切り替える必要はない。

---

## 第4層: Superpowers — 「考えてから書く」を強制する

最後のピースが[Superpowers](https://github.com/anthropics/claude-code-plugins/tree/main/superpowers)プラグインだ。Claude Codeの公式プラグインマーケットプレイスからインストールできる（`/plugins` → `superpowers` で検索）。

Claude Codeの最大の問題は、**考える前にコードを書き始める**ことだ。人間のジュニアエンジニアと全く同じ。「まず動くものを」と手を動かして、設計を考えずにスパゲッティを量産する。

Superpowersは、Claude Codeに**ワークフローを強制する**プラグインだ:

### 主要スキル

| スキル | 強制する行動 |
|--------|-------------|
| `brainstorming` | コードを書く前に設計を考える。2〜3のアプローチを比較する |
| `writing-plans` | 実装前に計画を立てる。変更ファイル、変更内容、検証手順を明記する |
| `test-driven-development` | テストを先に書く。実装はその後 |
| `systematic-debugging` | バグを見たら闇雲に直さず、仮説を立てて検証する |
| `verification-before-completion` | 「完了しました」と言う前に、自分でテストを走らせて確認する |

### Before/After

**Before（Superpowersなし）**:
```
俺: このバグ直して
Claude: [即座にコードを修正] → [ビルドエラー] → [別の修正] → [テスト失敗] → [また修正] → ループ5回
```

**After（Superpowersあり）**:
```
俺: このバグ直して
Claude: [systematic-debugging発動]
  1. 再現手順を確認
  2. 仮説を3つ立てる
  3. 最も可能性の高い仮説を検証
  4. 原因特定
  5. テストを先に書く
  6. 修正
  7. テスト通過を確認
  8. ブラウザで動作確認
```

ループ回数が体感で**70%減った**。

---

## 4層の相乗効果

この4層は独立して機能するが、組み合わせると相乗効果がある:

```
Layer 4: Superpowers  → 考えてから書く（ワークフロー強制）
Layer 3: MCP Gateway  → 正しい情報を使う（公式ドキュメント参照）
Layer 2: Hooks        → 危険な行動を物理的に止める（ガードレール）
Layer 1: CLAUDE.md    → 基本ルールと価値観を共有する（憲法）
```

下の層ほど「ハード」な制約で、上の層ほど「ソフト」な制約。

CLAUDE.mdだけでは「お願い」で終わる。Hooksで物理的に止めても、正しい情報がなければ間違ったコードを書く。正しい情報があっても、考えずに書いたらスパゲッティになる。

**4層全部揃って初めて、Claude Codeはシニアエンジニアのように動く。**

---

## 導入の順番

全部一気に入れる必要はない。俺が辿った順番で入れるのがおすすめだ:

### Step 1: CLAUDE.md を書く（30分）

まずはプロジェクトの基本ルールを書く。最低限:
- 使用言語
- やってはいけないこと（環境に依存するもの）
- 完了の定義（テスト必須、等）

### Step 2: Hooks を設定する（1時間）

一番効果が高い。`settings.json` に PreToolUse フックを追加して、危険なコマンドをブロックする。

### Step 3: MCP Gateway を導入する（半日）

Docker Composeで立ち上げてSSEで接続するだけ。最初はcontext7（ドキュメント参照）だけでも十分。

### Step 4: Superpowers を入れる（5分）

Claude Codeで `/plugins` → `superpowers` を検索してインストールするだけ。すぐに効果が出る。

---

## まとめ

Claude Codeは、設定次第で全く別物になる。

デフォルトのClaude Codeは「能力は高いが規律がないジュニアエンジニア」だ。CLAUDE.mdで価値観を共有し、Hooksで危険な行動を物理的に止め、MCP Gatewayで正しい情報にアクセスさせ、Superpowersで「考えてから書く」を強制する。

この4層を入れてから、俺は一人法人でありながら、以前の5倍のスピードでプロダクトを開発できるようになった。Claude Codeは「ツール」じゃない。正しく育てれば「チームメイト」になる。

この記事で紹介した設定は全て実際に本番環境で使っているものだ。質問があればコメントで聞いてほしい。

---

## 今すぐ試す

この4層の設定環境を自分でゼロから構築する必要はない。OSSとして公開しているので、すぐに使える。

### airis-mcp-gateway — 60以上のAIツールを1コマンドで

```bash
git clone https://github.com/agiletec-inc/airis-mcp-gateway.git
cd airis-mcp-gateway && docker compose up -d
claude mcp add --scope user --transport sse airis-mcp-gateway http://localhost:9400/sse
```

ドキュメント検索、Web検索、データベース操作、決済、インフラ管理、ブラウザ操作 — 全部これ1つで。

**GitHub**: [agiletec-inc/airis-mcp-gateway](https://github.com/agiletec-inc/airis-mcp-gateway)

### airis-monorepo — Docker-First開発環境を自動生成

`manifest.toml` に設定を書くだけで、Dockerfile、docker-compose.yml、CI/CDパイプラインを自動生成する。どのマシンでも同じ環境が再現できる。この記事で紹介したDocker-Firstの思想を実現するためのCLIツール。

**GitHub**: [agiletec-inc/airis-monorepo](https://github.com/agiletec-inc/airis-monorepo)

---

### 次回予告

この記事では4層の全体像を紹介した。次回以降、各層を深掘りする記事を個別に公開する予定だ:

- **CLAUDE.md 設計パターン集** — 実際に効果があったルールとその理由
- **airis-mcp-gateway 完全ガイド** — インストールからカスタムサーバー追加まで
- **Hooks実践レシピ** — PreToolUse / SessionStart / Stop の具体的な設定例
- **Superpowers活用術** — TDD、デバッグ、プランニングの自動化

気になるテーマがあればコメントで教えてほしい。優先的に書く。
