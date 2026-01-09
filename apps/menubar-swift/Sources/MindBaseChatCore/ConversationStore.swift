import SwiftUI

// MARK: - Conversation Model

public struct Conversation: Identifiable, Codable, Equatable {
    public let id: UUID
    public var title: String
    public var messages: [StoredMessage]
    public var createdAt: Date
    public var updatedAt: Date

    public init(id: UUID = UUID(), title: String = "New Chat", messages: [StoredMessage] = [], createdAt: Date = Date(), updatedAt: Date = Date()) {
        self.id = id
        self.title = title
        self.messages = messages
        self.createdAt = createdAt
        self.updatedAt = updatedAt
    }

    public var preview: String {
        messages.first(where: { $0.role == .user })?.content.prefix(50).description ?? "Empty chat"
    }

    public static func == (lhs: Conversation, rhs: Conversation) -> Bool {
        lhs.id == rhs.id
    }
}

// MARK: - Stored Message (Codable version)

public struct StoredMessage: Identifiable, Codable, Equatable {
    public let id: UUID
    public let role: MessageRole
    public let content: String
    public let timestamp: Date
    public var ragContextCount: Int

    public init(id: UUID = UUID(), role: MessageRole, content: String, timestamp: Date = Date(), ragContextCount: Int = 0) {
        self.id = id
        self.role = role
        self.content = content
        self.timestamp = timestamp
        self.ragContextCount = ragContextCount
    }

    public enum MessageRole: String, Codable {
        case user
        case assistant
        case system
    }
}

// MARK: - Conversation Store

@MainActor
public final class ConversationStore: ObservableObject {
    @Published public var conversations: [Conversation] = []
    @Published public var selectedConversationId: UUID?

    private let saveKey = "mindbase.conversations"
    private let maxConversations = 50

    public init() {
        loadConversations()
    }

    // MARK: - Selected Conversation

    public var selectedConversation: Conversation? {
        guard let id = selectedConversationId else { return nil }
        return conversations.first { $0.id == id }
    }

    // MARK: - CRUD Operations

    public func createConversation() -> Conversation {
        let conversation = Conversation()
        conversations.insert(conversation, at: 0)
        selectedConversationId = conversation.id
        saveConversations()
        return conversation
    }

    public func selectConversation(_ id: UUID) {
        selectedConversationId = id
    }

    public func deleteConversation(_ id: UUID) {
        conversations.removeAll { $0.id == id }
        if selectedConversationId == id {
            selectedConversationId = conversations.first?.id
        }
        saveConversations()
    }

    public func updateConversation(_ id: UUID, messages: [StoredMessage]) {
        guard let index = conversations.firstIndex(where: { $0.id == id }) else { return }

        conversations[index].messages = messages
        conversations[index].updatedAt = Date()

        // Auto-generate title from first user message
        if conversations[index].title == "New Chat",
           let firstUserMessage = messages.first(where: { $0.role == .user }) {
            conversations[index].title = String(firstUserMessage.content.prefix(40))
        }

        // Move to top
        let conversation = conversations.remove(at: index)
        conversations.insert(conversation, at: 0)

        saveConversations()
    }

    public func renameConversation(_ id: UUID, title: String) {
        guard let index = conversations.firstIndex(where: { $0.id == id }) else { return }
        conversations[index].title = title
        conversations[index].updatedAt = Date()
        saveConversations()
    }

    // MARK: - Persistence

    private func saveConversations() {
        // Limit stored conversations
        let toSave = Array(conversations.prefix(maxConversations))

        if let data = try? JSONEncoder().encode(toSave) {
            UserDefaults.standard.set(data, forKey: saveKey)
        }
    }

    private func loadConversations() {
        guard let data = UserDefaults.standard.data(forKey: saveKey),
              let loaded = try? JSONDecoder().decode([Conversation].self, from: data) else {
            // Create initial conversation
            let initial = Conversation()
            conversations = [initial]
            selectedConversationId = initial.id
            return
        }

        conversations = loaded
        selectedConversationId = conversations.first?.id
    }

    public func clearAllConversations() {
        conversations.removeAll()
        let newConversation = createConversation()
        selectedConversationId = newConversation.id
    }
}

// MARK: - Conversion Helpers

extension ChatMessage {
    public func toStored() -> StoredMessage {
        StoredMessage(
            id: id,
            role: role == .user ? .user : (role == .assistant ? .assistant : .system),
            content: content,
            timestamp: timestamp,
            ragContextCount: ragContextCount
        )
    }
}

extension StoredMessage {
    public func toChatMessage() -> ChatMessage {
        ChatMessage(
            role: role == .user ? .user : (role == .assistant ? .assistant : .system),
            content: content,
            ragContextCount: ragContextCount
        )
    }
}
