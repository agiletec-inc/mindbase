# MindBase Documentation

**Last Updated**: 2025-10-14

このディレクトリには、MindBaseプロジェクトの包括的なドキュメントが含まれています。

## 📋 ドキュメント一覧

### 🏗️ システム設計

#### [ARCHITECTURE.md](./ARCHITECTURE.md)
完全なシステムアーキテクチャドキュメント

**内容**:
- システム全体アーキテクチャ図
- コンポーネント設計（Collectors、FastAPI、PostgreSQL、Ollama）
- BaseCollector パターンとデータ正規化
- データベーススキーマ（pgvector統合）
- Embedding戦略（qwen3-embedding:8b）
- セキュリティとプライバシー設計
- エラーハンドリングとロギング
- デプロイメント戦略

**対象読者**: 開発者、アーキテクト

---

### 🗺️ 開発計画

#### [ROADMAP.md](./ROADMAP.md)
Phase 0-3 開発ロードマップとマイルストーン

**内容**:
- **Phase 0 (完了)**: 基盤構築
  - Docker Compose環境、PostgreSQL + pgvector、Ollama統合
  - 基本コレクター、REST API、処理パイプライン
- **Phase 1 (進行中, 30% complete)**: コア機能強化
  - Sprint 1.1: データソース拡張（Grok、Windsurf、既存有効化）
  - Sprint 1.2: Airis MCP Gateway統合
  - Sprint 1.3: Gmail & Google Drive統合
- **Phase 2 (計画中)**: 高度な機能と最適化
  - ハイブリッド検索、パフォーマンス最適化、自動化
- **Phase 3 (将来)**: 本番環境対応とスケール
  - セキュリティ強化、スケーラビリティ、Web UI

**成功指標**:
- コンテキスト継続率 > 90%
- レスポンス品質向上 > 20%
- ミス削減 > 50%
- 検索精度 > 80%

**対象読者**: プロダクトオーナー、プロジェクトマネージャー、開発者

---

### ✅ 実装タスク

#### [TASKS.md](./TASKS.md)
詳細な実装タスクリスト（優先順位付き）

**内容**:
- **Sprint 1.1: データソース拡張** (2週間)
  - Task 1.1.1: 既存コレクター有効化（ChatGPT、Cursor）
  - Task 1.1.2: Grok Collector実装
  - Task 1.1.3: Windsurf Collector実装
  - Task 1.1.4: データ正規化テスト

- **Sprint 1.2: Airis MCP Gateway統合** (2週間)
  - Task 1.2.1: MCP Tool定義実装
  - Task 1.2.2: Gateway Docker統合
  - Task 1.2.3: Claude Code統合テスト

- **Sprint 1.3: Gmail & Google Drive統合** (3週間)
  - Task 1.3.1: Gmail Collector実装
  - Task 1.3.2: Google Drive Collector実装
  - Task 1.3.3: OAuth Token管理

**優先度システム**:
- 🔴 P0: Critical - 今週中
- 🟠 P1: High - このスプリント（2週間）
- 🟡 P2: Medium - このフェーズ（2ヶ月）
- 🟢 P3: Low - 将来のフェーズ

**対象読者**: 開発者、スクラムマスター

---

### 🔌 MCP統合

#### [AIRIS_MCP_INTEGRATION.md](./AIRIS_MCP_INTEGRATION.md)
Airis MCP Gateway統合設計の完全ガイド

**内容**:
- MCP Server概要とゼロトークン統合アプローチ
- Tool定義（mindbase_search、mindbase_store）
- Docker Compose統合とネットワーク構成
- エラーハンドリング（Circuit Breaker、Retry Logic）
- パフォーマンス最適化（キャッシング、レート制限）
- セキュリティ考慮事項
- モニタリングとロギング
- 実装チェックリストとテストシナリオ

**対象読者**: 統合開発者、DevOps

---

### 🔬 リサーチ

#### [research/data-sources-research-2025-10-14.md](./research/data-sources-research-2025-10-14.md)
AI会話データソースの包括的調査

**内容**:
- **ChatGPT**: ローカルストレージ、Cloud Export API、Free vs Plus比較
- **Grok**: Web-based、公式エクスポート、サードパーティツール
- **Gmail**: Gmail API、OAuth 2.0統合パターン
- **Google Drive**: Google Drive API、ドキュメントエクスポート戦略
- **実装推奨**: 優先順位、データ収集戦略、タイムスタンプ戦略
- **セキュリティ**: OAuth Token管理、ローカル暗号化

**調査範囲**:
- 25+ Webソース参照
- 公式ドキュメント検証
- サードパーティツール評価

**対象読者**: 開発者、リサーチャー

---

## 📖 ドキュメント使用ガイド

### 新規参加者向け

**推奨読書順序**:
1. [../README.md](../README.md) - プロジェクト概要とクイックスタート
2. [ARCHITECTURE.md](./ARCHITECTURE.md) - システムの全体像を理解
3. [ROADMAP.md](./ROADMAP.md) - 開発の現状と方向性を把握
4. [TASKS.md](./TASKS.md) - 次に何をすべきか確認

### 実装開始前

**実装前チェックリスト**:
- [ ] [ARCHITECTURE.md](./ARCHITECTURE.md)でコンポーネント設計を確認
- [ ] [TASKS.md](./TASKS.md)で担当タスクの詳細を確認
- [ ] [AIRIS_MCP_INTEGRATION.md](./AIRIS_MCP_INTEGRATION.md)でMCP統合要件を理解（MCP関連タスクの場合）
- [ ] [research/data-sources-research-2025-10-14.md](./research/data-sources-research-2025-10-14.md)でデータソース仕様を確認（Collector実装の場合）

### 特定のトピック

| トピック | ドキュメント |
|---------|------------|
| システム全体の理解 | [ARCHITECTURE.md](./ARCHITECTURE.md) |
| 開発スケジュール | [ROADMAP.md](./ROADMAP.md) |
| 次のタスク | [TASKS.md](./TASKS.md) |
| MCP統合 | [AIRIS_MCP_INTEGRATION.md](./AIRIS_MCP_INTEGRATION.md) |
| データソース仕様 | [research/data-sources-research-2025-10-14.md](./research/data-sources-research-2025-10-14.md) |
| Collector実装 | [ARCHITECTURE.md](./ARCHITECTURE.md#collector-layer-python) + [research/data-sources-research-2025-10-14.md](./research/data-sources-research-2025-10-14.md) |
| データベース設計 | [ARCHITECTURE.md](./ARCHITECTURE.md#data-layer-postgresql--pgvector) |
| API仕様 | [ARCHITECTURE.md](./ARCHITECTURE.md#api-layer-fastapi) |

---

## 🔄 ドキュメント更新ポリシー

### 更新頻度
- **ARCHITECTURE.md**: 設計変更時（月次レビュー）
- **ROADMAP.md**: フェーズ完了時、四半期レビュー
- **TASKS.md**: スプリント開始/終了時
- **AIRIS_MCP_INTEGRATION.md**: MCP仕様変更時
- **research/**: 新規調査完了時

### 更新プロセス
1. 変更をドキュメントに反映
2. "Last Updated" 日付を更新
3. 変更履歴セクションに記録（該当する場合）
4. 関連ドキュメントの整合性を確認

### 整合性チェック
- ドキュメント間の矛盾を四半期ごとに確認
- 実装とドキュメントの乖離を月次で確認
- コードレビュー時にドキュメント更新を促す

---

## 📚 追加リソース

### 外部ドキュメント
- [FastAPI Documentation](https://fastapi.tiangolo.com/)
- [pgvector GitHub](https://github.com/pgvector/pgvector)
- [Ollama Documentation](https://ollama.ai/)
- [MCP Protocol Specification](https://modelcontextprotocol.io/)
- [Gmail API Python Quickstart](https://developers.google.com/workspace/gmail/api/quickstart/python)
- [Google Drive API Documentation](https://developers.google.com/drive/api/guides/about-sdk)

### プロジェクト関連
- [SuperClaude Framework](https://github.com/SuperClaude-Org/SuperClaude_Framework)
- [Airis MCP Gateway](https://github.com/airis-mcp-gateway)

---

**Maintainer**: PM Agent / MindBase Team
**Last Review**: 2025-10-14
**Next Review**: 2025-12-01
