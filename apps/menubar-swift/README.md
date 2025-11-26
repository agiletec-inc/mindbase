# MindBase Menubar (Swift)

**Native macOS menubar app for automatic AI conversation collection.**

Built with Swift + SwiftUI, inspired by OrbStack and cmd-ime patterns.

## Features

- **Native macOS**: MenuBarExtra + FSEvents (no Electron bloat)
- **Auto-Collection**: Monitors conversation directories and triggers collectors
- **Lightweight**: ~20MB memory (vs 150MB for Electron)
- **Fast**: Instant startup, native performance
- **Clean UI**: OrbStack-inspired minimalist design

## Installation

### From Source

```bash
cd apps/menubar-swift
swift build --configuration release
./.build/release/MindBaseMenubar
```

### Homebrew (Recommended)

```bash
brew tap agiletec-inc/mindbase
brew install mindbase-menubar

# Run as service
brew services start mindbase-menubar
```

## Usage

1. **Launch**: App appears in macOS menubar (🧠 icon)
2. **Toggle Auto-Collection**: Click menu → Toggle switch
3. **Monitor**: Status indicator shows API health (🟢 healthy / 🔴 down)

## Architecture

```
MindBaseMenubarApp (SwiftUI)
├── AppState (@MainActor)
│   ├── Health monitoring (URLSession)
│   ├── Auto-collection toggle
│   └── Collector execution (Process)
│
├── ConversationWatcher (FSEvents)
│   ├── Monitors: ~/.claude, ~/.cursor, ~/Library/Application Support/Windsurf
│   ├── Debouncing (1s)
│   └── Callback on file changes
│
└── MindBaseMenu (SwiftUI View)
    ├── Header (status indicator)
    ├── Toggle (Auto-Collection)
    ├── Actions (Refresh, Dashboard)
    └── Quit button
```

## Watched Directories

- **Claude Code**: `~/.claude/`
- **Claude Desktop**: `~/Library/Application Support/Claude/`
- **Cursor**: `~/.cursor/`
- **Windsurf**: `~/Library/Application Support/Windsurf/`
- **ChatGPT**: `~/Library/Application Support/ChatGPT/`

## Development

```bash
# Build
swift build

# Run
swift run

# Release build
swift build --configuration release

# Watch mode (with entr)
find Sources -name "*.swift" | entr -r swift run
```

## Comparison: Swift vs Electron

| Feature | Swift (This) | Electron (Old) |
|---------|-------------|----------------|
| **Build Time** | 15s ⚡ | Build broken ❌ |
| **Memory** | ~20MB 💚 | ~150MB 🔴 |
| **Startup** | Instant ⚡ | Slow 🐌 |
| **FSEvents** | Native ✅ | fs.watch (buggy) ❌ |
| **MenuBar** | MenuBarExtra ✅ | Tray (complex) ⚠️ |
| **Distribution** | Single binary ✅ | node_modules hell ❌ |

## Design Inspiration

- **OrbStack**: Clean, minimal menubar UI
- **cmd-ime**: Native Swift MenuBarExtra pattern
- **Raycast**: Quick actions with icons

## License

MIT
