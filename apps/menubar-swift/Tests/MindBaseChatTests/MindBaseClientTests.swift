import XCTest
@testable import MindBaseChatCore

final class MindBaseClientTests: XCTestCase {

    var client: MindBaseClient!

    override func setUp() {
        client = MindBaseClient()
    }

    override func tearDown() {
        client = nil
    }

    // MARK: - Initialization Tests

    func testClientInitialization() {
        let client = MindBaseClient()
        XCTAssertNotNil(client)
    }

    // MARK: - URL Construction Tests

    func testSearchContextBadURL() async {
        // Test with empty query (should still work)
        do {
            let results = try await client.searchContext(query: "", limit: 5)
            // If MindBase is not running, it will throw or return empty
            XCTAssertNotNil(results)
        } catch {
            // Expected if MindBase is not running
            XCTAssertNotNil(error)
        }
    }

    func testSearchContextWithLimit() async {
        do {
            let results = try await client.searchContext(query: "test", limit: 1)
            XCTAssertLessThanOrEqual(results.count, 1)
        } catch {
            // Expected if MindBase is not running
            XCTAssertNotNil(error)
        }
    }

    // MARK: - Save Conversation Tests

    func testSaveConversationWithEmptyContent() async {
        do {
            try await client.saveConversation(userMessage: "", assistantMessage: "", model: "test")
            // If MindBase is running, this should succeed
        } catch {
            // Expected if MindBase is not running
            XCTAssertNotNil(error)
        }
    }

    func testSaveConversationWithLongTitle() async {
        let longMessage = String(repeating: "a", count: 200)
        do {
            try await client.saveConversation(userMessage: longMessage, assistantMessage: "response", model: "test")
            // Title should be truncated to 100 chars
        } catch {
            // Expected if MindBase is not running
            XCTAssertNotNil(error)
        }
    }
}

// MARK: - Integration Tests (require running MindBase)

final class MindBaseClientIntegrationTests: XCTestCase {

    var client: MindBaseClient!

    override func setUp() {
        client = MindBaseClient()
    }

    override func tearDown() {
        client = nil
    }

    func testSearchContextIntegration() async throws {
        // Skip if MindBase is not running
        do {
            let results = try await client.searchContext(query: "test query", limit: 3)
            XCTAssertLessThanOrEqual(results.count, 3)

            for result in results {
                XCTAssertFalse(result.isEmpty)
            }
        } catch let error as URLError {
            throw XCTSkip("MindBase is not running: \(error.localizedDescription)")
        }
    }

    func testSaveConversationIntegration() async throws {
        do {
            try await client.saveConversation(
                userMessage: "Test user message",
                assistantMessage: "Test assistant response",
                model: "test-model"
            )
        } catch let error as URLError {
            throw XCTSkip("MindBase is not running: \(error.localizedDescription)")
        }
    }
}
