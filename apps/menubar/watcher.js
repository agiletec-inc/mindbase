/**
 * File System Watcher for AI Conversation Directories
 *
 * Monitors Claude Code, Cursor, Windsurf, ChatGPT conversation directories
 * and triggers collectors when new conversations are detected.
 */

const fs = require("fs");
const path = require("path");
const os = require("os");
const { spawn } = require("child_process");

class ConversationWatcher {
  constructor(settings, onConversationDetected) {
    this.settings = settings;
    this.onConversationDetected = onConversationDetected;
    this.watchers = new Map();
    this.debounceTimers = new Map();
    this.processedFiles = new Set(); // デバウンス用
  }

  /**
   * Get conversation directories to watch
   */
  getWatchPaths() {
    const home = os.homedir();
    return {
      "claude-code": path.join(home, ".claude"),
      "claude-desktop": path.join(home, "Library/Application Support/Claude"),
      cursor: path.join(home, ".cursor"),
      windsurf: path.join(home, "Library/Application Support/Windsurf"),
      chatgpt: path.join(home, "Library/Application Support/ChatGPT"), // 仮のパス
    };
  }

  /**
   * Start watching all conversation directories
   */
  start() {
    if (!this.settings.autoCollection?.enabled) {
      console.log("[Watcher] Auto-collection disabled");
      return;
    }

    const watchPaths = this.getWatchPaths();

    for (const [source, dirPath] of Object.entries(watchPaths)) {
      // Check if directory exists
      if (!fs.existsSync(dirPath)) {
        console.log(`[Watcher] Skip ${source}: directory not found (${dirPath})`);
        continue;
      }

      try {
        // Watch for changes (recursive)
        const watcher = fs.watch(
          dirPath,
          { recursive: true },
          (eventType, filename) => {
            if (!filename) return;

            // Filter: only JSON files (conversation files)
            if (!filename.endsWith(".json") && !filename.endsWith(".jsonl")) {
              return;
            }

            const fullPath = path.join(dirPath, filename);

            // Debounce: ignore rapid successive events
            const debounceKey = `${source}:${filename}`;
            if (this.debounceTimers.has(debounceKey)) {
              clearTimeout(this.debounceTimers.get(debounceKey));
            }

            this.debounceTimers.set(
              debounceKey,
              setTimeout(() => {
                this.handleFileChange(source, fullPath, filename);
                this.debounceTimers.delete(debounceKey);
              }, 1000) // 1秒のデバウンス
            );
          }
        );

        this.watchers.set(source, watcher);
        console.log(`[Watcher] Watching ${source}: ${dirPath}`);
      } catch (error) {
        console.error(`[Watcher] Failed to watch ${source}:`, error.message);
      }
    }

    console.log(`[Watcher] Started watching ${this.watchers.size} directories`);
  }

  /**
   * Handle file change event
   */
  handleFileChange(source, fullPath, filename) {
    // Check if file exists (might be deleted)
    if (!fs.existsSync(fullPath)) {
      console.log(`[Watcher] File deleted: ${filename}`);
      return;
    }

    // Check if already processed recently
    const processKey = `${source}:${filename}`;
    if (this.processedFiles.has(processKey)) {
      return;
    }

    console.log(`[Watcher] New conversation detected: ${source}/${filename}`);

    // Mark as processed (expires after 5 minutes)
    this.processedFiles.add(processKey);
    setTimeout(() => {
      this.processedFiles.delete(processKey);
    }, 5 * 60 * 1000);

    // Notify parent
    if (this.onConversationDetected) {
      this.onConversationDetected(source, fullPath, filename);
    }

    // Run collector automatically
    if (this.settings.autoCollection?.runCollectorOnDetection) {
      this.runCollector(source);
    }
  }

  /**
   * Run Python collector for specific source
   */
  runCollector(source) {
    const repoRoot = path.resolve(
      this.settings.repoRoot || path.join(os.homedir(), "github", "mindbase")
    );
    const collectorMap = {
      "claude-code": "claude_collector",
      "claude-desktop": "claude_collector",
      cursor: "cursor_collector",
      windsurf: "windsurf_collector",
      chatgpt: "chatgpt_collector",
    };

    const collectorName = collectorMap[source];
    if (!collectorName) {
      console.error(`[Watcher] Unknown source: ${source}`);
      return;
    }

    console.log(`[Watcher] Running collector: ${collectorName} for ${source}`);

    // Run Python collector
    const pythonPath = path.join(repoRoot, "libs", "collectors", `${collectorName}.py`);

    const child = spawn("python3", [pythonPath], {
      cwd: repoRoot,
      env: {
        ...process.env,
        PYTHONPATH: repoRoot,
      },
      stdio: "pipe",
    });

    child.stdout.on("data", (data) => {
      console.log(`[Collector:${source}] ${data.toString().trim()}`);
    });

    child.stderr.on("data", (data) => {
      console.error(`[Collector:${source}] ERROR: ${data.toString().trim()}`);
    });

    child.on("close", (code) => {
      if (code === 0) {
        console.log(`[Collector:${source}] Completed successfully`);
      } else {
        console.error(`[Collector:${source}] Failed with code ${code}`);
      }
    });

    child.on("error", (error) => {
      console.error(`[Collector:${source}] Spawn error:`, error.message);
    });
  }

  /**
   * Stop all watchers
   */
  stop() {
    for (const [source, watcher] of this.watchers) {
      watcher.close();
      console.log(`[Watcher] Stopped watching ${source}`);
    }
    this.watchers.clear();

    // Clear debounce timers
    for (const timer of this.debounceTimers.values()) {
      clearTimeout(timer);
    }
    this.debounceTimers.clear();

    console.log("[Watcher] All watchers stopped");
  }

  /**
   * Restart watchers (useful when settings change)
   */
  restart(newSettings) {
    this.stop();
    this.settings = newSettings;
    this.start();
  }
}

module.exports = { ConversationWatcher };
