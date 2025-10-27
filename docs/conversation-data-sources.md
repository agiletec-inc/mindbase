# Conversation Data Sources

MindBase では各種 LLM クライアントがローカルへ保存する会話ログを横断的に収集し、FastAPI + PostgreSQL（pgvector）に集約します。ここでは主要クライアントの保存場所・ファイル形式・取り込み時の注意点と、データベースへの格納方針をまとめます。実装作業の前に、ここで挙げたパスやスキーマが端末のバージョンと一致しているかを必ず確認してください。収集スクリプトは `scripts/collect-conversations.py` から起動でき、正規化したデータを `/conversations/store` に送信します。

## 1. 収集対象ごとの保存形式

### Claude Desktop
- **macOS**: `~/Library/Application Support/Claude/` 配下（`Session Storage/`, `IndexedDB/`, `Local Storage/` を含む）。LevelDB の `.ldb` と LOG、SQLite (`*.sqlite`, `*.db`)、JSON エクスポートが混在。
- **Linux**: `~/.config/Claude/` の同名ディレクトリ、場合によっては `~/.cache/Claude/`。
- **Windows**: `%USERPROFILE%\AppData\Roaming\Claude\`。
- **取り込みポイント**: `collectors/claude_collector.py` が LOG/LevelDB/SQLite の各パターンをスキャンし JSON を抽出。メッセージごとに `role`/`content`/`timestamp` を正規化し、欠損タイムスタンプは UTC 付与で補完する。

### Claude Code (VSCode / Windsurf Plugin)
- **macOS / Linux / Windows**: `~/.claude/` ディレクトリ。
  - `projects/{project}/{conversation_id}.jsonl`: プロジェクト別の JSONL。1 行 1 メッセージ構造。
  - `file-history/{conversation_id}.jsonl`: 古い会話のアーカイブ。
- **取り込みポイント**: `libs/processors/extract-modules.ts` が JSONL を読み込みモジュール化。Collector で読み込む際は `type`（`user`/`assistant`）をそのまま `role` に写経すればよい。

### ChatGPT Desktop
- **macOS**: `~/Library/Application Support/com.openai.chat/`、`~/Library/Application Support/ChatGPT/`、`~/Library/Application Support/OpenAI/` 内に SQLite (`*.db`)、IndexedDB (`*.sqlite`)、Web Storage (`*.ldb`) が配置。
- **Linux**: `~/.config/openai/`、`~/.local/share/openai/`、`~/.cache/openai/` 等。Electron ラッパーによってパスが変動するため `find ~/.config -maxdepth 3 -name 'chatgpt*'` 等で探索する。
- **Windows**: `%USERPROFILE%\AppData\Roaming\OpenAI\` や `%LOCALAPPDATA%\OpenAI\`。
- **取り込みポイント**: `collectors/chatgpt_collector.py` が SQLite・IndexedDB・JSON・ログを横断して抽出。テーブル名はバージョンごとに異なるため `sqlite3 <db> '.tables'` で確認し、`conversation`,`message`,`thread` を含むテーブルのみを対象にする。

### Cursor
- **macOS**: `~/Library/Application Support/Cursor/`（`conversations.db`, `chat_history.json` など）。
- **Linux**: `~/.config/cursor/`。
- **Windows**: `%USERPROFILE%\AppData\Roaming\Cursor\`。
- **現状**: `scripts/collect-conversations.py` の `CursorCollector` は未実装。SQLite/JSON の schema 調査（`PRAGMA table_info`) と Collector への実装が必要。

### Windsurf
- **macOS**: `~/Library/Application Support/WindSurf/`。
- **Linux**: `~/.config/windsurf/`。
- **Windows**: `%USERPROFILE%\AppData\Roaming\WindSurf\`。
- **現状**: `Cursor` と同様に Collector が空実装。アプリのバージョンによっては `chat_history.json` のみ保持するケースがあるため差分調査が必須。

### その他の計画中ソース
- **Slack / Gmail / Google Drive**: ローカルファイルではなく API 連携予定。OAuth トークンは `~/.config/mindbase/tokens/` に暗号化保存し、取得した JSON を `metadata` に付与する設計。
- **Supabase Functions**: 旧構成では `supabase/functions/mind-sync/index.ts` がバッチ同期を担い、`metadata.sync_source_info` に収集元のバージョン/タイムスタンプを保存していた。新 API へ移行する際も同等の情報を `metadata` に引き継ぐ。

## 2. 正規化ポリシー

取り込み時には `collectors/base_collector.py` が提供する `Conversation` / `Message` dataclass を使用し、以下を最低限整備します。

| 項目 | 説明 | 備考 |
| --- | --- | --- |
| `source` | 収集元（例: `claude-desktop`, `chatgpt`） | `conversations` テーブルの `CHECK` 制約に適合させる |
| `source_conversation_id` | 元システムの ID | ない場合はハッシュで合成 |
| `messages` | `role`（`user`/`assistant`/`system`）と `content` を持つ配列 | 文字列以外の payload は `json.dumps` で文字列化 |
| `source_created_at` | 会話の起点時刻 | タイムゾーン付き `datetime` へ正規化 |
| `metadata` | 元データの追加情報 | ファイルパス、クライアントバージョン等を格納 |

Collector では `validate_conversation` が必須フィールドを検証し、`deduplicate_conversations` が `source` × `thread_id` で重複排除します。

## 3. データベースへの取り込み

- FastAPI API (`apps/api/api/routes/conversations.py`) の `/conversations/store` を呼び出すと、`ConversationCreate` スキーマに準拠した JSON を受け取り、pgvector 埋め込みを生成して `conversations` テーブルへ保存します。
- スキーマ定義は `supabase/migrations/20250101000000_mindbase_postgresql.sql` を参照。一次データとベクトルを同じテーブルに保持し、`update_conversation_metrics` トリガーが `message_count` と `raw_content` を自動更新します。
- Embedding は qwen3-embedding:8b を標準としていますが、`embedding` カラムは `NULL` を許容するため、必要なら非同期ジョブで後追い生成も可能です。

## 4. 開発環境の起動手順

1. `.env.example` を `.env` にコピーし、`DATABASE_URL`, `OLLAMA_URL`, `EMBEDDING_MODEL`, `POSTGRES_*` など必須変数を設定。
2. モデル未取得の場合は `make model-pull` で `qwen3-embedding:8b` をダウンロード。
3. 初回のみ `make migrate` で PostgreSQL スキーマを適用。
4. `make up` で PostgreSQL / API / Ollama を起動。Apple Silicon はネイティブ Ollama、その他は Docker プロファイル（`make` の判定参照）。
5. ヘルスチェックは `make health` または `curl http://localhost:18002/health`。API が立ち上がったら Collector から `/conversations/store` を呼ぶとベクトル生成まで含めて保存される。

## 5. 実機確認チェックリスト

- [ ] 各アプリの最新版をインストールして、上記パスにファイルが存在するか確認したか。
- [ ] SQLite ファイルのテーブル構造 (`.tables`, `PRAGMA table_info`) を把握し、Collector のマッピングが実データに合致するか確認したか。
- [ ] JSON/ログ抽出時に文字コード（UTF-8/UTF-16）が混在しないか。
- [ ] 取り込み結果が `conversations` テーブルに期待どおり保存され、`message_count` や `raw_content` が自動更新されるか。
- [ ] `make up` → `make test` がローカルで通るか（ヘルスチェック、埋め込み生成含む）。

このガイドは収集・正規化・保存フローを共通理解として整理したものです。新しいクライアントやバージョンアップが発生した場合は、本書と Collector 実装を同時に更新してください。
