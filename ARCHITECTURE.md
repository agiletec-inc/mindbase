# MindBase Architecture

**Project**: AI Conversation Knowledge Management System
**Version**: 1.1.0
**Last Updated**: 2025-10-14

---

## Vision & Purpose

**MindBase = LLMの外部記憶装置**

### Core Value Proposition
1. **コンテキスト制約からの解放** - セッションをまたいだ会話の継続
2. **レスポンス品質向上** - 過去の会話を参照した高品質な応答
3. **時系列思考の実現** - タイムスタンプベースの古さ判断
4. **同じミスの防止** - 過去の失敗からの学習

### Use Cases
- **セッション継続**: Claude Codeとの会話が途切れずに継続
- **コンテキスト保持**: 過去のプロジェクト情報を自動参照
- **パターン学習**: 繰り返される課題の自動検出
- **ナレッジベース**: 技術的な議論のアーカイブと検索
- **ブログ生成**: 会話データから自動的に記事生成

---

## System Architecture

### High-Level Overview

```
┌─────────────────────────────────────────────────────────────────┐
│                      Data Collection Layer                       │
├─────────────────────────────────────────────────────────────────┤
│  Claude Code  │ Claude Desktop │  ChatGPT  │  Cursor  │  Grok   │
│  Windsurf     │     Gmail      │  GDrive   │   ...    │         │
└────────┬─────────────┬────────────┬─────────────┬───────────────┘
         │             │            │             │
         ▼             ▼            ▼             ▼
┌─────────────────────────────────────────────────────────────────┐
│                Python Collectors (Base Architecture)             │
│  - BaseCollector (abstract base class)                          │
│  - Message & Conversation dataclasses                           │
│  - Unified timestamp handling                                   │
│  - Source-agnostic normalization                                │
└────────┬────────────────────────────────────────────────────────┘
         │
         ▼
┌─────────────────────────────────────────────────────────────────┐
│                      FastAPI Backend (REST)                      │
│  Endpoints:                                                      │
│  - POST /conversations/store (auto-embedding generation)        │
│  - POST /conversations/search (semantic vector search)          │
│  - GET  /health (service health check)                          │
└────────┬────────────────────────────────────────────────────────┘
         │
         ▼
┌─────────────────────────────────────────────────────────────────┐
│                    Storage & Embedding Layer                     │
│  ┌──────────────────────┐  ┌────────────────────────────────┐  │
│  │  PostgreSQL 17       │  │  Ollama (Local Embedding)      │  │
│  │  + pgvector          │  │  - qwen3-embedding:8b          │  │
│  │  - conversations     │  │  - 1024-dim vectors            │  │
│  │  - thought_patterns  │  │  - MTEB #1 multilingual       │  │
│  │  - book_structure    │  │  - 完全無料・ローカル実行      │  │
│  └──────────────────────┘  └────────────────────────────────┘  │
└────────┬────────────────────────────────────────────────────────┘
         │
         ▼
┌─────────────────────────────────────────────────────────────────┐
│                    Airis MCP Gateway Layer                       │
│  - Exposes MindBase as MCP Server                               │
│  - Tools: mindbase_search, mindbase_store                       │
│  - Dynamic tool loading (zero-token baseline)                   │
└────────┬────────────────────────────────────────────────────────┘
         │
         ▼
┌─────────────────────────────────────────────────────────────────┐
│                       Claude Code Client                         │
│  - Auto-loads MindBase tools                                    │
│  - Contextual conversation search                               │
│  - Automatic conversation storage                               │
└─────────────────────────────────────────────────────────────────┘
```

---

## Component Architecture

### 1. Data Collection Layer

#### 1.1 Python Collectors (`collectors/`)

**Design Pattern**: Abstract Factory with Template Method

```python
BaseCollector (Abstract)
├── get_data_paths() → List[Path]        # Abstract
├── collect() → List[Conversation]       # Abstract
├── validate_conversation()              # Template
├── deduplicate_conversations()          # Template
├── filter_by_date()                     # Template
└── normalize_timestamp()                # Template

Concrete Implementations:
├── ClaudeCollector (Claude Desktop)
├── ChatGPTCollector (ChatGPT)
├── CursorCollector (Cursor IDE)
├── WindsurfCollector (Windsurf IDE)    # Pending
├── GrokCollector (Grok/xAI)            # Pending
├── GmailCollector (Gmail API)          # Pending
└── GoogleDriveCollector (GDrive API)   # Pending
```

**Key Classes**:

```python
@dataclass
class Message:
    role: str                    # 'user', 'assistant', 'system'
    content: str
    timestamp: datetime          # ← Critical for temporal analysis
    message_id: Optional[str]    # Auto-generated from hash
    parent_id: Optional[str]     # For threading
    metadata: Dict[str, Any]     # Source-specific fields

@dataclass
class Conversation:
    id: str                      # Auto-generated: conv_{source}_{hash}
    source: str                  # 'claude-code', 'chatgpt', 'gmail', etc.
    title: str
    messages: List[Message]
    created_at: datetime         # ← Critical
    updated_at: datetime         # ← Critical
    thread_id: Optional[str]     # Original conversation ID
    project: Optional[str]       # Project context
    tags: List[str]              # Classification tags
    metadata: Dict[str, Any]     # Source-specific metadata

    # Helper Methods
    def get_message_count() -> int
    def get_word_count() -> int
    def get_duration() -> float  # Conversation duration in seconds
```

#### 1.2 Data Normalization (`collectors/data_normalizer.py`)

**Responsibilities**:
- Cross-platform data format normalization
- Timestamp unification (all → UTC timezone-aware datetime)
- Content sanitization (privacy patterns removal)
- Metadata extraction and standardization

#### 1.3 Archive Storage

```
~/Library/Application Support/mindbase/
├── conversations/
│   ├── claude-code/
│   │   ├── by-date/2025/10/14/
│   │   ├── by-project/agiletec/
│   │   ├── by-project/mkk/
│   │   └── by-project/global/
│   ├── claude-desktop/
│   ├── chatgpt/
│   ├── cursor/
│   ├── windsurf/
│   ├── grok/
│   ├── gmail/
│   └── google-drive/
└── db/                          # Supabase local persistence
```

**Design Rationale**: Separate from Git repository to prevent Claude Code context noise.

---

### 2. Backend API Layer

#### 2.1 FastAPI Application (`app/`)

**Structure**:
```
app/
├── main.py                      # FastAPI app, CORS, router registration
├── config.py                    # Pydantic settings
├── database.py                  # SQLAlchemy async engine + pgvector
├── ollama_client.py             # Ollama embedding client
├── api/
│   └── routes/
│       ├── conversations.py     # Store & search endpoints
│       └── health.py            # Health check
├── crud/
│   └── conversation.py          # Database operations
├── models/
│   └── conversation.py          # SQLAlchemy models
└── schemas/
    └── conversation.py          # Pydantic validation schemas
```

#### 2.2 API Endpoints

**POST /conversations/store**
```json
Request:
{
  "source": "claude-code",
  "title": "Authentication Implementation",
  "content": {
    "messages": [
      {"role": "user", "content": "Implement JWT auth"},
      {"role": "assistant", "content": "Implementing..."}
    ]
  },
  "metadata": {
    "project": "agiletec",
    "tags": ["authentication", "security"]
  }
}

Response:
{
  "id": "conv_abc123",
  "source": "claude-code",
  "title": "Authentication Implementation",
  "created_at": "2025-10-14T10:30:00Z",
  "embedding_generated": true
}
```

**POST /conversations/search**
```json
Request:
{
  "query": "how to implement JWT authentication with refresh tokens",
  "limit": 10,
  "threshold": 0.7,
  "source": "claude-code"  // Optional filter
}

Response:
[
  {
    "id": "conv_abc123",
    "title": "Authentication Implementation",
    "source": "claude-code",
    "similarity": 0.92,
    "created_at": "2025-10-14T10:30:00Z",
    "content_preview": "Implementing JWT auth with refresh..."
  }
]
```

**GET /health**
```json
Response:
{
  "status": "healthy",
  "services": {
    "database": "connected",
    "ollama": "available",
    "embedding_model": "qwen3-embedding:8b"
  }
}
```

#### 2.3 Database Schema

**PostgreSQL 17 + pgvector**

```sql
-- Main conversations table
CREATE TABLE conversations (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    source VARCHAR(50) NOT NULL,           -- 'claude-code', 'chatgpt', etc.
    title TEXT NOT NULL,
    content JSONB NOT NULL,                 -- Full conversation with messages
    embedding vector(1024),                 -- pgvector embedding
    created_at TIMESTAMP WITH TIME ZONE NOT NULL,
    updated_at TIMESTAMP WITH TIME ZONE NOT NULL,
    thread_id VARCHAR(255),                 -- Original conversation ID
    project VARCHAR(100),
    tags TEXT[],
    metadata JSONB DEFAULT '{}'
);

CREATE INDEX idx_conversations_source ON conversations(source);
CREATE INDEX idx_conversations_created_at ON conversations(created_at DESC);
CREATE INDEX idx_conversations_project ON conversations(project);
CREATE INDEX idx_conversations_embedding ON conversations
    USING ivfflat (embedding vector_cosine_ops) WITH (lists = 100);

-- Thought patterns extraction
CREATE TABLE thought_patterns (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    conversation_id UUID REFERENCES conversations(id),
    pattern_type VARCHAR(50),              -- 'problem-solving', 'architectural', etc.
    pattern_content TEXT,
    confidence FLOAT,
    extracted_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Book/article structure
CREATE TABLE book_structure (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    parent_id UUID REFERENCES book_structure(id),
    title TEXT NOT NULL,
    content TEXT,
    order_index INTEGER,
    depth INTEGER,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);
```

#### 2.4 Embedding Strategy

**Model**: qwen3-embedding:8b (via Ollama)
- **Dimensions**: 1024
- **Performance**: MTEB #1 multilingual (2025)
- **Cost**: Free (local CPU/GPU execution)
- **Size**: ~4.7GB model download

**Generation Flow**:
```python
# Automatic on conversation storage
1. Extract text from conversation messages
2. Call Ollama embedding endpoint
3. Store 1024-dim vector in pgvector column
4. Index for efficient cosine similarity search
```

**Search Flow**:
```python
# Semantic search query
1. Generate embedding for search query
2. Perform cosine similarity search in pgvector
3. Filter by threshold (default: 0.7)
4. Return top N results with similarity scores
```

---

### 3. TypeScript Processing Layer

#### 3.1 Processors (`src/processors/`)

**extract-modules.ts** - Topic Classification
```typescript
// Extract and classify conversation topics
const TOPICS = {
  'Docker-First Development': ['docker', 'container', 'compose'],
  'Turborepo Monorepo': ['turborepo', 'monorepo', 'workspace'],
  'Supabase Self-Host': ['supabase', 'postgres', 'self-host'],
  'Multi-Tenancy': ['tenant', 'isolation', 'multi-tenant'],
  'SuperClaude Framework': ['mode', 'persona', 'mcp', 'superclaude'],
  // ... more topics
};

// Output: modules/{topic}.json
```

#### 3.2 Generators (`src/generators/`)

**generate-article.ts** - Markdown Article Generation
```typescript
// Convert extracted modules to blog articles
interface ArticleTemplate {
  category: string;
  modules: ExtractedModule[];
  template: 'technical' | 'tutorial' | 'case-study';
}

// Output: generated/{date}-{topic}.md
```

**publish-qiita.ts** - Qiita API Publishing
```typescript
// Publish generated articles to Qiita
interface PublishOptions {
  title: string;
  body: string;  // Markdown content
  tags: string[];
  tweet: boolean;
  private: boolean;
}

// Requires: QIITA_TOKEN environment variable
```

#### 3.3 Workflow Scripts (`scripts/`)

```bash
scripts/
├── archive/
│   ├── archive-conversations.sh      # 90日以上の会話をアーカイブ
│   └── optimize-dotclaude.sh         # ~/.claude/ 最適化
├── extract/
│   └── run-extraction.sh             # トピック抽出実行
├── generate/
│   └── run-generation.sh             # 記事生成実行
└── publish/
    └── run-publish.sh                # Qiita投稿実行
```

---

### 4. Airis MCP Gateway Integration

#### 4.1 Gateway Architecture

```
Claude Code
    ↓ (MCP Protocol)
Airis MCP Gateway (Docker)
    ↓ (HTTP)
MindBase FastAPI Backend
    ↓
PostgreSQL + Ollama
```

#### 4.2 MCP Tool Definition

**mindbase_search Tool**:
```json
{
  "name": "mindbase_search",
  "description": "Search past conversations semantically to find relevant context",
  "inputSchema": {
    "type": "object",
    "properties": {
      "query": {
        "type": "string",
        "description": "Search query for semantic similarity"
      },
      "limit": {
        "type": "integer",
        "default": 10,
        "description": "Maximum number of results"
      },
      "source": {
        "type": "string",
        "enum": ["claude-code", "chatgpt", "gmail", "all"],
        "description": "Filter by conversation source"
      }
    },
    "required": ["query"]
  }
}
```

**mindbase_store Tool**:
```json
{
  "name": "mindbase_store",
  "description": "Store current conversation for future reference",
  "inputSchema": {
    "type": "object",
    "properties": {
      "title": {
        "type": "string",
        "description": "Conversation title"
      },
      "messages": {
        "type": "array",
        "items": {"$ref": "#/definitions/Message"}
      },
      "project": {
        "type": "string",
        "description": "Project context"
      },
      "tags": {
        "type": "array",
        "items": {"type": "string"}
      }
    },
    "required": ["title", "messages"]
  }
}
```

#### 4.3 Gateway Configuration

**docker-compose.yml** (Airis Gateway):
```yaml
services:
  airis-gateway:
    image: airis-mcp-gateway:latest
    ports:
      - "8080:8080"
    environment:
      - MINDBASE_API_URL=http://mindbase-api:18002
    volumes:
      - ./config/mcp-tools.json:/app/config/tools.json
    depends_on:
      - mindbase-api
```

**config/mcp-tools.json**:
```json
{
  "tools": [
    {
      "name": "mindbase_search",
      "endpoint": "http://mindbase-api:18002/conversations/search",
      "method": "POST",
      "transform": {
        "input": "query_to_request",
        "output": "response_to_result"
      }
    },
    {
      "name": "mindbase_store",
      "endpoint": "http://mindbase-api:18002/conversations/store",
      "method": "POST"
    }
  ]
}
```

---

## Technology Stack

### Backend
- **Language**: Python 3.12
- **Framework**: FastAPI 0.115.0
- **Database**: PostgreSQL 17 + pgvector 0.3.6
- **ORM**: SQLAlchemy 2.0.36 (async)
- **Embedding**: Ollama 0.4.4 (qwen3-embedding:8b)
- **Validation**: Pydantic 2.10.2

### Frontend/Processing
- **Language**: TypeScript
- **Runtime**: tsx 4.19.2 (Node.js)
- **Package Manager**: pnpm

### Infrastructure
- **Containerization**: Docker Compose
- **Reverse Proxy**: (Future) Traefik
- **MCP Gateway**: Airis MCP Gateway

### Development Tools
- **Testing**: pytest 8.3.4, pytest-asyncio 0.24.0
- **Linting**: ruff 0.8.2
- **Formatting**: black 24.10.0
- **Type Checking**: mypy 1.13.0

---

## Design Principles

### 1. Data Separation
- **Code**: `~/github/mindbase/` (Git-tracked)
- **Data**: `~/Library/Application Support/mindbase/` (Git-ignored)
- **Rationale**: Prevent Claude Code context noise

### 2. Source Agnostic
- Unified `BaseCollector` interface
- Normalized `Conversation` and `Message` dataclasses
- Source-specific logic encapsulated in concrete collectors

### 3. Temporal Priority
- All data includes timezone-aware timestamps
- Enable "ancient data" awareness for LLMs
- Support time-based filtering and analysis

### 4. Privacy First
- Local processing only (no cloud API for embeddings)
- Pattern-based sensitive data exclusion
- OAuth token encryption
- User consent for cloud source integration

### 5. Docker-First Development
- All services containerized
- Mac host environment unpolluted
- Reproducible development environment
- Easy deployment and scaling

### 6. Zero-Token MCP Integration
- Dynamic tool loading via Airis Gateway
- Load tools only when needed
- Unload after use to minimize context
- Strategic tool caching for performance

---

## Scalability Considerations

### Current Capacity
- **Conversations**: Unlimited (PostgreSQL storage)
- **Vector Search**: Efficient with pgvector IVFFlat index
- **Embedding Generation**: Limited by Ollama throughput (~10-20 req/sec on CPU)

### Future Optimizations
1. **Batch Embedding Generation**: Queue system for bulk processing
2. **Read Replicas**: PostgreSQL read replicas for search scaling
3. **Caching Layer**: Redis for frequent searches
4. **Distributed Embedding**: Multiple Ollama instances
5. **Horizontal Scaling**: FastAPI supports multi-instance deployment

---

## Security Architecture

### Authentication & Authorization
- **Current**: No authentication (local-only deployment)
- **Future**: OAuth 2.0 for cloud deployment
- **API Keys**: For programmatic access

### Data Protection
- **At Rest**: PostgreSQL encryption, encrypted backups
- **In Transit**: HTTPS for production deployment
- **Sensitive Data**: Pattern-based filtering before storage

### OAuth Token Management
- **Storage**: `~/.config/mindbase/tokens/` (encrypted)
- **Rotation**: Periodic token refresh
- **Scope**: Minimal necessary permissions

---

## Monitoring & Observability

### Health Checks
- **API Health**: `/health` endpoint
- **Database**: Connection pool monitoring
- **Ollama**: Model availability check

### Metrics (Future)
- **Conversation Volume**: New conversations per day
- **Search Performance**: Query latency, cache hit rate
- **Embedding Generation**: Throughput, queue length
- **Error Rates**: Failed imports, API errors

### Logging
- **Level**: Configurable (DEBUG, INFO, WARN, ERROR)
- **Format**: Structured JSON logs
- **Retention**: 30 days (configurable)

---

## Deployment Architecture

### Development
```
make up → Docker Compose (API + PostgreSQL + Ollama)
pnpm archive → TypeScript workflow on Mac host
```

### Production (Future)
```
Docker Swarm / Kubernetes
├── MindBase API (3 replicas)
├── PostgreSQL (Primary + Replicas)
├── Ollama (GPU instances)
├── Airis MCP Gateway
└── Traefik (Reverse Proxy)
```

---

## Integration Points

### Existing Systems
- **Claude Code**: MCP integration for contextual search
- **Blog Platforms**: Qiita API (implemented), Zenn GitHub integration (pending)

### Future Integrations
- **Slack**: Conversation import from Slack threads
- **Discord**: Bot for conversation archival
- **Notion**: Document import and context linking
- **Linear**: Issue context integration

---

## References

### Documentation
- [FastAPI](https://fastapi.tiangolo.com/)
- [pgvector](https://github.com/pgvector/pgvector)
- [Ollama](https://ollama.ai/)
- [Airis MCP Gateway](https://github.com/airis-mcp-gateway)

### Related Projects
- [dot-claude-optimizer](../INTEGRATION_PLAN.md)
- [claude-blog-automation](../INTEGRATION_PLAN.md)

---

**Document Status**: Living Document - Updated as architecture evolves
**Maintainer**: PM Agent / MindBase Team
**Last Review**: 2025-10-14
