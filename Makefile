# MindBase Makefile - Docker-First Development
# 標準コマンド: makefile-global準拠

.PHONY: help up down restart logs ps clean clean-all config test

# デフォルトターゲット
.DEFAULT_GOAL := help

# 環境判別（Apple Silicon vs その他）
UNAME_S := $(shell uname -s)
UNAME_M := $(shell uname -m)

ifeq ($(UNAME_S),Darwin)
    ifeq ($(UNAME_M),arm64)
        PLATFORM := apple_silicon
    else
        PLATFORM := intel_mac
    endif
else
    PLATFORM := other
endif

OLLAMA_METHOD := docker
OLLAMA_URL := http://ollama:11434

## help: 全コマンド一覧表示
help:
	@echo "MindBase - AI Conversation Knowledge Management"
	@echo ""
	@echo "Platform: $(PLATFORM) | Ollama: $(OLLAMA_METHOD)"
	@echo ""
	@echo "Usage: make <target>"
	@echo ""
	@echo "Basic Operations:"
	@echo "  up           - Start all services (PostgreSQL + API + Ollama)"
	@echo "  down         - Stop all services"
	@echo "  restart      - Restart services"
	@echo "  logs         - Show all logs"
	@echo "  logs-<svc>   - Show specific service logs (api, postgres, ollama)"
	@echo "  ps           - Show container status"
	@echo ""
	@echo "Setup:"
	@echo "  init         - Initial setup (install Ollama + pull model)"
	@echo "  install-ollama - Install Ollama (auto-detect: brew or Docker)"
	@echo "  model-pull   - Pull qwen3-embedding:8b model"
	@echo "  migrate      - Run database migrations"
	@echo ""
	@echo "Development:"
	@echo "  api-shell       - Enter API container shell"
	@echo "  db-shell        - Enter PostgreSQL shell"
	@echo "  test            - Run all tests"
	@echo "  test-unit       - Run unit tests only"
	@echo "  test-integration - Run integration tests only"
	@echo "  test-e2e        - Run E2E tests only"
	@echo "  test-cov        - Run tests with coverage report"
	@echo ""
	@echo "Cleanup:"
	@echo "  clean        - Remove local artifacts (node_modules, __pycache__)"
	@echo "  clean-all    - Complete cleanup (⚠️ data loss: volumes deleted)"
	@echo ""
	@echo "Information:"
	@echo "  config       - Show Docker Compose configuration"
	@echo "  health       - Check service health status"
	@echo "  platform     - Show detected platform and Ollama method"
	@echo ""
ifeq ($(OLLAMA_METHOD),native)
	@echo "Note: Apple Silicon detected → Ollama via brew (Metal GPU 3-5x faster)"
else
	@echo "Note: Using Dockerized Ollama for all platforms"
endif

## platform: 検出されたプラットフォーム情報表示
platform:
	@echo "🖥️  Platform Detection:"
	@echo "  OS:            $(UNAME_S)"
	@echo "  Architecture:  $(UNAME_M)"
	@echo "  Platform:      $(PLATFORM)"
	@echo "  Ollama Method: $(OLLAMA_METHOD)"
	@echo "  Ollama URL:    $(OLLAMA_URL)"
ifeq ($(OLLAMA_METHOD),native)
	@echo "  GPU Support:   Metal (Apple Silicon)"
else
	@echo "  GPU Support:   Depends on Ollama container configuration"
endif

## up: 全サービス起動
up:
	@echo "🚀 Starting MindBase services ($(PLATFORM))..."
	docker compose --profile ollama up -d --remove-orphans
	@echo "✅ Services started"
	@echo ""
	@echo "  API:        http://localhost:18002"
	@echo "  Ollama:     $(OLLAMA_URL)"
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

## logs-ollama: Ollamaログ
logs-ollama:
ifeq ($(OLLAMA_METHOD),native)
	@echo "Native Ollama - check system logs or run: ollama serve (foreground)"
else
	docker compose logs -f ollama
endif


## ps: コンテナ状態確認
ps:
	docker compose ps

## init: 初回セットアップ
init: install-ollama up model-pull migrate
	@echo "✅ MindBase初期化完了"

## install-ollama: Ollama インストール（環境自動判別）
install-ollama:
ifeq ($(OLLAMA_METHOD),native)
	@# Apple Silicon → brew install
	@echo "📥 Installing Ollama for Apple Silicon (brew + Metal GPU)..."
	@if command -v ollama &> /dev/null; then \
		echo "✅ Ollama already installed"; \
		ollama --version; \
	else \
		echo "🔄 Installing via brew..."; \
		brew install ollama; \
		echo "✅ Ollama installed"; \
		ollama --version; \
	fi
else
	@# Intel Mac / Linux / Windows → Docker
	@echo "📥 Ollama will run via Docker (no installation needed)"
	@echo "✅ Docker Compose will handle Ollama service"
endif

## model-pull: qwen3-embedding:8b ダウンロード
model-pull:
	@echo "📥 Pulling qwen3-embedding:8b model..."
ifeq ($(OLLAMA_METHOD),native)
	@# Native Ollama
	@if ! command -v ollama &> /dev/null; then \
		echo "❌ Ollama not found. Run: make install-ollama"; \
		exit 1; \
	fi
	@if ! pgrep -x "ollama" > /dev/null; then \
		echo "🔄 Starting Ollama service..."; \
		ollama serve > /dev/null 2>&1 & \
		sleep 3; \
	fi
	ollama pull qwen3-embedding:8b
else
	@# Docker Ollama
	@if ! docker compose --profile ollama ps | grep -q ollama; then \
		echo "🔄 Starting Ollama container..."; \
		docker compose --profile ollama up -d ollama; \
		sleep 5; \
	fi
	docker compose exec ollama ollama pull qwen3-embedding:8b
endif
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

define RUN_IN_CONTAINER
	docker compose exec api bash -lc 'set -euo pipefail; \
		SRC=/workspace/mindbase; \
		WORK=/tmp/mindbase; \
		rm -rf "$$WORK"; \
		mkdir -p "$$WORK"; \
		cp "$$SRC/pytest.ini" "$$WORK/"; \
		cp -r "$$SRC/tests" "$$WORK/"; \
		cp -r "$$SRC/collectors" "$$WORK/"; \
		cp -r "$$SRC/scripts" "$$WORK/"; \
		if [ -d "$$SRC/docs" ]; then cp -r "$$SRC/docs" "$$WORK/"; fi; \
		cp -r "$$SRC/apps/api" "$$WORK/app"; \
		export PYTHONPATH="$$WORK"; \
		cd "$$WORK"; \
		$(1)'
endef

## test: 全テスト実行
test:
	$(call RUN_IN_CONTAINER,pytest tests/ -v)

## test-unit: ユニットテストのみ
test-unit:
	$(call RUN_IN_CONTAINER,pytest tests/unit -v -m unit)

## test-integration: 統合テストのみ
test-integration:
	$(call RUN_IN_CONTAINER,pytest tests/integration -v -m integration)

## test-e2e: E2Eテストのみ
test-e2e:
	$(call RUN_IN_CONTAINER,pytest tests/e2e -v -m e2e)

## test-cov: カバレッジレポート付きテスト
test-cov:
	$(call RUN_IN_CONTAINER,pytest tests/ -v --cov=app --cov=collectors --cov-report=html --cov-report=term-missing)

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
	@echo "🏥 Health Status ($(PLATFORM)):"
	@echo ""
	@echo "PostgreSQL:"
	@docker compose exec postgres pg_isready -U mindbase || echo "  ❌ Not ready"
	@echo ""
	@echo "Ollama ($(OLLAMA_METHOD)):"
ifeq ($(OLLAMA_METHOD),native)
	@ollama list 2>/dev/null || echo "  ❌ Not ready (run: ollama serve)"
else
	@docker compose exec ollama ollama list 2>/dev/null || echo "  ❌ Not ready (run: make up)"
endif
	@echo ""
	@echo "API:"
	@curl -s http://localhost:18002/health | jq . || echo "  ❌ Not ready"
