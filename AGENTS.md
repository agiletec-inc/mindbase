# MindBase

会話を保存・派生・検索するlocal-first memory substrate。FastAPI、TypeScript MCP、Postgres+pgvectorを持つ。
構成、command、endpoint、環境変数はworkspace manifest、`.env.example`、compose、testから読む。

## 推測できない境界

- port、URL、connection、provider、modelは環境変数が正本。暗黙fallbackやkey有無によるprovider切替をせず、
  必須値がなければfail fastする。secretを文書・log・fixtureへ入れない。
- root `package.json` と `pnpm-workspace.yaml` の旧generated headerは誤情報。`airis init`は存在せず、両方とも
  checked-in sourceとして直接編集する。現行generatorはこれらを生成しない。
- localはhost-native。Python/TypeScript/testは`uv`/`pnpm`、PostgresだけDocker。OllamaはApple Siliconでは
  host-native。旧`airis up/down/test/lint/exec/shell`を使わない。
- `supabase/migrations`は新しいvolumeの初期化時だけ自動適用される。既存volumeで再適用されたと仮定しない。
- raw conversationはappend-only。embedding等のderived dataと分離し、raw payloadを更新で上書きしない。
- `EMBEDDING_PROVIDER`を明示する。provider別vectorは共存し、切替時に既存vectorを破壊しない。現行の高次元
  vectorはANN indexではなくexact cosine scanを使うため、index追加は実測とpgvector制約を確認する。
- Python workspace packageはrepo rootからin-place importする。`app` symlinkや`PYTHONPATH`を追加しない。
- MCP toolの失敗契約は既存client consumerを確認する。例外形式を一方的に変更しない。

変更後は対象languageのlint/typecheck/testに加え、migration・RLS・search変更ならlocal Postgresで代表queryを
検証する。hook/CIは迂回せず、gateが誤りならgate本体と回帰テストを直す。
