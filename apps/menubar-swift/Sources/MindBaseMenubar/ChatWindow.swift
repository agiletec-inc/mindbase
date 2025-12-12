import SwiftUI

// MARK: - Chat Window
struct ChatWindow: View {
    @EnvironmentObject var appState: AppState
    @StateObject private var chatState = ChatState()
    @State private var inputText = ""

    var body: some View {
        VStack(spacing: 0) {
            // Header
            HStack {
                Circle()
                    .fill(chatState.isProcessing ? .orange : .green)
                    .frame(width: 8, height: 8)
                Text("MindBase Chat")
                    .font(.system(size: 13, weight: .medium))
                Spacer()
                Text(appState.selectedModel)
                    .font(.system(size: 11))
                    .foregroundColor(.secondary)
            }
            .padding(12)
            .background(Color(nsColor: .windowBackgroundColor))

            Divider()

            // Messages
            ScrollViewReader { proxy in
                ScrollView {
                    LazyVStack(alignment: .leading, spacing: 12) {
                        ForEach(chatState.messages) { message in
                            MessageBubble(message: message)
                                .id(message.id)
                        }
                    }
                    .padding(12)
                }
                .onChange(of: chatState.messages.count) {
                    if let lastMessage = chatState.messages.last {
                        withAnimation {
                            proxy.scrollTo(lastMessage.id, anchor: .bottom)
                        }
                    }
                }
            }

            Divider()

            // Input
            HStack(spacing: 8) {
                TextField("Ask about your conversations...", text: $inputText, axis: .vertical)
                    .textFieldStyle(.plain)
                    .lineLimit(1...5)
                    .padding(8)
                    .background(Color(nsColor: .textBackgroundColor))
                    .cornerRadius(8)
                    .onSubmit {
                        sendMessage()
                    }

                Button(action: sendMessage) {
                    Image(systemName: "arrow.up.circle.fill")
                        .font(.system(size: 24))
                        .foregroundColor(inputText.isEmpty ? .gray : .blue)
                }
                .buttonStyle(.plain)
                .disabled(inputText.isEmpty || chatState.isProcessing)
            }
            .padding(12)
        }
        .frame(width: 600, height: 500)
    }

    private func sendMessage() {
        guard !inputText.isEmpty else { return }

        let userMessage = inputText
        inputText = ""

        Task {
            await chatState.sendMessage(userMessage, model: appState.selectedModel)
        }
    }
}

// MARK: - Message Bubble
struct MessageBubble: View {
    let message: ChatMessage

    var body: some View {
        HStack(alignment: .top, spacing: 8) {
            Image(systemName: message.role == .user ? "person.circle.fill" : "brain.head.profile")
                .font(.system(size: 20))
                .foregroundColor(message.role == .user ? .blue : .purple)

            VStack(alignment: .leading, spacing: 4) {
                Text(message.role == .user ? "You" : "MindBase")
                    .font(.system(size: 11, weight: .semibold))
                    .foregroundColor(.secondary)

                Text(message.content)
                    .font(.system(size: 13))
                    .textSelection(.enabled)

                if !message.context.isEmpty {
                    Divider()
                    Text("Context:")
                        .font(.system(size: 10, weight: .semibold))
                        .foregroundColor(.secondary)
                    ForEach(message.context, id: \.self) { ctx in
                        Text("• \(ctx)")
                            .font(.system(size: 10))
                            .foregroundColor(.secondary)
                    }
                }
            }
        }
        .frame(maxWidth: .infinity, alignment: .leading)
    }
}

// MARK: - Chat State
@MainActor
class ChatState: ObservableObject {
    @Published var messages: [ChatMessage] = []
    @Published var isProcessing = false

    private let ollamaClient = OllamaClient()
    private let mindbaseClient = MindBaseClient()

    func sendMessage(_ content: String, model: String) async {
        // Add user message
        let userMessage = ChatMessage(role: .user, content: content)
        messages.append(userMessage)
        isProcessing = true

        // 1. Search relevant context from MindBase (optional - continue on failure)
        var contexts: [String] = []
        do {
            contexts = try await mindbaseClient.searchContext(query: content)
        } catch {
            print("[MindBase] Context search failed (continuing without context): \(error)")
        }

        // 2. Build prompt with context
        let prompt = buildPrompt(userQuestion: content, contexts: contexts)

        // 3. Get response from Ollama
        do {
            let response = try await ollamaClient.chat(prompt: prompt, model: model)

            // 4. Add assistant message
            let assistantMessage = ChatMessage(
                role: .assistant,
                content: response,
                context: contexts
            )
            messages.append(assistantMessage)

            // 5. Save conversation to MindBase (optional - log on failure)
            do {
                try await mindbaseClient.saveConversation(
                    userMessage: content,
                    assistantMessage: response,
                    model: model,
                    contexts: contexts
                )
            } catch {
                print("[MindBase] Conversation save failed (non-critical): \(error)")
            }

        } catch {
            let errorMessage = ChatMessage(
                role: .assistant,
                content: "Ollama error: \(error.localizedDescription)\n\nMake sure Ollama is running and the model '\(model)' is available.\nRun: ollama pull \(model)"
            )
            messages.append(errorMessage)
        }

        isProcessing = false
    }

    private func buildPrompt(userQuestion: String, contexts: [String]) -> String {
        var prompt = ""

        if !contexts.isEmpty {
            prompt += "過去の会話履歴:\n"
            for (index, context) in contexts.enumerated() {
                prompt += "\(index + 1). \(context)\n"
            }
            prompt += "\n"
        }

        prompt += "質問: \(userQuestion)\n\n"
        if contexts.isEmpty {
            prompt += "質問に答えてください。"
        } else {
            prompt += "上記の過去会話を参考に、質問に答えてください。"
        }

        return prompt
    }
}

// MARK: - Models
struct ChatMessage: Identifiable {
    let id = UUID()
    let role: Role
    let content: String
    var context: [String] = []

    enum Role {
        case user
        case assistant
    }
}

// MARK: - Ollama Client
struct OllamaClient {
    /// Timeout for Ollama requests (30 seconds)
    private let timeoutInterval: TimeInterval = 30.0

    func chat(prompt: String, model: String) async throws -> String {
        guard let url = URL(string: AppConfig.ollamaGenerateURL) else {
            throw OllamaError.invalidURL
        }

        var request = URLRequest(url: url)
        request.httpMethod = "POST"
        request.setValue("application/json", forHTTPHeaderField: "Content-Type")
        request.timeoutInterval = timeoutInterval

        let body: [String: Any] = [
            "model": model,
            "prompt": prompt,
            "stream": false
        ]
        request.httpBody = try JSONSerialization.data(withJSONObject: body)

        let (data, response) = try await URLSession.shared.data(for: request)

        guard let httpResponse = response as? HTTPURLResponse else {
            throw OllamaError.invalidResponse
        }

        guard httpResponse.statusCode == 200 else {
            throw OllamaError.httpError(statusCode: httpResponse.statusCode)
        }

        let ollamaResponse = try JSONDecoder().decode(OllamaResponse.self, from: data)
        return ollamaResponse.response
    }

    /// Fetch available models from Ollama
    static func fetchModels() async throws -> [String] {
        guard let url = URL(string: AppConfig.ollamaTagsURL) else {
            throw OllamaError.invalidURL
        }

        var request = URLRequest(url: url)
        request.timeoutInterval = 10.0

        let (data, _) = try await URLSession.shared.data(for: request)
        let tagsResponse = try JSONDecoder().decode(OllamaTagsResponse.self, from: data)
        return tagsResponse.models.map { $0.name }
    }

    struct OllamaResponse: Codable {
        let response: String
    }

    struct OllamaTagsResponse: Codable {
        let models: [OllamaModel]
    }

    struct OllamaModel: Codable {
        let name: String
    }

    enum OllamaError: LocalizedError {
        case invalidURL
        case invalidResponse
        case httpError(statusCode: Int)

        var errorDescription: String? {
            switch self {
            case .invalidURL:
                return "Invalid Ollama URL"
            case .invalidResponse:
                return "Invalid response from Ollama"
            case .httpError(let statusCode):
                return "Ollama returned HTTP \(statusCode)"
            }
        }
    }
}

// MARK: - MindBase Client
struct MindBaseClient {
    /// Timeout for MindBase API requests (10 seconds)
    private let timeoutInterval: TimeInterval = 10.0

    func searchContext(query: String, limit: Int = 5) async throws -> [String] {
        guard let url = URL(string: AppConfig.mindbaseSearchURL) else {
            throw MindBaseError.invalidURL
        }

        var request = URLRequest(url: url)
        request.httpMethod = "POST"
        request.setValue("application/json", forHTTPHeaderField: "Content-Type")
        request.timeoutInterval = timeoutInterval

        let body: [String: Any] = [
            "query": query,
            "limit": limit,
            "threshold": 0.6
        ]
        request.httpBody = try JSONSerialization.data(withJSONObject: body)

        let (data, response) = try await URLSession.shared.data(for: request)

        guard let httpResponse = response as? HTTPURLResponse,
              httpResponse.statusCode == 200 else {
            throw MindBaseError.searchFailed
        }

        let searchResponse = try JSONDecoder().decode(SearchResponse.self, from: data)

        return searchResponse.results.map { result in
            "[\(result.source)] \(result.title) - \(result.content_preview)"
        }
    }

    func saveConversation(userMessage: String, assistantMessage: String, model: String, contexts: [String]) async throws {
        guard let url = URL(string: AppConfig.mindbaseStoreURL) else {
            throw MindBaseError.invalidURL
        }

        var request = URLRequest(url: url)
        request.httpMethod = "POST"
        request.setValue("application/json", forHTTPHeaderField: "Content-Type")
        request.timeoutInterval = timeoutInterval

        let body: [String: Any] = [
            "source": "mindbase-chat",
            "title": userMessage,
            "content": [
                "user": userMessage,
                "assistant": assistantMessage
            ],
            "metadata": [
                "model": model,
                "contexts_used": contexts.count
            ]
        ]
        request.httpBody = try JSONSerialization.data(withJSONObject: body)

        let (_, response) = try await URLSession.shared.data(for: request)

        guard let httpResponse = response as? HTTPURLResponse,
              httpResponse.statusCode == 200 || httpResponse.statusCode == 201 else {
            throw MindBaseError.saveFailed
        }
    }

    struct SearchResponse: Codable {
        let results: [SearchResult]
    }

    struct SearchResult: Codable {
        let source: String
        let title: String
        let content_preview: String
    }

    enum MindBaseError: LocalizedError {
        case invalidURL
        case searchFailed
        case saveFailed

        var errorDescription: String? {
            switch self {
            case .invalidURL:
                return "Invalid MindBase API URL"
            case .searchFailed:
                return "Failed to search conversations"
            case .saveFailed:
                return "Failed to save conversation"
            }
        }
    }
}
