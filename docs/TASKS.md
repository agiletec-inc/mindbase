# MindBase Implementation Tasks

**Project**: AI Conversation Knowledge Management System
**Phase**: Phase 1 - Core Functionality Enhancement
**Last Updated**: 2025-10-14

---

## Task Priority Legend

| Priority | Description | Timeline |
|----------|-------------|----------|
| 🔴 P0 | Critical - Blocks other work | This week |
| 🟠 P1 | High - Core functionality | This sprint (2 weeks) |
| 🟡 P2 | Medium - Important but not blocking | This phase (2 months) |
| 🟢 P3 | Low - Nice to have | Future phases |

---

## Sprint 1.1: Data Source Expansion (2025-10-14 - 2025-10-27)

### 🔴 P0: Critical Path Tasks

#### Task 1.1.1: Activate Existing Collectors
**Priority**: 🔴 P0
**Estimated Effort**: 2 hours
**Dependencies**: None
**Owner**: Dev Team

**Description**: Enable and test collectors that are already implemented but not active.

**Subtasks**:
- [ ] Enable ChatGPT collector in `config/daemon-config.json`
  ```json
  "chatgpt": {
    "enabled": true,  // Change from false
    "data_paths": [
      "~/Library/Application Support/com.openai.chat/conversations-v2-{uuid}/"
    ]
  }
  ```

- [ ] Enable Cursor collector
  ```json
  "cursor": {
    "enabled": true,  // Change from false
    "data_paths": [
      "~/Library/Application Support/Cursor/conversations.db"
    ]
  }
  ```

- [ ] Test collectors
  ```bash
  make api-shell
  python -m collectors.chatgpt_collector
  python -m collectors.cursor_collector
  ```

- [ ] Verify data normalization
  - Check timestamp conversion
  - Verify message structure
  - Test conversation ID generation

**Acceptance Criteria**:
- ChatGPT conversations import successfully
- Cursor conversations import successfully
- All conversations stored in PostgreSQL with correct schema
- Embeddings generated for all conversations

**Testing**:
```bash
# Import test
python -m collectors.chatgpt_collector --dry-run

# Database verification
make db-shell
SELECT COUNT(*) FROM conversations WHERE source = 'chatgpt';
SELECT COUNT(*) FROM conversations WHERE source = 'cursor';
```

---

### 🟠 P1: High Priority Tasks

#### Task 1.1.2: Implement Grok Collector
**Priority**: 🟠 P1
**Estimated Effort**: 8 hours
**Dependencies**: Research completed (✅)
**Owner**: Dev Team

**Description**: Implement collector for Grok (xAI) conversations using official export API.

**Subtasks**:
- [ ] Create `collectors/grok_collector.py`
  ```python
  class GrokCollector(BaseCollector):
      def __init__(self):
          super().__init__(source_name="grok")

      def get_data_paths(self) -> List[Path]:
          # Grok is web-only, use API or export file
          return [Path.home() / "Downloads"]  # User export location

      def collect(self, since_date=None) -> List[Conversation]:
          # Parse Grok export file (JSON format)
          pass
  ```

- [ ] Implement export file parser
  - Handle Grok JSON format
  - Extract conversation threads
  - Normalize timestamps (UTC)

- [ ] Add Grok config to `daemon-config.json`
  ```json
  "grok": {
    "enabled": true,
    "export_path": "~/Downloads/grok_export_*.json",
    "note": "User must export via Grok.com → Settings → Data Controls"
  }
  ```

- [ ] Write unit tests
  ```bash
  pytest tests/test_grok_collector.py -v
  ```

**Acceptance Criteria**:
- Grok export files parse successfully
- Conversations normalize to MindBase schema
- Timestamps convert correctly
- Unit tests pass > 95% coverage

**Documentation**:
- Add user guide: "How to Export Grok Conversations"
- Update CLAUDE.md with Grok collector usage

---

#### Task 1.1.3: Implement Windsurf Collector
**Priority**: 🟠 P1
**Estimated Effort**: 12 hours
**Dependencies**: Data format investigation required
**Owner**: Dev Team

**Description**: Investigate Windsurf IDE data storage and implement collector.

**Subtasks**:
- [ ] **Investigation Phase** (4 hours)
  - [ ] Check for local storage paths
    ```bash
    ls -la ~/Library/Application\ Support/ | grep -i windsurf
    ls -la ~/.windsurf/
    ```

  - [ ] Identify data format (SQLite, JSON, or proprietary)
  - [ ] Document conversation structure
  - [ ] Check for API access (if available)

- [ ] **Implementation Phase** (6 hours)
  - [ ] Create `collectors/windsurf_collector.py`
  - [ ] Implement data extraction logic
  - [ ] Normalize to BaseCollector interface

- [ ] **Testing Phase** (2 hours)
  - [ ] Write unit tests
  - [ ] Test with real Windsurf data
  - [ ] Validate normalization

**Acceptance Criteria**:
- Windsurf data paths identified
- Data format documented
- Collector implemented and tested
- Conversations import successfully

**Risk Mitigation**:
- If no local storage exists: Investigate cloud export
- If proprietary format: Reverse engineer or request API access

---

### 🟡 P2: Medium Priority Tasks

#### Task 1.1.4: Integration Testing Suite
**Priority**: 🟡 P2
**Estimated Effort**: 6 hours
**Dependencies**: Task 1.1.1, 1.1.2, 1.1.3
**Owner**: QA / Dev Team

**Description**: Create comprehensive integration tests for all collectors.

**Subtasks**:
- [ ] Create test fixtures for each source
  ```python
  tests/fixtures/
  ├── claude_desktop_sample.json
  ├── chatgpt_sample.json
  ├── cursor_sample.db
  ├── grok_sample.json
  └── windsurf_sample.json
  ```

- [ ] Implement integration test suite
  ```python
  # tests/integration/test_collectors.py
  @pytest.mark.integration
  def test_all_collectors_end_to_end():
      for collector in [ClaudeCollector, ChatGPTCollector, ...]:
          conversations = collector.collect()
          assert all(c.validate() for c in conversations)
          # Store in test database
          # Verify embeddings generated
  ```

- [ ] Setup CI/CD integration
  ```yaml
  # .github/workflows/test.yml
  name: Integration Tests
  on: [push, pull_request]
  jobs:
    test:
      runs-on: ubuntu-latest
      steps:
        - uses: actions/checkout@v3
        - run: make up
        - run: pytest tests/integration/ -v
  ```

**Acceptance Criteria**:
- All collectors tested end-to-end
- CI/CD pipeline passes
- Test coverage > 80%

---

## Sprint 1.2: Airis MCP Gateway Integration (2025-10-28 - 2025-11-10)

### 🔴 P0: Critical Path Tasks

#### Task 1.2.1: Setup Airis MCP Gateway
**Priority**: 🔴 P0
**Estimated Effort**: 4 hours
**Dependencies**: None
**Owner**: DevOps / Dev Team

**Description**: Install and configure Airis MCP Gateway for MindBase.

**Subtasks**:
- [ ] Clone Airis Gateway repository
  ```bash
  cd ~/github/
  git clone https://github.com/airis-io/airis-mcp-gateway.git
  cd airis-mcp-gateway
  ```

- [ ] Create MindBase tool configuration
  ```bash
  mkdir -p config
  cp docs/AIRIS_MCP_INTEGRATION.md config/mindbase.json
  # Edit mindbase.json with actual configuration
  ```

- [ ] Configure docker-compose.yml
  ```yaml
  services:
    airis-gateway:
      image: airis-mcp-gateway:latest
      ports:
        - "8080:8080"
      volumes:
        - ./config:/app/config:ro
      environment:
        - MINDBASE_API_URL=http://mindbase-api:18002
      networks:
        - mindbase-network
  ```

- [ ] Start gateway
  ```bash
  docker compose up -d
  docker compose logs -f airis-gateway
  ```

- [ ] Verify health
  ```bash
  curl http://localhost:8080/health
  curl http://localhost:8080/tools
  ```

**Acceptance Criteria**:
- Gateway starts successfully
- Health check returns 200 OK
- Tools endpoint lists mindbase_search and mindbase_store
- Logs show no errors

---

#### Task 1.2.2: Implement MCP Tool Endpoints
**Priority**: 🔴 P0
**Estimated Effort**: 6 hours
**Dependencies**: Task 1.2.1
**Owner**: Dev Team

**Description**: Ensure MindBase API endpoints are MCP-compatible.

**Subtasks**:
- [ ] Review API endpoint responses
  - Check `/conversations/search` response format
  - Check `/conversations/store` response format
  - Ensure compatibility with tool output schemas

- [ ] Add MCP-specific metadata
  ```python
  # app/api/routes/conversations.py
  @router.post("/conversations/search", response_model=SearchResponse)
  async def search_conversations(query: SearchQuery):
      # Add response metadata for MCP
      return {
          "results": results,
          "total": len(results),
          "query_time_ms": query_time,
          "mcp_version": "1.0",  # MCP compatibility
          "tool_name": "mindbase_search"
      }
  ```

- [ ] Implement request validation
  - Validate query length (3-500 chars)
  - Validate limit (1-50)
  - Validate threshold (0.0-1.0)
  - Return MCP-compatible error responses

- [ ] Add detailed error responses
  ```python
  {
    "error": "invalid_input",
    "message": "Query must be between 3 and 500 characters",
    "field": "query",
    "provided_value": "aa",
    "mcp_error_code": "VALIDATION_ERROR"
  }
  ```

**Acceptance Criteria**:
- API responses match MCP tool schemas
- Input validation works correctly
- Error responses are MCP-compatible
- Unit tests pass

---

#### Task 1.2.3: Claude Code MCP Integration
**Priority**: 🔴 P0
**Estimated Effort**: 4 hours
**Dependencies**: Task 1.2.1, 1.2.2
**Owner**: Dev Team

**Description**: Configure Claude Code to use MindBase via MCP.

**Subtasks**:
- [ ] Create MCP server configuration
  ```json
  // ~/.claude/mcp_servers.json
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

- [ ] Test tool discovery
  - Start Claude Code
  - Check available tools
  - Verify mindbase_search and mindbase_store appear

- [ ] Test search tool
  ```
  User prompt in Claude Code:
  "Search past conversations about JWT authentication"

  Expected: Claude Code uses mindbase_search tool automatically
  ```

- [ ] Test store tool
  ```
  User prompt in Claude Code:
  "Store this conversation about implementing React hooks"

  Expected: Conversation stored with appropriate metadata
  ```

**Acceptance Criteria**:
- Claude Code discovers MindBase tools
- Search queries work from Claude Code
- Conversations store correctly
- No manual tool invocation required (auto-activation)

---

### 🟠 P1: High Priority Tasks

#### Task 1.2.4: Performance Optimization
**Priority**: 🟠 P1
**Estimated Effort**: 8 hours
**Dependencies**: Task 1.2.3
**Owner**: Dev Team

**Description**: Optimize MCP tool performance for production use.

**Subtasks**:
- [ ] Implement Redis caching
  ```yaml
  # docker-compose.yml
  services:
    redis:
      image: redis:7-alpine
      ports:
        - "6379:6379"
  ```

  ```python
  # app/cache.py
  import redis
  r = redis.Redis(host='redis', port=6379)

  @cache_search_results(ttl=300)
  async def search_conversations(query: str):
      # Cache key: hash(query + filters)
      pass
  ```

- [ ] Optimize embedding generation
  - Batch embedding requests
  - Cache common query embeddings
  - Implement async queue (Celery)

- [ ] Optimize database queries
  - Add missing indexes
  - Optimize vector search
  - Connection pooling tuning

- [ ] Load testing
  ```bash
  # k6 load test script
  k6 run scripts/load-test.js --vus 100 --duration 5m
  ```

**Acceptance Criteria**:
- Search response time < 500ms (p95)
- Cache hit rate > 40%
- Tool loading time < 100ms
- Load test passes (100 concurrent users)

---

#### Task 1.2.5: Error Handling & Retry Logic
**Priority**: 🟠 P1
**Estimated Effort**: 4 hours
**Dependencies**: Task 1.2.3
**Owner**: Dev Team

**Description**: Implement robust error handling and retry logic.

**Subtasks**:
- [ ] Implement circuit breaker pattern
  ```python
  from pybreaker import CircuitBreaker

  breaker = CircuitBreaker(
      fail_max=5,
      reset_timeout=30
  )

  @breaker
  async def search_with_breaker(query: str):
      return await search_conversations(query)
  ```

- [ ] Add exponential backoff retry
  ```python
  from tenacity import retry, wait_exponential, stop_after_attempt

  @retry(
      wait=wait_exponential(min=1, max=10),
      stop=stop_after_attempt(3)
  )
  async def search_with_retry(query: str):
      pass
  ```

- [ ] Implement graceful degradation
  - Return cached results on failure
  - Show user-friendly error messages
  - Log errors for debugging

- [ ] Add health check monitoring
  ```python
  @router.get("/health/detailed")
  async def detailed_health():
      return {
          "api": "healthy",
          "database": check_database(),
          "ollama": check_ollama(),
          "cache": check_redis()
      }
  ```

**Acceptance Criteria**:
- Circuit breaker prevents cascade failures
- Retry logic handles transient errors
- Degraded mode works correctly
- Health checks comprehensive

---

## Sprint 1.3: Gmail & Google Drive Integration (2025-11-11 - 2025-12-01)

### 🟠 P1: High Priority Tasks

#### Task 1.3.1: Gmail Collector Implementation
**Priority**: 🟠 P1
**Estimated Effort**: 16 hours
**Dependencies**: Gmail API research completed (✅)
**Owner**: Dev Team

**Description**: Implement Gmail API integration for email conversation import.

**Subtasks**:
- [ ] **OAuth 2.0 Setup** (4 hours)
  ```python
  # collectors/gmail_collector.py
  from google.oauth2.credentials import Credentials
  from googleapiclient.discovery import build

  class GmailCollector(BaseCollector):
      def __init__(self):
          super().__init__(source_name="gmail")
          self.service = self._authenticate()

      def _authenticate(self):
          creds = self._load_credentials()
          if not creds or not creds.valid:
              creds = self._refresh_or_authorize()
          return build('gmail', 'v1', credentials=creds)
  ```

- [ ] **Email Collection** (6 hours)
  - Implement email fetching with filters
  - Extract thread structure
  - Parse email content (HTML → text)
  - Handle attachments (skip or store references)

- [ ] **Data Normalization** (4 hours)
  - Email → Conversation conversion
  - Preserve sender/recipient context
  - Extract timestamps (sent_date)
  - Tag by email labels/folders

- [ ] **Testing** (2 hours)
  - Mock Gmail API responses
  - Test OAuth flow
  - Validate conversation structure

**Acceptance Criteria**:
- OAuth authentication works
- Emails import successfully
- Thread structure preserved
- Timestamps accurate

**Security**:
- Store OAuth tokens encrypted
- Request minimal scopes (gmail.readonly)
- Support token refresh

---

#### Task 1.3.2: Google Drive Collector Implementation
**Priority**: 🟠 P1
**Estimated Effort**: 12 hours
**Dependencies**: Google Drive API research completed (✅)
**Owner**: Dev Team

**Description**: Implement Google Drive API integration for document context.

**Subtasks**:
- [ ] **OAuth 2.0 Setup** (2 hours)
  - Share credentials with Gmail collector
  - Add Drive API scope

- [ ] **Document Collection** (6 hours)
  ```python
  class GoogleDriveCollector(BaseCollector):
      def collect_documents(self, folder_id=None):
          # Query: mimeType contains 'google-apps'
          # Export Google Docs as Markdown
          # Export Sheets as CSV
          # Download PDFs
  ```

- [ ] **Content Extraction** (3 hours)
  - Google Docs → Markdown
  - Google Sheets → structured data
  - Google Slides → text extraction
  - PDFs → text via OCR (future)

- [ ] **Testing** (1 hour)
  - Mock Drive API
  - Test file downloads
  - Validate conversions

**Acceptance Criteria**:
- Documents import successfully
- Google Docs convert to Markdown
- Metadata preserved (created, modified dates)
- Large files handled efficiently

---

### 🟡 P2: Medium Priority Tasks

#### Task 1.3.3: OAuth Token Management
**Priority**: 🟡 P2
**Estimated Effort**: 6 hours
**Dependencies**: Task 1.3.1, 1.3.2
**Owner**: Dev Team

**Description**: Implement secure OAuth token storage and management.

**Subtasks**:
- [ ] Create token storage system
  ```python
  # app/oauth/token_manager.py
  from cryptography.fernet import Fernet

  class TokenManager:
      def __init__(self):
          self.cipher = Fernet(self._load_key())

      def store_token(self, service: str, token: dict):
          encrypted = self.cipher.encrypt(json.dumps(token).encode())
          # Store in ~/.config/mindbase/tokens/{service}.enc

      def load_token(self, service: str) -> dict:
          # Load and decrypt
          pass

      def refresh_token(self, service: str):
          # Auto-refresh expired tokens
          pass
  ```

- [ ] Implement token rotation
- [ ] Add token expiry monitoring
- [ ] Setup auto-refresh background task

**Acceptance Criteria**:
- Tokens stored encrypted
- Auto-refresh works
- Expiry alerts functional

---

## Phase 1 Completion Tasks

### 🟡 P2: Documentation & Polish

#### Task 1.4.1: Update Documentation
**Priority**: 🟡 P2
**Estimated Effort**: 4 hours
**Dependencies**: All Phase 1 tasks
**Owner**: Dev Team

**Subtasks**:
- [ ] Update CLAUDE.md with new collectors
- [ ] Update README.md with usage examples
- [ ] Create user guides for each collector
- [ ] Document OAuth setup process
- [ ] Update API documentation (Swagger)

#### Task 1.4.2: Performance Benchmarking
**Priority**: 🟡 P2
**Estimated Effort**: 4 hours
**Dependencies**: All Phase 1 tasks
**Owner**: Dev Team

**Subtasks**:
- [ ] Run comprehensive performance tests
- [ ] Document baseline metrics
- [ ] Identify optimization opportunities
- [ ] Create performance dashboard

---

## Task Tracking

### Current Sprint Progress (Sprint 1.1)

| Task | Priority | Status | Progress | Owner |
|------|----------|--------|----------|-------|
| 1.1.1 Activate Collectors | 🔴 P0 | ⏳ Not Started | 0% | Dev |
| 1.1.2 Grok Collector | 🟠 P1 | ⏳ Not Started | 0% | Dev |
| 1.1.3 Windsurf Collector | 🟠 P1 | ⏳ Not Started | 0% | Dev |
| 1.1.4 Integration Tests | 🟡 P2 | ⏳ Not Started | 0% | QA |

### Sprint Velocity

| Sprint | Planned | Completed | Velocity |
|--------|---------|-----------|----------|
| 1.1 | 28h | TBD | TBD |
| 1.2 | 26h | TBD | TBD |
| 1.3 | 34h | TBD | TBD |

---

## Definition of Done

A task is considered complete when:
- [ ] All subtasks completed
- [ ] Code reviewed and merged
- [ ] Unit tests written and passing (> 80% coverage)
- [ ] Integration tests passing
- [ ] Documentation updated
- [ ] Performance benchmarks meet targets
- [ ] Deployed to staging environment
- [ ] User acceptance testing passed

---

## Risk Register

| Risk | Impact | Probability | Mitigation | Owner |
|------|--------|-------------|------------|-------|
| Windsurf data format proprietary | High | Medium | Reverse engineer or request API | Dev |
| OAuth setup complexity | Medium | Low | Use existing libraries | Dev |
| Performance bottleneck | High | Medium | Caching + optimization | Dev |
| MCP Gateway instability | High | Low | Circuit breaker + monitoring | DevOps |

---

## Resources

### Development Tools
- **IDE**: VS Code with Python/TypeScript extensions
- **Testing**: pytest, pytest-asyncio, httpx-mock
- **Profiling**: py-spy, cProfile
- **Load Testing**: k6, Locust

### References
- [ARCHITECTURE.md](./ARCHITECTURE.md)
- [ROADMAP.md](./ROADMAP.md)
- [AIRIS_MCP_INTEGRATION.md](./AIRIS_MCP_INTEGRATION.md)
- [Data Sources Research](./research/data-sources-research-2025-10-14.md)

---

**Document Status**: Living Document - Updated weekly
**Next Review**: End of Sprint 1.1 (2025-10-27)
**Maintainer**: PM Agent / Scrum Master
**Approval**: Product Owner

---

**Change Log**:
- 2025-10-14: Initial task breakdown for Phase 1
- TBD: Weekly sprint updates
