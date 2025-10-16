# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added
- Initial MindBase project structure
- FastAPI backend with PostgreSQL + pgvector for conversation storage
- Ollama integration with qwen3-embedding:8b (1024-dimensional vectors)
- Python collectors for multi-platform conversation gathering (Claude Code, Claude Desktop, ChatGPT, Cursor)
- TypeScript processors for topic extraction and content generation
- Docker-based development environment (API, PostgreSQL, Ollama)
- REST API endpoints for conversation storage and semantic search
- Database migrations with pgvector extension support
- Makefile with standardized development commands
- Archive scripts for conversation data management
- Data separation design (code in Git, conversations in Application Support)

### Documentation
- Comprehensive README with Quick Start guide
- Architecture documentation (ARCHITECTURE.md)
- Development roadmap (ROADMAP.md)
- Task management documentation (docs/TASKS.md)
- Airis MCP Gateway integration plans (docs/AIRIS_MCP_INTEGRATION.md)
- Research documentation for data source integrations

## [0.1.0] - 2025-10-16

### Added
- Project initialization
- MIT License
- Standard OSS project structure
- Git repository setup with proper .gitignore

### Changed
- Moved major documentation files to project root
- Established contribution guidelines
- Added security policy

### Infrastructure
- Docker Compose configuration with three services:
  - FastAPI backend (port 18002)
  - PostgreSQL 17 with pgvector (port 15433)
  - Ollama embedding service (port 11434)
