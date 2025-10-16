# MindBase Makefile - Docker-First Development
# 標準コマンド: makefile-global準拠

.PHONY: help up down restart logs ps clean clean-all config test

# デフォルトターゲット
.DEFAULT_GOAL := help

## help: 全コマンド一覧表示
help:
	@echo "MindBase - AI Conversation Knowledge Management"
	@echo ""
	@echo "Usage: make <target>"
	@echo ""
	@echo "Basic Operations:"
	@echo "  up           - Start all services (PostgreSQL + API)"
	@echo "  down         - Stop all services"
	@echo "  restart      - Restart services"
	@echo "  logs         - Show all logs"
	@echo "  logs-<svc>   - Show specific service logs (api, postgres)"
	@echo "  ps           - Show container status"
	@echo ""
	@echo "Setup:"
	@echo "  init         - Initial setup (install Ollama + pull model)"
	@echo "  install-ollama - Install Ollama via brew (Mac only)"
	@echo "  model-pull   - Pull qwen3-embedding:8b model (Mac Ollama)"
	@echo "  migrate      - Run database migrations"
	@echo ""
	@echo "Development:"
	@echo "  api-shell    - Enter API container shell"
	@echo "  db-shell     - Enter PostgreSQL shell"
	@echo "  test         - Run tests"
	@echo ""
	@echo "Cleanup:"
	@echo "  clean        - Remove local artifacts (node_modules, __pycache__)"
	@echo "  clean-all    - Complete cleanup (⚠️ data loss: volumes deleted)"
	@echo ""
	@echo "Information:"
	@echo "  config       - Show Docker Compose configuration"
	@echo "  health       - Check service health status"
	@echo ""
	@echo "Note: Ollama runs on Mac (brew), not Docker (GPU acceleration)"

## up: 全サービス起動
up:
	@echo "🚀 Starting MindBase services..."
	@if ! command -v ollama &> /dev/null; then \
		echo "⚠️  Ollama not found. Run: make install-ollama"; \
		exit 1; \
	fi
	@if ! pgrep -x "ollama" > /dev/null; then \
		echo "🔄 Starting Ollama (Mac)..."; \
		ollama serve > /dev/null 2>&1 & \
		sleep 2; \
	fi
	docker compose up -d --remove-orphans
	@echo "✅ Services started"
	@echo ""
	@echo "  API:        http://localhost:18002"
	@echo "  Ollama:     http://localhost:11434 (Mac)"
	@echo "  PostgreSQL: localhost:15433"

## down: 全サービス停止
down:
	@echo "🛑 Stopping MindBase services..."
	docker compose down --remove-orphans
	@echo "✅ Services stopped"

## restart: サービス再起動
restart: down up

## logs: 全ログ表示
logs:
	docker compose logs -f

## logs-api: APIログ
logs-api:
	docker compose logs -f api

## logs-postgres: PostgreSQLログ
logs-postgres:
	docker compose logs -f postgres


## ps: コンテナ状態確認
ps:
	docker compose ps

## init: 初回セットアップ
init: install-ollama up model-pull migrate
	@echo "✅ MindBase初期化完了"

## install-ollama: Ollama をbrewでインストール（Mac）
install-ollama:
	@if command -v ollama &> /dev/null; then \
		echo "✅ Ollama already installed"; \
	else \
		echo "📥 Installing Ollama via brew..."; \
		brew install ollama; \
		echo "✅ Ollama installed"; \
	fi

## model-pull: qwen3-embedding:8bダウンロード（Mac Ollama）
model-pull:
	@echo "📥 Pulling qwen3-embedding:8b model (Mac Ollama)..."
	@if ! command -v ollama &> /dev/null; then \
		echo "❌ Ollama not found. Run: make install-ollama"; \
		exit 1; \
	fi
	ollama pull qwen3-embedding:8b
	@echo "✅ Model downloaded"

## migrate: データベースマイグレーション
migrate:
	@echo "🗄️  Running database migrations..."
	docker compose exec postgres psql -U mindbase -d mindbase -f /docker-entrypoint-initdb.d/20241217120000_mind_base_schema.sql
	@echo "✅ Migrations completed"

## api-shell: APIコンテナシェル
api-shell:
	docker compose exec api bash

## db-shell: PostgreSQLシェル
db-shell:
	docker compose exec postgres psql -U mindbase -d mindbase

## test: テスト実行
test:
	docker compose exec api pytest tests/ -v

## clean: ローカル成果物削除
clean:
	@echo "🧹 Cleaning local artifacts..."
	find . -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name "node_modules" -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name ".pytest_cache" -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name "*.egg-info" -exec rm -rf {} + 2>/dev/null || true
	find . -type f -name ".DS_Store" -delete 2>/dev/null || true
	@echo "✅ Cleanup complete"

## clean-all: 完全削除（ボリューム含む）
clean-all:
	@echo "⚠️  WARNING: This will delete all data (PostgreSQL + Ollama models)"
	@read -p "Continue? [y/N] " -n 1 -r; \
	echo; \
	if [[ $$REPLY =~ ^[Yy]$$ ]]; then \
		docker compose down -v --remove-orphans; \
		echo "✅ Complete cleanup done"; \
	else \
		echo "❌ Aborted"; \
	fi

## config: Docker Compose設定表示
config:
	docker compose config

## health: サービスヘルスチェック
health:
	@echo "🏥 Health Status:"
	@echo ""
	@echo "PostgreSQL:"
	@docker compose exec postgres pg_isready -U mindbase || echo "  ❌ Not ready"
	@echo ""
	@echo "Ollama (Mac):"
	@ollama list 2>/dev/null || echo "  ❌ Not ready (run: ollama serve)"
	@echo ""
	@echo "API:"
	@curl -s http://localhost:18002/health | jq . || echo "  ❌ Not ready"
