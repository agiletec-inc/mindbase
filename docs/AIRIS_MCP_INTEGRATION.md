# Airis MCP Gateway Integration Design

**Project**: MindBase - AI Conversation Knowledge Management
**Component**: Airis MCP Gateway Integration Layer
**Version**: 1.0.0
**Last Updated**: 2025-10-14

---

## Overview

This document details the integration between MindBase and Airis MCP Gateway to expose conversation search and storage capabilities to Claude Code via the Model Context Protocol (MCP).

### Goals
1. **Seamless Integration**: Claude Code automatically accesses MindBase without manual configuration
2. **Zero-Token Baseline**: Tools load dynamically only when needed
3. **High Performance**: Search responses < 500ms, tool loading < 100ms
4. **Transparent Operation**: Users unaware of underlying MCP mechanics

---

## Architecture Overview

```
┌─────────────────────────────────────────────────────────────────┐
│                         Claude Code                              │
│  - User interaction                                              │
│  - MCP client built-in                                           │
└────────────────────┬────────────────────────────────────────────┘
                     │ MCP Protocol (stdio/SSE)
                     ▼
┌─────────────────────────────────────────────────────────────────┐
│                    Airis MCP Gateway                             │
│  - Tool registration & routing                                   │
│  - Request/response transformation                               │
│  - Error handling & retry logic                                  │
│  - Dynamic tool loading/unloading                                │
└────────────────────┬────────────────────────────────────────────┘
                     │ HTTP/REST
                     ▼
┌─────────────────────────────────────────────────────────────────┐
│                    MindBase FastAPI                              │
│  - POST /conversations/store                                     │
│  - POST /conversations/search                                    │
│  - GET  /health                                                  │
└────────────────────┬────────────────────────────────────────────┘
                     │
                     ▼
┌─────────────────────────────────────────────────────────────────┐
│              PostgreSQL + Ollama Embedding                       │
└─────────────────────────────────────────────────────────────────┘
```

---

## MCP Tool Definitions

### Tool 1: mindbase_search

**Purpose**: Semantic search across past conversations to find relevant context

#### Input Schema
```json
{
  "name": "mindbase_search",
  "description": "Search past conversations using semantic similarity. Use this when you need context from previous discussions, code implementations, or problem-solving sessions.",
  "inputSchema": {
    "type": "object",
    "properties": {
      "query": {
        "type": "string",
        "description": "The search query. Can be a question, topic, or description of what you're looking for. Examples: 'authentication implementation', 'database migration errors', 'React hooks patterns'"
      },
      "limit": {
        "type": "integer",
        "default": 10,
        "minimum": 1,
        "maximum": 50,
        "description": "Maximum number of results to return"
      },
      "threshold": {
        "type": "number",
        "default": 0.7,
        "minimum": 0.0,
        "maximum": 1.0,
        "description": "Similarity threshold (0.0-1.0). Higher values return only very similar results. Recommended: 0.7 for general search, 0.8 for specific matches"
      },
      "source": {
        "type": "string",
        "enum": ["all", "claude-code", "claude-desktop", "chatgpt", "cursor", "gmail", "google-drive"],
        "default": "all",
        "description": "Filter results by conversation source"
      },
      "project": {
        "type": "string",
        "description": "Filter by project name (e.g., 'agiletec', 'mkk', 'mindbase')"
      },
      "date_from": {
        "type": "string",
        "format": "date",
        "description": "Filter conversations from this date (ISO 8601 format: YYYY-MM-DD)"
      },
      "date_to": {
        "type": "string",
        "format": "date",
        "description": "Filter conversations up to this date (ISO 8601 format: YYYY-MM-DD)"
      }
    },
    "required": ["query"]
  }
}
```

#### Output Schema
```json
{
  "type": "object",
  "properties": {
    "results": {
      "type": "array",
      "items": {
        "type": "object",
        "properties": {
          "id": {"type": "string"},
          "title": {"type": "string"},
          "source": {"type": "string"},
          "project": {"type": "string"},
          "similarity": {"type": "number"},
          "created_at": {"type": "string", "format": "date-time"},
          "content_preview": {"type": "string"},
          "message_count": {"type": "integer"},
          "tags": {"type": "array", "items": {"type": "string"}}
        }
      }
    },
    "total": {"type": "integer"},
    "query_time_ms": {"type": "integer"}
  }
}
```

#### Example Usage (Claude Code)
```python
# Claude Code automatically uses this tool when searching context
results = mindbase_search(
    query="How did we implement JWT refresh tokens?",
    limit=5,
    threshold=0.8,
    project="agiletec"
)

# Response example:
{
  "results": [
    {
      "id": "conv_abc123",
      "title": "JWT Authentication with Refresh Tokens",
      "source": "claude-code",
      "project": "agiletec",
      "similarity": 0.94,
      "created_at": "2025-10-01T15:30:00Z",
      "content_preview": "Implementing JWT authentication with refresh token rotation...",
      "message_count": 28,
      "tags": ["authentication", "jwt", "security"]
    }
  ],
  "total": 1,
  "query_time_ms": 234
}
```

---

### Tool 2: mindbase_store

**Purpose**: Store current conversation for future reference and context

#### Input Schema
```json
{
  "name": "mindbase_store",
  "description": "Store the current conversation in MindBase for future reference. Automatically generates embeddings for semantic search. Use this when completing important work, solving complex problems, or implementing new features.",
  "inputSchema": {
    "type": "object",
    "properties": {
      "title": {
        "type": "string",
        "description": "Brief descriptive title for the conversation (e.g., 'Implement User Authentication', 'Debug PostgreSQL Performance')"
      },
      "messages": {
        "type": "array",
        "items": {
          "type": "object",
          "properties": {
            "role": {
              "type": "string",
              "enum": ["user", "assistant", "system"]
            },
            "content": {
              "type": "string"
            },
            "timestamp": {
              "type": "string",
              "format": "date-time"
            }
          },
          "required": ["role", "content"]
        },
        "description": "Array of conversation messages"
      },
      "project": {
        "type": "string",
        "description": "Project context (e.g., 'agiletec', 'mkk', 'mindbase')"
      },
      "tags": {
        "type": "array",
        "items": {"type": "string"},
        "description": "Classification tags (e.g., ['authentication', 'security', 'jwt'])"
      },
      "metadata": {
        "type": "object",
        "description": "Additional metadata (files modified, issues resolved, etc.)"
      }
    },
    "required": ["title", "messages"]
  }
}
```

#### Output Schema
```json
{
  "type": "object",
  "properties": {
    "id": {"type": "string"},
    "title": {"type": "string"},
    "source": {"type": "string"},
    "created_at": {"type": "string", "format": "date-time"},
    "embedding_generated": {"type": "boolean"},
    "message_count": {"type": "integer"}
  }
}
```

#### Example Usage (Claude Code)
```python
# Automatically triggered at conversation end or manually
result = mindbase_store(
    title="Implement JWT Authentication with Refresh Tokens",
    messages=[
        {"role": "user", "content": "How do I implement JWT auth?"},
        {"role": "assistant", "content": "Let me help you implement..."}
    ],
    project="agiletec",
    tags=["authentication", "jwt", "security"],
    metadata={
        "files_modified": ["app/auth.py", "app/middleware.py"],
        "issues_resolved": ["#123"]
    }
)

# Response example:
{
  "id": "conv_xyz789",
  "title": "Implement JWT Authentication with Refresh Tokens",
  "source": "claude-code",
  "created_at": "2025-10-14T16:45:00Z",
  "embedding_generated": true,
  "message_count": 28
}
```

---

## Airis Gateway Configuration

### Directory Structure

```
~/github/airis-mcp-gateway/
├── config/
│   ├── mindbase.json              # MindBase tool definitions
│   └── servers.json                # Server registry
├── docker-compose.yml
└── README.md
```

### mindbase.json Configuration

```json
{
  "name": "mindbase",
  "version": "1.0.0",
  "description": "AI Conversation Knowledge Management - Search and store conversations",
  "base_url": "http://mindbase-api:18002",
  "tools": [
    {
      "name": "mindbase_search",
      "endpoint": "/conversations/search",
      "method": "POST",
      "timeout_ms": 5000,
      "retry": {
        "attempts": 3,
        "backoff_ms": 1000
      },
      "transform": {
        "input": {
          "query": "$.query",
          "limit": "$.limit",
          "threshold": "$.threshold",
          "source": "$.source",
          "project": "$.project",
          "date_from": "$.date_from",
          "date_to": "$.date_to"
        },
        "output": {
          "results": "$.results",
          "total": "$.total",
          "query_time_ms": "$.query_time_ms"
        }
      },
      "cache": {
        "enabled": true,
        "ttl_seconds": 300,
        "key_fields": ["query", "source", "project"]
      }
    },
    {
      "name": "mindbase_store",
      "endpoint": "/conversations/store",
      "method": "POST",
      "timeout_ms": 10000,
      "retry": {
        "attempts": 3,
        "backoff_ms": 2000
      },
      "transform": {
        "input": {
          "source": "'claude-code'",
          "title": "$.title",
          "content": {"messages": "$.messages"},
          "metadata": {
            "project": "$.project",
            "tags": "$.tags",
            "custom": "$.metadata"
          }
        },
        "output": {
          "id": "$.id",
          "title": "$.title",
          "source": "$.source",
          "created_at": "$.created_at",
          "embedding_generated": "$.embedding_generated",
          "message_count": "$.message_count"
        }
      },
      "cache": {
        "enabled": false
      }
    }
  ],
  "health_check": {
    "endpoint": "/health",
    "method": "GET",
    "interval_seconds": 60,
    "timeout_ms": 3000
  }
}
```

### docker-compose.yml Integration

```yaml
version: '3.8'

services:
  airis-gateway:
    image: airis-mcp-gateway:latest
    container_name: airis-mcp-gateway
    ports:
      - "8080:8080"
    environment:
      - LOG_LEVEL=INFO
      - CACHE_ENABLED=true
      - CACHE_REDIS_URL=redis://redis:6379
    volumes:
      - ./config:/app/config:ro
    networks:
      - mindbase-network
    depends_on:
      - mindbase-api
      - redis
    restart: unless-stopped
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:8080/health"]
      interval: 30s
      timeout: 10s
      retries: 3

  redis:
    image: redis:7-alpine
    container_name: airis-cache
    ports:
      - "6379:6379"
    volumes:
      - redis_data:/data
    networks:
      - mindbase-network
    restart: unless-stopped

networks:
  mindbase-network:
    driver: bridge

volumes:
  redis_data:
    driver: local
```

---

## Claude Code Integration

### MCP Server Configuration

**Location**: `~/.claude/mcp_servers.json` (Claude Code auto-configures)

```json
{
  "mcpServers": {
    "mindbase": {
      "command": "docker",
      "args": [
        "compose",
        "-f", "/Users/kazuki/github/airis-mcp-gateway/docker-compose.yml",
        "exec", "-T", "airis-gateway",
        "mcp-stdio-server"
      ],
      "env": {
        "MCP_TOOLS_CONFIG": "/app/config/mindbase.json"
      }
    }
  }
}
```

### Auto-Activation Scenarios

#### 1. Context Search (Automatic)
```
User: "How did we implement the authentication flow in agiletec?"

Claude Code Internal:
1. Detects past implementation question
2. Auto-loads mindbase_search tool
3. Queries: "authentication flow implementation agiletec"
4. Returns relevant past conversations
5. Uses context to provide accurate answer
```

#### 2. Problem Solving with History
```
User: "I'm getting a PostgreSQL connection timeout error"

Claude Code Internal:
1. Checks if similar issues were solved before
2. mindbase_search(query="PostgreSQL connection timeout", threshold=0.8)
3. Finds previous solution
4. References past approach in current solution
```

#### 3. Auto-Storage at Session End
```
User: [Completes complex implementation]
Claude Code: "Great! We've successfully implemented JWT authentication."

Claude Code Internal:
1. Detects significant work completed
2. Auto-triggers mindbase_store
3. Stores conversation with:
   - Title: "JWT Authentication Implementation"
   - Project: "agiletec"
   - Tags: ["authentication", "jwt", "security"]
   - Files: ["app/auth.py", "tests/test_auth.py"]
```

---

## Performance Optimization

### Caching Strategy

#### Search Query Caching
```yaml
Strategy: Redis-based LRU cache
TTL: 5 minutes
Key Format: "mindbase:search:{hash(query, source, project)}"
Cache Hit Rate Target: > 40%

Benefits:
- Repeated searches return instantly
- Reduces PostgreSQL load
- Lower Ollama embedding generation calls
```

#### Tool Loading Optimization
```yaml
Strategy: Lazy loading with pre-warming
Load Time Target: < 100ms
Pre-warm: Common tools on gateway startup

Implementation:
1. Gateway starts: Load tool schemas only
2. First use: Load tool handler + cache
3. Subsequent: Retrieve from cache
4. Idle timeout: Unload after 10 minutes
```

### Request Optimization

#### Batch Operations (Future)
```python
# Instead of multiple individual searches
results = mindbase_search_batch([
    {"query": "authentication", "limit": 5},
    {"query": "database migration", "limit": 3}
])

# Single DB query with multiple embeddings
# 60% performance improvement
```

#### Embedding Caching
```yaml
Strategy: Cache embeddings for common queries
Storage: Redis with 24h TTL
Size Estimate: ~1024 bytes per embedding
Cache Keys: "mindbase:embedding:{hash(text)}"
```

---

## Error Handling

### Error Categories

#### 1. Gateway Errors
```json
{
  "error": "gateway_timeout",
  "message": "MindBase API did not respond within 5000ms",
  "retry_after_ms": 2000,
  "support_action": "check_mindbase_health"
}
```

**Handling**:
- Automatic retry with exponential backoff
- Fallback to cached results if available
- User notification on repeated failures

#### 2. API Errors
```json
{
  "error": "search_failed",
  "message": "PostgreSQL connection pool exhausted",
  "status": 503,
  "retry_after_ms": 5000
}
```

**Handling**:
- Circuit breaker pattern (5 failures → open for 30s)
- Graceful degradation (return "MindBase temporarily unavailable")
- Alert system administrators

#### 3. Data Validation Errors
```json
{
  "error": "invalid_input",
  "message": "Query must be between 3 and 500 characters",
  "field": "query",
  "provided_value": "aa"
}
```

**Handling**:
- Return validation error to Claude Code
- Claude reformulates query automatically
- No retry (fix input first)

### Retry Logic

```yaml
Retry Strategy: Exponential backoff with jitter
Max Attempts: 3
Base Delay: 1000ms
Max Delay: 10000ms
Jitter: ±500ms

Retry on:
- HTTP 5xx errors
- Network timeout
- Connection refused

Do NOT retry on:
- HTTP 4xx errors (bad input)
- Authentication failures
- Resource not found
```

---

## Security Considerations

### Authentication (Future)

#### Option 1: API Key (Simple)
```yaml
Implementation:
- Gateway validates API key in headers
- Keys stored in database with rate limits
- Separate keys per user/project

Headers:
  X-MindBase-API-Key: "mb_1234567890abcdef"
```

#### Option 2: OAuth 2.0 (Advanced)
```yaml
Implementation:
- OAuth 2.0 authorization code flow
- JWT tokens with short expiry (1h)
- Refresh tokens for long-lived access

Headers:
  Authorization: "Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9..."
```

### Data Privacy

#### Sensitive Data Filtering
```python
# Already implemented in collectors
EXCLUDE_PATTERNS = [
    r"password",
    r"api_key",
    r"secret",
    r"token",
    r"private_key"
]

# Applied before storage
def sanitize_content(text: str) -> str:
    for pattern in EXCLUDE_PATTERNS:
        text = re.sub(pattern, "[REDACTED]", text, flags=re.IGNORECASE)
    return text
```

#### Access Control
```yaml
Current: Single-user (no access control)

Future:
- User-based conversation isolation
- Project-based access control
- Read/write permission separation
```

---

## Monitoring & Observability

### Key Metrics

#### Gateway Metrics
```yaml
Tool Invocations:
- Total count per tool
- Success/failure rate
- Average response time
- P95/P99 latency

Cache Performance:
- Hit/miss ratio
- Cache size (MB)
- Eviction rate

Errors:
- Error count by type
- Retry success rate
- Circuit breaker state
```

#### API Metrics
```yaml
Endpoint Performance:
- Requests per second
- Response time distribution
- Error rate by endpoint

Database:
- Query latency
- Connection pool usage
- Index hit rate

Ollama:
- Embedding generation time
- Queue length
- Model load
```

### Logging

```yaml
Log Level: INFO (DEBUG for troubleshooting)
Format: JSON structured logs
Retention: 30 days

Log Events:
- Tool invocation (query, source, project)
- Search results (count, similarity scores)
- Storage operations (conversation ID, size)
- Errors (full stack trace)
- Performance (query time, embedding time)
```

### Alerting

```yaml
Critical Alerts:
- Gateway down (>1 min)
- API response time > 2s (sustained)
- Error rate > 5%
- Database connection pool exhausted

Warning Alerts:
- Cache hit rate < 30%
- Ollama queue length > 50
- Disk usage > 80%
```

---

## Testing Strategy

### Unit Tests

```python
# Test gateway tool routing
def test_mindbase_search_routing():
    request = {"query": "authentication", "limit": 5}
    response = gateway.route_tool("mindbase_search", request)
    assert response["status"] == 200
    assert len(response["results"]) <= 5

# Test input validation
def test_invalid_search_query():
    request = {"query": "ab", "limit": 5}  # Too short
    response = gateway.route_tool("mindbase_search", request)
    assert response["status"] == 400
    assert "invalid_input" in response["error"]
```

### Integration Tests

```python
# Test end-to-end flow
def test_search_and_store_flow():
    # Store conversation
    store_result = mindbase_store(
        title="Test Conversation",
        messages=[{"role": "user", "content": "test"}],
        project="test"
    )
    conv_id = store_result["id"]

    # Search for it
    search_result = mindbase_search(query="test", project="test")
    assert any(r["id"] == conv_id for r in search_result["results"])
```

### Load Tests

```yaml
Tool: k6, Locust, or Apache JMeter

Scenarios:
1. Search Load:
   - 100 concurrent users
   - 10 searches/user/minute
   - Duration: 10 minutes
   - Success rate target: > 99%

2. Storage Load:
   - 50 concurrent users
   - 5 stores/user/minute
   - Duration: 5 minutes
   - Success rate target: > 95%

3. Mixed Load:
   - 80% searches, 20% stores
   - 200 concurrent users
   - Duration: 15 minutes
```

---

## Deployment Checklist

### Pre-Deployment
- [ ] MindBase API running and healthy
- [ ] PostgreSQL + pgvector operational
- [ ] Ollama model downloaded (qwen3-embedding:8b)
- [ ] Redis cache running
- [ ] Airis Gateway configured

### Deployment Steps
1. **Start Services**:
   ```bash
   cd ~/github/mindbase && make up
   cd ~/github/airis-mcp-gateway && docker compose up -d
   ```

2. **Verify Health**:
   ```bash
   curl http://localhost:18002/health
   curl http://localhost:8080/health
   ```

3. **Test Tools**:
   ```bash
   # Test search
   curl -X POST http://localhost:8080/tools/mindbase_search \
     -H "Content-Type: application/json" \
     -d '{"query": "test", "limit": 5}'

   # Test store
   curl -X POST http://localhost:8080/tools/mindbase_store \
     -H "Content-Type: application/json" \
     -d '{
       "title": "Test Conversation",
       "messages": [{"role": "user", "content": "test"}]
     }'
   ```

4. **Configure Claude Code**:
   ```bash
   # Update MCP server configuration
   # (Auto-configured by Claude Code in most cases)
   ```

5. **Verify Integration**:
   - Open Claude Code
   - Type: "Search past conversations about authentication"
   - Verify mindbase_search tool is used automatically

### Post-Deployment
- [ ] Monitor logs for errors
- [ ] Check performance metrics
- [ ] Verify cache hit rates
- [ ] Test from Claude Code client

---

## Troubleshooting Guide

### Common Issues

#### 1. Tool Not Loading
```
Error: "mindbase_search tool not found"

Diagnosis:
- Check Airis Gateway health: curl http://localhost:8080/health
- Check tool configuration: cat ~/github/airis-mcp-gateway/config/mindbase.json
- Check MCP server logs: docker logs airis-mcp-gateway

Resolution:
- Restart gateway: docker compose restart airis-gateway
- Verify network connectivity to MindBase API
- Check Claude Code MCP server configuration
```

#### 2. Slow Search Performance
```
Error: Search taking > 2 seconds

Diagnosis:
- Check PostgreSQL query performance: EXPLAIN ANALYZE
- Check Ollama embedding generation time
- Check cache hit rate

Resolution:
- Optimize pgvector index: REINDEX INDEX idx_conversations_embedding
- Increase cache TTL
- Add more specific filters (project, date range)
```

#### 3. Storage Failures
```
Error: "Failed to store conversation"

Diagnosis:
- Check PostgreSQL connection pool
- Check Ollama availability
- Check disk space

Resolution:
- Increase connection pool size
- Restart Ollama: docker compose restart ollama
- Clean up old data if disk full
```

---

## Future Enhancements

### Phase 2
- [ ] Batch search operations
- [ ] Real-time conversation streaming
- [ ] Advanced filtering (tags, content type)
- [ ] Conversation similarity clustering

### Phase 3
- [ ] Multi-user support with authentication
- [ ] Conversation sharing via MCP
- [ ] Federated search across multiple MindBase instances
- [ ] AI-powered conversation summarization

---

## References

### Documentation
- [MCP Protocol Specification](https://modelcontextprotocol.io/)
- [Airis MCP Gateway](https://github.com/airis-mcp-gateway)
- [MindBase Architecture](./ARCHITECTURE.md)
- [MindBase Roadmap](./ROADMAP.md)

### Related Files
- `~/github/mindbase/app/api/routes/conversations.py` - API endpoints
- `~/github/mindbase/docker-compose.yml` - MindBase services
- `~/github/airis-mcp-gateway/config/mindbase.json` - Tool configuration

---

**Document Status**: Living Document - Updated as integration evolves
**Next Review**: After Phase 1 Sprint 1.2 completion
**Maintainer**: PM Agent / MindBase Team
**Approval**: Technical Lead

---

**Change Log**:
- 2025-10-14: Initial integration design document
- TBD: Post-implementation review and optimization
