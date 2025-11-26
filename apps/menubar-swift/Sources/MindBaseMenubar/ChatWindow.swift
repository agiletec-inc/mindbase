import SwiftUI

// MARK: - Chat Window
struct ChatWindow: View {
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
                Text("qwen2.5:3b")
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
            await chatState.sendMessage(userMessage)
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

    func sendMessage(_ content: String) async {
        // Add user message
        let userMessage = ChatMessage(role: .user, content: content)
        messages.append(userMessage)
        isProcessing = true

        do {
            // 1. Search relevant context from MindBase
            let contexts = try await mindbaseClient.searchContext(query: content)

            // 2. Build prompt with context
            let prompt = buildPrompt(userQuestion: content, contexts: contexts)

            // 3. Get response from Ollama
            let response = try await ollamaClient.chat(prompt: prompt, model: "qwen2.5:3b")

            // 4. Add assistant message
            let assistantMessage = ChatMessage(
                role: .assistant,
                content: response,
                context: contexts
            )
            messages.append(assistantMessage)

            // 5. Save conversation to MindBase
            try await mindbaseClient.saveConversation(
                userMessage: content,
                assistantMessage: response,
                contexts: contexts
            )

        } catch {
            let errorMessage = ChatMessage(
                role: .assistant,
                content: "Error: \(error.localizedDescription)"
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
        prompt += "上記の過去会話を参考に、質問に答えてください。"

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
    func chat(prompt: String, model: String) async throws -> String {
        let url = URL(string: "http://localhost:11434/api/generate")!
        var request = URLRequest(url: url)
        request.httpMethod = "POST"
        request.setValue("application/json", forHTTPHeaderField: "Content-Type")

        let body: [String: Any] = [
            "model": model,
            "prompt": prompt,
            "stream": false
        ]
        request.httpBody = try JSONSerialization.data(withJSONObject: body)

        let (data, _) = try await URLSession.shared.data(for: request)
        let response = try JSONDecoder().decode(OllamaResponse.self, from: data)
        return response.response
    }

    struct OllamaResponse: Codable {
        let response: String
    }
}

// MARK: - MindBase Client
struct MindBaseClient {
    func searchContext(query: String, limit: Int = 5) async throws -> [String] {
        let url = URL(string: "http://localhost:18002/conversations/search")!
        var request = URLRequest(url: url)
        request.httpMethod = "POST"
        request.setValue("application/json", forHTTPHeaderField: "Content-Type")

        let body: [String: Any] = [
            "query": query,
            "limit": limit,
            "threshold": 0.6
        ]
        request.httpBody = try JSONSerialization.data(withJSONObject: body)

        let (data, _) = try await URLSession.shared.data(for: request)
        let response = try JSONDecoder().decode(SearchResponse.self, from: data)

        return response.results.map { result in
            "[\(result.source)] \(result.title) - \(result.content_preview)"
        }
    }

    func saveConversation(userMessage: String, assistantMessage: String, contexts: [String]) async throws {
        let url = URL(string: "http://localhost:18002/conversations/store")!
        var request = URLRequest(url: url)
        request.httpMethod = "POST"
        request.setValue("application/json", forHTTPHeaderField: "Content-Type")

        let body: [String: Any] = [
            "source": "mindbase-chat",
            "title": userMessage,
            "content": [
                "user": userMessage,
                "assistant": assistantMessage
            ],
            "metadata": [
                "model": "qwen2.5:3b",
                "contexts_used": contexts.count
            ]
        ]
        request.httpBody = try JSONSerialization.data(withJSONObject: body)

        _ = try await URLSession.shared.data(for: request)
    }

    struct SearchResponse: Codable {
        let results: [SearchResult]
    }

    struct SearchResult: Codable {
        let source: String
        let title: String
        let content_preview: String
    }
}
