## MindBase Menubar Companion

Electron-based menu bar application that monitors the local MindBase stack and **automatically collects AI conversations** from Claude Code, Cursor, Windsurf, and ChatGPT.

### Features

#### Core Monitoring
- Polls the FastAPI `/health` endpoint and shows API, database, and Ollama status indicators.
- Lists configured collectors/pipelines from the shared Settings API so you always know which workspace they belong to.
- One-click `make up`, `make down`, `make logs`, and `make worker` helpers (runs in the configured repo root).
- Quick links to docs, issue tracker, Settings UI (which updates the server-side settings store).

#### **NEW: Auto-Collection** 🎯
- **File System Watcher**: Monitors conversation directories for Claude Code, Cursor, Windsurf, ChatGPT
- **Auto-Collector Execution**: Automatically runs Python collectors when new conversations are detected
- **Debouncing**: Prevents duplicate processing with smart debouncing (1s)
- **Toggle Control**: Enable/disable auto-collection via menu bar toggle (✓ Auto-Collection Enabled)

#### Settings
- Editable settings (API base URL, workspace root, repo root, refresh interval, collectors, pipelines, auto-collection)
- Settings stored under `~/Library/Application Support/mindbase-menubar` and synced to the API
- Auto-collection settings:
  - `enabled`: Enable/disable auto-collection
  - `runCollectorOnDetection`: Auto-run collectors on file detection
  - `debounceMs`: Debounce interval (default: 1000ms)

### Development

```bash
cd apps/menubar
pnpm install
pnpm dev
```

The tray icon will appear in the macOS menu bar. Use **Settings…** to edit collectors or change the API endpoint. Settings persist per-user in `userData/mindbase-menubar`.

### Auto-Collection Setup

1. **Enable Auto-Collection**: Click menu bar icon → "Auto-Collection Disabled" to toggle ON
2. **Verify Watched Paths**: Watcher monitors these directories:
   - Claude Code: `~/.claude`
   - Claude Desktop: `~/Library/Application Support/Claude`
   - Cursor: `~/.cursor`
   - Windsurf: `~/Library/Application Support/Windsurf`
   - ChatGPT: `~/Library/Application Support/ChatGPT` (if exists)
3. **Test**: Create/modify a conversation file in any watched directory
4. **Check Logs**: Run `pnpm dev` in terminal to see watcher logs

### Architecture

```
MindBase Menubar App
├── main.js              # Main process, menu, health polling
├── watcher.js           # NEW: File system watcher + collector runner
├── preload.js           # IPC bridge
├── settings.html        # Settings UI
└── config/
    └── default-settings.json  # Default settings (includes autoCollection)
```

### File Watcher Flow

```
1. User creates conversation in Claude Code
   ↓
2. fs.watch detects change in ~/.claude/
   ↓
3. Debounce filter (1s)
   ↓
4. watcher.js triggers collector
   ↓
5. Python collector runs (libs/collectors/claude_collector.py)
   ↓
6. Conversation saved to PostgreSQL via API
   ↓
7. Menu bar shows updated status
```
