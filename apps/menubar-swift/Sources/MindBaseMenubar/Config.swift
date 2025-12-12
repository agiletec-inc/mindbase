import Foundation

/// App configuration loaded from environment variables
/// Following CLAUDE.md guidelines: NEVER hardcode ports, URLs, or connection strings
enum AppConfig {
    /// Ollama API URL (default: http://localhost:11434)
    static var ollamaURL: String {
        ProcessInfo.processInfo.environment["OLLAMA_URL"] ?? "http://localhost:11434"
    }

    /// Default Ollama model for chat (default: qwen2.5:3b)
    static var defaultModel: String {
        ProcessInfo.processInfo.environment["OLLAMA_MODEL"] ?? "qwen2.5:3b"
    }

    /// MindBase API URL (default: http://localhost:18003)
    static var mindbaseAPIURL: String {
        ProcessInfo.processInfo.environment["MINDBASE_API_URL"] ?? "http://localhost:18003"
    }

    /// Ollama generate endpoint
    static var ollamaGenerateURL: String {
        "\(ollamaURL)/api/generate"
    }

    /// Ollama tags endpoint (for listing models)
    static var ollamaTagsURL: String {
        "\(ollamaURL)/api/tags"
    }

    /// MindBase health endpoint
    static var mindbaseHealthURL: String {
        "\(mindbaseAPIURL)/health"
    }

    /// MindBase conversations search endpoint
    static var mindbaseSearchURL: String {
        "\(mindbaseAPIURL)/conversations/search"
    }

    /// MindBase conversations store endpoint
    static var mindbaseStoreURL: String {
        "\(mindbaseAPIURL)/conversations/store"
    }

    /// MindBase API docs URL
    static var mindbaseDocsURL: String {
        "\(mindbaseAPIURL)/docs"
    }
}
