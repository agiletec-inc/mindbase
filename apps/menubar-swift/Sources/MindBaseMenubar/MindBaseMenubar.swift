import SwiftUI

@main
struct MindBaseMenubarApp: App {
    @StateObject private var appState = AppState()

    var body: some Scene {
        // Chat Window (先に定義)
        Window("MindBase Chat", id: "chat") {
            ChatWindow()
        }
        .defaultSize(width: 600, height: 500)
        .defaultPosition(.center)
        .windowLevel(.floating)

        // MenuBarExtra (後から定義)
        MenuBarExtra {
            MindBaseMenu()
                .environmentObject(appState)
        } label: {
            // アイコンは固定で brain
            ZStack(alignment: .bottomTrailing) {
                Image(systemName: "brain")

                // ON/OFFバッジ（右下）
                Circle()
                    .fill(appState.autoCollectionEnabled ? .green : .red)
                    .frame(width: 8, height: 8)
                    .overlay(
                        Image(systemName: appState.autoCollectionEnabled ? "checkmark" : "xmark")
                            .font(.system(size: 5, weight: .bold))
                            .foregroundColor(.white)
                    )
                    .offset(x: 4, y: 2)
            }
        }
    }
}

// MARK: - App State
@MainActor
class AppState: ObservableObject {
    @Published var autoCollectionEnabled = true  // デフォルトON
    @Published var apiHealthy = false
    @Published var lastHealthCheck: Date?

    private var watcher: ConversationWatcher?

    init() {
        // Initialize health check
        Task {
            await checkHealth()
        }

        // Auto-start watcher
        startWatcher()
    }

    func toggleAutoCollection() {
        autoCollectionEnabled.toggle()

        if autoCollectionEnabled {
            startWatcher()
        } else {
            stopWatcher()
        }
    }

    func startWatcher() {
        watcher = ConversationWatcher { source, path in
            print("[MindBase] Conversation detected: \(source) - \(path)")
            self.runCollector(source: source)
        }
        watcher?.start()
    }

    func stopWatcher() {
        watcher?.stop()
        watcher = nil
    }

    func runCollector(source: String) {
        Task {
            do {
                let repoRoot = FileManager.default.homeDirectoryForCurrentUser
                    .appendingPathComponent("github/mindbase")

                let collectorMap: [String: String] = [
                    "claude-code": "claude_collector",
                    "claude-desktop": "claude_collector",
                    "cursor": "cursor_collector",
                    "windsurf": "windsurf_collector",
                    "chatgpt": "chatgpt_collector"
                ]

                guard let collectorName = collectorMap[source] else {
                    print("[MindBase] Unknown source: \(source)")
                    return
                }

                let process = Process()
                process.executableURL = URL(fileURLWithPath: "/usr/bin/python3")
                process.arguments = ["-m", "libs.collectors.\(collectorName)"]
                process.currentDirectoryURL = repoRoot
                process.environment = [
                    "PYTHONPATH": repoRoot.path,
                    "PATH": ProcessInfo.processInfo.environment["PATH"] ?? ""
                ]

                let pipe = Pipe()
                process.standardOutput = pipe
                process.standardError = pipe

                try process.run()
                process.waitUntilExit()

                if process.terminationStatus == 0 {
                    print("[MindBase] Collector completed: \(source)")
                } else {
                    print("[MindBase] Collector failed: \(source)")
                }
            } catch {
                print("[MindBase] Error running collector: \(error)")
            }
        }
    }

    func checkHealth() async {
        do {
            let url = URL(string: "http://localhost:18002/health")!
            let (data, _) = try await URLSession.shared.data(from: url)
            let health = try JSONDecoder().decode(HealthStatus.self, from: data)

            await MainActor.run {
                self.apiHealthy = (health.status == "healthy")
                self.lastHealthCheck = Date()
            }
        } catch {
            print("[MindBase] Health check failed: \(error)")
            await MainActor.run {
                self.apiHealthy = false
            }
        }
    }
}

// MARK: - Menu View
struct MindBaseMenu: View {
    @EnvironmentObject var appState: AppState
    @Environment(\.openWindow) private var openWindow

    var body: some View {
        // Status header (disabled, just for display)
        Text("MindBase — \(appState.apiHealthy ? "✓ Healthy" : "⏳ Checking...")")

        Divider()

        // Auto-Collection Toggle
        Toggle(isOn: Binding(
            get: { appState.autoCollectionEnabled },
            set: { _ in appState.toggleAutoCollection() }
        )) {
            Text("Auto-Collection")
        }

        Divider()

        // Quick Actions
        Button {
            NSApp.activate(ignoringOtherApps: true)
            openWindow(id: "chat")
            DispatchQueue.main.asyncAfter(deadline: .now() + 0.1) {
                if let window = NSApp.windows.first(where: { $0.title == "MindBase Chat" }) {
                    window.makeKeyAndOrderFront(nil)
                    window.orderFrontRegardless()
                }
            }
        } label: {
            Label("Open Chat", systemImage: "message.fill")
        }

        Button {
            Task { await appState.checkHealth() }
        } label: {
            Label("Refresh Health", systemImage: "arrow.clockwise")
        }

        Button {
            if let url = URL(string: "http://localhost:18002/docs") {
                NSWorkspace.shared.open(url)
            }
        } label: {
            Label("Open Dashboard", systemImage: "chart.bar")
        }

        Divider()

        Button {
            NSApplication.shared.terminate(nil)
        } label: {
            Label("Quit", systemImage: "power")
        }
        .keyboardShortcut("q")
    }
}

// MARK: - Models
struct HealthStatus: Codable {
    let status: String
    let timestamp: String
    let version: String
    let services: [String: String]
}
