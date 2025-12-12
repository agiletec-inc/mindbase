import SwiftUI

@main
struct MindBaseMenubarApp: App {
    @StateObject private var appState = AppState()

    var body: some Scene {
        // MenuBarExtra only - Chat is separate app
        MenuBarExtra("MindBase", systemImage: "brain") {
            MindBaseMenu()
                .environmentObject(appState)
        }
    }
}

// MARK: - App State
@MainActor
class AppState: ObservableObject {
    @Published var autoCollectionEnabled = true  // デフォルトON
    @Published var apiHealthy = false
    @Published var ollamaHealthy = false
    @Published var lastHealthCheck: Date?

    // Model selection
    @AppStorage("selectedModel") var selectedModel: String = AppConfig.defaultModel
    @Published var availableModels: [String] = []
    @Published var isLoadingModels = false

    private var watcher: ConversationWatcher?

    init() {
        // Initialize health check and fetch models
        Task {
            await checkHealth()
            await checkOllamaHealth()
            await fetchModels()
        }

        // Auto-start watcher
        startWatcher()
    }

    /// Check Ollama health
    func checkOllamaHealth() async {
        do {
            guard let url = URL(string: AppConfig.ollamaTagsURL) else {
                throw URLError(.badURL)
            }
            var request = URLRequest(url: url)
            request.timeoutInterval = 5.0
            let (_, response) = try await URLSession.shared.data(for: request)

            await MainActor.run {
                if let httpResponse = response as? HTTPURLResponse {
                    self.ollamaHealthy = (httpResponse.statusCode == 200)
                }
            }
        } catch {
            print("[MindBase] Ollama health check failed: \(error)")
            await MainActor.run {
                self.ollamaHealthy = false
            }
        }
    }

    /// Fetch available models from Ollama
    func fetchModels() async {
        isLoadingModels = true
        defer { isLoadingModels = false }

        do {
            let models = try await OllamaClient.fetchModels()
            await MainActor.run {
                self.availableModels = models
                // If selected model is not available, use first available or default
                if !models.contains(selectedModel) && !models.isEmpty {
                    self.selectedModel = models.first ?? AppConfig.defaultModel
                }
            }
        } catch {
            print("[MindBase] Failed to fetch models: \(error)")
            // Keep default model on failure
            await MainActor.run {
                if self.availableModels.isEmpty {
                    self.availableModels = [AppConfig.defaultModel]
                }
            }
        }
    }

    func selectModel(_ model: String) {
        selectedModel = model
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
            guard let url = URL(string: AppConfig.mindbaseHealthURL) else {
                throw URLError(.badURL)
            }
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

    var body: some View {
        // Status header
        Text("MindBase — \(appState.apiHealthy ? "✓ API" : "⏳ API") | \(appState.ollamaHealthy ? "✓ Ollama" : "⏳ Ollama")")

        Divider()

        // Chat Options submenu
        Menu {
            Button {
                openOpenWebUI()
            } label: {
                Label("Open WebUI", systemImage: "globe")
            }

            Button {
                launchOllamaApp()
            } label: {
                Label("Ollama App", systemImage: "app")
            }

            Divider()

            Button {
                launchBuiltInChat()
            } label: {
                Label("MindBase Chat", systemImage: "message.fill")
            }
        } label: {
            Label("Open Chat", systemImage: "message.fill")
        }

        Divider()

        // Model Selection submenu
        Menu {
            if appState.isLoadingModels {
                Text("Loading models...")
            } else if appState.availableModels.isEmpty {
                Text("No models available")
                Button("Refresh") {
                    Task { await appState.fetchModels() }
                }
            } else {
                ForEach(appState.availableModels, id: \.self) { model in
                    Button {
                        appState.selectModel(model)
                    } label: {
                        HStack {
                            Text(model)
                            if model == appState.selectedModel {
                                Spacer()
                                Image(systemName: "checkmark")
                            }
                        }
                    }
                }
                Divider()
                Button {
                    Task { await appState.fetchModels() }
                } label: {
                    Label("Refresh Models", systemImage: "arrow.clockwise")
                }
            }
        } label: {
            Label("Model: \(appState.selectedModel)", systemImage: "cpu")
        }

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
            Task {
                await appState.checkHealth()
                await appState.checkOllamaHealth()
                await appState.fetchModels()
            }
        } label: {
            Label("Refresh Status", systemImage: "arrow.clockwise")
        }

        Button {
            if let url = URL(string: AppConfig.mindbaseDocsURL) {
                NSWorkspace.shared.open(url)
            }
        } label: {
            Label("Open API Docs", systemImage: "doc.text")
        }

        Divider()

        Button {
            NSApplication.shared.terminate(nil)
        } label: {
            Label("Quit", systemImage: "power")
        }
        .keyboardShortcut("q")
    }

    // MARK: - Chat Launch Methods

    /// Open WebUI (default: http://localhost:3000)
    private func openOpenWebUI() {
        let openWebUIURL = ProcessInfo.processInfo.environment["OPEN_WEBUI_URL"] ?? "http://localhost:3000"
        if let url = URL(string: openWebUIURL) {
            NSWorkspace.shared.open(url)
        }
    }

    /// Launch Ollama native app
    private func launchOllamaApp() {
        let possiblePaths = [
            "/Applications/Ollama.app",
            NSHomeDirectory() + "/Applications/Ollama.app"
        ]

        for path in possiblePaths {
            if FileManager.default.fileExists(atPath: path) {
                NSWorkspace.shared.openApplication(
                    at: URL(fileURLWithPath: path),
                    configuration: .init()
                ) { _, error in
                    if let error = error {
                        print("[MindBase] Failed to launch Ollama app: \(error)")
                    }
                }
                return
            }
        }
        // Fallback: open Ollama website
        if let url = URL(string: "https://ollama.com/download") {
            NSWorkspace.shared.open(url)
        }
    }

    /// Launch built-in MindBase Chat
    private func launchBuiltInChat() {
        // Try debug build first (development), then release paths
        let possiblePaths = [
            // Debug build (development)
            NSHomeDirectory() + "/github/mindbase/apps/menubar-swift/.build/debug/MindBaseChat",
            // App bundle paths
            NSHomeDirectory() + "/Applications/MindBase Chat.app",
            "/Applications/MindBase Chat.app",
            Bundle.main.bundlePath.replacingOccurrences(of: "MindBase.app", with: "MindBase Chat.app")
        ]

        for path in possiblePaths {
            if FileManager.default.fileExists(atPath: path) {
                if path.hasSuffix(".app") {
                    NSWorkspace.shared.openApplication(
                        at: URL(fileURLWithPath: path),
                        configuration: .init()
                    ) { _, error in
                        if let error = error {
                            print("[MindBase] Failed to launch chat: \(error)")
                        }
                    }
                } else {
                    // Launch executable directly
                    let process = Process()
                    process.executableURL = URL(fileURLWithPath: path)
                    try? process.run()
                }
                return
            }
        }
        print("[MindBase] Chat app not found")
    }
}

// MARK: - Models
struct HealthStatus: Codable {
    let status: String
    let timestamp: String
    let version: String
    let services: [String: String]
}
