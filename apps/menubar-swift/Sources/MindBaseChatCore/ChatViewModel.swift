import SwiftUI

// MARK: - Chat View Model

@MainActor
public final class ChatViewModel: ObservableObject {
    @Published public var messages: [ChatMessage] = []
    @Published public var streamingText: String = ""
    @Published public var isStreaming: Bool = false
    @Published public var error: String?

    @AppStorage("chat.model") public var selectedModel: String = "qwen2.5:3b"
    @Published public var availableModels: [OllamaModel] = []
    @Published public var isLoadingModels: Bool = false

    @AppStorage("chat.temperature") public var temperature: Double = 0.7
    @AppStorage("chat.maxTokens") public var maxTokens: Int = 2048

    @AppStorage("chat.systemPrompt") public var systemPrompt: String = """
        You are MindBase, a helpful AI assistant with access to the user's conversation history.
        Answer questions concisely and helpfully. Use the provided context when relevant.
        """

    private let ollama = OllamaClient()
    private var currentTask: Task<Void, Never>?
    private let mindbase = MindBaseClient()

    public init() {
        Task { await loadModels() }
    }

    // MARK: - Models

    public func loadModels() async {
        isLoadingModels = true
        defer { isLoadingModels = false }

        do {
            availableModels = try await ollama.listModels()

            // Check if current model is valid (not an embedding model and exists)
            let currentModelValid = availableModels.contains { $0.name == selectedModel }
            if !currentModelValid {
                // Prefer qwen2.5:3b, otherwise use first available
                if let qwen = availableModels.first(where: { $0.name.contains("qwen2.5") }) {
                    selectedModel = qwen.name
                } else if let first = availableModels.first {
                    selectedModel = first.name
                }
            }
        } catch {
            self.error = "Failed to load models: \(error.localizedDescription)"
        }
    }

    public func selectModel(_ model: OllamaModel) {
        selectedModel = model.name
    }

    public func pullModel(_ name: String) async {
        do {
            for try await progress in try await ollama.pullModel(name) {
                if progress.status == "success" {
                    await loadModels()
                }
            }
        } catch {
            self.error = "Failed to pull model: \(error.localizedDescription)"
        }
    }

    // MARK: - Chat

    public func send(_ userText: String) {
        guard !userText.trimmingCharacters(in: .whitespacesAndNewlines).isEmpty else { return }

        let userMessage = ChatMessage(role: .user, content: userText)
        messages.append(userMessage)
        streamingText = ""
        isStreaming = true
        error = nil

        currentTask?.cancel()

        currentTask = Task { [weak self] in
            guard let self = self else { return }

            do {
                let contexts = await self.fetchRAGContext(query: userText)

                var chatMessages: [OllamaChatMessage] = []
                var system = self.systemPrompt
                if !contexts.isEmpty {
                    system += "\n\n[CONTEXT FROM MINDBASE]\n"
                    system += contexts.joined(separator: "\n")
                    system += "\n[/CONTEXT]"
                }
                chatMessages.append(OllamaChatMessage(role: "system", content: system))

                let recentMessages = self.messages.suffix(10)
                for msg in recentMessages {
                    let role = msg.role == .user ? "user" : "assistant"
                    chatMessages.append(OllamaChatMessage(role: role, content: msg.content))
                }

                let options = OllamaOptions(temperature: self.temperature, numPredict: self.maxTokens)
                var fullResponse = ""

                for try await chunk in await self.ollama.chat(
                    model: self.selectedModel,
                    messages: chatMessages,
                    options: options
                ) {
                    if Task.isCancelled { break }
                    if let content = chunk.message?.content {
                        fullResponse += content
                        await MainActor.run { self.streamingText = fullResponse }
                    }
                }

                await MainActor.run {
                    if !fullResponse.isEmpty {
                        self.messages.append(ChatMessage(role: .assistant, content: fullResponse, ragContextCount: contexts.count))
                    }
                    self.streamingText = ""
                    self.isStreaming = false
                }

                Task { await self.saveToMindBase(user: userText, assistant: fullResponse) }

            } catch {
                await MainActor.run {
                    if !Task.isCancelled { self.error = error.localizedDescription }
                    self.isStreaming = false
                    self.streamingText = ""
                }
            }
        }
    }

    public func stop() {
        currentTask?.cancel()
        currentTask = nil
        if !streamingText.isEmpty {
            messages.append(ChatMessage(role: .assistant, content: streamingText + " [stopped]"))
        }
        streamingText = ""
        isStreaming = false
    }

    public func retry() {
        if let lastUserIndex = messages.lastIndex(where: { $0.role == .user }) {
            let userMessage = messages[lastUserIndex].content
            messages = Array(messages.prefix(lastUserIndex))
            send(userMessage)
        }
    }

    public func clearChat() {
        currentTask?.cancel()
        messages.removeAll()
        streamingText = ""
        isStreaming = false
        error = nil
    }

    public func deleteMessage(_ id: UUID) {
        messages.removeAll { $0.id == id }
    }

    // MARK: - RAG

    private func fetchRAGContext(query: String) async -> [String] {
        do {
            return try await mindbase.searchContext(query: query, limit: 3)
        } catch {
            return []
        }
    }

    private func saveToMindBase(user: String, assistant: String) async {
        do {
            try await mindbase.saveConversation(userMessage: user, assistantMessage: assistant, model: selectedModel)
        } catch {}
    }
}

// MARK: - Chat Message

public struct ChatMessage: Identifiable, Equatable {
    public let id = UUID()
    public let role: Role
    public let content: String
    public let timestamp = Date()
    public var ragContextCount: Int = 0

    public enum Role: Equatable {
        case user
        case assistant
        case system
    }

    public init(role: Role, content: String, ragContextCount: Int = 0) {
        self.role = role
        self.content = content
        self.ragContextCount = ragContextCount
    }

    public static func == (lhs: ChatMessage, rhs: ChatMessage) -> Bool {
        lhs.id == rhs.id
    }
}

// MARK: - MindBase Client

public struct MindBaseClient: Sendable {
    private var baseURL: String {
        ProcessInfo.processInfo.environment["MINDBASE_API_URL"] ?? "http://localhost:18002"
    }

    public init() {}

    public func searchContext(query: String, limit: Int = 5) async throws -> [String] {
        guard let url = URL(string: "\(baseURL)/conversations/search") else {
            throw URLError(.badURL)
        }

        var request = URLRequest(url: url)
        request.httpMethod = "POST"
        request.setValue("application/json", forHTTPHeaderField: "Content-Type")
        request.timeoutInterval = 5

        let body: [String: Any] = ["query": query, "limit": limit, "threshold": 0.6]
        request.httpBody = try JSONSerialization.data(withJSONObject: body)

        let (data, response) = try await URLSession.shared.data(for: request)

        guard let httpResponse = response as? HTTPURLResponse, httpResponse.statusCode == 200 else {
            return []
        }

        struct SearchResponse: Codable {
            struct Result: Codable {
                let source: String
                let title: String
                let content_preview: String
            }
            let results: [Result]
        }

        let searchResponse = try JSONDecoder().decode(SearchResponse.self, from: data)
        return searchResponse.results.map { "[\($0.source)] \($0.title): \($0.content_preview)" }
    }

    public func saveConversation(userMessage: String, assistantMessage: String, model: String) async throws {
        guard let url = URL(string: "\(baseURL)/conversations/store") else {
            throw URLError(.badURL)
        }

        var request = URLRequest(url: url)
        request.httpMethod = "POST"
        request.setValue("application/json", forHTTPHeaderField: "Content-Type")
        request.timeoutInterval = 5

        let body: [String: Any] = [
            "source": "mindbase-chat",
            "title": String(userMessage.prefix(100)),
            "content": ["user": userMessage, "assistant": assistantMessage],
            "metadata": ["model": model, "app": "MindBaseChat"]
        ]
        request.httpBody = try JSONSerialization.data(withJSONObject: body)

        _ = try await URLSession.shared.data(for: request)
    }
}
