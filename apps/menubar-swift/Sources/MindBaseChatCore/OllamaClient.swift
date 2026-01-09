import Foundation

// MARK: - Ollama Client (Swift 6 Concurrency Safe)

public actor OllamaClient {
    private let baseURL: URL
    private let session: URLSession

    public init(host: String = "http://127.0.0.1:11434") {
        self.baseURL = URL(string: host)!
        let config = URLSessionConfiguration.default
        config.timeoutIntervalForRequest = 300
        self.session = URLSession(configuration: config)
    }

    // MARK: - Models

    public func listModels() async throws -> [OllamaModel] {
        let url = baseURL.appendingPathComponent("api/tags")
        let (data, response) = try await session.data(from: url)

        guard let httpResponse = response as? HTTPURLResponse,
              httpResponse.statusCode == 200 else {
            throw OllamaError.invalidResponse
        }

        let result = try JSONDecoder().decode(OllamaModelsResponse.self, from: data)
        // Filter out embedding models (they can't be used for chat)
        return result.models.filter { !$0.isEmbeddingModel }
    }

    public func pullModel(_ name: String) async throws -> AsyncThrowingStream<OllamaPullProgress, Error> {
        let url = baseURL.appendingPathComponent("api/pull")
        var request = URLRequest(url: url)
        request.httpMethod = "POST"
        request.setValue("application/json", forHTTPHeaderField: "Content-Type")
        request.httpBody = try JSONEncoder().encode(["name": name])

        return AsyncThrowingStream { continuation in
            Task {
                do {
                    let (bytes, response) = try await self.session.bytes(for: request)

                    guard let httpResponse = response as? HTTPURLResponse,
                          httpResponse.statusCode == 200 else {
                        continuation.finish(throwing: OllamaError.invalidResponse)
                        return
                    }

                    for try await line in bytes.lines {
                        if let data = line.data(using: .utf8),
                           let progress = try? JSONDecoder().decode(OllamaPullProgress.self, from: data) {
                            continuation.yield(progress)
                            if progress.status == "success" {
                                break
                            }
                        }
                    }
                    continuation.finish()
                } catch {
                    continuation.finish(throwing: error)
                }
            }
        }
    }

    public func modelExists(_ name: String) async -> Bool {
        do {
            let models = try await listModels()
            return models.contains { $0.name == name || $0.name.hasPrefix(name + ":") }
        } catch {
            return false
        }
    }

    // MARK: - Chat (Streaming)

    public func chat(
        model: String,
        messages: [OllamaChatMessage],
        options: OllamaOptions? = nil
    ) -> AsyncThrowingStream<OllamaChatChunk, Error> {
        AsyncThrowingStream { continuation in
            Task {
                do {
                    let url = self.baseURL.appendingPathComponent("api/chat")
                    var request = URLRequest(url: url)
                    request.httpMethod = "POST"
                    request.setValue("application/json", forHTTPHeaderField: "Content-Type")

                    var body: [String: Any] = [
                        "model": model,
                        "messages": messages.map { $0.dictionary },
                        "stream": true
                    ]
                    if let options = options {
                        body["options"] = options.dictionary
                    }

                    request.httpBody = try JSONSerialization.data(withJSONObject: body)

                    let (bytes, response) = try await self.session.bytes(for: request)

                    guard let httpResponse = response as? HTTPURLResponse else {
                        continuation.finish(throwing: OllamaError.invalidResponse)
                        return
                    }

                    if httpResponse.statusCode != 200 {
                        continuation.finish(throwing: OllamaError.httpError(httpResponse.statusCode))
                        return
                    }

                    for try await line in bytes.lines {
                        if Task.isCancelled {
                            continuation.finish()
                            return
                        }

                        if let data = line.data(using: .utf8),
                           let chunk = try? JSONDecoder().decode(OllamaChatChunk.self, from: data) {
                            continuation.yield(chunk)
                            if chunk.done {
                                break
                            }
                        }
                    }
                    continuation.finish()
                } catch {
                    continuation.finish(throwing: error)
                }
            }
        }
    }

    public func isReachable() async -> Bool {
        do {
            _ = try await listModels()
            return true
        } catch {
            return false
        }
    }
}

// MARK: - Models

public struct OllamaModel: Codable, Sendable {
    public let name: String
    public let modifiedAt: String?
    public let size: Int64?

    enum CodingKeys: String, CodingKey {
        case name
        case modifiedAt = "modified_at"
        case size
    }

    public var displayName: String {
        name.replacingOccurrences(of: ":latest", with: "")
    }

    public var sizeFormatted: String {
        guard let size = size else { return "" }
        let gb = Double(size) / 1_000_000_000
        return String(format: "%.1fGB", gb)
    }

    public var isEmbeddingModel: Bool {
        let embeddingKeywords = ["embed", "embedding", "nomic-embed"]
        let lowerName = name.lowercased()
        return embeddingKeywords.contains { lowerName.contains($0) }
    }
}

struct OllamaModelsResponse: Codable, Sendable {
    let models: [OllamaModel]
}

public struct OllamaPullProgress: Codable, Sendable {
    public let status: String
    public let digest: String?
    public let total: Int64?
    public let completed: Int64?

    public var progress: Double {
        guard let total = total, let completed = completed, total > 0 else { return 0 }
        return Double(completed) / Double(total)
    }
}

// MARK: - Chat

public struct OllamaChatMessage: Sendable {
    public let role: String
    public let content: String

    public init(role: String, content: String) {
        self.role = role
        self.content = content
    }

    public var dictionary: [String: String] {
        ["role": role, "content": content]
    }
}

public struct OllamaChatChunk: Codable, Sendable {
    public let model: String?
    public let message: OllamaChatMessageResponse?
    public let done: Bool

    public struct OllamaChatMessageResponse: Codable, Sendable {
        public let role: String
        public let content: String
    }
}

// MARK: - Options

public struct OllamaOptions: Sendable {
    public var temperature: Double
    public var topP: Double
    public var topK: Int
    public var numPredict: Int

    public init(temperature: Double = 0.7, topP: Double = 0.9, topK: Int = 40, numPredict: Int = 2048) {
        self.temperature = temperature
        self.topP = topP
        self.topK = topK
        self.numPredict = numPredict
    }

    public var dictionary: [String: Any] {
        [
            "temperature": temperature,
            "top_p": topP,
            "top_k": topK,
            "num_predict": numPredict
        ]
    }
}

// MARK: - Errors

public enum OllamaError: LocalizedError, Sendable {
    case invalidResponse
    case httpError(Int)
    case notReachable
    case modelNotFound(String)

    public var errorDescription: String? {
        switch self {
        case .invalidResponse:
            return "Invalid response from Ollama"
        case .httpError(let code):
            return "HTTP error: \(code)"
        case .notReachable:
            return "Ollama is not running. Please start Ollama first."
        case .modelNotFound(let name):
            return "Model '\(name)' not found. Pull it first."
        }
    }
}
