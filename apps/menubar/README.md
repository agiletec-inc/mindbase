## MindBase Menubar Companion

Simple Electron-based menu bar application that keeps an eye on the local MindBase stack and provides quick access to collectors, pipelines, and settings.

### Features

- Polls the FastAPI `/health` endpoint and shows API, database, and Ollama status indicators.
- Lists configured collectors/pipelines from the shared Settings API so you always know which workspace they belong to.
- One-click `make up`, `make down`, `make logs`, and `make worker` helpers (runs in the configured repo root).
- Quick links to docs、issue tracker、Settings UI (which updates the server-side settings store).
- Editable settings (API base URL, workspace root, repo root, refresh interval, collectors, pipelines) stored under `~/Library/Application Support/mindbase-menubar` and synced to the API.

### Development

```bash
cd apps/menubar
pnpm install
pnpm dev
```

The tray icon will appear in the macOS menu bar. Use **Settings…** to edit collectors or change the API endpoint. Settings persist per-user in `userData/mindbase-menubar`.
