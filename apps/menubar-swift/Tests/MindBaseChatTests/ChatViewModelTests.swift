import XCTest
@testable import MindBaseChatCore

@MainActor
final class ChatViewModelTests: XCTestCase {

    var viewModel: ChatViewModel!

    override func setUp() async throws {
        viewModel = ChatViewModel()
        viewModel.clearChat()
    }

    override func tearDown() async throws {
        viewModel.stop()
        viewModel = nil
    }

    // MARK: - Initial State Tests

    func testInitialState() {
        XCTAssertTrue(viewModel.messages.isEmpty)
        XCTAssertEqual(viewModel.streamingText, "")
        XCTAssertFalse(viewModel.isStreaming)
        XCTAssertNil(viewModel.error)
    }

    func testDefaultSettings() {
        XCTAssertEqual(viewModel.temperature, 0.7)
        XCTAssertEqual(viewModel.maxTokens, 2048)
        XCTAssertFalse(viewModel.systemPrompt.isEmpty)
    }

    // MARK: - Message Tests

    func testSendEmptyMessage() {
        viewModel.send("")
        XCTAssertTrue(viewModel.messages.isEmpty)

        viewModel.send("   ")
        XCTAssertTrue(viewModel.messages.isEmpty)

        viewModel.send("\n\t")
        XCTAssertTrue(viewModel.messages.isEmpty)
    }

    func testSendValidMessage() {
        viewModel.send("Hello")

        XCTAssertEqual(viewModel.messages.count, 1)
        XCTAssertEqual(viewModel.messages.first?.role, .user)
        XCTAssertEqual(viewModel.messages.first?.content, "Hello")
    }

    func testSendMultipleMessages() {
        viewModel.send("First message")
        viewModel.stop()

        viewModel.send("Second message")
        viewModel.stop()

        let userMessages = viewModel.messages.filter { $0.role == .user }
        XCTAssertEqual(userMessages.count, 2)
    }

    // MARK: - Clear Chat Tests

    func testClearChat() {
        viewModel.send("Test message")
        viewModel.stop()

        XCTAssertFalse(viewModel.messages.isEmpty)

        viewModel.clearChat()

        XCTAssertTrue(viewModel.messages.isEmpty)
        XCTAssertEqual(viewModel.streamingText, "")
        XCTAssertFalse(viewModel.isStreaming)
        XCTAssertNil(viewModel.error)
    }

    // MARK: - Stop Tests

    func testStopWithStreamingText() {
        viewModel.send("Test")
        viewModel.streamingText = "Partial response"
        viewModel.isStreaming = true

        viewModel.stop()

        XCTAssertFalse(viewModel.isStreaming)
        XCTAssertEqual(viewModel.streamingText, "")

        let assistantMessages = viewModel.messages.filter { $0.role == .assistant }
        XCTAssertEqual(assistantMessages.count, 1)
        XCTAssertTrue(assistantMessages.first?.content.contains("[stopped]") ?? false)
    }

    func testStopWithoutStreamingText() {
        viewModel.isStreaming = true
        viewModel.streamingText = ""

        viewModel.stop()

        XCTAssertFalse(viewModel.isStreaming)
        XCTAssertTrue(viewModel.messages.filter { $0.role == .assistant }.isEmpty)
    }

    // MARK: - Retry Tests

    func testRetryWithNoMessages() {
        let initialCount = viewModel.messages.count
        viewModel.retry()
        XCTAssertEqual(viewModel.messages.count, initialCount)
    }

    func testRetryRemovesLastExchange() {
        viewModel.messages.append(ChatMessage(role: .user, content: "Question"))
        viewModel.messages.append(ChatMessage(role: .assistant, content: "Answer"))

        XCTAssertEqual(viewModel.messages.count, 2)

        viewModel.retry()
        viewModel.stop()

        let userMessages = viewModel.messages.filter { $0.role == .user }
        XCTAssertEqual(userMessages.count, 1)
    }

    // MARK: - Model Selection Tests

    func testSelectModel() {
        let model = OllamaModel(name: "llama3:8b", modifiedAt: nil, size: nil)
        viewModel.selectModel(model)

        XCTAssertEqual(viewModel.selectedModel, "llama3:8b")
    }
}

// MARK: - ChatMessage Tests

final class ChatMessageTests: XCTestCase {

    func testChatMessageCreation() {
        let message = ChatMessage(role: .user, content: "Hello")

        XCTAssertEqual(message.role, .user)
        XCTAssertEqual(message.content, "Hello")
        XCTAssertEqual(message.ragContextCount, 0)
        XCTAssertNotNil(message.id)
        XCTAssertNotNil(message.timestamp)
    }

    func testChatMessageWithRAGContext() {
        let message = ChatMessage(role: .assistant, content: "Response", ragContextCount: 3)

        XCTAssertEqual(message.role, .assistant)
        XCTAssertEqual(message.ragContextCount, 3)
    }

    func testChatMessageEquality() {
        let message1 = ChatMessage(role: .user, content: "Hello")
        let message2 = ChatMessage(role: .user, content: "Hello")

        XCTAssertNotEqual(message1, message2)
        XCTAssertEqual(message1, message1)
    }

    func testChatMessageRoles() {
        let user = ChatMessage(role: .user, content: "")
        let assistant = ChatMessage(role: .assistant, content: "")
        let system = ChatMessage(role: .system, content: "")

        XCTAssertEqual(user.role, .user)
        XCTAssertEqual(assistant.role, .assistant)
        XCTAssertEqual(system.role, .system)
    }
}
